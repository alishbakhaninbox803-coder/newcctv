import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://cctv:cctv123@localhost:5432/cctv_db"
    )

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_STREAM_NAME: str = os.getenv("REDIS_STREAM_NAME", "cctv_events")

    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_ADMIN_NUMBER: str = os.getenv("WHATSAPP_ADMIN_NUMBER", "")

    UNKNOWN_FACE_THRESHOLD: float = float(os.getenv("UNKNOWN_FACE_THRESHOLD", 0.45))
    # Alias for compatibility with code that references the older/alternate name.
    UNKNOWN_PERSON_DISTANCE_THRESHOLD: float = UNKNOWN_FACE_THRESHOLD

    # --- Strict frontal-face filtering ---
    # Any face (known-face registration OR live camera detection) that fails these
    # checks is dropped before it ever reaches matching/alerting logic.
    FACE_MAX_YAW_DEG: float = float(os.getenv("FACE_MAX_YAW_DEG", 20))     # left/right turn
    FACE_MAX_PITCH_DEG: float = float(os.getenv("FACE_MAX_PITCH_DEG", 20))  # up/down tilt
    FACE_MAX_ROLL_DEG: float = float(os.getenv("FACE_MAX_ROLL_DEG", 25))   # head tilt sideways
    FACE_MIN_DET_SCORE: float = float(os.getenv("FACE_MIN_DET_SCORE", 0.65))  # detector confidence
    FACE_MIN_SHARPNESS: float = float(os.getenv("FACE_MIN_SHARPNESS", 60))   # blur/quality (Laplacian variance)
    FACE_MIN_SIZE_PX: int = int(os.getenv("FACE_MIN_SIZE_PX", 60))  # min face box width/height in pixels
    RESTRICTED_OBJECTS: list = [
        o.strip().lower()
        for o in os.getenv("RESTRICTED_OBJECTS", "knife,gun,backpack").split(",")
    ]
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", 0.4))

    # Two-tier detection: light model runs continuously, heavier model confirms trespass events
    LIGHT_MODEL: str = os.getenv("LIGHT_MODEL", "yolov8n.pt")
    FORENSIC_MODEL: str = os.getenv("FORENSIC_MODEL", "yolov8m.pt")

    SNAPSHOT_DIR: str = os.getenv("SNAPSHOT_DIR", "data/snapshots")

    # --- Auth ---
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-this-secret-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", 480))
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "cctv2024")


settings = Settings()
os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)