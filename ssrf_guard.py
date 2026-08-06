"""Shared guard against SSRF via a URL this server fetches on someone else's
say-so: a CIMD client_id (attacker-controlled, reachable from unauthenticated
OAuth endpoints - see oauth/cimd.py) and a registered webhook endpoint
(admin-controlled, but a compromised admin account shouldn't get a free
pivot into internal infrastructure - see auth.py's create_webhook).

Resolves the hostname and rejects it unless every address it resolves to is
public. This closes the common case (a hostname that resolves to an
internal/private/loopback address); it does not fully close a DNS-rebinding
race, where the hostname could resolve to a different address by the time
the actual request connects moments later - fully closing that needs a
custom transport that pins the validated IP, which no caller here does.
"""

import asyncio
import ipaddress
import socket
from typing import Optional


def is_public_hostname(hostname: Optional[str]) -> bool:
    """Synchronous resolve-and-check - safe from a sync/threadpool route."""
    if not hostname:
        return False
    try:
        addrinfos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    return all(ipaddress.ip_address(sockaddr[0]).is_global for *_, sockaddr in addrinfos)


async def is_public_hostname_async(hostname: Optional[str]) -> bool:
    """Same check, resolved via asyncio's non-blocking resolver - use this
    from async code so DNS resolution doesn't stall the event loop."""
    if not hostname:
        return False
    loop = asyncio.get_running_loop()
    try:
        addrinfos = await loop.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    return all(ipaddress.ip_address(sockaddr[0]).is_global for *_, sockaddr in addrinfos)
