"""HMAC-signed webhook dispatch.

Delivery is best-effort and off the request path: a broken or slow receiver
must never make the operation that triggered the event (an expense
create/update/etc.) wait on it, so the actual HTTP POSTs - including
retries/backoff - happen in a background thread, not inline in
dispatch_event(). Nothing here ever raises back into the caller.

This is in-memory/fire-and-forget, not a durable outbox: if the process
restarts mid-retry, whatever hasn't been delivered yet is lost. Good enough
for a receiver that's briefly slow or down; a receiver that's down for
longer than the retry budget below still permanently misses the event, with
only a log line to show it happened.

Receivers verify authenticity by recomputing
HMAC-SHA256(endpoint_secret, raw_body) and comparing it to the
X-Webhook-Signature header (constant-time compare) - the same pattern
Stripe/GitHub webhooks use, so it should feel familiar to integrate against.
"""

import hashlib
import hmac
import json
import logging
import threading
import time
from decimal import Decimal

import httpx

from database import SessionLocal
from oauth.models import WebhookEndpoint

logger = logging.getLogger("expense_tracker.webhooks")

DELIVERY_TIMEOUT_SECONDS = 3.0
MAX_DELIVERY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = (1, 3)  # only needed between attempts, so len == MAX_DELIVERY_ATTEMPTS - 1


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _deliver_with_retry(url: str, secret: str, body: bytes, event_type: str) -> None:
    """Runs on a background thread (see dispatch_event) - blocking here,
    including the sleeps between retries, never delays the request that
    triggered the event."""
    signature = sign(secret, body)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event_type,
        "X-Webhook-Signature": f"sha256={signature}",
    }
    for attempt in range(1, MAX_DELIVERY_ATTEMPTS + 1):
        try:
            with httpx.Client(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
                response = client.post(url, content=body, headers=headers)
                response.raise_for_status()
            return
        except httpx.HTTPError:
            is_last_attempt = attempt == MAX_DELIVERY_ATTEMPTS
            logger.warning(
                "webhook delivery attempt %d/%d failed: event=%s url=%s%s",
                attempt, MAX_DELIVERY_ATTEMPTS, event_type, url,
                "" if is_last_attempt else " - retrying",
                exc_info=is_last_attempt,
            )
            if not is_last_attempt:
                time.sleep(RETRY_BACKOFF_SECONDS[attempt - 1])


def dispatch_event(event_type: str, data: dict) -> None:
    with SessionLocal() as db:
        endpoints = db.query(WebhookEndpoint).filter(WebhookEndpoint.active.is_(True)).all()
        matching = [e for e in endpoints if event_type in json.loads(e.events)]
        # Copy out what we need before the session closes.
        targets = [(e.url, e.secret) for e in matching]

    if not targets:
        return

    # Expense.amount is a Decimal (see models/expense_model.py) - json.dumps
    # doesn't know how to serialize one on its own, so event payloads
    # carrying an amount (e.g. "expense.created") would otherwise raise
    # TypeError here and silently drop that delivery.
    body = json.dumps(
        {"event": event_type, "data": data, "timestamp": int(time.time())},
        default=lambda o: float(o) if isinstance(o, Decimal) else str(o),
    ).encode("utf-8")

    for url, secret in targets:
        threading.Thread(
            target=_deliver_with_retry, args=(url, secret, body, event_type), daemon=True,
        ).start()
