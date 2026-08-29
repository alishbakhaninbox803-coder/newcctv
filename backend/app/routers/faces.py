import os
import cv2
import numpy as np
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnownFace, FaceEmbedding
from app.schemas import KnownFaceOut
from app.face_engine import extract_faces
from app.config import settings
from app.auth import get_current_user

router = APIRouter(tags=["Faces"])

# Same FIFO cap used by the Unknown-person conversion flow, kept consistent
# so a person never ends up with more reference photos from one path than
# the other.
MAX_FACE_IMAGES = 4


@router.post("/register-face", response_model=KnownFaceOut)
async def register_face(
    name: str = Form(...),
    company: str = Form(None),
    branch: str = Form(None),
    role: str = Form(None),
    files: list[UploadFile] = File(..., description="2-4 clear front-facing photos recommended"),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """
    Multi-photo registration: every uploaded photo that contains a detectable
    face becomes its own embedding row for this person, which meaningfully
    improves recognition across different lighting/angles.

    company / branch / role are optional profile fields (CCTV Known/Unknown
    Identification spec, Section 2) used later so operators can visually
    disambiguate people in the "Select Known Person" dropdown.
    """
    known_face = KnownFace(name=name, company=company, branch=branch, role=role)
    db.add(known_face)
    db.flush()  # get id before commit

    saved_count = 0
    cover_photo_path = None

    for idx, file in enumerate(files):
        contents = await file.read()
        img_array = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if frame is None:
            continue

        faces = extract_faces(frame)
        if not faces:
            continue  # skip photos with no detectable face, don't fail the whole batch

        photo_path = f"{settings.SNAPSHOT_DIR}/known_{name}_{idx}.jpg"
        cv2.imwrite(photo_path, frame)
        if cover_photo_path is None:
            cover_photo_path = photo_path

        embedding = FaceEmbedding(
            face_id=known_face.id, vector=faces[0].embedding.tolist(), photo_path=photo_path
        )
        db.add(embedding)
        saved_count += 1

    if saved_count == 0:
        db.rollback()
        raise HTTPException(400, "No face detected in any of the uploaded photos")

    known_face.photo_path = cover_photo_path
    db.commit()
    db.refresh(known_face)

    result = KnownFaceOut.model_validate(known_face)
    result.photo_count = saved_count
    return result


@router.get("/known-faces", response_model=list[KnownFaceOut])
def list_known_faces(db: Session = Depends(get_db)):
    faces = db.query(KnownFace).all()
    out = []
    for f in faces:
        item = KnownFaceOut.model_validate(f)
        item.photo_count = len(f.embeddings)
        out.append(item)
    return out


@router.delete("/known-faces/{face_id}")
def delete_known_face(
    face_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)
):
    known_face = db.query(KnownFace).filter(KnownFace.id == face_id).first()
    if not known_face:
        raise HTTPException(404, "Face not found")
    db.delete(known_face)  # cascade deletes all embeddings for this person
    db.commit()
    return {"status": "deleted", "id": face_id, "name": known_face.name}


# --- Person profile: view / add / delete / set-cover for individual photos ---

@router.get("/known-faces/{face_id}/photos")
def list_face_photos(face_id: int, db: Session = Depends(get_db)):
    known_face = db.query(KnownFace).filter(KnownFace.id == face_id).first()
    if not known_face:
        raise HTTPException(404, "Face not found")
    photos = sorted(known_face.embeddings, key=lambda e: e.added_at or datetime.min, reverse=True)
    return [
        {
            "id": e.id,
            "photo_path": e.photo_path,
            "added_at": e.added_at,
            "is_cover": bool(known_face.photo_path) and e.photo_path == known_face.photo_path,
        }
        for e in photos
    ]


@router.post("/known-faces/{face_id}/photos", response_model=KnownFaceOut)
async def add_face_photo(
    face_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Adds one more reference photo to an EXISTING known person. Enforces
    the same 4-photo FIFO cap as everywhere else: if already at the cap,
    the oldest photo (by added_at) is removed first."""
    known_face = db.query(KnownFace).filter(KnownFace.id == face_id).first()
    if not known_face:
        raise HTTPException(404, "Face not found")

    contents = await file.read()
    img_array = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Could not read image")

    faces = extract_faces(frame)
    if not faces:
        raise HTTPException(400, "No face detected in this photo")

    existing = (
        db.query(FaceEmbedding)
        .filter(FaceEmbedding.face_id == face_id)
        .order_by(FaceEmbedding.added_at.asc())
        .all()
    )
    if len(existing) >= MAX_FACE_IMAGES:
        oldest = existing[0]
        if oldest.photo_path and os.path.exists(oldest.photo_path):
            try:
                os.remove(oldest.photo_path)
            except OSError:
                pass
        db.delete(oldest)
        db.flush()

    known_dir = f"{settings.SNAPSHOT_DIR}/known"
    os.makedirs(known_dir, exist_ok=True)
    photo_path = f"{known_dir}/{known_face.name}_{known_face.id}_{int(datetime.utcnow().timestamp() * 1000)}.jpg"
    cv2.imwrite(photo_path, frame)

    db.add(FaceEmbedding(face_id=face_id, vector=faces[0].embedding.tolist(), photo_path=photo_path))
    if not known_face.photo_path:
        known_face.photo_path = photo_path
    db.commit()
    db.refresh(known_face)

    result = KnownFaceOut.model_validate(known_face)
    result.photo_count = len(known_face.embeddings)
    return result


@router.delete("/known-faces/{face_id}/photos/{embedding_id}")
def delete_face_photo(
    face_id: int,
    embedding_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    embedding = (
        db.query(FaceEmbedding)
        .filter(FaceEmbedding.id == embedding_id, FaceEmbedding.face_id == face_id)
        .first()
    )
    if not embedding:
        raise HTTPException(404, "Photo not found")

    known_face = db.query(KnownFace).filter(KnownFace.id == face_id).first()
    was_cover = known_face and known_face.photo_path == embedding.photo_path

    if embedding.photo_path and os.path.exists(embedding.photo_path):
        try:
            os.remove(embedding.photo_path)
        except OSError:
            pass
    db.delete(embedding)
    db.flush()

    if was_cover and known_face:
        remaining = (
            db.query(FaceEmbedding)
            .filter(FaceEmbedding.face_id == face_id)
            .order_by(FaceEmbedding.added_at.desc())
            .first()
        )
        known_face.photo_path = remaining.photo_path if remaining else None

    db.commit()
    return {"status": "deleted", "id": embedding_id}


@router.put("/known-faces/{face_id}/cover/{embedding_id}")
def set_cover_photo(
    face_id: int,
    embedding_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """"Change" action: makes an existing photo the person's profile picture."""
    known_face = db.query(KnownFace).filter(KnownFace.id == face_id).first()
    if not known_face:
        raise HTTPException(404, "Face not found")
    embedding = (
        db.query(FaceEmbedding)
        .filter(FaceEmbedding.id == embedding_id, FaceEmbedding.face_id == face_id)
        .first()
    )
    if not embedding:
        raise HTTPException(404, "Photo not found")
    known_face.photo_path = embedding.photo_path
    db.commit()
    return {"status": "ok"}