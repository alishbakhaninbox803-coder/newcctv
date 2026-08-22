"""
FILE PATH: backend/app/models.py
ACTION: REPLACE ENTIRE FILE
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime

from app.database import Base

# InsightFace 'buffalo_l' produces 512-d embeddings
EMBEDDING_DIM = 512


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)


class KnownFace(Base):
    __tablename__ = "known_faces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    photo_path = Column(String, nullable=True)  # cover/first photo
    created_at = Column(DateTime, default=datetime.utcnow)

    # one person can now have MULTIPLE embeddings (multi-photo registration)
    embeddings = relationship(
        "FaceEmbedding", back_populates="face", cascade="all, delete-orphan"
    )


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    face_id = Column(Integer, ForeignKey("known_faces.id"))
    vector = Column(Vector(EMBEDDING_DIM))
    photo_path = Column(String, nullable=True)

    face = relationship("KnownFace", back_populates="embeddings")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    source = Column(String, nullable=False)  # rtsp url / device index / video file
    is_active = Column(Boolean, default=False)


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), unique=True)
    # polygon stored as JSON string: "[[x1,y1],[x2,y2],...]" in source-frame pixel coords
    polygon = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)
    # "unknown_person" | "known_person" | "restricted_object" | "forensic_confirmation"
    camera_name = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    snapshot_path = Column(String, nullable=True)
    person_name = Column(String, nullable=True)
    is_unknown = Column(Boolean, default=False)
    object_name = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    in_zone = Column(Boolean, default=True)  # whether it happened inside a defined zone


# --- Unknown-person de-duplication (Requirements 6, 7, 14) ---
# One stable row per distinct unknown individual (id doubles as the
# "Unknown-NNN" identifier shown in the frontend), with many timestamped
# unknown_sighting rows underneath it — this is what lets the system reuse
# "Unknown-001" instead of creating Unknown-002, Unknown-003, ... for the
# same person appearing repeatedly or on a different camera.

class UnknownPerson(Base):
    __tablename__ = "unknown_persons"

    id = Column(Integer, primary_key=True, index=True)
    reference_embedding = Column(Vector(EMBEDDING_DIM))
    representative_snapshot_path = Column(String, nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    sightings = relationship(
        "UnknownSighting", back_populates="person", cascade="all, delete-orphan"
    )


class UnknownSighting(Base):
    __tablename__ = "unknown_sightings"

    id = Column(Integer, primary_key=True, index=True)
    unknown_person_id = Column(Integer, ForeignKey("unknown_persons.id"))
    camera_name = Column(String, nullable=False)
    snapshot_path = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    person = relationship("UnknownPerson", back_populates="sightings")