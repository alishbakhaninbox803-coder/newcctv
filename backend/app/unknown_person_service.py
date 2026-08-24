"""
Centralized unknown-person de-duplication + conversion service.

Each distinct Unknown identity gets exactly ONE dedicated folder:
    data/snapshots/unknown/Unknown-001/snapshot_<timestamp>.jpg
    data/snapshots/unknown/Unknown-001/snapshot_<timestamp>.jpg
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
from sqlalchemy import text, select
from sqlalchemy.orm import Session

from app.models import UnknownPerson, UnknownEmbedding, UnknownSighting, KnownFace, FaceEmbedding
from app.config import settings

# Any fixed 64-bit key works here - it only needs to be the same key on
# every call so pg_advisory_xact_lock() serializes match-or-create across
# every camera worker / process talking to this database.
_DEDUP_LOCK_KEY = 913_223_001


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
    os.makedirs(folder, exist_ok=True)
    # Timestamp-based filename keeps every snapshot unique, so repeated
    # sightings never overwrite each other inside the same folder.
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


def promote_to_known(unknown_person_id: int, name: str, db: Session) -> KnownFace:
    """
    Converts an unknown_person identity into a registered, named known_face.

      - Creates a new KnownFace(name=...).
      - Moves EVERY file out of unknown/Unknown-NNN/ into a new dedicated
        known/{name}_{known_face.id}/ folder (not just the representative
        snapshot) — matching the multi-photo registration pattern, each
        moved photo gets its own FaceEmbedding row (all seeded with the
        same reference_embedding, since only one embedding was ever
        computed for this identity) so `photo_count` in the UI is accurate
        and every photo is individually viewable, exactly like manually-
        registered known faces.
      - Deletes the now-empty Unknown-NNN folder and the unknown_person row
        (unknown_sighting history cascades away with it — that history no
        longer applies, the person is now a known, named individual).

    Raises ValueError if the unknown_person_id doesn't exist.
    """
    unknown_person = db.query(UnknownPerson).filter(UnknownPerson.id == unknown_person_id).first()
    if unknown_person is None:
        raise ValueError("unknown_person not found")

    known_face = KnownFace(name=name)
    db.add(known_face)
    db.flush()  # assigns known_face.id

    known_dir = f"{settings.SNAPSHOT_DIR}/known/{name}_{known_face.id}"
    os.makedirs(known_dir, exist_ok=True)

    unknown_dir = _unknown_folder(unknown_person.id)
    cover_photo_path = None
    moved_count = 0

    # Snapshot -> embedding pairing: every resolve_unknown_person() match
    # inserts exactly one UnknownSighting (a file) and one UnknownEmbedding
    # together, so the two lists stay 1:1 and chronologically aligned.
    stored_embeddings = list(unknown_person.embeddings)  # ordered by id (chronological)

    if os.path.isdir(unknown_dir):
        files = sorted(f for f in os.listdir(unknown_dir) if os.path.isfile(os.path.join(unknown_dir, f)))
        for idx, fname in enumerate(files):
            src = os.path.join(unknown_dir, fname)
            dst = os.path.join(known_dir, fname)
            shutil.move(src, dst)
            # Use this sighting's own embedding when we have one on file;
            # fall back to the identity's original reference embedding for
            # any file left over from before per-sighting embeddings existed.
            vector = (
                stored_embeddings[idx].vector
                if idx < len(stored_embeddings)
                else unknown_person.reference_embedding
            )
            db.add(
                FaceEmbedding(
                    face_id=known_face.id,
                    vector=vector,
                    photo_path=dst,
                )
            )
            cover_photo_path = dst
            moved_count += 1
        try:
            os.rmdir(unknown_dir)  # now empty — remove the folder itself
        except OSError:
            pass
    elif unknown_person.representative_snapshot_path and os.path.exists(
        unknown_person.representative_snapshot_path
    ):
        # Backward-compat fallback for identities created before this
        # per-folder layout existed.
        src = unknown_person.representative_snapshot_path
        dst = os.path.join(known_dir, os.path.basename(src))
        shutil.move(src, dst)
        db.add(
            FaceEmbedding(
                face_id=known_face.id,
                vector=unknown_person.reference_embedding,
                photo_path=dst,
            )
        )
        cover_photo_path = dst
        moved_count = 1

    if moved_count == 0:
        # No files existed on disk at all — still seed one embedding so the
        # person is recognizable, just with no photo attached.
        db.add(
            FaceEmbedding(
                face_id=known_face.id,
                vector=unknown_person.reference_embedding,
                photo_path=None,
            )
        )

    known_face.photo_path = cover_photo_path

    db.delete(unknown_person)  # cascades to unknown_sighting rows
    db.commit()
    db.refresh(known_face)
    return known_face