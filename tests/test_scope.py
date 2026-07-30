import pytest
import requests

from tests.conftest import create_user, mcp_call, mcp_initialize, oauth_login, register_client, unique


def test_read_only_scope_blocks_write_tools(base_url):
    username = unique("scope")
    create_user(base_url, username, "password123")
    client_id = register_client(base_url)
    tokens = oauth_login(base_url, username, "password123", client_id, scope="expenses:read")
    assert tokens["scope"] == "expenses:read"
    token = tokens["access_token"]

    session_id = mcp_initialize(base_url, token)

    # read tool succeeds
    mcp_call(base_url, token, session_id, "list_expenses", {})

    # write tool is blocked by scope, not just by authz
    with pytest.raises(RuntimeError, match="expenses:write"):
        mcp_call(base_url, token, session_id, "add_expense", {"amount": 1, "category": "FOOD", "transaction": "DEBIT"})


def test_unscoped_token_stays_unrestricted(base_url):
    """Backward compatibility: a token with no scope requested at all must
    still be able to write - this is how every token before scope
    enforcement existed behaved, and nothing should have silently broken."""
    username = unique("scope")
    create_user(base_url, username, "password123")
    client_id = register_client(base_url)
    tokens = oauth_login(base_url, username, "password123", client_id)
    assert not tokens.get("scope")
    token = tokens["access_token"]

    session_id = mcp_initialize(base_url, token)
    result = mcp_call(base_url, token, session_id, "add_expense", {"amount": 1, "category": "FOOD", "transaction": "DEBIT"})
    assert result["structuredContent"]["amount"] == 1
