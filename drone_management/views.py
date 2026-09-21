from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from authentication.decorators import supervisor_required
from authentication.access     import accessible_projects, can_access_project
from .models import Drone
from .forms  import DroneForm


@login_required(login_url='supervisor_login')
@supervisor_required
def list_drones(request):
    drones = Drone.objects.filter(project__in=accessible_projects(request.user)).select_related('project').order_by('name')
    form = DroneForm()
    form.fields['project'].queryset = accessible_projects(request.user)
    return render(request, 'website/drones.html', {'drones': drones, 'form': form})


@login_required(login_url='supervisor_login')
@supervisor_required
@require_http_methods(['POST'])
def add_drone(request):
    form = DroneForm(request.POST)
    if form.is_valid():
        drone = form.save(commit=False)
        if not can_access_project(request.user, drone.project):
            messages.error(request, 'Not authorized for this project.')
            return redirect('supervisor:list_drones')
        drone.save()
        messages.success(request, f'Drone "{drone.name}" added.')
    else:
        messages.error(request, 'Please correct the errors below.')
    return redirect('supervisor:list_drones')


@login_required(login_url='supervisor_login')
@supervisor_required
def update_drone(request, pk):
    drone = get_object_or_404(Drone, pk=pk)
    if not can_access_project(request.user, drone.project):
        return JsonResponse({'error': 'Not authorized for this project.'}, status=403)

    if request.method == 'GET':
        # AJAX: prefill the edit modal
        return JsonResponse({
            'id':        drone.id,
            'name':      drone.name,
            'drone_id':  drone.drone_id,
            'api_key':   drone.api_key,
            'project_id': drone.project_id,
            'is_active': drone.is_active,
        })

    if request.method == 'POST':
        form = DroneForm(request.POST, instance=drone)
        if form.is_valid():
            updated = form.save(commit=False)
            if not can_access_project(request.user, updated.project):
                messages.error(request, 'Not authorized for this project.')
                return redirect('supervisor:list_drones')
            updated.save()
            messages.success(request, f'Drone "{updated.name}" updated.')
        else:
            messages.error(request, 'Please correct the errors below.')
        return redirect('supervisor:list_drones')

    return JsonResponse({'error': 'Invalid request method.'}, status=405)


@login_required(login_url='supervisor_login')
@supervisor_required
@require_http_methods(['POST'])
def delete_drone(request, pk):
    drone = get_object_or_404(Drone, pk=pk)
    if not can_access_project(request.user, drone.project):
        return JsonResponse({'error': 'Not authorized for this project.'}, status=403)
    drone.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Drone removed.')
    return redirect('supervisor:list_drones')
