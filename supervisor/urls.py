from django.urls    import path
from .              import views
from camera_management import views as cam_views


app_name = 'supervisor'

urlpatterns = [
        #######* Dashboard / Global endpoints ##########
    path('', views.index, name='dashboard_super'),
    path('get_all_assets/', views.get_all_assets, name='get_all_assets'),
    
        #######* CRUD OF CLIENT  ##########
    path('list_client/', views.list_clients, name="list_client"),
    path('add_client/', views.add_client, name="add_client"),
    path('update_client/<int:pk>/', views.update_client, name="update_client"),
    path('delete_client/<int:pk>/', views.delete_client, name="delete_client"),

        #######* CRUD OF Project  ##########
    path('project_list/', views.list_project, name='list_project'),
    path('add_project/', views.add_project, name= 'add_project'),
    path('update_project/<int:project_id>', views.update_project, name='update_project'),
    path('delete_project/<int:pk>', views.delete_project, name='delete_project'),
    path('add_parcelle/', views.parcelle_create, name = 'add_parcelle'),
    path('get_parcelles_for_project/', views.get_parcelles_for_project, name='get_parcelles_for_project'),

        #######* Node Related  ##########
    path('add_node/', views.node_create, name='add_node'),
    path('get_parcelles_with_nodes_for_project/', views.get_parcelles_with_nodes_for_project, name='get_parcelles_with_nodes_for_project'),
    path('get_project_details/<int:project_id>/', views.get_project_details, name='get_project_details'),
    path('delete_node/<int:node_id>/', views.delete_node, name='delete_node'),

        #######* Camera Related  ##########
    path('add_camera/', cam_views.add_camera, name='add_camera'),
    path('get_cameras_for_project/', cam_views.list_cameras_for_project, name='get_cameras_for_project'),
    path('delete_camera/<int:camera_id>/', cam_views.delete_camera, name='delete_camera'),
    path('update_parcels_nodes/', views.update_parcels_nodes, name='update_parcels_nodes'),

        #######* Detection History  ##########
    path('detection_history/', cam_views.detection_history, name='detection_history'),
    path('detection_history/delete/<int:detection_id>/', cam_views.delete_detection_supervisor, name='delete_detection_supervisor'),
    path('detection_history/update_status/<int:detection_id>/', cam_views.update_detection_status, name='update_detection_status'),

        #######* Training Dataset Review (MLOps human-in-the-loop)  ##########
    path('review_queue/', cam_views.review_queue, name='review_queue'),
    path('review_queue/<int:detection_id>/', cam_views.review_detection, name='review_detection'),

        #######* Sensor History  ##########
    path('sensor_history/', views.sensor_history, name='sensor_history'),
    path('sensor_history/delete/<int:data_id>/', views.delete_sensor_data_supervisor, name='delete_sensor_data_supervisor'),

        #######* TTN Credentials  ##########
    path('ttn_credentials/', views.list_ttn_credentials, name='list_ttn_credentials'),
    path('ttn_credentials/add/', views.add_ttn_credential, name='add_ttn_credential'),
    path('ttn_credentials/delete/<int:pk>/', views.delete_ttn_credential, name='delete_ttn_credential'),
]


