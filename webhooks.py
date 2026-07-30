"""HMAC-signed webhook dispatch.

Delivery is best-effort and synchronous: a broken or slow receiver must
never break the actual operation that triggered the event, so every send
is wrapped, short-timeout, and log-only-on-failure - nothing here ever
raises back into the caller.

Receivers verify authenticity by recomputing
HMAC-SHA256(endpoint_secret, raw_body) and comparing it to the
X-Webhook-Signature header (constant-time compare) - the same pattern
Stripe/GitHub webhooks use, so it should feel familiar to integrate against.
"""

import hashlib
import hmac
import json
import logging
import time

import httpx

from database import SessionLocal
from oauth.models import WebhookEndpoint

logger = logging.getLogger("expense_tracker.webhooks")

DELIVERY_TIMEOUT_SECONDS = 3.0


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def dispatch_event(event_type: str, data: dict) -> None:
    with SessionLocal() as db:
        endpoints = db.query(WebhookEndpoint).filter(WebhookEndpoint.active.is_(True)).all()
        matching = [e for e in endpoints if event_type in json.loads(e.events)]
        # Copy out what we need before the session closes.
        targets = [(e.url, e.secret) for e in matching]

    if not targets:
        return

    body = json.dumps({"event": event_type, "data": data, "timestamp": int(time.time())}).encode("utf-8")

    for url, secret in targets:
        signature = sign(secret, body)
        try:
            with httpx.Client(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
                client.post(
                    url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Event": event_type,
                        "X-Webhook-Signature": f"sha256={signature}",
                    },
                )
        except httpx.HTTPError:
            logger.warning("webhook delivery failed: event=%s url=%s", event_type, url, exc_info=True)
