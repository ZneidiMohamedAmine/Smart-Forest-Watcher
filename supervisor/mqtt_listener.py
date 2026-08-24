"""
Shared TTN uplink parsing, used by the persistent listener
(supervisor/management/commands/listen_ttn.py). Kept separate from the
command itself so it's easy to unit test without spinning up MQTT.
"""
import hashlib
import json
import time

TTN_HOST = "eu1.cloud.thethings.network"
TTN_PORT = 8883

# Subscribing to the account-wide "#" wildcard (instead of just the uplink
# topic) means this can see the same uplink event more than once — TTN
# publishes several message types per uplink (queued, ack, uplink, ...) and
# some MQTT redelivery paths repeat a message. De-duplicate by exact raw
# payload within a short window: a genuine new reading always differs (TTN
# stamps every message with a unique correlation ID/timestamp), so an exact
# byte-for-byte repeat within a few seconds is always the same event.
_DEDUP_WINDOW_SECONDS = 10
_seen_payloads = {}  # sha256(payload) -> last-seen monotonic time


def _is_duplicate(payload: bytes) -> bool:
    now = time.monotonic()
    for key, seen_at in list(_seen_payloads.items()):
        if now - seen_at > _DEDUP_WINDOW_SECONDS:
            del _seen_payloads[key]

    digest = hashlib.sha256(payload).hexdigest()
    if digest in _seen_payloads:
        return True
    _seen_payloads[digest] = now
    return False


def parse_and_dispatch(payload):
    """Parses a TTN uplink JSON payload and queues calculate_fwi_task. Returns the device_id."""
    from supervisor.tasks.calcul_fwi import calculate_fwi_task

    parsed = json.loads(payload)
    device_id = parsed["end_device_ids"]["device_id"]

    if _is_duplicate(payload if isinstance(payload, bytes) else payload.encode()):
        return device_id

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
