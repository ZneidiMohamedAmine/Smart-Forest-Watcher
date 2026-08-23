# authentication/middlewares.py

from django.utils.deprecation import MiddlewareMixin

class MediaCorsMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if request.path.startswith('/img/') or '/api/' in request.path:
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response['Cross-Origin-Resource-Policy'] = 'cross-origin'
        return response


class SeparateSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            if hasattr(request.user, 'client'):
                request.session['client_authenticated'] = True
                request.session['supervisor_authenticated'] = False
            elif hasattr(request.user, 'supervisor'):
                request.session['supervisor_authenticated'] = True
                request.session['client_authenticated'] = False

    def process_response(self, request, response):
        if request.user.is_authenticated:
            if hasattr(request.user, 'client'):
                request.session['client_authenticated'] = True
            elif hasattr(request.user, 'supervisor'):
                request.session['supervisor_authenticated'] = True
        return response
