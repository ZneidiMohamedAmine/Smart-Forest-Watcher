from django.urls    import path
from .              import  views

urlpatterns = [

    path('client/', views.client_login, name='client_login'),
    path('api/client/login/', views.api_client_login, name='api_client_login'),
    path('api/client/logout/', views.api_client_logout, name='api_client_logout'),
    path('logout_client/', views.sign_out_client, name='logout_client'),

    path('supervisor/',views.supervisor_login, name = "supervisor_login"),
    path('logout_super/', views.sign_out, name = 'logout_supervisor'),
]
