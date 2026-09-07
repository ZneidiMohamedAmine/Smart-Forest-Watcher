from django.core.management.base import BaseCommand
from django.utils import timezone
from client.models import Client, MobileNotification
from client.notifications import send_mobile_notification
from camera_management.models import Camera, Detection


class Command(BaseCommand):
    help = 'Send a fake/test fire alert notification to the mobile app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Target client email (if omitted, sends to all registered clients)',
        )
        parser.add_argument(
            '--title',
            type=str,
            default=None,
            help='Alert title (default: "Fire Detected — <Camera> (<Project>)")',
        )
        parser.add_argument(
            '--body',
            type=str,
            default=None,
            help='Alert message body',
        )
        parser.add_argument(
            '--confidence',
            type=float,
            default=0.92,
            help='Confidence score between 0.0 and 1.0 (default: 0.92)',
        )
        parser.add_argument(
            '--camera-id',
            type=str,
            default=None,
            help='Camera ID to associate with the alert',
        )
        parser.add_argument(
            '--attach-latest-detection',
            action='store_true',
            help='Attach the latest real detection image and record if available',
        )

    def handle(self, *args, **options):
        clients = Client.objects.all()
        if options['email']:
            clients = clients.filter(email=options['email'])
            if not clients.exists():
                self.stderr.write(self.style.ERROR(f"No client found with email: {options['email']}"))
                return

        if not clients.exists():
            self.stderr.write(self.style.ERROR("No clients found in the database."))
            return

        camera = None
        if options['camera_id']:
            camera = Camera.objects.filter(camera_id=options['camera_id']).first()
        if not camera:
            camera = Camera.objects.first()

        detection = None
        if options['attach_latest_detection']:
            detection = Detection.objects.order_by('-detected_at').first()

        camera_name = camera.name if camera else 'Sector 1 Camera'
        camera_id = camera.camera_id if camera else 'pi-cam-test'
        project_name = camera.project.name if (camera and camera.project) else 'Forest Reserve'
        parcelle_name = (camera.parcelle.name if (camera and camera.parcelle) else 'Zone Alpha')
        confidence = options['confidence']

        now_str = timezone.now().strftime('%Y-%m-%d %H:%M UTC')

        title = options['title'] or f"Fire Detected - {camera_name} ({project_name})"
        body = options['body'] or (
            f"Camera '{camera_name}' detected fire in '{parcelle_name}'.\n"
            f"Confidence: {confidence * 100:.1f}%\n"
            f"Time: {now_str} [TEST ALERT]"
        )

        data = {
            'source': 'camera',
            'camera_id': camera_id,
            'camera_name': camera_name,
            'parcelle': parcelle_name,
            'project': project_name,
            'confidence': confidence,
            'detected_at': timezone.now().isoformat(),
            'is_test': True,
        }

        if detection and detection.image:
            data['image_url'] = detection.image.url

        for client in clients:
            self.stdout.write(f"Sending test alert to {client.email} ({client.firstName} {client.lastName})...")
            result = send_mobile_notification(
                user_id=client.email,
                title=title,
                body=body,
                data=data,
                camera=camera,
                detection=detection,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"[SUCCESS] Alert dispatched successfully (Notification ID: {result.get('notification_id')})"
                )
            )
