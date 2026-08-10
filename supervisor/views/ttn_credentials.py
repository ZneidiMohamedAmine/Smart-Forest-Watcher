from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from authentication.decorators import supervisor_required
from supervisor.forms import TTNCredentialForm
from supervisor.models.ttn_credential import TTNCredential
from supervisor.models.supervisor import Supervisor


@login_required(login_url='supervisor_login')
@supervisor_required
def list_ttn_credentials(request):
    """Shared list — any supervisor can see/add/remove any TTN app for now."""
    credentials = TTNCredential.objects.select_related('added_by').order_by('-created_at')
    form = TTNCredentialForm()
    return render(request, 'website/ttn_credentials.html', {'credentials': credentials, 'form': form})


@login_required(login_url='supervisor_login')
@supervisor_required
@require_http_methods(['POST'])
def add_ttn_credential(request):
    form = TTNCredentialForm(request.POST)
    if form.is_valid():
        credential = form.save(commit=False)
        credential.added_by = Supervisor.objects.filter(user=request.user).first()
        credential.save()
        messages.success(request, 'TTN app added. It will connect the next time the sensor feed reloads.')
    else:
        messages.error(request, 'Please correct the errors below.')
    return redirect('supervisor:list_ttn_credentials')


@login_required(login_url='supervisor_login')
@supervisor_required
@require_http_methods(['POST'])
def delete_ttn_credential(request, pk):
    credential = get_object_or_404(TTNCredential, pk=pk)
    credential.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'TTN app removed.')
    return redirect('supervisor:list_ttn_credentials')
