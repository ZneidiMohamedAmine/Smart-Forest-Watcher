from django.urls import path
from . import api

app_name = 'drone_management'

urlpatterns = [
    # ── Drone unit upload (no auth middleware, uses api_key field) ───────────
    path('api/upload/', api.receive_drone_upload, name='drone_upload'),
]
