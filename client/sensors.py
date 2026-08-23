"""
Client-facing sensor readings API — powers the mobile app's Sensors tab.

Returns the latest reading per node the logged-in client owns, plus a
server-computed `risk` label (based on FWI when available, falling back to
temperature) so the app can render a color-coded badge without needing to
know the underlying thresholds.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .notifications import _authenticate, _cors
from supervisor.models.node import Node


def _risk_level(fwi, temperature):
    """
    Fire-danger-style risk bucket. Prefers FWI (Canadian Fire Weather Index
    scale) when we have it; falls back to a coarse temperature read so a
    node still shows something useful before FWI data accumulates.
    """
    if fwi is not None:
        if fwi < 5:
            return 'low'
        if fwi < 12:
            return 'moderate'
        if fwi < 21:
            return 'high'
        if fwi < 38:
            return 'very_high'
        return 'extreme'

    if temperature is not None:
        if temperature < 20:
            return 'low'
        if temperature < 30:
            return 'moderate'
        if temperature < 38:
            return 'high'
        return 'very_high'

    return 'unknown'


@csrf_exempt
@require_http_methods(['GET', 'OPTIONS'])
def list_sensors(request):
    if request.method == 'OPTIONS':
        return _cors(JsonResponse({}))

    client = _authenticate(request)
    if not client:
        return _cors(JsonResponse({'error': 'Invalid or missing token'}, status=401))

    nodes = (
        Node.objects
        .filter(parcelle__project__client=client)
        .select_related('parcelle', 'parcelle__project')
        .prefetch_related('datas')
    )

    payload = []
    for node in nodes:
        latest = node.datas.order_by('-published_date').first()
        temperature = latest.temperature if latest else None
        humidity = latest.humidity if latest else None
        fwi = latest.fwi_predit if (latest and latest.fwi_predit is not None) else (latest.fwi if latest else None)

        payload.append({
            'id': node.id,
            'name': node.name,
            'project': node.parcelle.project.name if node.parcelle else None,
            'latitude': float(node.latitude) if node.latitude is not None else None,
            'longitude': float(node.longitude) if node.longitude is not None else None,
            'temperature': temperature,
            'humidity': humidity,
            'fwi': fwi,
            'risk': _risk_level(fwi, temperature),
            'battery': node.Battery_value,
            'status': node.status,
            'published_date': latest.published_date.isoformat() if latest else None,
        })

    return _cors(JsonResponse({'nodes': payload}))
