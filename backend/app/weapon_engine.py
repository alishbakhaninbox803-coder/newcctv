"""
Modular Weapon Detection Engine & Per-Camera Temporal Confirmation Tracker.

Features:
- Backend-only detection: NEVER modifies, renders on, or draws bounding boxes
  on video frames.
- Robust initialization: Fails gracefully without crashing camera workers if
  model weights cannot be loaded.
- Per-camera temporal confirmation: Requires N detections within a sliding
  time window before triggering alerts, suppressing single-frame false positives.
- Cooldown suppression: Prevents duplicate alert spamming for continuous
  weapon presence.
"""
import time
import logging
import torch
import ultralytics.nn.tasks

# Enable PyTorch safe globals for Ultralytics weights
try:
    torch.serialization.add_safe_globals([ultralytics.nn.tasks.DetectionModel])
except Exception:
    pass

from ultralytics import YOLO
from app.config import settings

logger = logging.getLogger(__name__)

import os
from pathlib import Path

# Recognized weapon keywords across standard COCO and custom YOLO weapon datasets
DEFAULT_WEAPON_KEYWORDS = {
    "gun", "knife", "pistol", "rifle", "firearm", "weapon", "dagger",
    "sword", "blade", "revolver", "handgun", "shotgun", "sniper", "assault rifle",
    "blunt_weapon", "blunt weapon", "explosive", "explosion", "fire_smoke", "fire smoke",
    "melee_weapon", "melee weapon", "grenade", "bomb", "blunt", "melee", "fire"
}

EXCLUDED_CLASSES = {
    "person", "tool", "human", "people"
}


class WeaponDetectionEngine:
    def __init__(self, model_path: str = None, confidence: float = None):
        self.model_path = model_path or settings.WEAPON_MODEL_PATH
        self.confidence = confidence if confidence is not None else settings.WEAPON_CONFIDENCE
        self.model = None
        self.is_ready = False
        self._load_model()

    def _resolve_model_path(self, path_str: str) -> str:
        """Resolves relative model paths against common base directories."""
        if not path_str:
            return path_str
        p = Path(path_str)
        if p.is_file():
            return str(p)
        # Check relative to backend/
        backend_p = Path(__file__).resolve().parent.parent / path_str
        if backend_p.is_file():
            return str(backend_p)
        # Check relative to project root
        root_p = Path(__file__).resolve().parent.parent.parent / path_str
        if root_p.is_file():
            return str(root_p)
        return path_str

    def _load_model(self):
        try:
            resolved_path = self._resolve_model_path(self.model_path)
            logger.info(f"[WeaponEngine] Loading weapon model from: {resolved_path}")
            self.model = YOLO(resolved_path)
            self.is_ready = True
            msg = f"[WeaponEngine] Model successfully loaded ({resolved_path}) with classes: {getattr(self.model, 'names', {})}"
            logger.info(msg)
            print(f"\033[92m{msg}\033[0m")
        except Exception as e:
            self.is_ready = False
            self.model = None
            err_msg = f"[WeaponEngine] FAILED to load weapon model from '{self.model_path}': {e}. Weapon detection disabled."
            logger.error(err_msg, exc_info=True)
            print(f"\033[91m{err_msg}\033[0m")

    def is_weapon_class(self, label: str) -> bool:
        """Determines if a detected class name represents a weapon, ignoring persons and tools."""
        cleaned = (label or "").strip().lower().replace("-", "_")
        if not cleaned or cleaned in EXCLUDED_CLASSES:
            return False
        # Direct match or substring keyword match
        if cleaned in DEFAULT_WEAPON_KEYWORDS:
            return True
        for kw in DEFAULT_WEAPON_KEYWORDS:
            if kw in cleaned:
                return True
        return False

    def detect(self, frame) -> list[dict]:
        """
        Runs weapon detection on the provided frame copy.

        Returns structured detections:
            [
                {
                    "class_name": str,
                    "confidence": float,
                    "bbox": (x1, y1, x2, y2)
                },
                ...
            ]

        CRITICAL: Does NOT modify the frame or draw bounding boxes.
        """
        if not self.is_ready or self.model is None or frame is None:
            return []

        try:
            results = self.model(frame, imgsz=640, conf=self.confidence, verbose=False)[0]
            detections = []

            for box in results.boxes:
                conf = float(box.conf[0])
                if conf < self.confidence:
                    continue

                raw_label = self.model.names[int(box.cls[0])]
                label = raw_label.lower().strip()

                # Strictly ensure class is a weapon and not person/tool
                if not self.is_weapon_class(label):
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append({
                    "class_name": raw_label,
                    "confidence": conf,
                    "bbox": (x1, y1, x2, y2),
                })

            return detections
        except Exception as exc:
            logger.error(f"[WeaponEngine] Inference error: {exc}")
            return []


class CameraWeaponTracker:
    """
    Maintains independent temporal confirmation and cooldown state for a single camera.
    """
    def __init__(
        self,
        camera_id: int,
        confirmation_count: int = None,
        window_seconds: float = None,
        cooldown_seconds: float = None,
    ):
        self.camera_id = camera_id
        self.confirmation_count = (
            confirmation_count if confirmation_count is not None else settings.WEAPON_CONFIRMATION_COUNT
        )
        self.window_seconds = (
            window_seconds if window_seconds is not None else settings.WEAPON_CONFIRMATION_WINDOW_SECONDS
        )
        self.cooldown_seconds = (
            cooldown_seconds if cooldown_seconds is not None else settings.WEAPON_COOLDOWN_SECONDS
        )
        self.history: list[tuple[float, str, float, tuple]] = []  # (timestamp, class_name, confidence, bbox)
        self.last_alert_time: float = 0.0

    def register_detection(
        self,
        class_name: str,
        confidence: float,
        bbox: tuple,
        now: float = None,
    ) -> tuple[bool, dict | None]:
        """
        Registers a valid in-zone weapon detection.

        Returns (is_confirmed, event_payload_or_None).
        `is_confirmed` is True ONLY if:
        1. At least `confirmation_count` detections occur within `window_seconds`.
        2. Time since `last_alert_time` >= `cooldown_seconds`.
        """
        curr_time = now if now is not None else time.time()

        # Prune history outside the sliding time window
        window_start = curr_time - self.window_seconds
        self.history = [h for h in self.history if h[0] >= window_start]

        # Record this detection
        self.history.append((curr_time, class_name, confidence, bbox))

        # Check temporal confirmation count
        if len(self.history) >= self.confirmation_count:
            # Check cooldown period
            if (curr_time - self.last_alert_time) >= self.cooldown_seconds:
                self.last_alert_time = curr_time
                # Pick the detection with the highest confidence in this window
                best = max(self.history, key=lambda item: item[2])
                payload = {
                    "class_name": best[1],
                    "confidence": best[2],
                    "bbox": best[3],
                    "confirmation_count": len(self.history),
                    "camera_id": self.camera_id,
                    "timestamp": curr_time,
                }
                return True, payload

        return False, None

    def reset(self):
        """Clears detection history for this camera."""
        self.history.clear()


# Global weapon engine singleton
weapon_engine = WeaponDetectionEngine()
