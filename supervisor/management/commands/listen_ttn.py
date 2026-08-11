"""
Persistent MQTT listener for every registered TTN app (supervisor:list_ttn_credentials).

Runs forever as its own long-lived process — see the mqtt-listener service
in docker-compose.yml — instead of being tied to a browser having a page
open. Re-checks the database every 60s so a TTN app added/removed via the
"TTN Sensor Apps" page takes effect without needing a restart.
"""
import time

import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand

from supervisor.mqtt_listener import TTN_HOST, TTN_PORT, parse_and_dispatch

POLL_INTERVAL = 60  # seconds between checking for new/removed TTN apps


class Command(BaseCommand):
    help = 'Persistent MQTT listener for all registered TTN apps. Runs forever.'

    def handle(self, *args, **options):
        active = {}  # TTNCredential.id -> mqtt.Client

        def on_message(client, userdata, message):
            try:
                device_id = parse_and_dispatch(message.payload)
                self.stdout.write(f"Uplink received from device: {device_id}")
            except Exception as exc:
                self.stderr.write(f"MQTT parse error on topic {message.topic}: {exc}")

        def connect_app(cred):
            client = mqtt.Client(client_id=f"ttn_listener_{cred.id}")
            client.username_pw_set(cred.username, cred.api_key)
            client.tls_set()
            client.on_message = on_message
            try:
                client.connect(TTN_HOST, TTN_PORT, 60)
                client.subscribe("#", qos=1)
                client.loop_start()
                self.stdout.write(self.style.SUCCESS(f"Connected to TTN app: {cred.username} ({cred.name})"))
                return client
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"Failed to connect {cred.username}: {exc}"))
                return None

        self.stdout.write("Starting persistent TTN MQTT listener...")
        while True:
            from supervisor.models.ttn_credential import TTNCredential
            current = {c.id: c for c in TTNCredential.objects.all()}

            for cred_id, cred in current.items():
                if cred_id not in active:
                    client = connect_app(cred)
                    if client:
                        active[cred_id] = client

            for cred_id in list(active.keys()):
                if cred_id not in current:
                    active[cred_id].loop_stop()
                    active[cred_id].disconnect()
                    del active[cred_id]
                    self.stdout.write(f"Disconnected removed TTN app id={cred_id}")

            time.sleep(POLL_INTERVAL)
