"""
Read + convert endpoints for unknown persons (Requirements 8-11).

FILE PATH: backend/app/routers/unknown_persons.py
ACTION: CREATE NEW FILE
"""
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.database import get_db
from app.models import UnknownPerson, UnknownSighting, User
from app.schemas import UnknownPersonOut, UnknownSightingOut, KnownFaceOut
from app.unknown_person_service import promote_to_known
from app.auth import get_current_user, require_admin
from app.config import settings

router = APIRouter(tags=["Unknown Persons"])


class ConvertToKnownRequest(BaseModel):
    name: str


@router.get("/unknown-persons", response_model=list[UnknownPersonOut])
def list_unknown_persons(
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One row per distinct unknown individual, most recently seen first,
    with a detection_count so the dashboard can show it without a second
    round-trip per row."""
    rows = (
        db.query(UnknownPerson, func.count(UnknownSighting.id).label("detection_count"))
        .outerjoin(UnknownSighting, UnknownSighting.unknown_person_id == UnknownPerson.id)
        .group_by(UnknownPerson.id)
        .order_by(desc(UnknownPerson.last_seen))
        .limit(limit)
        .all()
    )
    results = []
    for person, count in rows:
        item = UnknownPersonOut.model_validate(person)
        item.detection_count = count
        results.append(item)
    return results


@router.get("/unknown-persons/{unknown_person_id}", response_model=UnknownPersonOut)
def get_unknown_person(
    unknown_person_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    person = db.query(UnknownPerson).filter(UnknownPerson.id == unknown_person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Unknown person not found")
    count = (
        db.query(func.count(UnknownSighting.id))
        .filter(UnknownSighting.unknown_person_id == unknown_person_id)
        .scalar()
    )
    item = UnknownPersonOut.model_validate(person)
    item.detection_count = count or 0
    return item


@router.get("/unknown-persons/{unknown_person_id}/sightings", response_model=list[UnknownSightingOut])
def list_sightings(
    unknown_person_id: int,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Full sighting history for one unknown_person, newest first — includes
    camera_name per sighting, satisfying Requirement 9's "cameras where
    detected" and "detection history" fields."""
    person = db.query(UnknownPerson).filter(UnknownPerson.id == unknown_person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Unknown person not found")

    return (
        db.query(UnknownSighting)
        .filter(UnknownSighting.unknown_person_id == unknown_person_id)
        .order_by(desc(UnknownSighting.timestamp))
        .limit(limit)
        .all()
    )


@router.post("/unknown-persons/{unknown_person_id}/convert-to-known", response_model=KnownFaceOut)
def convert_to_known(
    unknown_person_id: int,
    payload: ConvertToKnownRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Requirement 10: converts an unknown_person into a named known_face."""
    if not payload.name.strip():
        raise HTTPException(400, "Name is required")
    try:
        known_face = promote_to_known(unknown_person_id, payload.name.strip(), db)
    except ValueError:
        raise HTTPException(404, "Unknown person not found")

    result = KnownFaceOut.model_validate(known_face)
    result.photo_count = 1
    return result


@router.delete("/unknown-persons/{unknown_person_id}")
def delete_unknown_person(
    unknown_person_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Delete an unknown person and all associated embeddings/sightings (Admin only)."""
    person = db.query(UnknownPerson).filter(UnknownPerson.id == unknown_person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Unknown person not found")

    unknown_dir = os.path.join(
        settings.SNAPSHOT_DIR, "unknown", f"Unknown-{person.id:03d}"
    )
    if os.path.isdir(unknown_dir):
        shutil.rmtree(unknown_dir, ignore_errors=True)

    db.delete(person)
    db.commit()
    return {"status": "deleted", "id": unknown_person_id}