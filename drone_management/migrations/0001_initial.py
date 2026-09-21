from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('supervisor', '0011_alter_project_client'),
    ]

    operations = [
        migrations.CreateModel(
            name='Drone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('drone_id', models.CharField(max_length=100, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('api_key', models.CharField(default='', max_length=64)),
                ('is_active', models.BooleanField(default=True)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('battery_level', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('last_seen', models.DateTimeField(blank=True, null=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='drones', to='supervisor.project')),
            ],
        ),
    ]
