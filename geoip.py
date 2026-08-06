"""Best-effort city lookup for session IPs, shown in the sessions/devices UI.

Security note: resolving an IP to a city means sending that IP to a
third-party service (ip-api.com's free, no-signup tier) - this is a real
privacy tradeoff, not just an implementation detail. Only call this for
data you're already comfortable exposing to a third party, and never for
anything more sensitive than "which of my own sessions is this."
"""

import ipaddress
import logging
import threading
import time
from collections import OrderedDict

import httpx

logger = logging.getLogger(__name__)

# Batch endpoint: one request resolves up to BATCH_SIZE IPs, instead of one
# request per IP. list_sessions() renders a whole page of sessions at once,
# so batching turns N sequential (and each up-to-timeout) HTTP round trips
# into a small, fixed number - see cities_for_ips().
IP_API_BATCH_URL = "http://ip-api.com/batch?fields=status,city,regionName,country,query"
BATCH_SIZE = 100

# Successful lookups are cached forever - an IP's city doesn't change within
# a session's lifetime. Failed lookups (timeout, non-200, rate-limited, or
# ip-api returning status=fail) get a short TTL instead of being cached
# forever: caching a transient hiccup permanently would silently blind that
# IP to city resolution for the rest of the process's life.
NEGATIVE_TTL_SECONDS = 5 * 60

# Session lists get re-fetched often (every page load of the sessions UI),
# but a long-running process talking to many distinct users/IPs shouldn't
# grow this cache without bound. Evict the least-recently-used entry once
# the cache exceeds this size.
MAX_CACHE_SIZE = 10_000

# ip -> (city_or_none, expiry_monotonic_or_none). expiry is None for
# successful lookups (never expire); set for negative results (see above).
_cache: "OrderedDict[str, tuple[str | None, float | None]]" = OrderedDict()

# list_sessions() runs as a sync FastAPI route, which Starlette executes in
# a threadpool - concurrent requests can hit this module-level cache from
# different threads at once. Guard every read-then-write sequence (expiry
# check + delete, insert + evict) so one thread can't act on a state another
# thread has already changed.
_cache_lock = threading.Lock()

_MISS = object()


def _is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved)


def _cache_get(ip: str):
    """Returns the cached city (possibly None), or the _MISS sentinel if
    there's no live entry - distinct from a cached "no city" result."""
    with _cache_lock:
        entry = _cache.get(ip)
        if entry is None:
            return _MISS
        city, expiry = entry
        if expiry is not None and time.monotonic() >= expiry:
            _cache.pop(ip, None)
            return _MISS
        _cache.move_to_end(ip)
        return city


def _cache_set(ip: str, city: str | None) -> None:
    expiry = None if city else time.monotonic() + NEGATIVE_TTL_SECONDS
    with _cache_lock:
        _cache[ip] = (city, expiry)
        _cache.move_to_end(ip)
        while len(_cache) > MAX_CACHE_SIZE:
            _cache.popitem(last=False)  # evict least-recently-used


def cities_for_ips(ips) -> dict[str, str | None]:
    """Best-effort city lookup for many IPs at once: 'City, Region, Country'
    per IP, or None for IPs that are missing, private/local, or fail to
    resolve. Prefer this over calling city_for_ip() in a loop - it batches
    the actual network calls instead of making one request per IP."""
    result: dict[str, str | None] = {}
    to_query: list[str] = []
    seen: set[str] = set()

    for ip in ips:
        if not ip or ip in seen:
            continue
        seen.add(ip)
        cached = _cache_get(ip)
        if cached is not _MISS:
            result[ip] = cached
        elif _is_public_ip(ip):
            to_query.append(ip)
        else:
            _cache_set(ip, None)
            result[ip] = None

    for start in range(0, len(to_query), BATCH_SIZE):
        chunk = to_query[start : start + BATCH_SIZE]
        try:
            response = httpx.post(IP_API_BATCH_URL, json=chunk, timeout=5.0)
            response.raise_for_status()
            entries = response.json()
        except httpx.HTTPError as exc:
            logger.warning("geoip batch lookup failed for %d IPs: %s", len(chunk), exc)
            for ip in chunk:
                _cache_set(ip, None)
                result[ip] = None
            continue

        for entry in entries:
            ip = entry.get("query")
            if not ip:
                continue
            if entry.get("status") == "success":
                parts = [p for p in (entry.get("city"), entry.get("regionName"), entry.get("country")) if p]
                city = ", ".join(parts) or None
            else:
                city = None
            _cache_set(ip, city)
            result[ip] = city

    return result


def city_for_ip(ip: str | None) -> str | None:
    """'City, Region, Country', or None if the IP is missing, private/local
    (nothing meaningful to resolve), or the lookup fails.

    Resolving one IP at a time. If you're rendering a list of sessions,
    call cities_for_ips() with all their IPs instead - it batches the
    lookup into a single request rather than one per IP."""
    if not ip:
        return None
    return cities_for_ips([ip]).get(ip)
