import json
import traceback
from django.contrib.gis.geos.error import GEOSException
from supervisor.models.node         import Node
from django.db.models               import Count, Value
from django.contrib.gis.geos        import Polygon
from django.contrib                 import messages
from django.http                    import JsonResponse
from django.shortcuts               import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from authentication.decorators      import supervisor_required
from authentication.access          import accessible_projects, can_access_project
from django.db.models.functions     import Concat
from django.contrib.gis.geos        import Point
from supervisor.models.parcelle     import Parcelle 
from supervisor.models.project      import Project
from supervisor.forms               import ProjectForm
from supervisor.forms               import ParcelleForm
from supervisor.forms               import NodeForm
from camera_management.forms         import CameraForm



@login_required(login_url='supervisor_login')
@supervisor_required
def list_project(request):
    client_id = request.GET.get('client_id')
    my_projects = accessible_projects(request.user)
    projects_by_client = my_projects.annotate(
        full_name=Concat('client__firstName', Value(' '), 'client__lastName')
    ).values('full_name', 'client_id').annotate(count=Count('client')).order_by('full_name')
    if client_id:
        projects = my_projects.filter(client_id=client_id)
    else:
        projects = my_projects
    form = ProjectForm()
    node_form = NodeForm()
    camera_form = CameraForm()
    parcelle_form = ParcelleForm()
    return render(request, 'website/project.html', {
        'projects_by_client': projects_by_client,
        'projects': projects,
        'form': form,
        'node_form': node_form,
        'camera_form': camera_form,
        'parcelle_form': parcelle_form,
        'show_modal': True if client_id else False
    })

@login_required(login_url='supervisor_login')
@supervisor_required
def add_project(request):
    form = ProjectForm(request.POST or None, request.FILES or None)
    data = {'latitude': None, 'longitude': None}
    client_name = None
    project_name = None

    if request.method == 'POST':
        if form.is_valid():
            project = form.save(commit=False)
            project_name = project.name
            client_name = f"{project.client.firstName} {project.client.lastName}"

            #! Vérifiez si un projet avec le même nom et la même ville existe déjà
            existing_project = Project.objects.filter(name=project_name, city=project.city).first()

            if existing_project:
                if not can_access_project(request.user, existing_project):
                    messages.error(request, 'A project with that name and city already exists and you are not authorized to modify it.')
                    return redirect('supervisor:list_project')
                existing_project.descp = form.cleaned_data.get('descp', existing_project.descp)
                existing_project.date_debut = form.cleaned_data.get('date_debut', existing_project.date_debut)
                existing_project.date_fin = form.cleaned_data.get('date_fin', existing_project.date_fin)
                existing_project.client = form.cleaned_data.get('client', existing_project.client)
                existing_project.save()
                messages.success(request, 'Project updated successfully.')
                project = existing_project
            else:
                project.save()
                form.save_m2m()
                supervisor = getattr(request.user, 'supervisor', None)
                if supervisor and not supervisor.is_admin:
                    supervisor.projects.add(project)
                messages.success(request, 'Project added successfully.')
            
            latitude = float(project.city.latitude)
            longitude = float(project.city.longitude)
            data = {'latitude': latitude, 'longitude': longitude}
            request.session['project_added'] = True  
            request.session['map_data'] = data
            parcelle_form = ParcelleForm(initial={'project': project})
            node_form = NodeForm()
            camera_form = CameraForm()
            # Fetch project lists to ensure UI updates without refresh
            my_projects = accessible_projects(request.user)
            projects_by_client = my_projects.annotate(
                full_name=Concat('client__firstName', Value(' '), 'client__lastName')
            ).values('full_name', 'client_id').annotate(count=Count('client')).order_by('full_name')
            projects = my_projects

            return render(request, 'website/project.html', {
                'projects_by_client': projects_by_client,
                'projects': projects,
                'form': form,
                'show_map_modal': True,
                'data': data,
                'parcelle_form': parcelle_form,
                'node_form': node_form,
                'camera_form': camera_form,
                'project_name': project_name,
                'client_name': client_name
            })
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProjectForm()

    if 'map_data' in request.session:
        data = request.session['map_data']

    show_map_modal = request.session.get('project_added', False)
    my_projects = accessible_projects(request.user)
    projects_by_client = my_projects.annotate(
        full_name=Concat('client__firstName', Value(' '), 'client__lastName')
    ).values('full_name', 'client_id').annotate(count=Count('client')).order_by('full_name')
    projects = my_projects

    response = render(request, 'website/project.html', {
        'projects_by_client': projects_by_client,
        'projects': projects,
        'form': form,
        'show_map_modal': show_map_modal,
        'data': data,
        'project_name': project_name,
        'client_name': client_name,
        'node_form': NodeForm(),
        'camera_form': CameraForm(),
        'parcelle_form': ParcelleForm(),
    })

    request.session['project_added'] = False
    request.session['map_data'] = None

    return response


@login_required(login_url='supervisor_login')
@supervisor_required
def get_project_details(request, project_id):
    try:
        project = Project.objects.get(pk=project_id)
        if not can_access_project(request.user, project):
            return JsonResponse({'error': 'Not authorized for this project.'}, status=403)
        data = {
            'project_name': project.name,
            'client_name': f"{project.client.firstName} {project.client.lastName}",
            'latitude': project.city.latitude,
            'longitude': project.city.longitude,
        }
        return JsonResponse(data)
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)


@login_required(login_url='supervisor_login')
@supervisor_required
def delete_project(request, pk):
    from django.db import connection
    project = get_object_or_404(Project, pk=pk)
    if not can_access_project(request.user, project):
        messages.error(request, 'You are not authorized to delete this project.')
        return redirect('supervisor:list_project')

    # 1. Modern ORM cleanup
    project.cameras.all().delete()
    project.parcelle.all().delete() 
    
    # 2. Legacy "Ghost Table" cleanup
    # The IntegrityError reveals an old 'supervisor_camera' table exists that the ORM doesn't see.
    with connection.cursor() as cursor:
        try:
            cursor.execute("DELETE FROM supervisor_camera WHERE project_id = %s", [pk])
        except Exception:
            # Table might not exist in all environments, ignore if it fails
            pass
            
    # 3. Final Project Deletion
    project.delete()
    messages.success(request, f'Project {project.name} deleted successfully.')
    return redirect('supervisor:list_project')


    return redirect('supervisor:list_project')




@login_required(login_url='supervisor_login')
@supervisor_required
def parcelle_create(request):
    if request.method == 'POST':
        form = ParcelleForm(request.POST)
        if form.is_valid():
            coordinates_data = request.POST.get('coordinates')
            parcelle_id = request.POST.get('parcelle_id', None)
            try:
                coordinates = json.loads(coordinates_data)
                if coordinates[0] != coordinates[-1]:
                    coordinates.append(coordinates[0])
                polygon = Polygon(coordinates)

                if parcelle_id:
                    parcelle = get_object_or_404(Parcelle, id=parcelle_id)
                    if not can_access_project(request.user, parcelle.project):
                        return JsonResponse({'error': 'Not authorized for this project.'}, status=403)
                    parcelle.polygon = polygon
                    parcelle.save()
                    message = 'Polygon updated successfully.'
                else:
                    new_parcelle_project = form.cleaned_data.get('project')
                    if not can_access_project(request.user, new_parcelle_project):
                        return JsonResponse({'error': 'Not authorized for this project.'}, status=403)

                    existing_parcelles = Parcelle.objects.all()
                    for existing_parcelle in existing_parcelles:
                        if existing_parcelle.polygon and polygon.equals_exact(existing_parcelle.polygon, tolerance=1e-9):
                            return JsonResponse({'error': {'name': [{'message': 'A parcel with these coordinates already exists.', 'code': 'unique'}]}}, status=400)

                    parcelle = form.save(commit=False)
                    parcelle.polygon = polygon
                    parcelle.save()
                    message = 'Polygon added successfully.'

                parcels = [{
                    'id': p.id,
                    'name': p.name,
                    'coordinates': list(p.polygon.coords[0])
                } for p in Parcelle.objects.filter(project=parcelle.project) if p.polygon]

                return JsonResponse({'message': message, 'parcels': parcels}, status=200)
            except GEOSException as e:
                traceback.print_exc()
                return JsonResponse({'error': {'coordinates': [{'message': f'Geometry error: {e}', 'code': 'invalid'}]}}, status=400)
            except (ValueError, TypeError) as e:
                traceback.print_exc()
                return JsonResponse({'error': {'coordinates': [{'message': f'Invalid coordinates format: {e}', 'code': 'invalid'}]}}, status=400)
            except Exception as e:
                traceback.print_exc()
                return JsonResponse({'error': {'coordinates': [{'message': f'Unexpected error: {e}', 'code': 'invalid'}]}}, status=500)
        else:
            errors = form.errors.get_json_data()
            return JsonResponse({'error': errors}, status=400)
    else:
        form = ParcelleForm()
        projects = accessible_projects(request.user)
        project_data = []

        for project in projects:
            parcelles = Parcelle.objects.filter(project=project)
            project_parcelles = [{
                'id': parcelle.id,
                'name': parcelle.name,
                'coordinates': list(parcelle.polygon.coords[0])
            } for parcelle in parcelles if parcelle.polygon]
            project_data.append({
                'project': {
                    'id': project.polygon_id,
                    'name': project.name,
                    'latitude': project.city.latitude if project.city else None,
                    'longitude': project.city.longitude if project.city else None
                },
                'parcelles': project_parcelles
            })

        return render(request, 'website/project.html', {
            'form': form,
            'project_data': project_data,
            'node_form': NodeForm(),
            'camera_form': CameraForm(),
            'parcelle_form': form, 
        })



@login_required(login_url='supervisor_login')
@supervisor_required
def get_parcelles_for_project(request):
    project_id = request.GET.get('project_id')
    if project_id:
        project = get_object_or_404(Project, pk=project_id)
        if not can_access_project(request.user, project):
            return JsonResponse({'error': 'Not authorized for this project.'}, status=403)
        parcelles = Parcelle.objects.filter(project_id=project_id)
        parcelle_data = [{
            'id': parcelle.id,
            'name': parcelle.name,
            'coordinates': list(parcelle.polygon.coords[0])
        } for parcelle in parcelles if parcelle.polygon]
        return JsonResponse({'parcelles': parcelle_data}, status=200)
    else:
        return JsonResponse({'error': 'No project ID provided.'}, status=400)
    


@login_required(login_url='supervisor_login')
@supervisor_required
def node_create(request):
    if request.method == 'POST':
        node_form = NodeForm(request.POST)

        if node_form.is_valid():
            coordinates_data = request.POST.get('position')
            parcelle_id = request.POST.get('parcelle')
            try:
                coordinates = coordinates_data.strip('POINT()').split()
                longitude = float(coordinates[0])
                latitude = float(coordinates[1])
                point = Point(latitude, longitude)
                print(point)
                parcelle = get_object_or_404(Parcelle, id=parcelle_id)
                if not can_access_project(request.user, parcelle.project):
                    return JsonResponse({'error': 'Not authorized for this project.'}, status=403)

                if parcelle.polygon.contains(point):
                    node = node_form.save(commit=False)
                    node.position = point
                    node.latitude = latitude
                    node.longitude = longitude
                    node.parcelle = parcelle
                    node.save()
                    message = 'Node added successfully.'
                    
                    nodes = [{
                        'id': n.id,
                        'name': n.name,
                        'latitude': n.position.x,
                        'longitude': n.position.y,
                        'ref': n.reference
                    } for n in Node.objects.filter(parcelle=node.parcelle)]
                    
                    return JsonResponse({
                        'message': message, 
                        'nodes': nodes,
                        'parcelle_id': parcelle.id,
                        'project_id': parcelle.project.polygon_id,
                        'project_name': parcelle.project.name,
                        'latitude': parcelle.project.city.latitude,
                        'longitude': parcelle.project.city.longitude
                    }, status=200)
                else:
                    return JsonResponse({'error': {'_all__': 'The node must be placed inside the plot.'}}, status=400)
            except (ValueError, TypeError) as e:
                return JsonResponse({'error': {'coordinates': [{'message': 'Invalid coordinates format.', 'code': 'invalid'}]}}, status=400)
        else:
            errors = node_form.errors.get_json_data()
            return JsonResponse({'error': errors}, status=400)
    else:
        node_form = NodeForm()
        return render(request, 'website/project.html', {
            'node_form': node_form,
            'camera_form': CameraForm(),
            'parcelle_form': ParcelleForm(),
            'form': ProjectForm(),
        })

    


@login_required(login_url='supervisor_login')
@supervisor_required
def get_parcelles_with_nodes_for_project(request):
    project_id = request.GET.get('project_id')
    if project_id:
        project = get_object_or_404(Project, pk=project_id)
        if not can_access_project(request.user, project):
            return JsonResponse({'error': 'Not authorized for this project.'}, status=403)
        parcelles = Parcelle.objects.filter(project_id=project_id)
        parcelle_data = []
        for parcelle in parcelles:
            if not parcelle.polygon:
                continue
            nodes = Node.objects.filter(parcelle=parcelle)
            node_data = [{
                'id': node.id,
                'name': node.name,
                'latitude': node.position.x,
                'longitude': node.position.y,
                'ref': node.reference
            } for node in nodes]
            parcelle_data.append({
                'id': parcelle.id,
                'name': parcelle.name,
                'coordinates': list(parcelle.polygon.coords[0]),
                'nodes': node_data
            })
        return JsonResponse({'parcelles': parcelle_data}, status=200)
    else:
        return JsonResponse({'error': 'No project ID provided.'}, status=400)











































































@login_required(login_url='supervisor_login')
@supervisor_required
def update_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if not can_access_project(request.user, project):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': 'Not authorized for this project.'}, status=403)
        messages.error(request, 'You are not authorized to modify this project.')
        return redirect('supervisor:list_project')

    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project updated successfully.')
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                project_data = {
                    'pk': project.pk,
                    'name': project.name,
                    'description': project.description,
                    'start_date': project.start_date,
                    'end_date': project.end_date,
                }
                return JsonResponse({'success': True, 'project': project_data})
            return redirect('supervisor:list_project')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProjectForm(instance=project)

    return render(request, 'website/project.html', {
        'form': form,
        'update': True,
        'project': project,
        'node_form': NodeForm(),
        'camera_form': CameraForm(),
        'parcelle_form': ParcelleForm(),
    })










@login_required(login_url='supervisor_login')
@supervisor_required
def update_parcels_nodes(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        project_id = data.get('project_id')
        polygons = data.get('polygons', [])
        markers = data.get('markers', [])
        deleted_polygons = data.get('deleted_polygons', [])
        deleted_markers = data.get('deleted_markers', [])

        project = get_object_or_404(Project, pk=project_id)
        if not can_access_project(request.user, project):
            return JsonResponse({'error': 'Not authorized for this project.'}, status=403)

        #! Supprimer les parcelles
        for parcelle_id in deleted_polygons:
            parcelle = get_object_or_404(Parcelle, pk=parcelle_id, project=project)
            parcelle.delete()

        #! Supprimer les nœuds
        for node_id in deleted_markers:
            node = get_object_or_404(Node, pk=node_id, parcelle__project=project)
            node.delete()

        #TODO Mettre à jour les parcelles
        for polygon_data in polygons:
            parcelle_id = polygon_data.get('id')
            coordinates = polygon_data.get('coordinates')
            if parcelle_id:
                parcelle = get_object_or_404(Parcelle, pk=parcelle_id, project=project)
                parcelle.polygon = Polygon(coordinates)
                parcelle.save()
            else:
                Parcelle.objects.create(project=project, polygon=Polygon(coordinates))

        #TODO Mettre à jour les nœuds
        for marker_data in markers:
            node_id = marker_data.get('id')
            latitude = marker_data.get('latitude')
            longitude = marker_data.get('longitude')
            modified = marker_data.get('modified', False)
            if node_id and modified:
                node = get_object_or_404(Node, pk=node_id, parcelle__project=project)
                node.position = Point(latitude, longitude)  # longitude, latitude
                node.latitude = latitude
                node.longitude = longitude
                node.save()
            elif not node_id:
                Node.objects.create(parcelle=project, position=Point(latitude, longitude), latitude=latitude, longitude=longitude)

        return JsonResponse({'message': 'Parcels and nodes updated successfully.'}, status=200)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)


@login_required(login_url='supervisor_login')
@supervisor_required
def delete_node(request, node_id):
    if request.method == 'POST':
        node = get_object_or_404(Node.objects.select_related('parcelle__project'), pk=node_id)
        if not can_access_project(request.user, node.parcelle.project):
            return JsonResponse({'error': 'Not authorized for this project.'}, status=403)
        node.delete()
        return JsonResponse({'success': True, 'message': 'Node deleted successfully.'})
    return JsonResponse({'error': 'Invalid request method.'}, status=400)