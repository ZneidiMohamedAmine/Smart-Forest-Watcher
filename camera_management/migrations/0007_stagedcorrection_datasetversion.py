from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('camera_management', '0006_detection_annotated_image_detection_is_confirmed_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatasetVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(max_length=32, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('image_count', models.PositiveIntegerField(default=0)),
                ('train_count', models.PositiveIntegerField(default=0)),
                ('val_count', models.PositiveIntegerField(default=0)),
                ('test_count', models.PositiveIntegerField(default=0)),
                ('class_counts', models.JSONField(default=dict)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StagedCorrection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('boxes', models.JSONField(default=list)),
                ('status', models.CharField(choices=[('approved', 'Approved'), ('merged', 'Merged'), ('rejected', 'Rejected')], default='approved', max_length=10)),
                ('reject_reason', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('merged_at', models.DateTimeField(blank=True, null=True)),
                ('detection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='staged_corrections', to='camera_management.detection')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
