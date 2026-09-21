from django.db import migrations, models
import django.db.models.deletion


def backfill_project(apps, schema_editor):
    """Every existing Detection is camera-sourced — copy camera.project onto
    the new denormalized project field so nothing needs a null check."""
    Detection = apps.get_model('camera_management', 'Detection')
    for detection in Detection.objects.filter(project__isnull=True, camera__isnull=False).select_related('camera'):
        detection.project_id = detection.camera.project_id
        detection.save(update_fields=['project'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('camera_management', '0007_stagedcorrection_datasetversion'),
        ('drone_management', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='detection',
            name='camera',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='detections', to='camera_management.camera'),
        ),
        migrations.AddField(
            model_name='detection',
            name='drone',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='detections', to='drone_management.drone'),
        ),
        migrations.AddField(
            model_name='detection',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='detections', to='supervisor.project'),
        ),
        migrations.RunPython(backfill_project, noop_reverse),
    ]
