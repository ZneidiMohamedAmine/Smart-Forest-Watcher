import logging
from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
import redis

logger = logging.getLogger(__name__)

@require_http_methods(['GET'])
def health_check(request):
    """Health check endpoint for monitoring."""
    status = {
        'status': 'healthy',
        'checks': {}
    }
    http_status = 200

    checks = {
        'database': _check_database,
        'redis': _check_redis,
        'cache': _check_cache,
    }

    for check_name, check_func in checks.items():
        try:
            checks[check_name] = check_func()
            if not checks[check_name]['healthy']:
                status['status'] = 'degraded'
                http_status = 503
        except Exception as e:
            checks[check_name] = {
                'healthy': False,
                'error': str(e)
            }
            status['status'] = 'unhealthy'
            http_status = 503

    status['checks'] = checks
    return JsonResponse(status, status=http_status)

def _check_database():
    """Check database connectivity."""
    try:
        connection = connections['default']
        connection.ensure_connection()
        return {'healthy': True, 'message': 'Database connected'}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {'healthy': False, 'message': str(e)}

def _check_redis():
    """Check Redis connectivity."""
    try:
        from django.conf import settings
        redis_host = settings.REDIS_HOST
        redis_port = getattr(settings, 'REDIS_PORT', 6379)

        r = redis.Redis(host=redis_host, port=redis_port, socket_connect_timeout=2)
        r.ping()
        return {'healthy': True, 'message': 'Redis connected'}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {'healthy': False, 'message': str(e)}

def _check_cache():
    """Check cache system."""
    try:
        test_key = 'health_check_test'
        cache.set(test_key, 'ok', timeout=1)
        result = cache.get(test_key)
        if result == 'ok':
            return {'healthy': True, 'message': 'Cache working'}
        else:
            return {'healthy': False, 'message': 'Cache get/set failed'}
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {'healthy': False, 'message': str(e)}

@require_http_methods(['GET'])
def readiness_check(request):
    """Readiness check - app is ready to serve traffic."""
    try:
        checks = {
            'database': _check_database(),
            'redis': _check_redis(),
        }

        all_healthy = all(c.get('healthy', False) for c in checks.values())
        status_code = 200 if all_healthy else 503

        return JsonResponse({
            'ready': all_healthy,
            'checks': checks
        }, status=status_code)
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JsonResponse({'ready': False, 'error': str(e)}, status=503)

@require_http_methods(['GET'])
def liveness_check(request):
    """Liveness check - app is running."""
    return JsonResponse({'alive': True}, status=200)
