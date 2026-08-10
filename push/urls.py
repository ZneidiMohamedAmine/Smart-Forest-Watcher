from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.register_device_token, name='register_device_token'),
]
