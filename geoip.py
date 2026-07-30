"""Best-effort city lookup for session IPs, shown in the sessions/devices UI.

Security note: resolving an IP to a city means sending that IP to a
third-party service (ip-api.com's free, no-signup tier) - this is a real
privacy tradeoff, not just an implementation detail. Only call this for
data you're already comfortable exposing to a third party, and never for
anything more sensitive than "which of my own sessions is this."
"""

import ipaddress
import logging

import httpx

logger = logging.getLogger(__name__)

IP_API_URL = "http://ip-api.com/json/{ip}?fields=status,city,regionName,country"

# Small in-memory cache - session lists get re-fetched often (every page
# load of the sessions UI) and an IP's city doesn't change within a
# session's lifetime, so there's no reason to re-query per request.
_cache: dict[str, str | None] = {}


def _is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved)


def city_for_ip(ip: str | None) -> str | None:
    """'City, Region, Country', or None if the IP is missing, private/local
    (nothing meaningful to resolve), or the lookup fails."""
    if not ip:
        return None
    if ip in _cache:
        return _cache[ip]
    if not _is_public_ip(ip):
        _cache[ip] = None
        return None

    try:
        response = httpx.get(IP_API_URL.format(ip=ip), timeout=2.0)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "success":
            _cache[ip] = None
            return None
        parts = [p for p in (data.get("city"), data.get("regionName"), data.get("country")) if p]
        city = ", ".join(parts) or None
    except httpx.HTTPError as exc:
        logger.warning("geoip lookup failed for %s: %s", ip, exc)
        city = None

    _cache[ip] = city
    return city
