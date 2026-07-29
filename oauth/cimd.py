"""Client ID Metadata Documents (CIMD).

CIMD is the zero-registration alternative to Dynamic Client Registration that
the MCP authorization spec allows: instead of calling POST /oauth/register,
a client's `client_id` IS an HTTPS URL. That URL serves a JSON document
describing the client (redirect_uris, client_name, ...), in the same shape as
an RFC 7591 registration response.

The security property that makes this safe is self-certification: the
document served at the client_id URL must itself declare that exact URL as
its `client_id`. That binding is what stops one client from claiming another
client's identity - an attacker can put whatever they want at a URL they
control, but they cannot make someone else's URL serve a document that
points back at the attacker, because they don't control that URL.

Because anyone can host a CIMD document, the authorization server must never
treat it as more trustworthy than "some client claiming this redirect_uri
set" - exactly the same trust level as a self-registered DCR client. What it
buys the client is not having to call /oauth/register against every MCP
server it talks to.
"""

import time
from typing import Optional
from urllib.parse import urlparse

import httpx

CACHE_TTL_SECONDS = 600
MAX_DOCUMENT_BYTES = 64 * 1024
FETCH_TIMEOUT_SECONDS = 5.0

_cache: dict[str, tuple[float, dict]] = {}


def is_cimd_client_id(client_id: str) -> bool:
    return client_id.startswith("https://") or client_id.startswith("http://")


def _validate_url(client_id: str, *, allow_insecure_http: bool) -> None:
    parsed = urlparse(client_id)
    if parsed.fragment:
        raise ValueError("client_id URL must not contain a fragment")
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and allow_insecure_http:
        # allow_insecure_http is itself the explicit dev-only opt-in (see
        # CIMD_ALLOW_INSECURE_HTTP in .env.example); it must never be set in
        # a real deployment, so there's no extra safety in also restricting
        # which hostnames it applies to.
        return
    raise ValueError("client_id URL must use https")


async def resolve_cimd_client(client_id: str, *, allow_insecure_http: bool = False) -> dict:
    """Fetch and validate a Client ID Metadata Document, using a short-lived cache."""

    cached = _cache.get(client_id)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    _validate_url(client_id, allow_insecure_http=allow_insecure_http)

    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=False) as client:
        response = await client.get(client_id, headers={"Accept": "application/json"})
        response.raise_for_status()

        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > MAX_DOCUMENT_BYTES:
            raise ValueError("client metadata document too large")
        if len(response.content) > MAX_DOCUMENT_BYTES:
            raise ValueError("client metadata document too large")

        metadata = response.json()

    if metadata.get("client_id") != client_id:
        raise ValueError("client metadata document does not self-certify this client_id")

    redirect_uris = metadata.get("redirect_uris")
    if not isinstance(redirect_uris, list) or not redirect_uris:
        raise ValueError("client metadata document missing redirect_uris")

    metadata.setdefault("token_endpoint_auth_method", "none")
    metadata.setdefault("grant_types", ["authorization_code", "refresh_token"])
    metadata.setdefault("response_types", ["code"])

    _cache[client_id] = (time.monotonic() + CACHE_TTL_SECONDS, metadata)
    return metadata


def get_cached_cimd_client(client_id: str) -> Optional[dict]:
    cached = _cache.get(client_id)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    return None
