import requests

from tests.conftest import create_user, rest_login, unique


def test_registration_stays_public(base_url):
    resp = requests.post(
        f"{base_url}/users/",
        json={"username": unique("public"), "password": "password123"},
    )
    assert resp.status_code == 201


def test_listing_requires_auth(base_url):
    resp = requests.get(f"{base_url}/users/")
    assert resp.status_code == 401


def test_self_can_view_own_record_stranger_cannot(base_url):
    username = unique("self")
    stranger = unique("stranger")
    user_id = create_user(base_url, username, "password123")
    create_user(base_url, stranger, "password123")
    own_token = rest_login(base_url, username, "password123")
    stranger_token = rest_login(base_url, stranger, "password123")

    own = requests.get(f"{base_url}/users/{user_id}", headers={"Authorization": f"Bearer {own_token}"})
    assert own.status_code == 200

    other = requests.get(f"{base_url}/users/{user_id}", headers={"Authorization": f"Bearer {stranger_token}"})
    assert other.status_code == 403


def test_delete_requires_admin(base_url):
    username = unique("nonadmin")
    target = unique("target")
    create_user(base_url, username, "password123")
    target_id = create_user(base_url, target, "password123")
    token = rest_login(base_url, username, "password123")

    resp = requests.delete(f"{base_url}/users/{target_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
