"""
Face quality + orientation gating (Requirements 1-3 of the research paper).

Runs BEFORE a detected face is allowed to touch the known/unknown matching
pipeline at all. A face that fails either check is discarded outright:
no Event row, no Unknown ID, no snapshot, no wasted DB write.

FILE PATH: backend/app/face_quality.py
ACTION: CREATE NEW FILE
"""
import cv2
import numpy as np

from app.config import settings


def _variance_of_laplacian(gray_image: np.ndarray) -> float:
    """Standard blur metric: low variance of the Laplacian = flat/blurry image."""
    return cv2.Laplacian(gray_image, cv2.CV_64F).var()


def is_face_clear(frame: np.ndarray, face) -> bool:
    """
    Requirement 1: reject faces that are too small, too low-confidence, or
    too blurry to reliably recognize.

    `face` is an insightface Face object (has .bbox and .det_score).
    """
    x1, y1, x2, y2 = map(int, face.bbox)
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, frame.shape[1]), min(y2, frame.shape[0])
    width, height = x2 - x1, y2 - y1

    if width < settings.MIN_FACE_SIZE or height < settings.MIN_FACE_SIZE:
        return False

    det_score = float(getattr(face, "det_score", 1.0))
    if det_score < settings.MIN_DETECTION_CONFIDENCE:
        return False

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return False

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blur_score = _variance_of_laplacian(gray)
    return blur_score >= settings.MIN_BLUR_SCORE


def is_front_facing(face) -> bool:
    """
    Requirement 2: reject faces that are too far turned away from the
    camera to recognize reliably.

    Prefers insightface's `.pose` attribute ([yaw, pitch, roll] in degrees,
    available because the buffalo_l bundle includes the landmark_3d_68
    model — confirmed already loading in your logs). Falls back to a
    simple 5-point-landmark symmetry estimate if `.pose` isn't present
    on some other model bundle, and fails OPEN (treats as front-facing)
    if neither is available, so a missing attribute never silently drops
    every face.
    """
    pose = getattr(face, "pose", None)
    if pose is not None:
        yaw, pitch = float(pose[0]), float(pose[1])
        return abs(yaw) <= settings.MAX_YAW_DEGREES and abs(pitch) <= settings.MAX_PITCH_DEGREES

    kps = getattr(face, "kps", None)
    if kps is None:
        return True  # no landmark data at all — fail open rather than block everything

    left_eye, right_eye, nose = kps[0], kps[1], kps[2]
    eye_dist = float(np.linalg.norm(right_eye - left_eye))
    if eye_dist < 1e-3:
        return False

    nose_to_left = float(np.linalg.norm(nose - left_eye))
    nose_to_right = float(np.linalg.norm(nose - right_eye))
    symmetry_ratio = abs(nose_to_left - nose_to_right) / eye_dist
    return symmetry_ratio <= settings.MAX_LANDMARK_ASYMMETRY