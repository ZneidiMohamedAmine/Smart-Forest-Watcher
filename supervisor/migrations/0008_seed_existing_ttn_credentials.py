import os

from django.db import migrations


def seed_credentials(apps, schema_editor):
    TTNCredential = apps.get_model('supervisor', 'TTNCredential')

    existing = [
        {
            'name': 'lorae5app2',
            'username': os.environ.get('TTN_USER_1', 'lorae5app2@ttn'),
            'api_key': os.environ.get('TTN_PASS_1', ''),
        },
        {
            'name': 'chottmariem',
            'username': os.environ.get('TTN_USER_2', 'chottmariem@ttn'),
            'api_key': os.environ.get('TTN_PASS_2', ''),
        },
    ]

    for entry in existing:
        if entry['api_key'] and not TTNCredential.objects.filter(username=entry['username']).exists():
            TTNCredential.objects.create(**entry)


class Migration(migrations.Migration):

    dependencies = [
        ('supervisor', '0007_ttncredential'),
    ]

    operations = [
        migrations.RunPython(seed_credentials, migrations.RunPython.noop),
    ]
