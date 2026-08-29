"""
Centralized unknown-person de-duplication + conversion service.

Each distinct Unknown identity gets exactly ONE dedicated folder:
    data/snapshots/unknown/Unknown-001/snapshot_<timestamp>.webp
    data/snapshots/unknown/Unknown-001/snapshot_<timestamp>.webp
    ...
Every subsequent sighting of that same person (any camera, any time) adds
another file into that SAME folder — never a new folder, never a new ID —
as long as the embedding matches within UNKNOWN_PERSON_DISTANCE_THRESHOLD.
"""
import os
import time
import shutil
import cv2
import numpy as np
from datetime import datetime
from sqlalchemy import text, select, func
from sqlalchemy.orm import Session

from app.models import UnknownPerson, UnknownEmbedding, UnknownSighting, KnownFace, FaceEmbedding
from app.config import settings
from app.face_quality import _variance_of_laplacian

# Any fixed 64-bit key works here - it only needs to be the same key on
# every call so pg_advisory_xact_lock() serializes match-or-create across
# every camera worker / process talking to this database.
_DEDUP_LOCK_KEY = 913_223_001

# Max reference photos kept per registered known person (same FIFO cap as
# the Known/Unknown Identification spec's manual "Make Known" flow).
MAX_FACE_IMAGES = 4

# Sharpness floor for "clear" (variance-of-laplacian). Kept local instead of
# reading from settings.MIN_BLUR_SCORE, since that attribute name doesn't
# exist in this project's config.py — avoids a config mismatch crash.
_MIN_BLUR_SCORE = 50.0


def _cosine_distance(embedding: np.ndarray, stored_vector) -> float:
    stored = np.array(stored_vector, dtype=np.float32)
    cos_sim = np.dot(embedding, stored) / (
        np.linalg.norm(embedding) * np.linalg.norm(stored) + 1e-8
    )
    return float(1 - cos_sim)


def _nearest_by_sighting_embeddings(embedding: np.ndarray, db: Session):
    """
    Nearest match across every stored per-sighting embedding, for every
    identity. This is the primary/growing match path: the more times a
    person is seen, the more angles/lighting conditions are on file for
    them, so later sightings keep finding a close-enough match.
    """
    row = db.execute(
        select(UnknownEmbedding)
        .order_by(UnknownEmbedding.vector.cosine_distance(embedding))
        .limit(1)
    ).scalars().first()
    if row is None:
        return None, None
    return row.unknown_person_id, _cosine_distance(embedding, row.vector)


def _nearest_by_reference_embedding(embedding: np.ndarray, db: Session):
    """
    Nearest match via each identity's original single reference_embedding.
    Covers identities created before per-sighting embeddings were tracked
    (so older Unknown-NNN rows don't get orphaned/duplicated after this
    upgrade) — safe to keep running alongside the check above indefinitely.
    """
    row = db.execute(
        select(UnknownPerson)
        .order_by(UnknownPerson.reference_embedding.cosine_distance(embedding))
        .limit(1)
    ).scalars().first()
    if row is None:
        return None, None
    return row.id, _cosine_distance(embedding, row.reference_embedding)


def _unknown_folder(unknown_id: int) -> str:
    return f"{settings.SNAPSHOT_DIR}/unknown/Unknown-{unknown_id:03d}"


def _save_snapshot_into(folder: str, camera_name: str, frame: np.ndarray) -> str:
    """
    Saves as WebP (smaller files than JPEG at similar visual quality). If
    this particular OpenCV build lacks WebP encoder support, imwrite()
    returns False instead of raising — in that case we fall back to JPEG
    so a snapshot never silently fails to save.
    """
    os.makedirs(folder, exist_ok=True)
    # Timestamp-based filename keeps every snapshot unique, so repeated
    # sightings never overwrite each other inside the same folder.
    filename = f"{camera_name}_{int(time.time()*1000)}.webp"
    path = f"{folder}/{filename}"
    success = cv2.imwrite(path, frame, [cv2.IMWRITE_WEBP_QUALITY, 90])
    if not success:
        filename = f"{camera_name}_{int(time.time()*1000)}.jpg"
        path = f"{folder}/{filename}"
        cv2.imwrite(path, frame)
    return path


def resolve_unknown_person(
    embedding: np.ndarray,
    frame: np.ndarray,
    db: Session,
    camera_name: str,
) -> tuple[UnknownPerson, bool]:
    """
    Compares `embedding` against stored unknown_person reference embeddings.
    The snapshot is saved AFTER the match decision, directly into that
    person's dedicated folder (Unknown-001, Unknown-002, ...) — never into
    a temp/flat location first, so there's no risk of a mismatched path.

    Returns (unknown_person, is_new_identity):
      - Match found  -> reuses the SAME Unknown-NNN folder, updates
        last_seen + representative snapshot, inserts an unknown_sighting
        row, returns (existing_person, False).
      - No match     -> creates a new unknown_person row + its own new
        Unknown-NNN folder, returns (new_person, True).
    """
    now = datetime.utcnow()

    # Serialize the whole match-or-create step across every camera worker.
    # Released automatically at transaction end (commit below).
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _DEDUP_LOCK_KEY})

    # Check both match paths and keep whichever candidate is actually closer.
    pid_a, dist_a = _nearest_by_sighting_embeddings(embedding, db)
    pid_b, dist_b = _nearest_by_reference_embedding(embedding, db)

    best_person_id, best_distance = None, None
    for pid, dist in ((pid_a, dist_a), (pid_b, dist_b)):
        if pid is not None and (best_distance is None or dist < best_distance):
            best_person_id, best_distance = pid, dist

    matched_person = None
    if best_person_id is not None and best_distance <= settings.UNKNOWN_PERSON_DISTANCE_THRESHOLD:
        matched_person = db.query(UnknownPerson).filter(UnknownPerson.id == best_person_id).first()

    if matched_person is not None:
        snapshot_path = _save_snapshot_into(_unknown_folder(matched_person.id), camera_name, frame)
        matched_person.last_seen = now
        matched_person.representative_snapshot_path = snapshot_path
        db.add(
            UnknownSighting(
                unknown_person_id=matched_person.id,
                camera_name=camera_name,
                snapshot_path=snapshot_path,
                timestamp=now,
            )
        )
        # Bank this sighting's embedding too, so the identity keeps getting
        # richer/easier to match on future, differently-angled sightings.
        db.add(
            UnknownEmbedding(
                unknown_person_id=matched_person.id,
                vector=embedding,
                snapshot_path=snapshot_path,
                created_at=now,
            )
        )
        db.commit()
        db.refresh(matched_person)
        return matched_person, False

    new_person = UnknownPerson(
        reference_embedding=embedding,
        first_seen=now,
        last_seen=now,
    )
    db.add(new_person)
    db.flush()  # assigns new_person.id — needed before we know its folder name

    snapshot_path = _save_snapshot_into(_unknown_folder(new_person.id), camera_name, frame)
    new_person.representative_snapshot_path = snapshot_path

    db.add(
        UnknownSighting(
            unknown_person_id=new_person.id,
            camera_name=camera_name,
            snapshot_path=snapshot_path,
            timestamp=now,
        )
    )
    db.add(
        UnknownEmbedding(
            unknown_person_id=new_person.id,
            vector=embedding,
            snapshot_path=snapshot_path,
            created_at=now,
        )
    )
    db.commit()
    db.refresh(new_person)
    return new_person, True


def _score_snapshot(path: str) -> float:
    """Reuses the same sharpness metric as face_quality.py's clarity gate,
    so 'clear' here means the same thing it means everywhere else in the
    app, not a new/different definition."""
    frame = cv2.imread(path)
    if frame is None:
        return -1.0
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return _variance_of_laplacian(gray)


def promote_to_known(unknown_person_id: int, name: str, db: Session) -> KnownFace:
    """
    Converts an unknown_person identity into a registered known_face.

      - If a KnownFace with this name ALREADY exists, reuses it instead of
        creating a duplicate — the new photo is added to that existing
        person's set (this is the fix for "two Alishba Khan entries").
      - Only ONE unknown snapshot is kept per conversion: the CLEAREST,
        MOST RECENT one on file — scored with the same sharpness metric
        used by face_quality.py's clarity gate — not every sighting.
      - A hard cap of MAX_FACE_IMAGES (4) reference photos per known
        person is enforced: once full, adding the new photo evicts the
        OLDEST existing one (by FaceEmbedding.added_at), matching the
        FIFO rule from the Known/Unknown Identification spec.
      - Every other unknown snapshot (not selected) is discarded along
        with the now-retired Unknown-NNN folder — the unknown_person row
        is deleted either way, so nothing is left orphaned on disk or in
        the DB.

    Raises ValueError if the unknown_person_id doesn't exist.
    """
    unknown_person = db.query(UnknownPerson).filter(UnknownPerson.id == unknown_person_id).first()
    if unknown_person is None:
        raise ValueError("unknown_person not found")

    normalized_name = name.strip()

    # Reuse an existing person with the same name (case-insensitive) instead
    # of creating a duplicate KnownFace row.
    known_face = (
        db.query(KnownFace)
        .filter(func.lower(KnownFace.name) == normalized_name.lower())
        .first()
    )
    is_new_known_face = known_face is None
    if known_face is None:
        known_face = KnownFace(name=normalized_name)
        db.add(known_face)
        db.flush()  # assigns known_face.id

    known_dir = f"{settings.SNAPSHOT_DIR}/known/{normalized_name}_{known_face.id}"
    os.makedirs(known_dir, exist_ok=True)

    unknown_dir = _unknown_folder(unknown_person.id)
    # Snapshot -> embedding pairing: every resolve_unknown_person() match
    # inserts exactly one UnknownSighting (a file) and one UnknownEmbedding
    # together, so the two lists stay 1:1 and chronologically aligned.
    stored_embeddings = list(unknown_person.embeddings)  # ordered by id (chronological)

    # Gather every candidate photo with its embedding + sharpness score.
    candidates = []
    if os.path.isdir(unknown_dir):
        files = sorted(f for f in os.listdir(unknown_dir) if os.path.isfile(os.path.join(unknown_dir, f)))
        for idx, fname in enumerate(files):
            src = os.path.join(unknown_dir, fname)
            vector = (
                stored_embeddings[idx].vector
                if idx < len(stored_embeddings)
                else unknown_person.reference_embedding
            )
            candidates.append({
                "src": src,
                "vector": vector,
                "quality": _score_snapshot(src),
                "mtime": os.path.getmtime(src),
            })
    elif unknown_person.representative_snapshot_path and os.path.exists(
        unknown_person.representative_snapshot_path
    ):
        # Backward-compat fallback for identities created before this
        # per-folder layout existed.
        src = unknown_person.representative_snapshot_path
        candidates.append({
            "src": src,
            "vector": unknown_person.reference_embedding,
            "quality": _score_snapshot(src),
            "mtime": os.path.getmtime(src),
        })

    # "Clear and latest": newest first, pick the first one that meets the
    # sharpness floor. If NONE meet it, fall back to the single sharpest
    # candidate rather than ending up with zero photos for a real
    # conversion. Only ONE photo is ever selected here — not the whole set.
    candidates.sort(key=lambda c: c["mtime"], reverse=True)
    qualified = [c for c in candidates if c["quality"] >= _MIN_BLUR_SCORE]
    if qualified:
        best_candidate = qualified[0]  # newest among the clear ones
    elif candidates:
        best_candidate = max(candidates, key=lambda c: c["quality"])  # sharpest available, as a fallback
    else:
        best_candidate = None
    clear_candidates = [best_candidate] if best_candidate else []

    # Current photo set for this known person, oldest first, so we know
    # exactly how much room is left before FIFO eviction kicks in.
    existing_embeddings = (
        db.query(FaceEmbedding)
        .filter(FaceEmbedding.face_id == known_face.id)
        .order_by(FaceEmbedding.added_at.asc())
        .all()
    )

    moved_count = 0
    cover_photo_path = known_face.photo_path  # keep current cover unless we set a new one below
    for candidate in clear_candidates:
        if len(existing_embeddings) >= MAX_FACE_IMAGES:
            oldest = existing_embeddings.pop(0)  # FIFO: oldest by added_at, per the spec
            if oldest.photo_path and os.path.exists(oldest.photo_path):
                try:
                    os.remove(oldest.photo_path)
                except OSError:
                    pass
            db.delete(oldest)
            db.flush()

        dst = os.path.join(known_dir, os.path.basename(candidate["src"]))
        shutil.move(candidate["src"], dst)
        new_embedding = FaceEmbedding(face_id=known_face.id, vector=candidate["vector"], photo_path=dst)
        db.add(new_embedding)
        db.flush()
        existing_embeddings.append(new_embedding)
        cover_photo_path = dst
        moved_count += 1

    # Discard anything left in the unknown folder that wasn't selected
    # (the rest of the sightings) — this identity is being retired regardless.
    if os.path.isdir(unknown_dir):
        for fname in os.listdir(unknown_dir):
            fpath = os.path.join(unknown_dir, fname)
            if os.path.isfile(fpath):
                try:
                    os.remove(fpath)
                except OSError:
                    pass
        try:
            os.rmdir(unknown_dir)
        except OSError:
            pass

    if moved_count == 0 and is_new_known_face:
        # No usable photo at all for a brand-new person — still seed one
        # embedding so they're recognizable, just with no photo attached.
        db.add(FaceEmbedding(
            face_id=known_face.id, vector=unknown_person.reference_embedding, photo_path=None
        ))

    if cover_photo_path:
        known_face.photo_path = cover_photo_path

    db.delete(unknown_person)  # cascades to unknown_sighting rows
    db.commit()
    db.refresh(known_face)
    return known_face