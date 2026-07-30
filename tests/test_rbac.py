import requests

from tests.conftest import create_user, rest_login, unique


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_owner_full_access_stranger_zero_access(base_url):
    owner = unique("owner")
    stranger = unique("stranger")
    create_user(base_url, owner, "password123")
    create_user(base_url, stranger, "password123")
    owner_token = rest_login(base_url, owner, "password123")
    stranger_token = rest_login(base_url, stranger, "password123")

    created = requests.post(
        f"{base_url}/expenses/",
        headers=auth_header(owner_token),
        json={"amount": 100, "category": "FOOD", "transaction": "DEBIT", "user_id": 0},
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    view_own = requests.get(f"{base_url}/expenses/{expense_id}", headers=auth_header(owner_token))
    assert view_own.status_code == 200

    view_stranger = requests.get(f"{base_url}/expenses/{expense_id}", headers=auth_header(stranger_token))
    assert view_stranger.status_code == 403


def test_viewer_share_grants_read_not_write(base_url):
    owner = unique("owner")
    viewer = unique("viewer")
    create_user(base_url, owner, "password123")
    viewer_id = create_user(base_url, viewer, "password123")
    owner_token = rest_login(base_url, owner, "password123")
    viewer_token = rest_login(base_url, viewer, "password123")

    expense_id = requests.post(
        f"{base_url}/expenses/",
        headers=auth_header(owner_token),
        json={"amount": 50, "category": "FOOD", "transaction": "DEBIT", "user_id": 0},
    ).json()["id"]

    share = requests.post(
        f"{base_url}/expenses/{expense_id}/share",
        headers=auth_header(owner_token),
        json={"target_user_id": viewer_id, "relation": "viewer"},
    )
    assert share.status_code == 200, share.text

    view = requests.get(f"{base_url}/expenses/{expense_id}", headers=auth_header(viewer_token))
    assert view.status_code == 200

    delete_attempt = requests.delete(f"{base_url}/expenses/{expense_id}", headers=auth_header(viewer_token))
    assert delete_attempt.status_code == 403


def test_editor_share_grants_write(base_url):
    owner = unique("owner")
    editor = unique("editor")
    create_user(base_url, owner, "password123")
    editor_id = create_user(base_url, editor, "password123")
    owner_token = rest_login(base_url, owner, "password123")
    editor_token = rest_login(base_url, editor, "password123")

    expense_id = requests.post(
        f"{base_url}/expenses/",
        headers=auth_header(owner_token),
        json={"amount": 50, "category": "FOOD", "transaction": "DEBIT", "user_id": 0},
    ).json()["id"]

    requests.post(
        f"{base_url}/expenses/{expense_id}/share",
        headers=auth_header(owner_token),
        json={"target_user_id": editor_id, "relation": "editor"},
    )

    update = requests.put(
        f"{base_url}/expenses/{expense_id}",
        headers=auth_header(editor_token),
        json={"amount": 999},
    )
    assert update.status_code in (200, 201), update.text
    assert update.json()["amount"] == 999
    # category/transaction from the original create must survive a
    # partial update (regression check for the exclude_none=True fix).
    assert update.json()["category"] == "FOOD"

    delete_attempt = requests.delete(f"{base_url}/expenses/{expense_id}", headers=auth_header(editor_token))
    assert delete_attempt.status_code == 403


def test_unshare_revokes_access(base_url):
    owner = unique("owner")
    viewer = unique("viewer")
    create_user(base_url, owner, "password123")
    viewer_id = create_user(base_url, viewer, "password123")
    owner_token = rest_login(base_url, owner, "password123")
    viewer_token = rest_login(base_url, viewer, "password123")

    expense_id = requests.post(
        f"{base_url}/expenses/",
        headers=auth_header(owner_token),
        json={"amount": 50, "category": "FOOD", "transaction": "DEBIT", "user_id": 0},
    ).json()["id"]

    requests.post(
        f"{base_url}/expenses/{expense_id}/share",
        headers=auth_header(owner_token),
        json={"target_user_id": viewer_id, "relation": "viewer"},
    )
    assert requests.get(f"{base_url}/expenses/{expense_id}", headers=auth_header(viewer_token)).status_code == 200

    unshare = requests.delete(f"{base_url}/expenses/{expense_id}/share/{viewer_id}", headers=auth_header(owner_token))
    assert unshare.status_code == 200

    assert requests.get(f"{base_url}/expenses/{expense_id}", headers=auth_header(viewer_token)).status_code == 403


def test_stranger_cannot_share_someone_elses_expense(base_url):
    owner = unique("owner")
    stranger = unique("stranger")
    create_user(base_url, owner, "password123")
    create_user(base_url, stranger, "password123")
    target_id = create_user(base_url, unique("target"), "password123")
    owner_token = rest_login(base_url, owner, "password123")
    stranger_token = rest_login(base_url, stranger, "password123")

    expense_id = requests.post(
        f"{base_url}/expenses/",
        headers=auth_header(owner_token),
        json={"amount": 50, "category": "FOOD", "transaction": "DEBIT", "user_id": 0},
    ).json()["id"]

    forbidden = requests.post(
        f"{base_url}/expenses/{expense_id}/share",
        headers=auth_header(stranger_token),
        json={"target_user_id": target_id, "relation": "viewer"},
    )
    assert forbidden.status_code == 403
