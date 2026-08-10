from django.core.management.base import BaseCommand

from camera_management.workers.dataset_pipeline import run_merge_staging


class Command(BaseCommand):
    help = 'Validate and merge approved StagedCorrection rows into yolo/data/dataset_finale/'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-batch-size', type=int, default=None,
            help='Override MLOPS_MIN_STAGING_BATCH for this run (e.g. --min-batch-size 1 for a demo)',
        )

    def handle(self, *args, **options):
        version = run_merge_staging(min_batch_size=options['min_batch_size'])
        if version:
            self.stdout.write(self.style.SUCCESS(f'Merged into dataset version {version}'))
        else:
            self.stdout.write(self.style.WARNING('Nothing merged (not enough pending corrections, or all invalid).'))
