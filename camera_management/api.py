"""
HTTP endpoint that receives fire-detection images from Raspberry Pi units.

Method : POST
URL    : /camera_management/api/upload/
Auth   : api_key field (matched against Camera.api_key in DB)

Expected multipart/form-data body:
  camera_id       string   — matches Camera.camera_id
  api_key         string   — secret shared  with the Pi
  confidence      float    — YOLO detection confidence (0.0 – 1.0)
  bounding_boxes  JSON str — list of {x1,y1,x2,y2} dicts (optional)
  image           file     — JPEG / PNG of the annotated frame

On success:
  1. Deletes the previous Detection for this camera (one-per-camera rule)
  2. Saves the new Detection
  3. Fires the Celery alert task (WebSocket + email)
  4. Returns 200 JSON

On error: 400 / 401 / 405 JSON
"""

import json
from django.http                  import JsonResponse
from channels.db                  import database_sync_to_async
from .models                      import Camera, Detection
from .workers.alert_worker        import send_camera_alert

CONFIDENCE_THRESHOLD = 0.50    # ignore detections below this level


async def receive_detection(request):
    """
    NOTE: csrf_exempt is set as an attribute below the function (line after def)
    instead of using @csrf_exempt decorator. This avoids the 'unawaited coroutine'
    bug when the sync csrf_exempt wrapper wraps an async view under Daphne.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    # ── Auth ─────────────────────────────────────────────────────────────────
    camera_id = request.POST.get('camera_id', '').strip()
    api_key   = request.POST.get('api_key',   '').strip()

    @database_sync_to_async
    def get_camera():
        try:
            return Camera.objects.get(camera_id=camera_id)
        except Camera.DoesNotExist:
            return None

    camera = await get_camera()
    if not camera:
        return JsonResponse({'error': 'Unknown camera_id'}, status=401)

    if camera.api_key != api_key:
        return JsonResponse({'error': 'Invalid api_key'}, status=401)

    if not camera.is_active:
        return JsonResponse({'error': 'Camera is disabled'}, status=403)

    # ── Validate payload ─────────────────────────────────────────────────────
    image = request.FILES.get('image')
    if not image:
        return JsonResponse({'error': 'No image provided'}, status=400)

    try:
        confidence = float(request.POST.get('confidence', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid confidence value'}, status=400)

    if confidence < CONFIDENCE_THRESHOLD:
        # Pi sent a low-confidence detection — ignore it silently
        return JsonResponse({'message': 'Below threshold, ignored'}, status=200)

    raw_boxes = request.POST.get('bounding_boxes', '[]')
    try:
        bounding_boxes = json.loads(raw_boxes)
    except json.JSONDecodeError:
        bounding_boxes = []

    # ── Save Detection (keep history — do NOT delete old ones) ───────────────
    @database_sync_to_async
    def save_detection():
        return Detection.objects.create(
            camera           = camera,
            confidence_score = confidence,
            bounding_boxes   = bounding_boxes,
            image            = image,
        )

    detection = await save_detection()

    # ── Trigger async alert ──────────────────────────────────────────────────
    send_camera_alert.delay(detection.id)

    return JsonResponse({
        'message':      'Detection saved',
        'detection_id': detection.id,
        'confidence':   confidence,
    }, status=200)


# ✅ Bypass CSRF check without using the @csrf_exempt decorator wrapper.
# This is the correct way to exempt async views from CSRF in all Django versions.
receive_detection.csrf_exempt = True
