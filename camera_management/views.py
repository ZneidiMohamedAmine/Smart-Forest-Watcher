"""
Views for camera_management.

add_camera  — supervisor places a camera on the Leaflet map (same UX as add_node).
              POST → validates point is inside parcelle → saves Camera → returns JSON.
              GET  → returns the camera form (rendered inline in project.html).

list_cameras_for_project — AJAX endpoint: returns all cameras for a project_id.
                           Used by the map to render camera markers alongside nodes.
"""

import json
import logging
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos        import Point
from django.http                    import JsonResponse
from django.shortcuts               import get_object_or_404, render
from authentication.decorators      import supervisor_required, client_required
from supervisor.models.parcelle     import Parcelle
from supervisor.models.project      import Project
from .models  import Camera
from .forms   import CameraForm

log = logging.getLogger(__name__)


@login_required(login_url='supervisor_login')
@supervisor_required
def add_camera(request):
    if request.method == 'POST':
        camera_form = CameraForm(request.POST)

        if camera_form.is_valid():
            coordinates_data = request.POST.get('position', '')
            parcelle_id      = request.POST.get('parcelle')

            try:
                # Parse "POINT(lng lat)" — same parsing as node_create
                coords    = coordinates_data.strip('POINT()').split()
                longitude = float(coords[0])
                latitude  = float(coords[1])
                point     = Point(latitude, longitude)

                parcelle = get_object_or_404(Parcelle, id=parcelle_id)

                if not parcelle.polygon.contains(point):
                    return JsonResponse(
                        {'error': {'_all__': 'The camera must be placed inside the parcelle.'}},
                        status=400
                    )

                camera           = camera_form.save(commit=False)
                camera.position  = point
                camera.latitude  = latitude
                camera.longitude = longitude
                camera.parcelle  = parcelle
                camera.project   = parcelle.project
                camera.save()

                # Return all cameras for this parcelle so the map updates
                cameras = [
                    {
                        'id':        c.id,
                        'name':      c.name,
                        'camera_id': c.camera_id,
                        'latitude':  float(c.latitude),
                        'longitude': float(c.longitude),
                        'has_alert': c.detections.exists(),
                    }
                    for c in Camera.objects.filter(parcelle=parcelle)
                ]

                return JsonResponse({
                    'message':     'Camera added successfully.',
                    'cameras':     cameras,
                    'parcelle_id': parcelle.id,
                    'project_id':  parcelle.project.polygon_id,
                }, status=200)

            except (ValueError, TypeError):
                return JsonResponse(
                    {'error': {'coordinates': [{'message': 'Invalid coordinates.', 'code': 'invalid'}]}},
                    status=400
                )
        else:
            return JsonResponse({'error': camera_form.errors.get_json_data()}, status=400)

    else:
        camera_form = CameraForm()
        return render(request, 'website/project.html', {'camera_form': camera_form})


@login_required(login_url='supervisor_login')
@supervisor_required
def list_cameras_for_project(request):
    """AJAX: return cameras + their alert status for a given project_id."""
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'error': 'No project_id provided'}, status=400)

    cameras = Camera.objects.filter(
        project_id=project_id
    ).select_related('parcelle').prefetch_related('detections')

    data = []
    for c in cameras:
        try:
            det         = c.detections.latest('detected_at')
            has_alert   = True
            detected_at = det.detected_at.isoformat()
            image_url   = det.image.url
            confidence  = det.confidence_score
        except Exception:
            has_alert   = False
            detected_at = None
            image_url   = None
            confidence  = None

        data.append({
            'id':          c.id,
            'name':        c.name,
            'camera_id':   c.camera_id,
            'parcelle_id': c.parcelle_id,
            'latitude':    float(c.latitude)  if c.latitude  else None,
            'longitude':   float(c.longitude) if c.longitude else None,
            'is_active':   c.is_active,
            'has_alert':   has_alert,
            'detected_at': detected_at,
            'image_url':   image_url,
            'confidence':  confidence,
        })

    return JsonResponse({'cameras': data}, status=200)

@login_required(login_url='client_login')
@client_required
def camera_detail(request, project_id, camera_id):
    project = get_object_or_404(Project, polygon_id=project_id, client=request.user.client)
    camera = get_object_or_404(Camera, id=camera_id, project=project)

    # All detections ordered newest first
    all_detections = camera.detections.order_by('-detected_at')
    latest    = all_detections.first()          # shown prominently at top
    history   = all_detections[1:6]             # previous 5 detections shown below

    context = {
        'project':   project,
        'camera':    camera,
        'detection': latest,     # keeps template variable name compatible
        'history':   history,
    }

    return render(request, 'camera_management/camera_detail.html', context)

@login_required(login_url='client_login')
@client_required
def delete_detection(request, detection_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    from .models import Detection
    detection = Detection.objects.filter(id=detection_id).first()
    if detection is None:
        return JsonResponse({'error': f'Detection {detection_id} not found (already deleted?)'}, status=404)

    # Ensure client owns the project
    try:
        project_client = detection.camera.project.client
    except Exception as exc:
        log.error("delete_detection: could not resolve project.client for detection %d: %s", detection_id, exc)
        return JsonResponse({'error': 'Server error resolving ownership'}, status=500)

    if project_client is None or project_client != request.user.client:
        log.warning(
            "delete_detection: ownership mismatch — project.client=%s, request.user.client=%s",
            project_client, getattr(request.user, 'client', None)
        )
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    detection.delete()
    log.info("delete_detection: detection %d deleted by user %s", detection_id, request.user.username)
    return JsonResponse({'success': True, 'message': 'Image deleted successfully'})


@login_required(login_url='supervisor_login')
@supervisor_required
def delete_camera(request, camera_id):
    if request.method == 'POST':
        camera = get_object_or_404(Camera, pk=camera_id)
        camera.delete()
        return JsonResponse({'success': True, 'message': 'Camera deleted successfully.'})
    return JsonResponse({'error': 'Invalid request method.'}, status=400)


# ── Detection History (Supervisor) ───────────────────────────────────────────

@login_required(login_url='supervisor_login')
@supervisor_required
def detection_history(request):
    """
    Supervisor-only view: lists ALL detections across every camera/project.
    Supports filtering by project, confirmation status, and date range.
    Paginated — 20 records per page.
    """
    from .models import Detection
    from supervisor.models.project import Project
    from django.core.paginator import Paginator

    qs = Detection.objects.select_related(
        'camera', 'camera__project', 'camera__project__client'
    ).order_by('-detected_at')

    # ── Filters ───────────────────────────────────────────────────────────────
    project_id = request.GET.get('project')
    status     = request.GET.get('status')        # confirmed / rejected / pending
    date_from  = request.GET.get('date_from')
    date_to    = request.GET.get('date_to')

    if project_id:
        qs = qs.filter(camera__project__polygon_id=project_id)

    if status == 'confirmed':
        qs = qs.filter(is_confirmed=True)
    elif status == 'rejected':
        qs = qs.filter(is_confirmed=False)
    elif status == 'pending':
        qs = qs.filter(is_confirmed__isnull=True)

    if date_from:
        qs = qs.filter(detected_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(detected_at__date__lte=date_to)

    # ── Pagination ────────────────────────────────────────────────────────────
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    # ── Stats ─────────────────────────────────────────────────────────────────
    total     = qs.count()
    confirmed = qs.filter(is_confirmed=True).count()
    rejected  = qs.filter(is_confirmed=False).count()
    pending   = qs.filter(is_confirmed__isnull=True).count()

    projects  = Project.objects.all().order_by('name')

    context = {
        'page_obj':   page_obj,
        'projects':   projects,
        'total':      total,
        'confirmed':  confirmed,
        'rejected':   rejected,
        'pending':    pending,
        # preserve filter values for the form
        'f_project':   project_id or '',
        'f_status':    status or '',
        'f_date_from': date_from or '',
        'f_date_to':   date_to or '',
    }
    return render(request, 'supervisor/detection_history.html', context)


@login_required(login_url='supervisor_login')
@supervisor_required
def delete_detection_supervisor(request, detection_id):
    """Supervisor can delete any detection (no ownership check needed)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    from .models import Detection
    detection = Detection.objects.filter(id=detection_id).first()
    if detection is None:
        return JsonResponse({'error': f'Detection {detection_id} not found'}, status=404)

    detection.delete()
    log.info("Supervisor deleted detection %d", detection_id)
    return JsonResponse({'success': True})

@login_required(login_url='supervisor_login')
@supervisor_required
def update_detection_status(request, detection_id):
    """Supervisor can manually confirm or reject a detection."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    from .models import Detection
    detection = Detection.objects.filter(id=detection_id).first()
    if detection is None:
        return JsonResponse({'error': f'Detection {detection_id} not found'}, status=404)

    try:
        data = json.loads(request.body)
        new_status = data.get('status') # 'confirmed', 'rejected', or 'pending'
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if new_status == 'confirmed':
        detection.is_confirmed = True
    elif new_status == 'rejected':
        detection.is_confirmed = False
    elif new_status == 'pending':
        detection.is_confirmed = None
    else:
        return JsonResponse({'error': 'Invalid status value'}, status=400)

    detection.save(update_fields=['is_confirmed'])
    log.info("Supervisor updated detection %d to %s", detection_id, new_status)
    return JsonResponse({'success': True, 'new_status': new_status})


VALID_TRAINING_LABELS = ['fire', 'smoke', 'other']


@login_required(login_url='supervisor_login')
@supervisor_required
def review_queue(request):
    """
    Supervisor-only: lists detections that haven't been reviewed/corrected
    yet for the training dataset pipeline (MLOps human-in-the-loop step).
    """
    from django.core.paginator import Paginator
    from .models import Detection

    qs = (
        Detection.objects
        .filter(staged_corrections__isnull=True)
        .select_related('camera', 'camera__project')
        .order_by('-detected_at')
    )

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'supervisor/review_queue.html', {
        'page_obj': page_obj,
        'total_pending': paginator.count,
    })


@login_required(login_url='supervisor_login')
@supervisor_required
def review_detection(request, detection_id):
    """
    GET  — renders the canvas box-correction editor for one detection.
    POST — saves the supervisor's corrected boxes as a StagedCorrection,
           ready to be picked up by run_merge_staging().
    """
    from .models import Detection, StagedCorrection

    detection = get_object_or_404(Detection, pk=detection_id)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            boxes = data.get('boxes', [])
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        for box in boxes:
            if box.get('label') not in VALID_TRAINING_LABELS:
                return JsonResponse({'error': f"Invalid label: {box.get('label')}"}, status=400)
            for key in ('x1', 'y1', 'x2', 'y2'):
                if not isinstance(box.get(key), (int, float)):
                    return JsonResponse({'error': f"Box missing numeric '{key}'"}, status=400)
            if box['x2'] <= box['x1'] or box['y2'] <= box['y1']:
                return JsonResponse({'error': 'Box coordinates must have x2>x1 and y2>y1'}, status=400)

        StagedCorrection.objects.create(
            detection=detection,
            boxes=boxes,
            reviewed_by=request.user,
            status='approved',
        )
        log.info("Supervisor staged %d corrected box(es) for detection %d", len(boxes), detection_id)
        return JsonResponse({'success': True})

    return render(request, 'supervisor/review_detection.html', {
        'detection': detection,
        'existing_boxes_json': json.dumps(detection.bounding_boxes or []),
        'valid_labels': VALID_TRAINING_LABELS,
    })
