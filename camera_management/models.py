from django.contrib.gis.db import models
from supervisor.models.project   import Project
from supervisor.models.parcelle  import Parcelle


class Camera(models.Model):
    """
    A camera unit deployed in the field, linked to both a Project and a Parcelle.
    GPS position is set via Leaflet Draw (same UX as adding a Node).
    The api_key is sent by the Raspberry Pi with every detection upload.
    """
    project              = models.ForeignKey(Project,  on_delete=models.CASCADE, related_name='cameras')
    parcelle             = models.ForeignKey(Parcelle, on_delete=models.CASCADE, related_name='cameras', null=True)
    camera_id            = models.CharField(max_length=100, unique=True)
    name                 = models.CharField(max_length=100)
    location_description = models.CharField(max_length=255, blank=True)
    position             = models.PointField(null=True, blank=True)          # Leaflet Draw point
    latitude             = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude            = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    api_key              = models.CharField(max_length=64, default='')       # RPi auth token
    is_active            = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.camera_id})"


class Detection(models.Model):
    """
    Stores fire detection images for a camera.
    ForeignKey allows a full history — the latest is ordered first by detected_at.
    bounding_boxes: list of {x1, y1, x2, y2, confidence} dicts from YOLO output.
    """
    camera           = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='detections')
    confidence_score = models.FloatField()
    bounding_boxes   = models.JSONField(blank=True, null=True)
    image            = models.ImageField(upload_to='detections/')
    detected_at      = models.DateTimeField(auto_now_add=True)
    server_confidence = models.FloatField(null=True, blank=True)   # yolo26m score
    annotated_image   = models.ImageField(upload_to='detections/annotated/', null=True, blank=True)
    is_confirmed      = models.BooleanField(null=True, blank=True) # None=pending, True=confirmed, False=rejected


    def __str__(self):
        return f"🔥 Fire @ {self.camera.name}  |  conf={self.confidence_score:.2f}  |  {self.detected_at:%Y-%m-%d %H:%M}"