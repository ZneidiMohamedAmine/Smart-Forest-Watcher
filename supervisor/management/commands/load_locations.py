import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from supervisor.models.localisation import Localisation

DEFAULT_CSV = os.path.join(settings.BASE_DIR, 'supervisor', 'fixtures', 'tunisia_locations.csv')


class Command(BaseCommand):
    help = 'Load Tunisia locations (gouvernorat / delegation / localite) into the Localisation table from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=DEFAULT_CSV,
            help='Path to the locations CSV (columns: id, gouvernorat_libelle, delegation_libelle, localite_libelle, latitude, longitude)',
        )

    def handle(self, *args, **options):
        csv_path = options['file']

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f'CSV file not found: {csv_path}'))
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with open(csv_path, encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                localite = (row.get('localite_libelle') or '').strip()
                if not localite:
                    skipped_count += 1
                    continue

                gouvernorat = (row.get('gouvernorat_libelle') or '').strip() or None
                delegation = (row.get('delegation_libelle') or '').strip() or None

                try:
                    latitude = row.get('latitude') or None
                    longitude = row.get('longitude') or None
                    loc, created = Localisation.objects.update_or_create(
                        gouvernorat_libelle=gouvernorat,
                        delegation_libelle=delegation,
                        localite_libelle=localite,
                        defaults={
                            'latitude': latitude,
                            'longitude': longitude,
                        },
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                except Exception as e:
                    skipped_count += 1
                    self.stderr.write(self.style.WARNING(f'Skipped "{localite}": {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'Done. Created {created_count}, updated {updated_count}, skipped {skipped_count}.'
        ))
