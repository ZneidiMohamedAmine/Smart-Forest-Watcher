"""
Server-side YOLO engine — yolo26m model.
Loaded once per Celery worker process (module-level singleton).
"""
import os
import logging
from pathlib import Path
from io import BytesIO

log = logging.getLogger(__name__)
_model = None   # singleton — loaded on first call

def _load_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        model_path = os.environ.get('YOLO_MODEL_PATH', 'camera_management/models_weights/yolo26m.pt')
        p = Path(model_path)
        if p.exists() and p.stat().st_size > 0:
            # Custom fire-detection model is present
            _model = YOLO(str(p))
            log.info("Custom model loaded from %s", model_path)
        else:
            # ── Fallback: download yolov8m.pt from Ultralytics ──────────────
            log.warning(
                "Custom model not found or empty at '%s'. "
                "Falling back to yolov8m.pt (generic objects — replace with "
                "a fire-trained model before production).",
                model_path,
            )
            _model = YOLO('yolov8m.pt')   # ultralytics auto-downloads on first run
    return _model


def run_inference(image_path: str, conf_threshold: float = 0.45):
    """
    Run yolo26m on image_path.
    Returns:
        best_confidence  float
        bounding_boxes   list[dict]  — {x1,y1,x2,y2,confidence,label}
        annotated_bytes  bytes       — JPEG of annotated frame (bboxes drawn)
    """
    model   = _load_model()
    results = model.predict(source=image_path, conf=conf_threshold, save=False, verbose=False)

    boxes     = []
    best_conf = 0.0

    for result in results:
        for box in result.boxes:
            conf  = float(box.conf[0])
            cls   = int(box.cls[0])
            label = result.names.get(cls, str(cls))
            if label == "other":
                # Not a real fire/smoke indicator — never surface it (no box drawn,
                # never stored, never counted toward confidence).
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            boxes.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2,
                          "confidence": conf, "label": label})
            if conf > best_conf:
                best_conf = conf

    # Draw bounding boxes using PIL
    annotated_bytes = _draw_boxes(image_path, boxes)

    log.info("yolo26m inference — best_conf=%.3f  detections=%d", best_conf, len(boxes))
    return best_conf, boxes, annotated_bytes


def _draw_boxes(image_path: str, boxes: list) -> bytes:
    """Draw bounding boxes on the image, return JPEG bytes."""
    from PIL import Image, ImageDraw, ImageFont
    img  = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    for b in boxes:
        draw.rectangle([b["x1"], b["y1"], b["x2"], b["y2"]], outline="red", width=3)
        label = f"{b['label']} {b['confidence']:.0%}"
        draw.text((b["x1"] + 4, b["y1"] + 4), label, fill="red")

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()
