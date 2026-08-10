from django.db import models

from .supervisor import Supervisor


class TTNCredential(models.Model):
    """
    A registered TTN (The Things Network) application MQTT login. The
    MQTTConsumer opens one MQTT connection per row here — previously this
    list was hardcoded in supervisor/consummer.py, so only one TTN app
    (or whichever were manually added to the source file) could ever be
    received. Shared across all supervisors for now, not scoped per-account.
    """
    name        = models.CharField(max_length=100, help_text="A label to recognize this app, e.g. the TTN application ID")
    username    = models.CharField(max_length=255, help_text="TTN MQTT username, e.g. my-app@ttn")
    api_key     = models.CharField(max_length=255, help_text="TTN MQTT password / API key")
    added_by    = models.ForeignKey(Supervisor, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.username})'
