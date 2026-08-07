import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from authentication.decorators import supervisor_required
from supervisor.models.data import Data
from supervisor.models.project import Project
from django.core.paginator import Paginator
from django.db.models import Avg

log = logging.getLogger(__name__)

@login_required(login_url='supervisor_login')
@supervisor_required
def sensor_history(request):
    """
    Supervisor-only view: lists ALL sensor data across every node/project.
    Supports filtering by project, node, and date range.
    Paginated — 20 records per page.
    """
    qs = Data.objects.select_related(
        'node', 'node__parcelle', 'node__parcelle__project'
    ).order_by('-published_date')

    # ── Filters ───────────────────────────────────────────────────────────────
    project_id = request.GET.get('project')
    node_id    = request.GET.get('node')
    date_from  = request.GET.get('date_from')
    date_to    = request.GET.get('date_to')

    if project_id:
        qs = qs.filter(node__parcelle__project__polygon_id=project_id)
    if node_id:
        qs = qs.filter(node__id=node_id)

    if date_from:
        qs = qs.filter(published_date__date__gte=date_from)
    if date_to:
        qs = qs.filter(published_date__date__lte=date_to)

    # ── Pagination ────────────────────────────────────────────────────────────
    paginator = Paginator(qs, 30) # 30 per page since it's a table
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    # ── Stats ─────────────────────────────────────────────────────────────────
    total = qs.count()
    
    # Calculate some aggregates for the stats bar
    aggregates = qs.aggregate(
        avg_temp=Avg('temperature'),
        avg_hum=Avg('humidity'),
        avg_fwi=Avg('fwi_predit')
    )
    
    avg_temp = round(aggregates['avg_temp'], 1) if aggregates['avg_temp'] is not None else 0
    avg_hum  = round(aggregates['avg_hum'], 1) if aggregates['avg_hum'] is not None else 0
    avg_fwi  = round(aggregates['avg_fwi'], 2) if aggregates['avg_fwi'] is not None else 0

    projects = Project.objects.all().order_by('name')

    context = {
        'page_obj':    page_obj,
        'projects':    projects,
        'total':       total,
        'avg_temp':    avg_temp,
        'avg_hum':     avg_hum,
        'avg_fwi':     avg_fwi,
        
        # preserve filter values for the form
        'f_project':   project_id or '',
        'f_node':      node_id or '',
        'f_date_from': date_from or '',
        'f_date_to':   date_to or '',
    }
    return render(request, 'supervisor/sensor_history.html', context)


@login_required(login_url='supervisor_login')
@supervisor_required
def delete_sensor_data_supervisor(request, data_id):
    """Supervisor can delete any sensor reading."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    data_record = Data.objects.filter(idData=data_id).first()
    if data_record is None:
        return JsonResponse({'error': f'Data {data_id} not found'}, status=404)

    data_record.delete()
    log.info("Supervisor deleted sensor data %d", data_id)
    return JsonResponse({'success': True})
