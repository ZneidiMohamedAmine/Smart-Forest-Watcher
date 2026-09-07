import logging
import json
from django.shortcuts               import render, redirect
from django.contrib.auth            import login, logout
from django.http                    import JsonResponse
from django.utils.http              import url_has_allowed_host_and_scheme
from django.views.decorators.csrf   import csrf_exempt
from django.views.decorators.http   import require_http_methods
from client.models                  import Client, ClientAuthToken
from .forms                         import ClientLoginForm, SupervisorLoginForm
from supervisor.models.supervisor   import Supervisor
from django.contrib.auth.hashers    import check_password

logger = logging.getLogger(__name__)


def _safe_next(request, next_url, default):
    """Only follow a user-supplied ?next= if it's a same-origin relative URL --
    otherwise an attacker-crafted login link could redirect off-site (open redirect)."""
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return default

def _cors(response):
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


def _parse_json(request):
    try:
        return json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return None

@require_http_methods(['GET', 'POST'])
def client_login(request):
    if request.method == 'POST':
        form_client = ClientLoginForm(request.POST)
        if form_client.is_valid():
            email = form_client.cleaned_data['email']
            password = form_client.cleaned_data['password']
            try:
                client = Client.objects.select_related('user').get(email=email)
                if client.user and check_password(password, client.user.password):
                    login(request, client.user)
                    request.session['client_authenticated'] = True
                    request.session['supervisor_authenticated'] = False
                    next_url = _safe_next(request, request.POST.get('next'), 'select_project_of_project')
                    return redirect(next_url)
                else:
                    form_client.add_error(None, "Invalid email or password!!!")
            except Client.DoesNotExist:
                form_client.add_error(None, "Invalid email or password!!!")
        return render(request, 'website/client.html', {'form_client': form_client})
    form_client = ClientLoginForm()
    return render(request, 'website/client.html', {'form_client': form_client})


# CSRF-exempt: called by the Flutter app directly, which has no Django
# session/CSRF cookie to send. Auth is via email+password in the body.
@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def api_client_login(request):
    if request.method == 'OPTIONS':
        return _cors(JsonResponse({}))

    payload = _parse_json(request)
    if payload is None:
        return _cors(JsonResponse({'error': 'Invalid JSON'}, status=400))

    email = (payload.get('email') or '').strip()
    password = (payload.get('password') or '').strip()
    if not email or not password:
        return _cors(JsonResponse({'error': 'Email and password are required'}, status=400))

    try:
        client = Client.objects.select_related('user').get(email=email)
    except Client.DoesNotExist:
        return _cors(JsonResponse({'error': 'Invalid email or password!!!'}, status=401))

    if not client.user or not check_password(password, client.user.password):
        return _cors(JsonResponse({'error': 'Invalid email or password!!!'}, status=401))

    login(request, client.user)
    request.session['client_authenticated'] = True
    request.session['supervisor_authenticated'] = False
    token = ClientAuthToken.issue(client)
    return _cors(JsonResponse({
        'id': client.id,
        'email': client.email,
        'username': client.user.get_username() or client.email,
        'token': token.key,
    }))


# CSRF-exempt: called by the Flutter app directly, which has no Django
# session/CSRF cookie to send. Auth is via the Bearer token header.
@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def api_client_logout(request):
    if request.method == 'OPTIONS':
        return _cors(JsonResponse({}))

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        ClientAuthToken.objects.filter(key=auth_header[len('Bearer '):].strip()).delete()

    # Also unregister this device's push token, so it stops receiving this
    # client's alerts now that they've logged out — otherwise the device
    # keeps getting pushed to indefinitely until a different account logs
    # in on the same device and overwrites the registration.
    payload = _parse_json(request) or {}
    fcm_token = (payload.get('fcm_token') or '').strip()
    if fcm_token:
        from push.models import DeviceToken
        DeviceToken.objects.filter(token=fcm_token).delete()

    return _cors(JsonResponse({}))


def sign_out_client(request):
    if request.session.get('client_authenticated'):
        request.session.flush()
        logout(request)
    return redirect('client_login')



@require_http_methods(['GET', 'POST'])
def supervisor_login(request):
    if request.method == 'POST':
        form = SupervisorLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            supervisor = Supervisor.objects.get(email=email)
            login(request, supervisor.user)
            request.session['supervisor_authenticated'] = True
            request.session['client_authenticated'] = False
            next_url = _safe_next(request, request.POST.get('next'), 'supervisor:dashboard_super')
            return redirect(next_url)
        return render(request, 'website/supervisor.html', {'form': form})
    form = SupervisorLoginForm()
    return render(request, 'website/supervisor.html', {'form': form})




def sign_out(request):
    if request.session.get('supervisor_authenticated'):
        request.session.flush()
        logout(request)
    return redirect('supervisor_login')
