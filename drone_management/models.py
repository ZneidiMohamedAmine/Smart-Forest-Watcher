from django.db import models
from supervisor.models.project import Project


class Drone(models.Model):
    """
    A mobile drone unit, linked to a Project (not a fixed Parcelle — unlike
    Camera/Node, a drone patrols freely rather than sitting at one point).
    Position is live: latitude/longitude/last_seen are overwritten on every
    GPS+image upload rather than set once at creation.
    """
    project        = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='drones')
    drone_id       = models.CharField(max_length=100, unique=True)
    name           = models.CharField(max_length=100)
    api_key        = models.CharField(max_length=64, default='')   # onboard-unit auth token
    is_active      = models.BooleanField(default=True)
    latitude       = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude      = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    battery_level  = models.PositiveSmallIntegerField(null=True, blank=True)  # 0-100
    last_seen      = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.drone_id})"
