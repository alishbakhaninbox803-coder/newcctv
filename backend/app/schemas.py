"""
FILE PATH: backend/app/schemas.py
ACTION: REPLACE ENTIRE FILE
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Union


class EventOut(BaseModel):
    id: int
    event_type: str
    camera_name: str
    timestamp: datetime
    snapshot_path: Optional[str] = None
    person_name: Optional[str] = None
    is_unknown: bool
    object_name: Optional[str] = None
    confidence: Optional[float] = None
    in_zone: bool

    class Config:
        from_attributes = True


class KnownFaceOut(BaseModel):
    id: int
    name: str
    photo_path: Optional[str] = None
    created_at: datetime
    photo_count: int = 0

    class Config:
        from_attributes = True


class CameraCreate(BaseModel):
    name: str
    source: str


class CameraOut(BaseModel):
    id: int
    name: str
    source: str
    is_active: bool

    class Config:
        from_attributes = True


class StatisticsOut(BaseModel):
    total_events: int
    unknown_person_events: int
    restricted_object_events: int
    known_person_events: int
    forensic_confirmations: int
    total_known_faces: int
    active_cameras: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class ZoneIn(BaseModel):
    camera_id: int
    points: list[list[float]]  # [[x,y], [x,y], ...] in source-frame pixel coords


class ZoneOut(BaseModel):
    camera_id: int
    points: list[list[float]]


class WorkerHealth(BaseModel):
    # Availability
    camera_id: int
    camera_name: str
    running: bool
    state: Optional[str] = None
    last_frame_at: Optional[str] = None
    frames_processed: int = 0
    reconnect_count: int = 0

    # Capture pipeline
    fps_source: Optional[Union[float, str]] = None
    capture_fps: Optional[float] = None
    frame_age_ms: Optional[float] = None
    dropped_frames: int = 0

    # Stream pipeline
    frames_delivered: int = 0
    stream_errors: int = 0
    jpeg_encode_ms: Optional[float] = None

    # AI pipeline
    yolo_fps: Optional[float] = None
    yolo_inference_ms: Optional[float] = None
    insightface_inference_ms: Optional[float] = None
    detection_frame_age_ms: Optional[float] = None
    detection_frames_skipped: int = 0
    active_tracks: int = 0
    latest_detection_at: Optional[str] = None


class SystemResources(BaseModel):
    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None
    gpu_percent: Optional[float] = None
    gpu_memory_percent: Optional[float] = None


class HealthOut(BaseModel):
    api_status: str
    redis_connected: bool
    database_connected: bool
    workers: list[WorkerHealth]
    system: Optional[SystemResources] = None


# --- Unknown persons (Requirements 7, 8, 9) ---

class UnknownPersonOut(BaseModel):
    id: int
    first_seen: datetime
    last_seen: datetime
    representative_snapshot_path: Optional[str] = None
    detection_count: int = 0

    class Config:
        from_attributes = True


class UnknownSightingOut(BaseModel):
    id: int
    unknown_person_id: int
    camera_name: str
    snapshot_path: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True