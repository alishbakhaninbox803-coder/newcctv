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


class UnknownPerson(Base):
    """One row per distinct unknown identity (Unknown-001, Unknown-002, ...)."""
    __tablename__ = "unknown_persons"

    id = Column(Integer, primary_key=True, index=True)
    # First-ever embedding for this identity. Kept as a fallback match target
    # (see unknown_person_service) for identities that predate per-sighting
    # embeddings below, plus as a quick reference for promote_to_known().
    reference_embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    representative_snapshot_path = Column(String, nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    sightings = relationship(
        "UnknownSighting", back_populates="unknown_person", cascade="all, delete-orphan"
    )
    embeddings = relationship(
        "UnknownEmbedding", back_populates="unknown_person",
        cascade="all, delete-orphan", order_by="UnknownEmbedding.id",
    )


class UnknownEmbedding(Base):
    """
    One row per sighting's embedding for an UnknownPerson (mirrors how
    FaceEmbedding stores multiple photos per KnownFace). Matching against
    ALL of a person's past embeddings — not just their first one — lets
    the same person keep getting recognized across different angles/
    lighting as more sightings accumulate.
    """
    __tablename__ = "unknown_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    unknown_person_id = Column(Integer, ForeignKey("unknown_persons.id"))
    vector = Column(Vector(EMBEDDING_DIM))
    snapshot_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    unknown_person = relationship("UnknownPerson", back_populates="embeddings")


class UnknownSighting(Base):
    """Every re-appearance of an UnknownPerson, across any camera."""
    __tablename__ = "unknown_sightings"

    id = Column(Integer, primary_key=True, index=True)
    unknown_person_id = Column(Integer, ForeignKey("unknown_persons.id"))
    camera_name = Column(String)
    snapshot_path = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    unknown_person = relationship("UnknownPerson", back_populates="sightings")


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