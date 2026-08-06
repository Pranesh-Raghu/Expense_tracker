"""High-level authorization operations used by the REST API and MCP tools.

Nothing outside this module should talk to authz/client.py directly, and
nothing outside this module should know OpenFGA's user/relation/object
string format - callers pass plain ints (user ids, expense ids) and get
plain bools/lists back.
"""

import logging

from fastapi import HTTPException, status

from authz import client
from authz.model import ORG_OBJECT

logger = logging.getLogger("expense_tracker.authz")

SHARE_RELATIONS = ("viewer", "editor")


def _user_ref(user_id: int) -> str:
    return f"user:{user_id}"


def _expense_ref(expense_id: int) -> str:
    return f"expense:{expense_id}"


# ---------------------------------------------------------------------------
# Lifecycle hooks: called when an expense is created/deleted
# ---------------------------------------------------------------------------

def on_expense_created(owner_id: int, expense_id: int) -> None:
    client.write_tuples(writes=[
        {"user": _user_ref(owner_id), "relation": "owner", "object": _expense_ref(expense_id)},
        {"user": ORG_OBJECT, "relation": "parent_org", "object": _expense_ref(expense_id)},
    ])


def on_expense_deleted(expense_id: int) -> None:
    existing = client.read_tuples(object_=_expense_ref(expense_id))
    if not existing:
        return
    deletes = [{"user": t["user"], "relation": t["relation"], "object": t["object"]} for t in existing]
    client.write_tuples(deletes=deletes)


# ---------------------------------------------------------------------------
# Permission checks
# ---------------------------------------------------------------------------

def can_view(user_id: int, expense_id: int) -> bool:
    return client.check(_user_ref(user_id), "can_view", _expense_ref(expense_id))


def can_edit(user_id: int, expense_id: int) -> bool:
    return client.check(_user_ref(user_id), "can_edit", _expense_ref(expense_id))


def can_delete(user_id: int, expense_id: int) -> bool:
    return client.check(_user_ref(user_id), "can_delete", _expense_ref(expense_id))


def can_share(user_id: int, expense_id: int) -> bool:
    return client.check(_user_ref(user_id), "can_share", _expense_ref(expense_id))


def require(allowed: bool, detail: str = "You don't have permission to do that") -> None:
    if not allowed:
        logger.warning("permission denied: %s", detail)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def is_admin(user_id: int) -> bool:
    return client.check(_user_ref(user_id), "admin", ORG_OBJECT)


def list_viewable_expense_ids(user_id: int) -> list[int]:
    objects = client.list_objects(_user_ref(user_id), "can_view", "expense")
    return [int(obj.split(":", 1)[1]) for obj in objects]


def bulk_expense_permissions(user_id: int) -> dict[str, set[int]]:
    """The ids of every expense this user can edit/delete/share, one
    list_objects call per relation (3 total) - not one check() call per
    (expense, relation) pair. attach_bulk_permissions below uses this to
    give a whole list response its per-expense permissions in O(1) OpenFGA
    round trips per relation instead of O(number of expenses)."""
    user_ref = _user_ref(user_id)

    def _ids(relation: str) -> set[int]:
        return {int(obj.split(":", 1)[1]) for obj in client.list_objects(user_ref, relation, "expense")}

    return {
        "can_edit": _ids("can_edit"),
        "can_delete": _ids("can_delete"),
        "can_share": _ids("can_share"),
    }


# ---------------------------------------------------------------------------
# Role and sharing management
# ---------------------------------------------------------------------------

def grant_admin(user_id: int) -> None:
    if is_admin(user_id):
        return
    client.write_tuples(writes=[{"user": _user_ref(user_id), "relation": "admin", "object": ORG_OBJECT}])
    logger.info("granted admin role to user_id=%s", user_id)


def revoke_admin(user_id: int) -> None:
    if not is_admin(user_id):
        return
    client.write_tuples(deletes=[{"user": _user_ref(user_id), "relation": "admin", "object": ORG_OBJECT}])
    logger.info("revoked admin role from user_id=%s", user_id)


def share_expense(expense_id: int, target_user_id: int, relation: str) -> None:
    if relation not in SHARE_RELATIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"relation must be one of {SHARE_RELATIONS}")

    # OpenFGA rejects both duplicate writes and deletes of non-existent
    # tuples, so reconcile against what's actually there first: if the
    # target already has this exact relation, there's nothing to do; if they
    # have the other one (e.g. upgrading viewer -> editor), swap it.
    existing = client.read_tuples(object_=_expense_ref(expense_id), user=_user_ref(target_user_id))
    existing_relations = {t["relation"] for t in existing if t["relation"] in SHARE_RELATIONS}
    if relation in existing_relations:
        return

    deletes = [
        {"user": _user_ref(target_user_id), "relation": r, "object": _expense_ref(expense_id)}
        for r in existing_relations
    ]
    client.write_tuples(
        writes=[{"user": _user_ref(target_user_id), "relation": relation, "object": _expense_ref(expense_id)}],
        deletes=deletes,
    )


def unshare_expense(expense_id: int, target_user_id: int) -> None:
    # OpenFGA errors on deleting a tuple that doesn't exist, so look up which
    # relation (viewer or editor) is actually present before deleting it.
    existing = client.read_tuples(object_=_expense_ref(expense_id), user=_user_ref(target_user_id))
    deletes = [
        {"user": t["user"], "relation": t["relation"], "object": t["object"]}
        for t in existing if t["relation"] in SHARE_RELATIONS
    ]
    client.write_tuples(deletes=deletes)
