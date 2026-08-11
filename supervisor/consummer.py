from channels.generic.websocket import AsyncWebsocketConsumer


class MQTTConsumer(AsyncWebsocketConsumer):
    """
    Historically this opened a fresh MQTT connection to every registered TTN
    app on every page visit, and dropped them again when the page closed —
    meaning sensor data was only ever received while someone had a specific
    page open in a browser. Real MQTT listening now runs as its own
    persistent process (see `manage.py listen_ttn` / the mqtt-listener
    service in docker-compose.yml), so this consumer no longer needs to do
    anything beyond accepting the connection for backward compatibility with
    the frontend JS that still opens it.
    """
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass
