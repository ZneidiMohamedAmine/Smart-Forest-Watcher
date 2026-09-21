from django.shortcuts                   import get_object_or_404
from django.contrib.auth.decorators     import login_required
from django.http                        import JsonResponse
from django.utils                       import timezone
from django.db.models                   import Prefetch
from datetime                           import timedelta
from authentication.decorators          import client_required
from supervisor.models.data             import Data
from supervisor.models.project          import Project
from supervisor.models.parcelle         import Parcelle
from supervisor.models.node             import Node
from camera_management.models          import Camera, Detection
from drone_management.models           import Drone



@login_required(login_url='client_login')
@client_required
def fetch_parcelles_for_project(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'No project ID provided.'}, status=400)

    project = get_object_or_404(Project, polygon_id=project_id, client=request.user.client)
    parcelles = Parcelle.objects.filter(project=project).prefetch_related(
        Prefetch(
            'nodes',
            queryset=Node.objects.prefetch_related(
                Prefetch('datas', queryset=Data.objects.order_by('-published_date'), to_attr='latest_datas')
            ),
        )
    )
    parcelle_data = []
    all_nodes = []

    for parcelle in parcelles:
        nodes = parcelle.nodes.all()
        node_data = []
        for node in nodes:
            last_comm = node.latest_datas[0] if node.latest_datas else None
            is_online = False
            if last_comm and last_comm.published_date:
                is_online = (timezone.now() - last_comm.published_date) < timedelta(minutes=60)
                
            node_data.append({
                'id': node.id,
                'name': node.name,
                'latitude': node.position.x,  
                'longitude': node.position.y, 
                'ref': node.reference, 
                'last_data': get_last_data(node),
                'is_online': is_online
            })
        
        all_nodes.extend(node_data)

        parcelle_data.append({
            'id': parcelle.id,
            'name': parcelle.name,
            'coordinates': list(parcelle.polygon.coords[0]),
            'nodes': node_data
        })

    city_data = {
        'localite_libelle': project.city.localite_libelle,
        'latitude': project.city.latitude,
        'longitude': project.city.longitude
    }
    
    # Fetch Cameras for the project
    cameras = Camera.objects.filter(project=project).prefetch_related(
        Prefetch('detections', queryset=Detection.objects.order_by('-detected_at'), to_attr='latest_detections')
    )
    camera_data = []
    for c in cameras:
        has_alert = False
        try:
            # Check if camera has a linked FireDetection (One-to-One)
            if hasattr(c, 'detection'):
                has_alert = True
        except Exception:
            pass
            
        latest_detection = c.latest_detections[0] if c.latest_detections else None
        image_url = None
        if latest_detection and latest_detection.image:
            try:
                image_url = latest_detection.image.url
            except ValueError:
                pass
                
        is_online = False
        if latest_detection:
            is_online = (timezone.now() - latest_detection.detected_at) < timedelta(minutes=60)

        camera_data.append({
            'id': c.id,
            'name': c.name,
            'camera_id': c.camera_id,
            'latitude': float(c.latitude) if c.latitude else c.position.y if c.position else 0,
            'longitude': float(c.longitude) if c.longitude else c.position.x if c.position else 0,
            'has_alert': has_alert or (latest_detection is not None),
            'is_active': c.is_active,
            'is_online': is_online and c.is_active,
            'latest_alert_image': image_url,
            'latest_alert_time': latest_detection.detected_at.strftime('%Y-%m-%d %H:%M:%S') if latest_detection else None
        })
    

    # Fetch Drones for the project — project-level, not tied to a parcelle
    drones = Drone.objects.filter(project=project).prefetch_related(
        Prefetch('detections', queryset=Detection.objects.order_by('-detected_at'), to_attr='latest_detections')
    )
    drone_data = []
    for d in drones:
        latest_detection = d.latest_detections[0] if d.latest_detections else None
        image_url = None
        if latest_detection and latest_detection.image:
            try:
                image_url = latest_detection.image.url
            except ValueError:
                pass

        is_online = False
        if d.last_seen:
            is_online = (timezone.now() - d.last_seen) < timedelta(minutes=60)

        drone_data.append({
            'id': d.id,
            'name': d.name,
            'drone_id': d.drone_id,
            'latitude': float(d.latitude) if d.latitude else None,
            'longitude': float(d.longitude) if d.longitude else None,
            'battery_level': d.battery_level,
            'has_alert': latest_detection is not None and latest_detection.is_confirmed is not False,
            'is_active': d.is_active,
            'is_online': is_online and d.is_active,
            'latest_alert_image': image_url,
            'latest_alert_time': latest_detection.detected_at.strftime('%Y-%m-%d %H:%M:%S') if latest_detection else None
        })

    return JsonResponse({
        'parcelles': parcelle_data,
        'city': city_data,
        'cameras': camera_data,
        'drones': drone_data,
    })


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
            'prediction_result': node.detection,
            'pressure': last_data.pressur,
            'gaz': last_data.gaz,
            'wind_speed': last_data.wind,
            'rain_volume': last_data.rain,
        }
    except Data.DoesNotExist:
        return {}
    
#تعمل API
# ترجع JSON
# frontend يستعملها باش يرسم map 

# يرسم parcelles (polygon)
#يحط nodes (markers)
#يعرض data   
