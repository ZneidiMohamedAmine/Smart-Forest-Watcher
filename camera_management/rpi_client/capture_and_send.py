#!/usr/bin/env python3
"""
Raspberry Pi 4 — Fire Detection Client
=======================================
Runs every 15 minutes via cron:
  */15 * * * * /home/pi/venv/bin/python3 /home/pi/fire_cam/capture_and_send.py >> /home/pi/fire_cam/cam.log 2>&1

Requirements (install on Pi):
  pip install ultralytics requests picamera2

Steps:
  1. Capture a single frame from the Pi camera
  2. Run YOLO inference — model path set in CONFIG below
  3. If fire detected above CONFIDENCE threshold → POST to Django server
  4. Retry up to MAX_RETRIES times on network failure (4G can drop briefly)
"""

import io
import json
import time
import logging
from datetime import datetime   
from pathlib  import Path

import requests

# ── Try to import camera library ─────────────────────────────────────────────
try:
    from picamera2 import Picamera2
    USE_PICAMERA2 = True
except ImportError:
    # Fallback for testing on a non-Pi machine (uses a test image)
    USE_PICAMERA2 = False

# ── Try to import YOLO ────────────────────────────────────────────────────────
try:
    from ultralytics import YOLO
    USE_YOLO = True
except ImportError:
    USE_YOLO = False

# ── CONFIG — edit these values ────────────────────────────────────────────────
SERVER_URL        = "https://your-server.com/camera_management/api/upload/"
CAMERA_ID         = "cam-001"          # must match Camera.camera_id in Django
API_KEY           = "your-secret-key"  # must match Camera.api_key in Django
MODEL_PATH        = "/home/pi/fire_cam/best.pt"   # trained YOLO weights
CONFIDENCE        = 0.30               # minimum confidence to send alert
MAX_RETRIES       = 3
RETRY_DELAY_SEC   = 10
CAPTURE_PATH      = "/home/pi/fire_cam/fire_frame.jpg"  # not /tmp: a shared, world-writable dir is a symlink-attack risk
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)


def capture_frame(path: str) -> bool:
    """Capture one frame from the Pi camera and save to path."""
    if USE_PICAMERA2:
        cam = Picamera2()
        cam.configure(cam.create_still_configuration())
        cam.start()
        time.sleep(2)           # let the sensor settle
        cam.capture_file(path)
        cam.close()
        log.info("Frame captured → %s", path)
        return True
    else:
        # ─ Non-Pi fallback: use a local test image ─
        test_img = Path("test_fire.jpg")
        if test_img.exists():
            import shutil
            shutil.copy(str(test_img), path)
            log.warning("PiCamera2 not available — using test image")
            return True
        log.error("No camera and no test image found.")
        return False


def run_inference(image_path: str):
    """
    Run YOLO detection on the captured frame.
    Returns (best_confidence, bounding_boxes_list) or (0, []) if no fire.
    bounding_boxes format: [{"x1": int, "y1": int, "x2": int, "y2": int, "confidence": float}]
    """
    if not USE_YOLO:
        log.warning("ultralytics not installed — skipping YOLO inference.")
        return 0.0, []

    model   = YOLO(MODEL_PATH)
    results = model.predict(source=image_path, conf=CONFIDENCE, save=True, save_txt=False)

    boxes      = []
    best_conf  = 0.0

    for result in results:
        for box in result.boxes:
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            boxes.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "confidence": conf})
            if conf > best_conf:
                best_conf = conf

    log.info("YOLO done — best confidence: %.2f  |  detections: %d", best_conf, len(boxes))
    return best_conf, boxes


def send_to_server(image_path: str, confidence: float, bboxes: list) -> bool:
    """POST the detection image + metadata to Django. Retries on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with open(image_path, 'rb') as img_file:
                response = requests.post(
                    SERVER_URL,
                    data={
                        'camera_id':      CAMERA_ID,
                        'api_key':        API_KEY,
                        'confidence':     str(confidence),
                        'bounding_boxes': json.dumps(bboxes),
                    },
                    files={'image': ('frame.jpg', img_file, 'image/jpeg')},
                    timeout=30,
                )

            if response.status_code == 200:
                log.info("✅ Detection sent successfully: %s", response.json())
                return True
            else:
                log.warning("Server returned %d: %s", response.status_code, response.text)
                return False

        except requests.exceptions.RequestException as e:
            log.warning("Attempt %d/%d failed: %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)

    log.error("❌ All %d attempts failed. Detection NOT sent.", MAX_RETRIES)
    return False


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # SET THIS TO TRUE TO TEST WITHOUT YOLO
    TEST_MODE = True 

    log.info("=== Fire Detection Run — %s ===", datetime.now().isoformat())
    if TEST_MODE:
        log.warning("⚠️ TEST MODE ENABLED: Bypassing YOLO inference.")

    if not capture_frame(CAPTURE_PATH):
        log.error("Frame capture failed. Exiting.")
        raise SystemExit(1)

    if TEST_MODE:
        # Dummy data for testing
        confidence = 1.0
        bboxes = [{"x1": 10, "y1": 10, "x2": 100, "y2": 100, "confidence": 1.0}]
        log.info("Test mode: sending frame with dummy confidence 1.0")
    else:
        confidence, bboxes = run_inference(CAPTURE_PATH)

    if confidence < CONFIDENCE and not TEST_MODE:
        log.info("No fire detected (conf=%.2f < threshold=%.2f). Nothing sent.", confidence, CONFIDENCE)
    else:
        log.info("🔥 Fire detected! (or Test Mode) Sending to server...")
        send_to_server(CAPTURE_PATH, confidence, bboxes)
