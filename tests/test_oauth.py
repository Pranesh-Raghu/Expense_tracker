import requests

from tests.conftest import create_user, oauth_login, pkce_pair, register_client, unique


def test_dcr_issues_public_client_with_no_secret(base_url):
    client_id = register_client(base_url)
    assert client_id


def test_pkce_wrong_verifier_is_rejected(base_url):
    username = unique("oauth")
    create_user(base_url, username, "password123")
    client_id = register_client(base_url)
    _verifier, challenge = pkce_pair()
    wrong_verifier, _ = pkce_pair()

    resp = requests.post(
        f"{base_url}/oauth/authorize",
        data={
            "username": username,
            "password": "password123",
            "decision": "approve",
            "client_id": client_id,
            "redirect_uri": "http://localhost:9000/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "x",
        },
        allow_redirects=False,
    )
    code = resp.headers["location"].split("code=")[1].split("&")[0]

    token_resp = requests.post(
        f"{base_url}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:9000/callback",
            "code_verifier": wrong_verifier,
            "client_id": client_id,
        },
    )
    assert token_resp.status_code == 400
    assert "PKCE" in token_resp.json()["detail"]


def test_pkce_malformed_verifier_is_rejected_not_a_500(base_url):
    # A code_verifier outside RFC 7636's charset (here: non-ASCII) used to
    # reach code_verifier.encode("ascii") unchecked and raise
    # UnicodeEncodeError - an unhandled 500 instead of a clean invalid_grant.
    username = unique("oauth")
    create_user(base_url, username, "password123")
    client_id = register_client(base_url)
    _verifier, challenge = pkce_pair()

    resp = requests.post(
        f"{base_url}/oauth/authorize",
        data={
            "username": username,
            "password": "password123",
            "decision": "approve",
            "client_id": client_id,
            "redirect_uri": "http://localhost:9000/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "x",
        },
        allow_redirects=False,
    )
    code = resp.headers["location"].split("code=")[1].split("&")[0]

    token_resp = requests.post(
        f"{base_url}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:9000/callback",
            "code_verifier": "not-ascii-é" * 6,  # 43+ chars, contains é
            "client_id": client_id,
        },
    )
    assert token_resp.status_code == 400
    assert "PKCE" in token_resp.json()["detail"]


def test_authorization_code_is_single_use(base_url):
    username = unique("oauth")
    create_user(base_url, username, "password123")
    client_id = register_client(base_url)
    tokens = oauth_login(base_url, username, "password123", client_id)
    assert tokens["access_token"]
    assert tokens["refresh_token"]


def test_refresh_token_rotates_and_old_one_dies(base_url):
    username = unique("oauth")
    create_user(base_url, username, "password123")
    client_id = register_client(base_url)
    tokens = oauth_login(base_url, username, "password123", client_id)
    old_refresh = tokens["refresh_token"]

    refreshed = requests.post(
        f"{base_url}/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": old_refresh, "client_id": client_id},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != old_refresh

    replay = requests.post(
        f"{base_url}/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": old_refresh, "client_id": client_id},
    )
    assert replay.status_code == 400


def test_revoke_kills_an_unexpired_access_token(base_url):
    username = unique("oauth")
    create_user(base_url, username, "password123")
    client_id = register_client(base_url)
    tokens = oauth_login(base_url, username, "password123", client_id)
    access_token = tokens["access_token"]

    introspect_before = requests.post(f"{base_url}/oauth/introspect", data={"token": access_token})
    assert introspect_before.json()["active"] is True

    revoke = requests.post(f"{base_url}/oauth/revoke", data={"token": access_token})
    assert revoke.status_code == 200

    introspect_after = requests.post(f"{base_url}/oauth/introspect", data={"token": access_token})
    assert introspect_after.json()["active"] is False


def test_introspect_garbage_token_returns_inactive_no_error(base_url):
    resp = requests.post(f"{base_url}/oauth/introspect", data={"token": "not-a-real-token"})
    assert resp.status_code == 200
    assert resp.json() == {"active": False}


def test_metadata_endpoints_resolve(base_url):
    for path in [
        "/.well-known/oauth-authorization-server",
        "/.well-known/oauth-protected-resource/mcp",
        "/.well-known/jwks.json",
    ]:
        resp = requests.get(f"{base_url}{path}")
        assert resp.status_code == 200, path
