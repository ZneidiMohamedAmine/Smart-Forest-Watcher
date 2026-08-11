from django.db import migrations


def grandfather_existing_supervisors(apps, schema_editor):
    Supervisor = apps.get_model('supervisor', 'Supervisor')
    Supervisor.objects.update(is_admin=True)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('supervisor', '0009_supervisor_is_admin_supervisor_projects'),
    ]

    operations = [
        migrations.RunPython(grandfather_existing_supervisors, reverse_noop),
    ]
