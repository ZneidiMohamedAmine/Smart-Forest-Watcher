import logging
import json
from django.shortcuts               import render, redirect
from django.contrib.auth            import login, logout
from django.http                    import JsonResponse
from django.views.decorators.csrf   import csrf_exempt
from django.views.decorators.http   import require_http_methods
from client.models                  import Client
from .forms                         import ClientLoginForm, SupervisorLoginForm
from supervisor.models.supervisor   import Supervisor
from django.contrib.auth.hashers    import check_password

logger = logging.getLogger(__name__)

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

def client_login(request):
    if request.method == 'POST':
        form_client = ClientLoginForm(request.POST)
        if form_client.is_valid():
            email = form_client.cleaned_data['email']
            password = form_client.cleaned_data['password']
            try:
                client = Client.objects.get(email=email)
                if check_password(password, client.password):
                    login(request, client.user)
                    request.session['client_authenticated'] = True
                    request.session['supervisor_authenticated'] = False
                    next_url = request.POST.get('next', 'select_project_of_project')
                    return redirect(next_url)
                else:
                    form_client.add_error(None, "Invalid email or password!!!")
            except Client.DoesNotExist:
                form_client.add_error(None, "Invalid email or password!!!")
        return render(request, 'website/client.html', {'form_client': form_client})
    form_client = ClientLoginForm()
    return render(request, 'website/client.html', {'form_client': form_client})


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

    if not check_password(password, client.password):
        return _cors(JsonResponse({'error': 'Invalid email or password!!!'}, status=401))

    login(request, client.user)
    request.session['client_authenticated'] = True
    request.session['supervisor_authenticated'] = False
    return _cors(JsonResponse({
        'id': client.id,
        'email': client.email,
        'username': client.user.get_username() or client.email,
    }))


def sign_out_client(request):
    if request.session.get('client_authenticated'):
        request.session.flush()
        logout(request)
    return redirect('client_login')



def supervisor_login(request):
    if request.method == 'POST':
        form = SupervisorLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            supervisor = Supervisor.objects.get(email=email)
            login(request, supervisor.user)
            request.session['supervisor_authenticated'] = True
            request.session['client_authenticated'] = False
            next_url = request.POST.get('next', 'supervisor:dashboard_super')
            return redirect(next_url)
        return render(request, 'website/supervisor.html', {'form': form})
    form = SupervisorLoginForm()
    return render(request, 'website/supervisor.html', {'form': form})




def sign_out(request):
    if request.session.get('supervisor_authenticated'):
        request.session.flush()
        logout(request)
    return redirect('supervisor_login')
