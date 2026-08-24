"""
Face recognition wrapper around InsightFace.
Handles: embedding extraction + matching against known faces stored in pgvector.
"""
import logging

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import FaceEmbedding, KnownFace
from app.config import settings

logger = logging.getLogger(__name__)

# 'buffalo_l' is a free, pre-trained InsightFace model bundle (downloads on first run)
_face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
_face_app.prepare(ctx_id=0, det_size=(640, 640))


def _face_sharpness(frame: np.ndarray, box) -> float:
    """Laplacian-variance sharpness score of the face crop. Low value = blurry/motion-blur."""
    x1, y1, x2, y2 = [int(v) for v in box]
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    crop = frame[y1:y2, x1:x2]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def is_strict_frontal_face(face, frame: np.ndarray = None) -> bool:
    """
    Strict gate applied to every face before it's used for anything (registration
    or live matching): only a clear, sharp, front-facing face passes.
    Rejects side/turned poses, tilted heads, blurry crops, low-confidence
    detections, and faces too small to be reliable. Applies identically
    regardless of whether the face ends up 'known' or 'unknown'.

    `frame` is optional: if not provided, the sharpness/blur check is skipped
    (pose, detection-confidence, and size checks still apply).
    """
    # 1. Detector confidence
    det_score = float(getattr(face, "det_score", 1.0))
    if det_score < settings.FACE_MIN_DET_SCORE:
        return False

    # 2. Face box size (tiny/far-away faces are unreliable for pose+recognition)
    x1, y1, x2, y2 = face.bbox
    box_w, box_h = x2 - x1, y2 - y1
    if box_w < settings.FACE_MIN_SIZE_PX or box_h < settings.FACE_MIN_SIZE_PX:
        return False

    # 3. Head pose — yaw/pitch/roll must all be near-zero (i.e. looking straight at camera)
    pose = getattr(face, "pose", None)
    if pose is None:
        # No pose estimate available (model not producing landmark_3d_68) -> can't
        # verify frontality, so fail closed rather than let a side-face slip through.
        return False
    yaw, pitch, roll = [float(v) for v in pose]
    if abs(yaw) > settings.FACE_MAX_YAW_DEG:
        return False
    if abs(pitch) > settings.FACE_MAX_PITCH_DEG:
        return False
    if abs(roll) > settings.FACE_MAX_ROLL_DEG:
        return False

    # 4. Sharpness / blur check on the face crop itself (only if a frame was given)
    if frame is not None:
        sharpness = _face_sharpness(frame, face.bbox)
        if sharpness < settings.FACE_MIN_SHARPNESS:
            return False

    return True


# Alias kept for backwards-compatibility with any code importing the older name.
is_frontal_face = is_strict_frontal_face


def extract_faces(frame: np.ndarray):
    """
    Returns list of insightface Face objects detected in a BGR frame,
    filtered down to only clear, sharp, strictly front-facing faces.
    This is the single choke point used by BOTH known-face registration
    and live camera recognition, so the same strict rule applies everywhere.
    """
    raw_faces = _face_app.get(frame)
    accepted = []
    for face in raw_faces:
        if is_strict_frontal_face(face, frame):
            accepted.append(face)
        else:
            logger.debug(
                "Rejected face: det_score=%s pose=%s bbox=%s (not strictly frontal/clear)",
                getattr(face, "det_score", None), getattr(face, "pose", None), face.bbox,
            )
    return accepted


def match_face(embedding: np.ndarray, db: Session):
    """
    Compares an embedding against all known face embeddings using cosine distance
    via pgvector's <=> operator. Returns (name, distance) or (None, None) if no match.
    """
    result = db.execute(
        select(FaceEmbedding, KnownFace.name)
        .join(KnownFace, FaceEmbedding.face_id == KnownFace.id)
        .order_by(FaceEmbedding.vector.cosine_distance(embedding))
        .limit(1)
    ).first()

    if result is None:
        return None, None

    face_embedding, name = result
    # recompute exact cosine distance in python for the threshold check
    stored = np.array(face_embedding.vector, dtype=np.float32)
    cos_sim = np.dot(embedding, stored) / (
        np.linalg.norm(embedding) * np.linalg.norm(stored) + 1e-8
    )
    cos_distance = 1 - cos_sim

    if cos_distance <= settings.UNKNOWN_FACE_THRESHOLD:
        return name, float(cos_distance)
    return None, float(cos_distance)