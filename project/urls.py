from django.contrib import admin
from django.urls    import path, include
from django.conf import settings
from django.conf.urls.static import static
from project.health_check import health_check, readiness_check, liveness_check

urlpatterns = [
    path('admin/',              admin.site.urls),
    path('',                    include('home.urls')),
    path('connect_as/',         include('authentication.urls')),
    path('dashboard_super/',    include('supervisor.urls')),
    path('dashboard_client/',   include('client.urls')),
    path('camera_management/',  include('camera_management.urls')),
    path('i18n/',               include('django.conf.urls.i18n')),
    path('health/',             health_check, name='health_check'),
    path('ready/',              readiness_check, name='readiness_check'),
    path('live/',               liveness_check, name='liveness_check'),
    path('',                    include('django_prometheus.urls')),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

