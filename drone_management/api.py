"""
HTTP endpoint that receives fire-detection images + live GPS telemetry from
drone units. Mirrors camera_management/api.py's receive_detection, with two
differences: the drone is mobile, so every upload also carries its current
latitude/longitude (and optional battery level), which overwrite the Drone
row's live position; and detections created here point at `drone` instead
of `camera` (see camera_management.models.Detection).

Method : POST
URL    : /drone_management/api/upload/
Auth   : api_key field (matched against Drone.api_key in DB)

Expected multipart/form-data body:
  drone_id        string   — matches Drone.drone_id
  api_key         string   — secret shared with the onboard unit
  latitude        float    — current GPS latitude
  longitude       float    — current GPS longitude
  battery         int      — optional, 0-100
  confidence      float    — YOLO detection confidence (0.0 – 1.0)
  bounding_boxes  JSON str — list of {x1,y1,x2,y2} dicts (optional)
  image           file     — JPEG / PNG of the current frame

Position/telemetry is updated on every valid-auth request, even if the
frame's confidence is below threshold and no Detection is saved — a drone
should keep reporting "I'm here" on every heartbeat, not just on fire hits.

On success: 200 JSON. On error: 400 / 401 / 403 / 405 JSON.
"""

import json
from django.http import JsonResponse
from django.utils import timezone
from channels.db  import database_sync_to_async
from .models       import Drone
from camera_management.models import Detection
from camera_management.workers.inference_worker import run_server_inference


CONFIDENCE_THRESHOLD = 0.25    # ignore detections below this level, same as camera


async def receive_drone_upload(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    # ── Auth ─────────────────────────────────────────────────────────────────
    drone_id = request.POST.get('drone_id', '').strip()
    api_key  = request.POST.get('api_key',  '').strip()

    @database_sync_to_async
    def get_drone():
        try:
            return Drone.objects.get(drone_id=drone_id)
        except Drone.DoesNotExist:
            return None

    drone = await get_drone()
    if not drone:
        return JsonResponse({'error': 'Unknown drone_id'}, status=401)

    if drone.api_key != api_key:
        return JsonResponse({'error': 'Invalid api_key'}, status=401)

    if not drone.is_active:
        return JsonResponse({'error': 'Drone is disabled'}, status=403)

    # ── Update live telemetry (always, regardless of what follows) ───────────
    try:
        latitude  = float(request.POST.get('latitude'))
        longitude = float(request.POST.get('longitude'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid or missing latitude/longitude'}, status=400)

    battery_raw = request.POST.get('battery')
    battery = None
    if battery_raw not in (None, ''):
        try:
            battery = max(0, min(100, int(battery_raw)))
        except ValueError:
            battery = None

    @database_sync_to_async
    def update_telemetry():
        drone.latitude  = latitude
        drone.longitude = longitude
        drone.last_seen = timezone.now()
        if battery is not None:
            drone.battery_level = battery
        drone.save(update_fields=['latitude', 'longitude', 'last_seen', 'battery_level'])

    await update_telemetry()

    # ── Validate detection payload ─────────────────────────────────────────────
    image = request.FILES.get('image')
    if not image:
        return JsonResponse({'message': 'Telemetry updated, no image provided'}, status=200)

    try:
        confidence = float(request.POST.get('confidence', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid confidence value'}, status=400)

    if confidence < CONFIDENCE_THRESHOLD:
        return JsonResponse({'message': 'Telemetry updated, confidence below threshold'}, status=200)

    raw_boxes = request.POST.get('bounding_boxes', '[]')
    try:
        bounding_boxes = json.loads(raw_boxes)
    except json.JSONDecodeError:
        bounding_boxes = []

    # ── Save Detection (keep history — do NOT delete old ones) ───────────────
    @database_sync_to_async
    def save_detection():
        return Detection.objects.create(
            drone            = drone,
            project          = drone.project,
            confidence_score = confidence,
            bounding_boxes   = bounding_boxes,
            image            = image,
        )

    detection = await save_detection()

    # ── Trigger the same async YOLO + alert pipeline cameras use ──────────────
    run_server_inference.delay(detection.id)

    return JsonResponse({
        'message':      'Detection saved',
        'detection_id': detection.id,
        'confidence':   confidence,
    }, status=200)


# See camera_management/api.py's identical note: csrf_exempt is set as an
# attribute (not @csrf_exempt) to avoid an async/Daphne unawaited-coroutine bug.
receive_drone_upload.csrf_exempt = True
