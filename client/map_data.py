"""
Client-facing project map API — powers the mobile app's dashboard map
(parcelle polygon(s), camera markers, sensor node markers) for the
logged-in client's single project.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .notifications import _authenticate, _cors
from .sensors import _risk_level
from supervisor.models.project import Project
from supervisor.models.parcelle import Parcelle
from supervisor.models.node import Node
from camera_management.models import Camera


@csrf_exempt
@require_http_methods(['GET', 'OPTIONS'])
def project_map(request):
    if request.method == 'OPTIONS':
        return _cors(JsonResponse({}))

    client = _authenticate(request)
    if not client:
        return _cors(JsonResponse({'error': 'Invalid or missing token'}, status=401))

    project = Project.objects.filter(client=client).first()
    if not project:
        return _cors(JsonResponse({'parcelles': [], 'cameras': [], 'nodes': []}))

    parcelles = [
        {'id': p.id, 'name': p.name,
         'coordinates': list(p.polygon.coords[0]) if p.polygon else []}
        for p in Parcelle.objects.filter(project=project)
    ]

    cameras = [
        {'id': c.id, 'name': c.name,
         'latitude': float(c.latitude) if c.latitude else (c.position.y if c.position else None),
         'longitude': float(c.longitude) if c.longitude else (c.position.x if c.position else None)}
        for c in Camera.objects.filter(project=project)
    ]

    nodes = []
    for n in Node.objects.filter(parcelle__project=project).select_related('parcelle').prefetch_related('datas'):
        latest = n.datas.order_by('-published_date').first()
        fwi = latest.fwi_predit if (latest and latest.fwi_predit is not None) else (latest.fwi if latest else None)
        nodes.append({
            'id': n.id, 'name': n.name,
            'latitude': float(n.latitude) if n.latitude is not None else None,
            'longitude': float(n.longitude) if n.longitude is not None else None,
            'risk': _risk_level(fwi, latest.temperature if latest else None),
            'temperature': latest.temperature if latest else None,
            'humidity': latest.humidity if latest else None,
            'gaz': latest.gaz if latest else None,
            'pressure': latest.pressur if latest else None,
            'fwi': fwi,
        })

    return _cors(JsonResponse({'parcelles': parcelles, 'cameras': cameras, 'nodes': nodes}))
