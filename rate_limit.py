"""In-memory rate limiting for credential-sensitive endpoints (password
login, passwordless request/verify, /oauth/token): none of these had any
attempt throttling, so a correct guess was the only thing standing between
an attacker and an account.

This is intentionally simple - a fixed-window counter per key, held in a
process-local dict - not a distributed limiter. Running multiple app worker
processes/replicas without a shared store (e.g. Redis) means each one
enforces its own independent limit, so the effective limit scales with
worker count. Good enough to raise the cost of unthrottled guessing without
adding a new infra dependency to this project; swap for a shared store if
this ever runs as more than one process.
"""

import threading
import time
from collections import OrderedDict

from fastapi import HTTPException, status

# Bounds the tracked-key dict so an attacker can't grow it without limit by
# hitting an endpoint with many distinct keys (e.g. one IP per request) -
# evicts the least-recently-touched key once over this, same idea as
# geoip.py's cache cap.
MAX_TRACKED_KEYS = 50_000

_lock = threading.Lock()
_buckets: "OrderedDict[str, tuple[float, int]]" = OrderedDict()


def enforce(key: str, *, max_attempts: int, window_seconds: float) -> None:
    """Raises 429 once `key` has been hit more than max_attempts times
    within the trailing window_seconds; otherwise records this hit and
    returns normally. Call this before doing the expensive/sensitive work
    (password check, token lookup, ...) - the point is to slow attempts
    down, not just count them after the fact."""
    now = time.monotonic()
    with _lock:
        window_start, count = _buckets.get(key, (now, 0))
        if now - window_start >= window_seconds:
            window_start, count = now, 0
        count += 1
        _buckets[key] = (window_start, count)
        _buckets.move_to_end(key)
        while len(_buckets) > MAX_TRACKED_KEYS:
            _buckets.popitem(last=False)

        if count > max_attempts:
            retry_after = max(1, int(window_start + window_seconds - now))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts - try again later",
                headers={"Retry-After": str(retry_after)},
            )
