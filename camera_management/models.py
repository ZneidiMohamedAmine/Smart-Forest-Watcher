from django.contrib.gis.db import models
from django.contrib.auth.models import User
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


class StagedCorrection(models.Model):
    """
    A supervisor-reviewed, corrected set of bounding boxes for a Detection's
    image — the human-in-the-loop step of the MLOps dataset pipeline.
    Sits in "staging" until run_merge_staging() folds it into
    yolo/data/dataset_finale/ once enough approved corrections pile up.
    """
    STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('merged', 'Merged'),
        ('rejected', 'Rejected'),
    ]

    detection   = models.ForeignKey(Detection, on_delete=models.CASCADE, related_name='staged_corrections')
    boxes       = models.JSONField(default=list)   # [{x1,y1,x2,y2,label}, ...] absolute pixel coords
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='approved')
    reject_reason = models.CharField(max_length=255, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    merged_at   = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Correction for detection {self.detection_id} ({self.status})'


class DatasetVersion(models.Model):
    """
    One row per successful run_merge_staging() batch — the "PROFILE" step's
    version history (yolo/data/profiles/versions.json mirrors this table).
    """
    version      = models.CharField(max_length=32, unique=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    image_count  = models.PositiveIntegerField(default=0)
    train_count  = models.PositiveIntegerField(default=0)
    val_count    = models.PositiveIntegerField(default=0)
    test_count   = models.PositiveIntegerField(default=0)
    class_counts = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Dataset version {self.version} ({self.image_count} images)'