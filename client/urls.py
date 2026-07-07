from django.urls    import path
from .              import views
from .              import notifications
from camera_management import views as cam_views

urlpatterns = [
    path('api/notifications', notifications.list_notifications, name='api_list_notifications'),
    path('api/notifications/send', notifications.send_notification, name='api_send_notification'),
    path('<int:project_id>/', views.index1, name='dashboard_client'),
    path('node_detail/<int:project_id>/<int:node_id>/', views.node_detail, name='node_detail'),
    path('node_list/<int:project_id>/', views.node_list, name='node_list'),
    path('camera_detail/<int:project_id>/<int:camera_id>/', cam_views.camera_detail, name='camera_detail'),
    path('select_project_of_client/', views.select_client_of_project, name='select_project_of_project'),
    path('fetch_parcelles_for_project/', views.fetch_parcelles_for_project, name = 'fetch_parcelles_for_project'),
    path('delete_detection/<int:detection_id>/', cam_views.delete_detection, name='delete_detection'),
]
