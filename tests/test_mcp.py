import requests

from tests.conftest import create_user, mcp_call, mcp_initialize, oauth_login, register_client, unique


def test_mcp_rejects_missing_token_with_discovery_header(base_url):
    resp = requests.post(
        f"{base_url}/mcp",
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "1"}},
        },
    )
    assert resp.status_code == 401
    assert "resource_metadata" in resp.headers.get("www-authenticate", "")


def test_mcp_tool_call_round_trip(base_url):
    username = unique("mcp")
    create_user(base_url, username, "password123")
    client_id = register_client(base_url)
    tokens = oauth_login(base_url, username, "password123", client_id)
    token = tokens["access_token"]

    session_id = mcp_initialize(base_url, token)

    created = mcp_call(base_url, token, session_id, "add_expense", {"amount": 12.5, "category": "FOOD", "transaction": "DEBIT"})
    expense = created["structuredContent"]
    assert expense["amount"] == 12.5

    listed = mcp_call(base_url, token, session_id, "list_expenses", {})
    ids = [e["id"] for e in listed["structuredContent"]["result"]]
    assert expense["id"] in ids
