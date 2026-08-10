"""
Sends real Android push notifications via Firebase Cloud Messaging —
delivered by Google's own servers, so they reach the device even if the
app has been fully closed/killed (unlike the existing MobileNotification
polling path, which only works while the app process is alive).

Needs a Firebase service account key. Until FIREBASE_CREDENTIALS_PATH
points at a real file, send_push_to_client() just no-ops — the existing
in-app notification/polling pipeline keeps working exactly as before
either way, this is purely additive.
"""
import logging
import os

import firebase_admin
from firebase_admin import credentials, messaging

log = logging.getLogger(__name__)

_firebase_app = None
_firebase_app_checked = False


def _get_firebase_app():
    global _firebase_app, _firebase_app_checked
    if _firebase_app_checked:
        return _firebase_app
    _firebase_app_checked = True

    cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'firebase-service-account.json')
    if not os.path.exists(cred_path):
        log.warning("FCM not configured — no service account file at '%s'. Push notifications disabled.", cred_path)
        return None

    cred = credentials.Certificate(cred_path)
    _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def send_push_to_client(client, title, body, data=None):
    """No-ops quietly if Firebase isn't configured or the client has no registered devices."""
    app = _get_firebase_app()
    if app is None:
        return

    from .models import DeviceToken

    tokens = list(client.device_tokens.values_list('token', flat=True))
    if not tokens:
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=tokens,
    )

    try:
        response = messaging.send_each_for_multicast(message, app=app)
    except Exception:
        log.exception("FCM send failed for client %s", client.email)
        return

    for token, result in zip(tokens, response.responses):
        if not result.success and result.exception and 'registration-token-not-registered' in str(result.exception).lower():
            DeviceToken.objects.filter(token=token).delete()
