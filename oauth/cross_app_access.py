"""Cross-App Access: RFC 7523 JWT-bearer grant.

Lets a client already holding a signed identity assertion from a trusted
external issuer (a real IdP - Okta, Auth0, your company SSO; see
mock_idp.py for the demo stand-in) exchange it at /oauth/token for a native
access token here, without that user doing an interactive /oauth/authorize
login at this server. This is the "Cross-App Access" / ID-JAG pattern: one
app, already trusted by a shared IdP, acting on a user's behalf against a
second app's resources.

The trust boundary is real: only issuers explicitly added as a
TrustedIssuer (oauth/models.py) are honored, and the assertion's signature,
expiry, issuer, and audience are all verified before anything is trusted.
"""

import json
import logging
import time

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from database import SessionLocal
from oauth.models import TrustedIssuer

logger = logging.getLogger("expense_tracker.cross_app_access")

JWKS_CACHE_TTL_SECONDS = 600
_jwks_cache: dict[str, tuple[float, dict]] = {}


async def _fetch_jwks(jwks_url: str) -> dict:
    cached = _jwks_cache.get(jwks_url)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    # Async client, not sync: this is called from an async route handler,
    # and the URL being fetched can be this very app's own public URL (the
    # mock IdP's JWKS, reached back through its own tunnel). A *blocking*
    # HTTP call here would freeze the single event loop for the whole
    # request - including the inbound request needed to serve this very
    # fetch - which deadlocks until the request times out.
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        jwks = response.json()

    _jwks_cache[jwks_url] = (time.monotonic() + JWKS_CACHE_TTL_SECONDS, jwks)
    return jwks


def _find_trusted_issuer(issuer: str) -> TrustedIssuer | None:
    with SessionLocal() as db:
        row = db.query(TrustedIssuer).filter(TrustedIssuer.issuer == issuer).first()
        if row is None:
            return None
        # Detach values we need after the session closes.
        db.expunge(row)
        return row


async def verify_identity_assertion(assertion: str, *, client_id: str, expected_audience: str) -> dict:
    """Verify a Cross-App Access identity assertion end to end. Returns the
    decoded claims on success; raises HTTPException(400) on any failure -
    deliberately generic messages, since telling a caller exactly *why*
    assertion validation failed (wrong issuer vs bad signature vs expired)
    hands an attacker a debugging oracle for forging one.
    """
    try:
        unverified_claims = jwt.get_unverified_claims(assertion)
        header = jwt.get_unverified_header(assertion)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: malformed assertion")

    issuer = unverified_claims.get("iss")
    trusted = _find_trusted_issuer(issuer) if issuer else None
    if not trusted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: untrusted assertion issuer")

    allowed_clients = json.loads(trusted.allowed_client_ids) if trusted.allowed_client_ids else None
    if allowed_clients and client_id not in allowed_clients:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid_grant: client not allowed to use this issuer")

    try:
        jwks = await _fetch_jwks(trusted.jwks_url)
        matching_key = next(k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid"))
    except (httpx.HTTPError, StopIteration):
        logger.warning("could not resolve signing key for issuer=%s kid=%s", issuer, header.get("kid"), exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: could not resolve issuer's signing key")

    try:
        claims = jwt.decode(assertion, matching_key, algorithms=["RS256"], audience=expected_audience, issuer=issuer)
    except JWTError:
        logger.warning("assertion verification failed for issuer=%s", issuer, exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: assertion verification failed")

    subject_value = claims.get(trusted.subject_claim)
    if not subject_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: assertion missing subject claim")

    return {"subject": subject_value}
