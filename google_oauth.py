"""Google OAuth 2.0 login ("Sign in with Google") for this app's own users.

This is a different role from oauth/ (which makes THIS app an authorization
server for MCP/API clients) - here, this app is the OAuth *client*, and
Google is the identity provider. Deliberately implemented with plain httpx
calls rather than authlib's Starlette integration, since that needs
SessionMiddleware wired into the whole app just to store CSRF state; a
short-lived in-memory dict does the same job for a single-instance
deployment with far less surface area.
"""

import os
import secrets
import time
from urllib.parse import urlencode

import httpx

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Where the frontend SPA is served from - after Google redirects back here
# and we've minted our own JWT, the browser is sent on to this app's own
# /auth/callback route (not a backend route) to pick the token up.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# OAUTH_ISSUER is this app's own public base URL (see oauth/service.py) -
# reused here so the Google redirect_uri always matches wherever this
# service is actually reachable, without a second env var to keep in sync.
OAUTH_ISSUER = os.environ.get("OAUTH_ISSUER", "http://localhost:8000")
REDIRECT_URI = f"{OAUTH_ISSUER}/auth/google/callback"

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

STATE_TTL_SECONDS = 600

# state -> issued_at. Single-instance only - a multi-instance deployment
# would need this in a shared store (Redis, DB) instead, same caveat as
# oauth/service.py's in-process bits.
_pending_states: dict[str, float] = {}


def _prune_expired_states() -> None:
    cutoff = time.time() - STATE_TTL_SECONDS
    expired = [s for s, issued_at in _pending_states.items() if issued_at < cutoff]
    for s in expired:
        _pending_states.pop(s, None)


def build_authorize_url() -> tuple[str, str]:
    _prune_expired_states()
    state = secrets.token_urlsafe(24)
    _pending_states[state] = time.time()

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}", state


def consume_state(state: str) -> bool:
    """True if `state` was one we issued and hasn't been used/expired yet -
    consumes it either way, so it can't be replayed."""
    _prune_expired_states()
    return _pending_states.pop(state, None) is not None


def exchange_code_for_access_token(code: str) -> str:
    response = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        timeout=5.0,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_userinfo(access_token: str) -> dict:
    response = httpx.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=5.0,
    )
    response.raise_for_status()
    return response.json()
