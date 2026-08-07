import requests

from tests.conftest import (
    create_user, get_passwordless_login_code, oauth_login, register_client, rest_login, unique,
)


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_keepwarm_ping_is_public_and_reaches_openfga(base_url):
    # No auth needed - this is what a free external scheduled pinger hits
    # to keep OpenFGA's Render service from spinning down (see keepwarm.py).
    resp = requests.get(f"{base_url}/internal/keepwarm")
    assert resp.status_code == 200
    assert resp.json()["openfga"] == "ok"


def test_cross_app_access_exchange(base_url):
    username = unique("xaa")
    create_user(base_url, username, "password123")
    client_id = register_client(base_url)

    # The assertion's audience must match this server's configured OAUTH_ISSUER
    # (e.g. an ngrok URL), which isn't necessarily the same as base_url (e.g.
    # localhost) used to reach it in tests.
    issuer = requests.get(f"{base_url}/.well-known/oauth-authorization-server").json()["issuer"]

    assertion_resp = requests.post(
        f"{base_url}/mock-idp/login",
        json={"username": username, "password": "password123", "audience": issuer},
    )
    assert assertion_resp.status_code == 200, assertion_resp.text
    assertion = assertion_resp.json()["identity_assertion"]

    token_resp = requests.post(
        f"{base_url}/oauth/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
            "client_id": client_id,
        },
    )
    assert token_resp.status_code == 200, token_resp.text
    assert token_resp.json()["access_token"]


def test_cross_app_access_rejects_forged_issuer(base_url):
    client_id = register_client(base_url)
    # alg=none, unsigned - not from any trusted issuer
    forged = (
        "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."
        "eyJpc3MiOiJodHRwczovL2V2aWwuZXhhbXBsZS5jb20iLCJzdWIiOiJmb28ifQ."
    )
    resp = requests.post(
        f"{base_url}/oauth/token",
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": forged, "client_id": client_id},
    )
    assert resp.status_code == 400
    assert "untrusted" in resp.json()["detail"]


def test_sessions_list_and_revoke(base_url):
    username = unique("sess")
    create_user(base_url, username, "password123")
    client_id = register_client(base_url)
    tokens = oauth_login(base_url, username, "password123", client_id)

    rest_token = rest_login(base_url, username, "password123")
    sessions = requests.get(f"{base_url}/auth/sessions", headers=auth_header(rest_token)).json()
    # Two independent logins, two distinct sessions - the OAuth
    # authorization_code flow (the registered third-party client_id) and
    # this rest_login password grant (tracked under the fixed
    # "expense-tracker-web" client_id, see oauth/service.py's
    # WEB_SESSION_CLIENT_ID). Same idea as a "your devices & connected
    # apps" page listing a browser session and a connected app separately -
    # they shouldn't collapse into one. Pick the OAuth one by client_id
    # rather than assuming list order, since list_sessions sorts by
    # last_used_at and rest_login (the most recent action) sorts first.
    assert len(sessions) == 2
    oauth_session = next(s for s in sessions if s["client_id"] == client_id)

    revoke = requests.delete(f"{base_url}/auth/sessions/{oauth_session['session_id']}", headers=auth_header(rest_token))
    assert revoke.status_code == 204

    # the underlying refresh token must actually be dead, not just hidden from the list
    replay = requests.post(
        f"{base_url}/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"], "client_id": client_id},
    )
    assert replay.status_code == 400


def test_passwordless_login_round_trip(base_url):
    username = unique("magic")
    create_user(base_url, username, "password123")

    requested = requests.post(f"{base_url}/auth/passwordless/request", json={"username": username})
    assert requested.status_code == 200
    # The response never carries the code (see auth.py) - only the account's
    # real inbox does. Mailpit stands in for that inbox here.
    magic_token = get_passwordless_login_code(f"{username}@example.com")

    verified = requests.post(f"{base_url}/auth/passwordless/verify", json={"token": magic_token})
    assert verified.status_code == 200
    access_token = verified.json()["access_token"]

    me = requests.get(f"{base_url}/auth/me", headers=auth_header(access_token))
    assert me.status_code == 200
    assert me.json()["username"] == username

    # single-use
    replay = requests.post(f"{base_url}/auth/passwordless/verify", json={"token": magic_token})
    assert replay.status_code == 401


def test_passwordless_request_does_not_leak_username_existence(base_url):
    # Same response shape whether the username exists or not, and neither
    # case ever returns a usable code (see auth.py) - a caller learns
    # nothing that would let them tell the two apart, or log in either way.
    real_username = unique("real")
    create_user(base_url, real_username, "password123")

    real = requests.post(f"{base_url}/auth/passwordless/request", json={"username": real_username})
    fake = requests.post(f"{base_url}/auth/passwordless/request", json={"username": unique("doesnotexist")})

    assert real.status_code == fake.status_code == 200
    assert real.json() == fake.json()


def test_webhook_management_requires_admin(base_url):
    username = unique("nonadmin")
    create_user(base_url, username, "password123")
    token = rest_login(base_url, username, "password123")

    resp = requests.post(
        f"{base_url}/auth/webhooks",
        headers=auth_header(token),
        json={"url": "https://example.com/hook", "events": ["expense.created"]},
    )
    assert resp.status_code == 403
