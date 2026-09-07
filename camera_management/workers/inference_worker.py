"""
Celery task: runs yolo26m on a received detection image.
Called from api.py immediately after saving the Detection.
"""
import os
import logging
from celery       import shared_task
from django.core.files.base import ContentFile

log = logging.getLogger(__name__)

SERVER_CONFIDENCE_THRESHOLD = float(os.environ.get('YOLO_SERVER_CONFIDENCE', 0.45))


@shared_task(name="run_server_inference")
def run_server_inference(detection_id: int):
    from camera_management.models    import Detection
    from camera_management.yolo_engine import run_inference
    from camera_management.workers.alert_worker import send_camera_alert

    try:
        detection = Detection.objects.get(pk=detection_id)
    except Detection.DoesNotExist:
        log.error("Detection %d not found", detection_id)
        return

    image_path = detection.image.path   # absolute path on disk

    try:
        _, bboxes, annotated_bytes = run_inference(image_path)
    except Exception as exc:
        log.exception("yolo26m inference failed for detection %d: %s", detection_id, exc)
        # Fall back — trigger alert with Pi's original confidence
        send_camera_alert.delay(detection_id)
        return

    # yolo_engine.run_inference already drops 'other' (non-fire) detections,
    # so every remaining box is a real fire/smoke match.
    alert_conf = max((b['confidence'] for b in bboxes), default=0.0)

    if alert_conf < SERVER_CONFIDENCE_THRESHOLD:
        log.info(
            "Detection %d: server-side yolo26m conf=%.3f < threshold=%.3f — alert suppressed.",
            detection_id, alert_conf, SERVER_CONFIDENCE_THRESHOLD,
        )
        # Optional: mark detection as a false positive
        detection.is_confirmed = False
        detection.save(update_fields=['is_confirmed'])
        return

    # Update record with server-verified data
    detection.server_confidence = alert_conf
    detection.bounding_boxes    = bboxes
    detection.is_confirmed      = True

    # Save annotated image
    annotated_name = f"annotated_{detection_id}.jpg"
    detection.annotated_image.save(annotated_name, ContentFile(annotated_bytes), save=False)

    detection.save(update_fields=['server_confidence', 'bounding_boxes',
                                  'is_confirmed', 'annotated_image'])

    log.info("Detection %d confirmed by yolo26m (conf=%.3f). Firing alert.", detection_id, alert_conf)
    send_camera_alert.delay(detection_id)
