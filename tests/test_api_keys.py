import requests

from tests.conftest import create_user, rest_login, unique


def test_api_key_works_on_rest_and_is_revocable(base_url):
    username = unique("apikey")
    create_user(base_url, username, "password123")
    session_token = rest_login(base_url, username, "password123")

    created = requests.post(
        f"{base_url}/auth/api-keys",
        headers={"Authorization": f"Bearer {session_token}"},
        json={"name": "pytest-key"},
    )
    assert created.status_code == 201, created.text
    api_key = created.json()["api_key"]
    assert api_key.startswith("eak_")

    resp = requests.get(f"{base_url}/expenses/", headers={"Authorization": f"Bearer {api_key}"})
    assert resp.status_code == 200

    listing = requests.get(f"{base_url}/auth/api-keys", headers={"Authorization": f"Bearer {session_token}"})
    key_id = next(k["key_id"] for k in listing.json() if k["name"] == "pytest-key")

    revoked = requests.delete(f"{base_url}/auth/api-keys/{key_id}", headers={"Authorization": f"Bearer {session_token}"})
    assert revoked.status_code == 204

    resp_after = requests.get(f"{base_url}/expenses/", headers={"Authorization": f"Bearer {api_key}"})
    assert resp_after.status_code == 401
