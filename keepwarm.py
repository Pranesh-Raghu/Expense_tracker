"""Keeps OpenFGA from spinning down on Render's free tier.

OpenFGA (authz/client.py's OPENFGA_API_URL) is a private Render service
with no public port - Render's own free-tier spin-down/cold-start applies
to it, and since nearly every authenticated request in this app calls
OpenFGA at least once (permission checks, admin checks, ...), a cold
OpenFGA makes the *whole app* feel slow on the first request after any
idle period.

This app's own web service (unlike OpenFGA) is on an always-on paid plan,
so it can't go cold itself - but an external pinger can't reach OpenFGA
directly, since it has no public port. This module bridges that: a public,
unauthenticated endpoint on this already-always-on service that forwards a
health check to OpenFGA internally. A free scheduled pinger (see
.github/workflows/keepwarm.yml) hits this endpoint every few minutes,
keeping OpenFGA's activity alive without ever needing to reach it directly.

This doesn't eliminate OpenFGA's cold start if it's ALREADY gone idle
(nothing can - the point is to ping often enough that it never gets there);
it also doesn't help at all if OpenFGA is intentionally scaled down or the
whole stack is offline for other reasons. It's a narrow fix for one
specific, common cause of "the app feels slow."
"""

import logging

import httpx
from fastapi import APIRouter, Request

from authz.client import OPENFGA_API_URL
import rate_limit

logger = logging.getLogger("expense_tracker.keepwarm")

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    # Same logic as auth.py's/oauth/router.py's/mock_idp.py's versions.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/internal/keepwarm")
def keepwarm(request: Request):
    """Best-effort - always returns 200 regardless of whether OpenFGA
    responded, since the caller (a scheduled ping) only cares that a
    request happened, not the result. Failures are logged, not surfaced,
    so a slow/cold OpenFGA can't make this endpoint itself look broken.

    Unauthenticated by design (a free external pinger has no credentials to
    send), so it's rate-limited to keep it from becoming a way to generate
    repeated load against OpenFGA."""
    rate_limit.enforce(f"keepwarm:ip:{_client_ip(request) or 'unknown'}", max_attempts=12, window_seconds=60)
    try:
        with httpx.Client(base_url=OPENFGA_API_URL, timeout=10.0) as client:
            client.get("/healthz").raise_for_status()
        return {"openfga": "ok"}
    except httpx.HTTPError:
        logger.warning("keepwarm ping to OpenFGA failed", exc_info=True)
        return {"openfga": "unreachable"}
