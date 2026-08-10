from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# Définit les paramètres Django par défaut pour Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')  # Remplace 'project' par le nom réel

app = Celery('project')

# Charge les configs CELERY_ depuis settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover les tâches dans les apps Django
app.autodiscover_tasks(['supervisor.tasks.calcul_fwi', 'supervisor.tasks.Pediction_ml', 'client'])

# camera_management keeps its Celery tasks under workers/ instead of the
# tasks.py convention autodiscover_tasks looks for, so register explicitly.
import camera_management.workers.dataset_pipeline  # noqa: E402,F401

# Beat Schedule : exécute une tâche toutes les 5 minutes
'''app.conf.beat_schedule = {
    'predict_fwi_every_5min': {
        'task': 'supervisor.tasks.receive_sensor_data.receive_sensor_data',  # Appelle d’abord la récupération dynamique
        'schedule': crontab(minute='*/5'),
    },
}'''

'''from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# Définit les paramètres Django par défaut pour Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')  # Remplace 'project' par le nom réel

app = Celery('project')

# Charge les configs CELERY_ depuis settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover les tâches dans les apps Django
app.autodiscover_tasks()

# Beat Schedule : exécute une tâche toutes les 5 minutes
app.conf.beat_schedule = {
    'predict_fwi_every_5min': {
        'task': 'supervisor.tasks.receive_sensor_data.receive_sensor_data',  # Appelle d’abord la récupération dynamique
        'schedule': crontab(minute='*/5'),
    },
}'''
