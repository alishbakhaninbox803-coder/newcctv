import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend/ or project root directory with forced override
_backend_env = Path(__file__).resolve().parent.parent / ".env"
_root_env = Path(__file__).resolve().parent.parent.parent / ".env"

if _root_env.is_file():
    load_dotenv(dotenv_path=_root_env, override=True)
elif _backend_env.is_file():
    load_dotenv(dotenv_path=_backend_env, override=True)
else:
    load_dotenv(override=True)


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://cctv:cctv123@localhost:5432/cctv_db"
    )

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_STREAM_NAME: str = os.getenv("REDIS_STREAM_NAME", "cctv_events")

    # --- Meta WhatsApp Alerts ---
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "").strip().strip('"').strip("'")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip().strip('"').strip("'")
    WHATSAPP_ADMIN_NUMBER: str = os.getenv("WHATSAPP_ADMIN_NUMBER", "").strip().strip('"').strip("'")

    UNKNOWN_FACE_THRESHOLD: float = float(os.getenv("UNKNOWN_FACE_THRESHOLD", 0.45))
    UNKNOWN_PERSON_DISTANCE_THRESHOLD: float = UNKNOWN_FACE_THRESHOLD

    # --- Strict frontal-face filtering ---
    FACE_MAX_YAW_DEG: float = float(os.getenv("FACE_MAX_YAW_DEG", 20))
    FACE_MAX_PITCH_DEG: float = float(os.getenv("FACE_MAX_PITCH_DEG", 20))
    FACE_MAX_ROLL_DEG: float = float(os.getenv("FACE_MAX_ROLL_DEG", 25))
    FACE_MIN_DET_SCORE: float = float(os.getenv("FACE_MIN_DET_SCORE", 0.65))
    FACE_MIN_SHARPNESS: float = float(os.getenv("FACE_MIN_SHARPNESS", 60))
    FACE_MIN_SIZE_PX: int = int(os.getenv("FACE_MIN_SIZE_PX", 60))
    RESTRICTED_OBJECTS: list = [
        o.strip().lower()
        for o in os.getenv("RESTRICTED_OBJECTS", "knife,gun,backpack").split(",")
    ]
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", 0.4))

    # Two-tier detection
    LIGHT_MODEL: str = os.getenv("LIGHT_MODEL", "yolov8n.pt")
    FORENSIC_MODEL: str = os.getenv("FORENSIC_MODEL", "yolov8m.pt")

    # --- Weapon Detection ---
    WEAPON_DETECTION_ENABLED: bool = os.getenv("WEAPON_DETECTION_ENABLED", "true").lower() in ("true", "1", "yes")
    WEAPON_MODEL_PATH: str = os.getenv("WEAPON_MODEL_PATH", "models/weapon/weapon-yolo26x/best.pt")
    WEAPON_CONFIDENCE: float = float(os.getenv("WEAPON_CONFIDENCE", "0.55"))
    WEAPON_CONFIRMATION_COUNT: int = int(os.getenv("WEAPON_CONFIRMATION_COUNT", "3"))
    WEAPON_CONFIRMATION_WINDOW_SECONDS: float = float(os.getenv("WEAPON_CONFIRMATION_WINDOW_SECONDS", "2.0"))
    WEAPON_COOLDOWN_SECONDS: float = float(os.getenv("WEAPON_COOLDOWN_SECONDS", "30.0"))
    WEAPON_FORENSIC_ENABLED: bool = os.getenv("WEAPON_FORENSIC_ENABLED", "true").lower() in ("true", "1", "yes")

    SNAPSHOT_DIR: str = os.getenv("SNAPSHOT_DIR", "data/snapshots")

    # --- Auth ---
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-this-secret-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", 480))
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "cctv2024")


settings = Settings()
os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)