"""
Celery async tasks for the camera_management app.

Triggered from api.py after a new Detection is saved:
  send_camera_alert.delay(detection_id)

Responsibilities:
  1. Push a WebSocket event to the 'camera_alerts' channel group
     → all connected browsers receive the notification instantly.
  2. Send an email to the Supervisor AND the assigned Client.
"""

import json
from celery          import shared_task
from asgiref.sync    import async_to_sync
from channels.layers import get_channel_layer
from django.core.mail import send_mail

CAMERA_GROUP = "camera_alerts"


@shared_task(name="send_camera_alert")
def send_camera_alert(detection_id: int):
    # ── 1. Load detection ────────────────────────────────────────────────────
    from camera_management.models import Detection   # late import avoids circular
    try:
        detection = Detection.objects.select_related(
            'camera__parcelle', 'drone', 'project__client',
        ).get(pk=detection_id)
    except Detection.DoesNotExist:
        return

    camera  = detection.camera
    drone   = detection.drone
    source  = camera or drone
    source_type  = 'camera' if camera else 'drone'
    source_label = 'Camera' if camera else 'Drone'
    project = detection.project
    if not source or not project:
        return

    client  = project.client
    parcelle_name = camera.parcelle.name if (camera and camera.parcelle) else None

    # ── 2. WebSocket push ────────────────────────────────────────────────────
    payload = json.dumps({
        "type":               "camera_alert",
        "source_type":        source_type,
        "camera_id":          camera.camera_id if camera else None,
        "camera_name":        source.name,
        "parcelle":           parcelle_name or 'N/A',
        "project":            project.name,
        "confidence":         detection.confidence_score,
        "image_url":          detection.image.url,
        "annotated_image_url": detection.annotated_image.url if detection.annotated_image else detection.image.url,
        "is_confirmed":       detection.is_confirmed,
        "server_confidence":  detection.server_confidence,
        "detected_at":        detection.detected_at.isoformat(),
    })

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        CAMERA_GROUP,
        {"type": "camera_message", "text": payload}
    )
    # ── 3. Email alert ───────────────────────────────────────────────────────
    subject  = f"🔥 Fire Detected — {source.name} ({project.name})"
    location_bit = f"in parcelle '{parcelle_name}', " if parcelle_name else ""
    message  = (
        f"Fire was detected by {source_type} '{source.name}' "
        f"{location_bit}project '{project.name}'.\n\n"
        f"Confidence: {detection.confidence_score * 100:.1f}%\n"
        f"Detected at: {detection.detected_at:%Y-%m-%d %H:%M UTC}\n\n"
        f"Please check the dashboard immediately."
    )

    recipients = []
    # Always email the supervisor (Django superusers)
    from django.contrib.auth.models import User
    supervisors = User.objects.filter(is_superuser=True).values_list('email', flat=True)
    recipients.extend([e for e in supervisors if e])

    # Also email the assigned client
    if client and client.email:
        recipients.append(client.email)

    if recipients:
        send_mail(
            subject,
            message,
            'smartforgreen-alerts@gmail.com',
            recipients,
            fail_silently=True,
        )

    # ── 4. Mobile app notification for the project client ────────────────────
    from client.notifications import notify_client_for_detection
    notify_client_for_detection(detection)
