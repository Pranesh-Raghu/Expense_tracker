"""A mock external identity provider, standing in for a real one (Okta,
Auth0, Google, your company SSO, ...) so Cross-App Access (see
oauth/cross_app_access.py) can be demonstrated end to end without an actual
third-party IdP.

This is deliberately a SEPARATE signer from the main OAuth AS (its own RSA
keypair, its own issuer string) - that distinctness is the entire point:
Cross-App Access only means something when the assertion comes from a
genuinely different trust domain, not this app re-signing its own tokens
under a different name.

In a real deployment you would NOT run this - you'd add a real external
IdP's issuer/JWKS URL as a TrustedIssuer instead (oauth/models.py) and delete
this module entirely.
"""

import os
import time

from fastapi import APIRouter, HTTPException, Request, status
from jose import jwt
from pydantic import BaseModel

from models.user_model import User
from oauth.keys import SigningKeySet
import rate_limit

router = APIRouter()

_KEY_DIR = os.environ.get("OAUTH_KEY_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys"))
_keys = SigningKeySet(_KEY_DIR, "mock_idp_signing_key.pem", "mock-idp-key-1")

ISSUER_PATH = "/mock-idp"


def issuer_url(base_url: str) -> str:
    return f"{base_url}{ISSUER_PATH}"


class MockIdpLoginRequest(BaseModel):
    username: str
    password: str
    # The Cross-App Access spec calls this the "requesting app" - the
    # audience the assertion is minted for, i.e. this Expense Tracker's own
    # OAuth issuer. Left explicit rather than hardcoded so the same mock IdP
    # could plausibly assert identity to more than one resource app.
    audience: str


class MockIdpLoginResponse(BaseModel):
    identity_assertion: str
    token_type: str = "urn:ietf:params:oauth:token-type:jwt"


def _client_ip(request: Request) -> str | None:
    # Same logic as auth.py's and oauth/router.py's versions of this helper.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=MockIdpLoginResponse)
def mock_idp_login(request: Request, payload: MockIdpLoginRequest):
    # This does a real password check (authenticate_user below) - without
    # rate limiting it'd be an unthrottled oracle for the exact same
    # passwords /auth/token protects, just reached through a different
    # route. Same two keys as /auth/token: IP-keyed slows one attacker
    # guessing many usernames, username-keyed slows credential-stuffing one
    # account from many IPs.
    client_ip = _client_ip(request) or "unknown"
    rate_limit.enforce(f"mock-idp-login:ip:{client_ip}", max_attempts=20, window_seconds=300)
    rate_limit.enforce(f"mock-idp-login:user:{payload.username}", max_attempts=10, window_seconds=300)

    user = User.authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")

    now = int(time.time())
    claims = {
        "iss": issuer_url(_base_url()),
        "sub": user.username,
        "preferred_username": user.username,
        "aud": payload.audience,
        "iat": now,
        "exp": now + 300,  # short-lived: this is an assertion to be exchanged immediately, not held onto
    }
    assertion = jwt.encode(claims, _keys.get_signing_key_pem(), algorithm="RS256", headers={"kid": _keys.kid})
    return MockIdpLoginResponse(identity_assertion=assertion)


@router.get("/.well-known/jwks.json")
def mock_idp_jwks():
    return _keys.get_jwks()


def _base_url() -> str:
    from oauth import service

    return service.ISSUER
