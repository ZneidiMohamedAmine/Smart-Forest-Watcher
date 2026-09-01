from django.shortcuts                   import render, get_object_or_404
from django.contrib.auth.decorators     import login_required
from authentication.decorators          import client_required
from supervisor.models.project          import Project
from supervisor.models.data             import Data



@login_required(login_url='client_login')
@client_required
def index1(request, project_id):
    project = get_object_or_404(Project, polygon_id=project_id, client=request.user.client)
    latest_data = (
        Data.objects
        .filter(node__parcelle__project=project)
        .order_by('-published_date')
        .first()
    )
    return render(request, 'website/index1.html', {'project': project, 'latest_data': latest_data})