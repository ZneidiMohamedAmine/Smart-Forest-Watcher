"""
Shared TTN uplink parsing, used by the persistent listener
(supervisor/management/commands/listen_ttn.py). Kept separate from the
command itself so it's easy to unit test without spinning up MQTT.
"""
import json

TTN_HOST = "eu1.cloud.thethings.network"
TTN_PORT = 8883


def parse_and_dispatch(payload):
    """Parses a TTN uplink JSON payload and queues calculate_fwi_task. Returns the device_id."""
    from supervisor.tasks.calcul_fwi import calculate_fwi_task

    parsed = json.loads(payload)
    device_id = parsed["end_device_ids"]["device_id"]
    up = parsed.get("uplink_message", {})
    dp = up.get("decoded_payload", {})

    data = {
        "device_id": device_id,
        "temperature": dp.get("temperature"),
        "humidity": dp.get("humidity"),
        "gaz": dp.get("gaz"),
        "pressure": dp.get("pressure") or dp.get("pressur"),  # Handle both spellings
        "rain": dp.get("rain", 0),
        "rssi": (up.get("rx_metadata") or [{}])[0].get("rssi"),
        "battery": dp.get("battery_percent"),
    }
    calculate_fwi_task.delay(data)
    return device_id
