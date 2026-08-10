import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from client.notifications import _authenticate, _cors
from .models import DeviceToken


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def register_device_token(request):
    """Called by the mobile app after login (and whenever FCM issues a new token)."""
    if request.method == 'OPTIONS':
        return _cors(JsonResponse({}))

    client = _authenticate(request)
    if not client:
        return _cors(JsonResponse({'error': 'Invalid or missing token'}, status=401))

    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return _cors(JsonResponse({'error': 'Invalid JSON'}, status=400))

    fcm_token = (payload.get('fcm_token') or '').strip()
    if not fcm_token:
        return _cors(JsonResponse({'error': 'fcm_token is required'}, status=400))

    DeviceToken.objects.update_or_create(token=fcm_token, defaults={'client': client})
    return _cors(JsonResponse({'success': True}))
