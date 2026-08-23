from django.contrib.gis.db          import models
from django.utils                   import timezone
from client.models                  import Client
from .localisation                  import Localisation


class Project(models.Model):
    name            = models.CharField(max_length=30)
    descp           = models.TextField(null=True)
    date_debut      = models.DateTimeField(default=timezone.now)
    date_fin        = models.DateTimeField()
    city            = models.ForeignKey(Localisation, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    piece_joindre   = models.FileField(upload_to='uploads/%Y/%m/%d/', null=True, blank=True)
    # An agent (Client) manages exactly one project — enforced at the DB
    # level so this can't drift again the way it did before.
    client          = models.OneToOneField(Client, on_delete=models.CASCADE, null=True)
    polygon_id      = models.BigAutoField(primary_key=True, default=None)

    @property
    def total_nodes(self):
        from supervisor.models.node import Node
        return Node.objects.filter(parcelle__project=self).count()

    @property
    def total_cameras(self):
        return self.cameras.count()


    def __str__(self):
        return f'Project: {self.name}'