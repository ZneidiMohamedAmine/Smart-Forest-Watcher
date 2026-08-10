from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supervisor', '0006_remove_project_city_name_project_city'),
    ]

    operations = [
        migrations.CreateModel(
            name='TTNCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='A label to recognize this app, e.g. the TTN application ID', max_length=100)),
                ('username', models.CharField(help_text='TTN MQTT username, e.g. my-app@ttn', max_length=255)),
                ('api_key', models.CharField(help_text='TTN MQTT password / API key', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('added_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='supervisor.supervisor')),
            ],
        ),
    ]
