"""MCP server exposing the expense tracker as tools over Streamable HTTP.

This is the OAuth "protected resource" side of the MCP spec. FastMCP's
RemoteAuthProvider wraps our HybridTokenVerifier (oauth/token_verifier.py) to:
  - reject requests with a missing/invalid Bearer token (401 +
    WWW-Authenticate pointing at our protected resource metadata), and
  - serve RFC 9728 protected resource metadata itself, listing this app's
    own OAuth authorization server (oauth/router.py) as the issuer to use.
"""

from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.auth.auth import RemoteAuthProvider
from fastmcp.server.dependencies import get_access_token

from authz import service as authz
from oauth import service
from oauth.token_verifier import HybridTokenVerifier
from schemas.expense_schemas import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from services import expense_services

auth_provider = RemoteAuthProvider(
    token_verifier=HybridTokenVerifier(),
    authorization_servers=[service.ISSUER],
    # base_url + the mcp_path passed to http_app() below (RemoteAuthProvider
    # appends it) together form the resource URL - it must equal
    # service.MCP_RESOURCE_URL, which is what's checked as the JWT `aud`.
    base_url=service.ISSUER,
    resource_name="Expense Tracker",
)

mcp = FastMCP("expense-tracker", auth=auth_provider)


def _current_user() -> dict:
    token = get_access_token()
    if not token or not token.subject:
        raise PermissionError("no authenticated user on this request")
    username = (token.claims or {}).get("username", "")
    return {"username": username, "id": int(token.subject)}


def _require_scope(required: str) -> None:
    """Enforce the OAuth scope the token was actually issued with.

    A token with NO scope at all (the common case: a client that didn't
    request one, or an API key - HybridTokenVerifier always grants API keys
    both scopes) is treated as unrestricted, matching how every token minted
    before this check existed behaved - this stays backward compatible.
    A token that DOES carry scopes is capped to exactly those: a client that
    asked for "expenses:read" only should never be able to write, even if
    the authenticated user otherwise could.
    """
    token = get_access_token()
    scopes = token.scopes if token else []
    if scopes and required not in scopes:
        raise PermissionError(f"this token's scope does not include '{required}'")


def _serialize(expense) -> dict:
    return ExpenseResponse.model_validate(expense, from_attributes=True).model_dump(mode="json")


@mcp.tool()
def list_expenses() -> list[dict]:
    """List every expense recorded by the current user."""
    _require_scope("expenses:read")
    user = _current_user()
    expenses = expense_services.get_all_expenses(user)
    return [_serialize(e) for e in expenses]


@mcp.tool()
def get_expense(expense_id: int) -> dict:
    """Get a single expense by id."""
    _require_scope("expenses:read")
    user = _current_user()
    return _serialize(expense_services.get_expense_by_id(user, expense_id))


@mcp.tool()
def add_expense(amount: float, category: str, transaction: str) -> dict:
    """Record a new expense. category and transaction must match one of the
    values returned by list_categories / list_transaction_types."""
    _require_scope("expenses:write")
    user = _current_user()
    # Ownership comes from `user`, passed separately to create_expense below -
    # ExpenseCreate has no user_id field, so a user_id kwarg here would be
    # silently dropped by pydantic rather than doing anything.
    payload = ExpenseCreate(amount=amount, category=category, transaction=transaction)
    return _serialize(expense_services.create_expense(user, payload))


@mcp.tool()
def update_expense(
    expense_id: int,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    transaction: Optional[str] = None,
) -> dict:
    """Update fields on an existing expense. Only provided fields change."""
    _require_scope("expenses:write")
    user = _current_user()
    payload = ExpenseUpdate(amount=amount, category=category, transaction=transaction)
    return _serialize(expense_services.update_expense(user, expense_id, payload))


@mcp.tool()
def delete_expense(expense_id: int) -> dict:
    """Delete an expense by id."""
    _require_scope("expenses:write")
    user = _current_user()
    return _serialize(expense_services.delete_expense(user, expense_id))


@mcp.tool()
def share_expense(expense_id: int, target_user_id: int, relation: str) -> dict:
    """Share an expense with another user. relation must be "viewer" (read-only)
    or "editor" (can also update it). Only the owner, or an org admin, can share."""
    _require_scope("expenses:write")
    user = _current_user()
    return expense_services.share_expense(user, expense_id, target_user_id, relation)


@mcp.tool()
def unshare_expense(expense_id: int, target_user_id: int) -> dict:
    """Remove another user's shared access (viewer or editor) to an expense."""
    _require_scope("expenses:write")
    user = _current_user()
    return expense_services.unshare_expense(user, expense_id, target_user_id)


@mcp.tool()
def my_permissions() -> dict:
    """Report whether the current user has the org admin role."""
    user = _current_user()
    return {"user_id": user["id"], "username": user["username"], "is_admin": authz.is_admin(user["id"])}


@mcp.tool()
def list_categories() -> list[str]:
    """List the valid expense categories."""
    _require_scope("expenses:read")
    user = _current_user()
    return [c.value for c in expense_services.expense_categories(user)["categories"]]


@mcp.tool()
def list_transaction_types() -> list[str]:
    """List the valid transaction types (e.g. DEBIT, CREDIT)."""
    _require_scope("expenses:read")
    user = _current_user()
    return [t.value for t in expense_services.expense_transaction_types(user)["transaction"]]


@mcp.tool()
def monthly_report(year: int, month: int) -> list[dict]:
    """Get every expense recorded in a given month."""
    _require_scope("expenses:read")
    user = _current_user()
    return [_serialize(e) for e in expense_services.get_monthly_reports(user, month, year)]


@mcp.tool()
def monthly_total(year: int, month: int) -> dict:
    """Get the total expense amount for a given month."""
    _require_scope("expenses:read")
    user = _current_user()
    return expense_services.get_monthly_amount(user, month, year)


@mcp.tool()
def yearly_report(year: int) -> list[dict]:
    """Get every expense recorded in a given year."""
    _require_scope("expenses:read")
    user = _current_user()
    return [_serialize(e) for e in expense_services.get_yearly_reports(user, year)]


@mcp.tool()
def yearly_total(year: int) -> dict:
    """Get the total expense amount for a given year."""
    _require_scope("expenses:read")
    user = _current_user()
    return expense_services.get_yearly_amount(user, year)


def build_mcp_asgi_app():
    """Streamable-HTTP ASGI app for the MCP server, mounted at /mcp in main.py."""
    return mcp.http_app(path="/mcp")
