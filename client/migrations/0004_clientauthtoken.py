from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0003_mobilenotification'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientAuthToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(db_index=True, max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='auth_token', to='client.client')),
            ],
        ),
    ]
