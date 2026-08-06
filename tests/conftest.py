"""Integration tests run against a LIVE stack (docker compose up), the same
way every behavior in this project was verified manually during development.
This app is too tightly coupled to MySQL/OpenFGA/RSA keys to unit-test in
isolation without mocking away the exact things worth testing - these tests
codify the manual curl walkthroughs from the README instead.

Run with the stack up: `pytest` (needs `pip install pytest requests`).
"""

import base64
import hashlib
import os
import secrets

import pytest
import requests

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")


def unique(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)[:64]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


@pytest.fixture(scope="session")
def base_url() -> str:
    resp = requests.get(f"{BASE_URL}/.well-known/oauth-authorization-server", timeout=5)
    if resp.status_code != 200:
        pytest.skip(f"stack not reachable at {BASE_URL} - is `docker compose up` running?")
    return BASE_URL


def create_user(base_url: str, username: str, password: str) -> int:
    # Signup only takes email + password (see schemas/user_schemas.py) -
    # the username is generated server-side from the email's local part
    # (User.generate_username_from_email). `unique()` below already only
    # produces lowercase letters/digits/underscore, so the derived username
    # comes back out exactly equal to the `username` this helper was given -
    # every caller's rest_login(base_url, username, password) still works
    # unmodified.
    resp = requests.post(f"{base_url}/users/", json={"email": f"{username}@example.com", "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def rest_login(base_url: str, username: str, password: str) -> str:
    resp = requests.post(f"{base_url}/auth/token", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def register_client(base_url: str, redirect_uri: str = "http://localhost:9000/callback") -> str:
    resp = requests.post(
        f"{base_url}/oauth/register",
        json={"redirect_uris": [redirect_uri], "client_name": "pytest-client"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["client_id"]


def oauth_login(
    base_url: str,
    username: str,
    password: str,
    client_id: str,
    scope: str | None = None,
    redirect_uri: str = "http://localhost:9000/callback",
) -> dict:
    """Full authorization_code + PKCE flow, returns the token response dict."""
    verifier, challenge = pkce_pair()
    data = {
        "username": username,
        "password": password,
        "decision": "approve",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "pytest",
    }
    if scope:
        data["scope"] = scope
    resp = requests.post(f"{base_url}/oauth/authorize", data=data, allow_redirects=False)
    assert resp.status_code == 302, resp.text
    location = resp.headers["location"]
    code = location.split("code=")[1].split("&")[0]

    token_resp = requests.post(
        f"{base_url}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
            "client_id": client_id,
        },
    )
    assert token_resp.status_code == 200, token_resp.text
    return token_resp.json()


def mcp_initialize(base_url: str, token: str) -> str:
    """Returns the mcp-session-id for subsequent calls."""
    resp = requests.post(
        f"{base_url}/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "1"}},
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.headers["mcp-session-id"]


def mcp_call(base_url: str, token: str, session_id: str, tool: str, arguments: dict, request_id: int = 2) -> dict:
    """Calls an MCP tool and returns the parsed JSON-RPC result (raises on tool error)."""
    resp = requests.post(
        f"{base_url}/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "mcp-session-id": session_id,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        json={"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": {"name": tool, "arguments": arguments}},
    )
    assert resp.status_code == 200, resp.text
    body = _parse_sse_json(resp.text)
    result = body["result"]
    if result.get("isError"):
        raise RuntimeError(result["content"][0]["text"])
    return result


def _parse_sse_json(text: str) -> dict:
    import json

    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])
    raise ValueError(f"no SSE data line found in response: {text!r}")
