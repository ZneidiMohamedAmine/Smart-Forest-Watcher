import json
from urllib.parse import urlsplit

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import MobileNotification, Client, ClientAuthToken


def _cors(response):
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


def _authenticate(request):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    key = auth_header[len('Bearer '):].strip()
    token = ClientAuthToken.objects.select_related('client').filter(key=key).first()
    return token.client if token else None


def _parse_json(request):
    try:
        return json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return None


def _absolute_media_url(path, request=None):
    if not path:
        return ''
    if path.startswith(('http://', 'https://')):
        parsed = urlsplit(path)
        media_prefix = settings.MEDIA_URL.rstrip('/') + '/'
        if request and parsed.path.startswith(media_prefix):
            return request.build_absolute_uri(parsed.path)
        return path
    if request:
        return request.build_absolute_uri(path)
    base = getattr(settings, 'PUBLIC_BASE_URL', '').rstrip('/')
    if base:
        return f"{base}/{path.lstrip('/')}"
    return path


def _notification_image_url(notification, request=None):
    if notification.detection_id and notification.detection.image:
        url = notification.detection.image.url
    else:
        url = (notification.data or {}).get('image_url') or ''
    return _absolute_media_url(url, request)


def _serialize_notification(n, request=None):
    return {
        'id': n.id,
        'user_id': n.user_id,
        'title': n.title,
        'body': n.body,
        'source': 'camera' if n.camera_id else (n.data or {}).get('source', 'manual'),
        'camera_id': n.camera.camera_id if n.camera else None,
        'camera_name': n.camera.name if n.camera else None,
        'detection_id': n.detection_id,
        'project': (n.data or {}).get('project'),
        'image_url': _notification_image_url(n, request),
        'confidence': (n.data or {}).get('confidence'),
        'detected_at': (n.data or {}).get('detected_at'),
        'created_at': n.created_at.isoformat(),
    }


def send_mobile_notification(user_id, title, body='', data=None, camera=None, detection=None):
    if not user_id:
        return None
    notification = MobileNotification.objects.create(
        user_id=user_id,
        title=title or '',
        body=body or '',
        data=data or {},
        camera=camera,
        detection=detection,
    )
    return {'notification_id': notification.id}


def notify_client_for_detection(detection):
    camera = detection.camera
    project = camera.project or (camera.parcelle.project if camera.parcelle else None)
    client = project.client if project else None
    if not client or not client.email:
        return None

    parcelle_name = camera.parcelle.name if camera.parcelle else 'Unknown'
    title = f"Fire Detected — {camera.name} ({project.name})"
    body = (
        f"Camera '{camera.name}' detected fire in '{parcelle_name}'.\n"
        f"Confidence: {detection.confidence_score * 100:.1f}%\n"
        f"Time: {detection.detected_at:%Y-%m-%d %H:%M UTC}"
    )
    data = {
        'source': 'camera',
        'camera_id': camera.camera_id,
        'camera_name': camera.name,
        'parcelle': parcelle_name,
        'project': project.name,
        'confidence': detection.confidence_score,
        'detected_at': detection.detected_at.isoformat(),
    }
    return send_mobile_notification(
        user_id=client.email,
        title=title,
        body=body,
        data=data,
        camera=camera,
        detection=detection,
    )


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def send_notification(request):
    if request.method == 'OPTIONS':
        return _cors(JsonResponse({}))

    payload = _parse_json(request)
    if payload is None:
        return _cors(JsonResponse({'error': 'Invalid JSON'}, status=400))

    user_id = (payload.get('user_id') or '').strip()
    if not user_id:
        return _cors(JsonResponse({'error': 'user_id required'}, status=400))

    data = payload.get('data') or {}
    if data.get('image_url'):
        data['image_url'] = _absolute_media_url(data['image_url'], request)

    result = send_mobile_notification(
        user_id=user_id,
        title=payload.get('title'),
        body=payload.get('body'),
        data=data,
    )
    return _cors(JsonResponse(result))


@csrf_exempt
@require_http_methods(['GET', 'OPTIONS'])
def list_notifications(request):
    if request.method == 'OPTIONS':
        return _cors(JsonResponse({}))

    client = _authenticate(request)
    if not client:
        return _cors(JsonResponse({'error': 'Invalid or missing token'}, status=401))

    rows = (
        MobileNotification.objects
        .filter(user_id=client.email)
        .select_related('camera', 'detection')
        .order_by('-id')
    )
    return _cors(JsonResponse({
        'notifications': [_serialize_notification(n, request) for n in rows],
    }))


@csrf_exempt
@require_http_methods(['GET', 'OPTIONS'])
def client_summary(request):
    if request.method == 'OPTIONS':
        return _cors(JsonResponse({}))

    client = _authenticate(request)
    if not client:
        return _cors(JsonResponse({'error': 'Invalid or missing token'}, status=401))

    from camera_management.models import Camera

    projects = list(client.project_set.values_list('name', flat=True))
    cameras = list(
        Camera.objects
        .filter(project__client=client)
        .values('camera_id', 'name', 'project__name')
    )

    return _cors(JsonResponse({
        'projects': projects,
        'cameras': [
            {'camera_id': c['camera_id'], 'name': c['name'], 'project': c['project__name']}
            for c in cameras
        ],
    }))
