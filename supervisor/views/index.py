from django.shortcuts               import render
from django.contrib.auth.decorators import login_required
from authentication.decorators      import supervisor_required
from authentication.access          import accessible_projects
from django.http                    import JsonResponse
from django.db.models               import Prefetch
from supervisor.models.project      import Project
from supervisor.models.parcelle     import Parcelle
from supervisor.models.node         import Node
from supervisor.models.data         import Data
from camera_management.models       import Camera, Detection

@login_required(login_url='supervisor_login')
@supervisor_required
def index(request):
    my_projects = accessible_projects(request.user)
    total_nodes = Node.objects.filter(parcelle__project__in=my_projects).count()
    total_cameras = Camera.objects.filter(project__in=my_projects).count()
    total_projects = my_projects.count()

    context = {
        'total_nodes': total_nodes,
        'total_cameras': total_cameras,
        'total_projects': total_projects,
    }
    return render(request, 'website/index.html', context)

@login_required(login_url='supervisor_login')
@supervisor_required
def get_all_assets(request):
    projects = accessible_projects(request.user).prefetch_related(
        Prefetch(
            'parcelle',
            queryset=Parcelle.objects.prefetch_related(
                Prefetch(
                    'nodes',
                    queryset=Node.objects.prefetch_related(
                        Prefetch('datas', queryset=Data.objects.order_by('-published_date'), to_attr='latest_datas')
                    ),
                ),
                Prefetch(
                    'cameras',
                    queryset=Camera.objects.prefetch_related(
                        Prefetch('detections', queryset=Detection.objects.order_by('-detected_at'), to_attr='latest_detections')
                    ),
                ),
            ),
            to_attr='prefetched_parcelles',
        )
    )
    data = []
    
    for project in projects:
        parcelles_data = []
        parcelles = project.prefetched_parcelles
        for parcelle in parcelles:
            nodes = parcelle.nodes.all()
            node_data = [{
                'id': node.id,
                'name': node.name,
                'latitude': float(node.latitude) if node.latitude else (node.position.y if node.position else None),
                'longitude': float(node.longitude) if node.longitude else (node.position.x if node.position else None),
                'ref': node.reference,
                'last_data': get_last_data(node)
            } for node in nodes]

            cameras = parcelle.cameras.all()
            camera_data = []
            for cam in cameras:
                latest_detection = cam.latest_detections[0] if cam.latest_detections else None
                image_url = None
                if latest_detection and latest_detection.image:
                    try:
                        image_url = latest_detection.image.url
                    except ValueError:
                        pass
                
                camera_data.append({
                    'id': cam.id,
                    'name': cam.name,
                    'camera_id': cam.camera_id,
                    'is_active': cam.is_active,
                    'latitude': float(cam.latitude) if cam.latitude else None,
                    'longitude': float(cam.longitude) if cam.longitude else None,
                    'has_alert': hasattr(cam, 'detection') or (latest_detection is not None),
                    'latest_alert_image': image_url,
                    'latest_alert_time': latest_detection.detected_at.strftime('%Y-%m-%d %H:%M:%S') if latest_detection else None
                })

            parcelles_data.append({
                'id': parcelle.id,
                'name': parcelle.name,
                'coordinates': list(parcelle.polygon.coords[0]) if parcelle.polygon else [],
                'nodes': node_data,
                'cameras': camera_data
            })
            
        data.append({
            'project_id': project.pk,
            'project_name': project.name,
            'parcelles': parcelles_data
        })
        
    return JsonResponse({'projects': data}, status=200)

def get_last_data(node):
    try:
        prefetched = getattr(node, 'latest_datas', None)
        if prefetched is not None:
            if not prefetched:
                return {}
            last_data = prefetched[0]
        else:
            last_data = Data.objects.filter(node=node).latest('published_date')
        return {
            'temperature': last_data.temperature,
            'humidity': last_data.humidity,
            'rssi': node.RSSI,
            'fwi': node.FWI,
            'fwi_predit': getattr(last_data, 'fwi_predit', 0),
            'prediction_result': node.detection,
            'pressure': last_data.pressur,
            'gaz': last_data.gaz,
            'wind_speed': getattr(last_data, 'wind', None),
            'rain_volume': getattr(last_data, 'rain', None),
        }
    except Data.DoesNotExist:
        return {}
