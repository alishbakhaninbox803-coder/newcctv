"""
One CameraWorker runs per camera in its own thread, so multiple cameras
process independently.

Pipeline per frame:
  capture -> publish live frame (every frame, for the MJPEG stream)
          -> every Nth frame: YOLOv8n objects + InsightFace faces
          -> zone check (only alert if inside the camera's defined zone, if any)
          -> log event -> push to Redis Stream -> WhatsApp alert
          -> if trespass-worthy (unknown person / restricted object in zone):
             re-run detection with the heavier YOLOv8m "forensic" model and
             log a confirmation event with (usually) higher confidence.
"""
import cv2
import json
import time
import threading
import logging
import os
from datetime import datetime

# Force TCP for stability and disable internal FFmpeg buffering for zero-latency RTSP
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|analyzeduration;0|probesize;1048576"

from app.database import SessionLocal
from app.models import Event, Zone
from app.face_engine import extract_faces, match_face, is_frontal_face
from app.object_engine import (
    detect_objects, detect_objects_forensic, filter_restricted, box_center,
)
from app.redis_stream import push_event
from app.whatsapp import (
    send_whatsapp_text,
    send_whatsapp_image_alert,
    build_unknown_person_message,
    build_restricted_object_message,
    build_weapon_message,
)
from app.alert_dispatcher import dispatch_image_alert
from app.unknown_person_service import resolve_unknown_person
from app.weapon_engine import weapon_engine, CameraWeaponTracker
from app.config import settings
from app.stream_manager import publish_frame, clear_frame

logger = logging.getLogger(__name__)
INFER_EVERY_N_FRAMES = 15  # Run detection every 15 frames (~2 FPS at 30 FPS input)
STREAM_JPEG_QUALITY = 70 # Reduce JPEG quality to 50% for faster streaming


def _point_in_zone(point, polygon_points) -> bool:
    """cv2.pointPolygonTest expects a numpy int32 array of the polygon."""
    import numpy as np
    poly = np.array(polygon_points, dtype=np.int32)
    return cv2.pointPolygonTest(poly, point, False) >= 0


class CameraWorker:
    def __init__(self, camera_id: int, camera_name: str, source: str):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.source = int(source) if str(source).isdigit() else source
        self._running = False
        self._thread = None
        self._detection_thread = None
        self.zone_polygon = self._load_zone()
        # Latest-frame strategy: detection always gets the newest frame
        self._detection_frame = None
        self._detection_frame_time = None  # Capture timestamp for age calc
        self._detection_lock = threading.Lock()
        self._detection_event = threading.Event()
        self.weapon_tracker = CameraWeaponTracker(self.camera_id)

        self.status = {
            # Availability
            "camera_id": camera_id,
            "camera_name": camera_name,
            "running": False,
            "state": "initializing",
            "last_frame_at": None,
            "frames_processed": 0,
            "reconnect_count": 0,
            # Capture
            "fps_source": None,
            "capture_fps": None,
            "frame_age_ms": None,
            "dropped_frames": 0,
            # Stream
            "frames_delivered": 0,
            "stream_errors": 0,
            "jpeg_encode_ms": None,
            # AI
            "yolo_fps": None,
            "yolo_inference_ms": None,
            "insightface_inference_ms": None,
            "detection_frame_age_ms": None,
            "detection_frames_skipped": 0,
            "latest_detection_at": None,
        }

    def _load_zone(self):
        db = SessionLocal()
        try:
            zone = db.query(Zone).filter(Zone.camera_id == self.camera_id).first()
            return json.loads(zone.polygon) if zone else None
        finally:
            db.close()

    def start(self):
        if self._running:
            return
        self._running = True
        self.status["running"] = True
        self._thread = threading.Thread(target=self._run_capture, daemon=True, name=f"camera-capture-{self.camera_id}")
        self._detection_thread = threading.Thread(target=self._run_detection, daemon=True, name=f"camera-detect-{self.camera_id}")
        self._thread.start()
        self._detection_thread.start()
        _active_workers[self.camera_id] = self

    def stop(self):
        self._running = False
        self.status["running"] = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._detection_thread:
            self._detection_thread.join(timeout=2)
        clear_frame(self.camera_id)

    def _save_snapshot(self, frame, category: str = "misc") -> str:
        folder = f"{settings.SNAPSHOT_DIR}/{category}"
        os.makedirs(folder, exist_ok=True)
        filename = f"{self.camera_name}_{int(time.time()*1000)}.jpg"
        path = f"{folder}/{filename}"
        cv2.imwrite(path, frame)
        return path

    def _log_and_alert(self, event_type, person_name=None, is_unknown=False,
                        object_name=None, confidence=None, frame=None, in_zone=True,
                        snapshot_path=None):
        """
        snapshot_path: pass this in when a snapshot was already saved
        elsewhere (e.g. resolve_unknown_person() saving into its own
        Unknown-NNN folder) so we don't save the same frame to disk twice.
        If omitted, falls back to the old flat-file save-per-event.
        """
        if snapshot_path is None and frame is not None:
            snapshot_path = self._save_snapshot(frame)
        db = SessionLocal()
        try:
            event = Event(
                event_type=event_type,
                camera_name=self.camera_name,
                timestamp=datetime.utcnow(),
                snapshot_path=snapshot_path,
                person_name=person_name,
                is_unknown=is_unknown,
                object_name=object_name,
                confidence=confidence,
                in_zone=in_zone,
            )
            db.add(event)
            db.commit()
        finally:
            db.close()

        push_event({
            "event_type": event_type,
            "camera_name": self.camera_name,
            "timestamp": str(datetime.utcnow()),
            "person_name": person_name,
            "object_name": object_name,
            "confidence": confidence,
        })

        if event_type == "unknown_person":
            msg = build_unknown_person_message(
                self.camera_name, datetime.utcnow().strftime("%I:%M %p"), confidence or 0
            )
            if person_name:
                msg = f"{msg}\nIdentity: {person_name}"
            dispatch_image_alert(snapshot_path, msg)
        elif event_type == "restricted_object":
            msg = build_restricted_object_message(
                self.camera_name, object_name, datetime.utcnow().strftime("%I:%M %p"), confidence or 0
            )
            dispatch_image_alert(snapshot_path, msg)
        elif event_type == "weapon_detected":
            msg = build_weapon_message(
                self.camera_name,
                object_name or "Weapon",
                datetime.utcnow().strftime("%I:%M %p"),
                confidence or 0,
                zone_name=f"Camera {self.camera_id} Zone" if in_zone else None,
                forensic_confirmed=True,
            )
            dispatch_image_alert(snapshot_path, msg)

    def _forensic_confirm(self, frame, trigger_label):
        """Re-run the heavier model on this frame to confirm a trespass event."""
        detections = detect_objects_forensic(frame)
        best = max(detections, key=lambda d: d["confidence"], default=None)
        self._log_and_alert(
            "forensic_confirmation",
            object_name=best["label"] if best else trigger_label,
            confidence=best["confidence"] if best else None,
            frame=frame,
        )

    def _in_zone_or_no_zone(self, box) -> bool:
        if not self.zone_polygon:
            return True  # no zone defined = whole frame counts
        return _point_in_zone(box_center(box), self.zone_polygon)

    def _run_capture(self):
        """Capture frames and publish them ASAP, handling reconnections."""
        logger.info(f"[{self.camera_name}] Starting frame capture thread. Source: {self.source}")
        
        latest_frame = [None]
        latest_frame_time = [None]  # Capture timestamp for frame_age_ms
        
        def reader(cap):
            """Drains buffer as fast as possible to avoid stale frames."""
            frames_read = 0
            start_time = time.time()
            while self._running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                capture_time = time.time()
                # Diagnostics: Drop stale frames if main loop hasn't consumed
                if latest_frame[0] is not None:
                    self.status["dropped_frames"] += 1
                
                latest_frame[0] = frame
                latest_frame_time[0] = capture_time
                frames_read += 1
                
                elapsed = time.time() - start_time
                if elapsed >= 1.0:
                    self.status["capture_fps"] = round(frames_read / elapsed, 1)
                    frames_read = 0
                    start_time = time.time()
        
        while self._running:
            self.status["state"] = "connecting"
            if isinstance(self.source, str) and (self.source.startswith("http") or self.source.startswith("rtsp")):
                cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            elif isinstance(self.source, int) or (isinstance(self.source, str) and self.source.isdigit()):
                cap = cv2.VideoCapture(int(self.source), cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(self.source)
                
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not cap.isOpened():
                logger.error(f"[{self.camera_name}] FAILED to open camera source: {self.source}")
                self.status["state"] = "failed"
                time.sleep(5.0)  # Wait before reconnect
                self.status["reconnect_count"] += 1
                continue
            
            self.status["state"] = "connected"
            source_fps = cap.get(cv2.CAP_PROP_FPS)
            self.status["fps_source"] = round(source_fps, 1) if (source_fps and source_fps > 0) else None
            target_sleep = 1.0 / source_fps if (source_fps and source_fps > 0 and source_fps <= 60) else 0.033
            
            reader_thread = threading.Thread(target=reader, args=(cap,), daemon=True)
            reader_thread.start()

            try:
                while self._running and reader_thread.is_alive():
                    frame = latest_frame[0]
                    if frame is None:
                        time.sleep(0.01)
                        continue
                    
                    frame_time = latest_frame_time[0]
                    latest_frame[0] = None  # Consume frame
                    self.status["frames_processed"] += 1

                    # Measure frame age: time from capture to stream publish
                    if frame_time:
                        self.status["frame_age_ms"] = round((time.time() - frame_time) * 1000, 1)

                    try:
                        t_enc = time.time()
                        ok_jpeg, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY])
                        self.status["jpeg_encode_ms"] = round((time.time() - t_enc) * 1000, 1)
                        if ok_jpeg:
                            publish_frame(self.camera_id, buf.tobytes())
                            self.status["frames_delivered"] += 1
                        else:
                            self.status["stream_errors"] += 1
                    except Exception:
                        self.status["stream_errors"] += 1

                    self.status["last_frame_at"] = datetime.utcnow().isoformat()

                    if self.status["frames_processed"] % INFER_EVERY_N_FRAMES == 0:
                        with self._detection_lock:
                            if self._detection_frame is not None:
                                # Overwriting a pending frame — that's a skipped detection
                                self.status["detection_frames_skipped"] += 1
                            self._detection_frame = frame.copy()
                            self._detection_frame_time = frame_time  # Pass capture time for age calc
                        self._detection_event.set()
                    
                    # No forced sleep. Loop naturally waits on `latest_frame[0] is None` above.
                    
            except Exception as e:
                logger.error(f"[{self.camera_name}] Capture thread error: {e}", exc_info=True)
            finally:
                cap.release()
                if self._running:
                    logger.warning(f"[{self.camera_name}] Stream disconnected. Reconnecting in 5s...")
                    self.status["state"] = "reconnecting"
                    self.status["reconnect_count"] += 1
                    time.sleep(5.0)

    def _run_detection(self):
        """Run detection on queued frames (can be slow, doesn't block video stream)."""
        logger.info(f"[{self.camera_name}] Starting detection thread")
        db = SessionLocal()
        
        yolo_count = 0
        yolo_fps_start = time.time()
        
        try:
            while self._running:
                # Wait for a new detection frame (event-driven, no busy-wait)
                self._detection_event.wait(timeout=0.5)
                self._detection_event.clear()
                
                with self._detection_lock:
                    frame = self._detection_frame
                    frame_capture_time = self._detection_frame_time
                    self._detection_frame = None  # Consume it
                    self._detection_frame_time = None
                
                if frame is None:
                    continue
                
                # Frame age: how old is this frame when YOLO starts?
                if frame_capture_time:
                    self.status["detection_frame_age_ms"] = round(
                        (time.time() - frame_capture_time) * 1000, 1
                    )
                
                try:
                    # 1. --- Weapon Detection & Temporal Confirmation (PRIORITY) ---
                    if settings.WEAPON_DETECTION_ENABLED and weapon_engine.is_ready:
                        try:
                            w_detections = weapon_engine.detect(frame)
                            for w_obj in w_detections:
                                inside_zone = self._in_zone_or_no_zone(w_obj["bbox"])
                                if not inside_zone:
                                    continue  # Filtered by zone

                                is_confirmed, event_data = self.weapon_tracker.register_detection(
                                    class_name=w_obj["class_name"],
                                    confidence=w_obj["confidence"],
                                    bbox=w_obj["bbox"],
                                )

                                print(f"\033[93m[{self.camera_name}] [WEAPON CANDIDATE] {w_obj['class_name']} ({w_obj['confidence']:.1%}, confirmed: {is_confirmed})\033[0m")
                                logger.info(f"[{self.camera_name}] Weapon candidate: {w_obj['class_name']} (conf: {w_obj['confidence']:.2f}, confirmed: {is_confirmed})")

                                if is_confirmed:
                                    print(f"\033[91m[{self.camera_name}] >>> WEAPON ALERT TRIGGERED: {event_data['class_name']} ({event_data['confidence']:.1%}) <<<\033[0m")

                                    # Save clean snapshot (NO bounding boxes rendered)
                                    snap_path = self._save_snapshot(frame, category="weapon")

                                    self._log_and_alert(
                                        "weapon_detected",
                                        object_name=event_data["class_name"],
                                        confidence=event_data["confidence"],
                                        in_zone=True,
                                        snapshot_path=snap_path,
                                    )
                        except Exception as w_exc:
                            logger.error(f"[{self.camera_name}] Error during weapon detection: {w_exc}", exc_info=True)

                    # 2. --- Object detection (light model) ---
                    t_yolo = time.time()
                    detections = detect_objects(frame)
                    self.status["yolo_inference_ms"] = round((time.time() - t_yolo) * 1000, 1)
                    
                    for obj in filter_restricted(detections):
                        inside = self._in_zone_or_no_zone(obj["box"])
                        if not inside:
                            continue
                        self._log_and_alert(
                            "restricted_object", object_name=obj["label"],
                            confidence=obj["confidence"], frame=frame, in_zone=True,
                        )
                        self._forensic_confirm(frame, obj["label"])

                    # 3. --- Face recognition ---
                    t_face = time.time()
                    faces = extract_faces(frame)
                    self.status["insightface_inference_ms"] = round((time.time() - t_face) * 1000, 1)
                    
                    for face in faces:
                        if not is_frontal_face(face):
                            continue  # side/profile face — skip entirely, no match, no alert
                        box = tuple(map(int, face.bbox))
                        inside = self._in_zone_or_no_zone(box)
                        name, distance = match_face(face.embedding, db)
                        if name:
                            self._log_and_alert(
                                "known_person", person_name=name,
                                confidence=1 - (distance or 0), frame=frame, in_zone=inside,
                            )
                        else:
                            if not inside:
                                continue
                            unknown_person, is_new = resolve_unknown_person(
                                face.embedding, frame, db, self.camera_name,
                            )
                            label = f"Unknown-{unknown_person.id:03d}"
                            self._log_and_alert(
                                "unknown_person", person_name=label, is_unknown=True,
                                confidence=1 - (distance or 0), in_zone=True,
                                snapshot_path=unknown_person.representative_snapshot_path,
                            )
                            print("[DEBUG-UNKNOWN] Alert attempted, snapshot=" + str(unknown_person.representative_snapshot_path))
                            # Only run forensic check for newly detected unknown persons to prevent CPU starvation
                            if is_new:
                                self._forensic_confirm(frame, label)
                    
                    self.status["latest_detection_at"] = datetime.utcnow().isoformat()
                    
                except Exception as e:
                    logger.error(f"[{self.camera_name}] Error during detection: {e}")
                
                yolo_count += 1
                elapsed = time.time() - yolo_fps_start
                if elapsed >= 5.0:
                    self.status["yolo_fps"] = round(yolo_count / elapsed, 2)
                    yolo_count = 0
                    yolo_fps_start = time.time()
                    
        except Exception as e:
            logger.error(f"[{self.camera_name}] Unexpected error in detection thread: {e}", exc_info=True)
        finally:
            db.close()
            logger.info(f"[{self.camera_name}] Detection thread stopped.")

    def _run(self):
        """Legacy method name (kept for compatibility) - now just delegates to capture."""
        self._run_capture()

# Registry of active workers so API endpoints can start/stop them and check health
_active_workers: dict[int, CameraWorker] = {}


def start_camera(camera_id: int, camera_name: str, source: str):
    if camera_id in _active_workers and _active_workers[camera_id].status["running"]:
        return
    worker = CameraWorker(camera_id, camera_name, source)
    worker.start()


def stop_camera(camera_id: int):
    worker = _active_workers.pop(camera_id, None)
    if worker:
        worker.stop()


def get_all_worker_status():
    return [w.status for w in _active_workers.values()]


def refresh_zone(camera_id: int):
    """Call after saving a new zone so a running worker picks it up immediately."""
    worker = _active_workers.get(camera_id)
    if worker:
        worker.zone_polygon = worker._load_zone()