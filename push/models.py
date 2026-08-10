from django.db import models

from client.models import Client


class DeviceToken(models.Model):
    """
    A Firebase Cloud Messaging registration token for one of a client's
    devices. A client can have several (phone + tablet, or a reinstalled
    app issuing a new token) — send_push_to_client() fans out to all of them.
    """
    client     = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='device_tokens')
    token      = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'FCM token for {self.client.email}'
