"""Thin sync HTTP client for OpenFGA, plus idempotent store/model bootstrap.

Sync (not async) deliberately: the rest of this codebase's request handlers
and MCP tools are synchronous functions, and these are fast local calls to
the openfga container - not worth threading an async client through
everything just for this.
"""

import os
import time

import httpx

from authz.model import AUTHORIZATION_MODEL, STORE_NAME

OPENFGA_API_URL = os.environ.get("OPENFGA_API_URL", "http://localhost:8081")

_store_id: str | None = None
_model_id: str | None = None


def _client() -> httpx.Client:
    return httpx.Client(base_url=OPENFGA_API_URL, timeout=5.0)


def bootstrap() -> tuple[str, str]:
    """Find-or-create the store and authorization model. Idempotent - safe
    to call on every app startup, including against an already-bootstrapped
    OpenFGA instance from a previous run (the store/model persist in MySQL).
    """
    global _store_id, _model_id
    if _store_id and _model_id:
        return _store_id, _model_id

    # The app container can start before the openfga container has finished
    # migrating/booting - retry rather than crashing the whole app on a
    # transient connection failure during startup. On Render's free tier
    # specifically, an idle service spins all the way down (not just
    # "asleep" - the container is torn down), so waking it can take well
    # over 30s; the old 15-attempt/2s budget (30s total) wasn't enough and
    # crash-looped the app whenever OpenFGA happened to be cold. 40
    # attempts/3s (120s) comfortably outlasts that.
    last_error = None
    for attempt in range(40):
        try:
            # Longer timeout than _client()'s usual 5s: while cold, OpenFGA
            # may accept the connection but respond slowly rather than
            # refusing outright, and 5s isn't always enough to tell the
            # difference from a real hang.
            with httpx.Client(base_url=OPENFGA_API_URL, timeout=10.0) as client:
                client.get("/healthz").raise_for_status()
            last_error = None
            break
        except httpx.HTTPError as exc:
            last_error = exc
            time.sleep(3)
    if last_error:
        raise RuntimeError(f"OpenFGA not reachable at {OPENFGA_API_URL} after retries") from last_error

    with _client() as client:
        stores = client.get("/stores").json().get("stores", [])
        existing = next((s for s in stores if s["name"] == STORE_NAME), None)
        store_id = existing["id"] if existing else client.post("/stores", json={"name": STORE_NAME}).json()["id"]

        models = client.get(f"/stores/{store_id}/authorization-models").json().get("authorization_models", [])
        if models:
            # OpenFGA returns models newest-first.
            model_id = models[0]["id"]
        else:
            model_id = client.post(
                f"/stores/{store_id}/authorization-models", json=AUTHORIZATION_MODEL
            ).json()["authorization_model_id"]

    _store_id, _model_id = store_id, model_id
    return store_id, model_id


def check(user: str, relation: str, object_: str) -> bool:
    store_id, model_id = bootstrap()
    with _client() as client:
        response = client.post(
            f"/stores/{store_id}/check",
            json={
                "tuple_key": {"user": user, "relation": relation, "object": object_},
                "authorization_model_id": model_id,
            },
        )
        response.raise_for_status()
        return response.json().get("allowed", False)


def write_tuples(writes: list[dict] | None = None, deletes: list[dict] | None = None) -> None:
    """writes/deletes are lists of {"user": ..., "relation": ..., "object": ...} dicts."""
    if not writes and not deletes:
        return
    store_id, model_id = bootstrap()
    body = {"authorization_model_id": model_id}
    if writes:
        body["writes"] = {"tuple_keys": writes}
    if deletes:
        body["deletes"] = {"tuple_keys": deletes}
    with _client() as client:
        response = client.post(f"/stores/{store_id}/write", json=body)
        response.raise_for_status()


def read_tuples(object_: str | None = None, user: str | None = None, relation: str | None = None) -> list[dict]:
    store_id, _ = bootstrap()
    tuple_key = {}
    if object_:
        tuple_key["object"] = object_
    if user:
        tuple_key["user"] = user
    if relation:
        tuple_key["relation"] = relation
    with _client() as client:
        response = client.post(f"/stores/{store_id}/read", json={"tuple_key": tuple_key})
        response.raise_for_status()
        return [t["key"] for t in response.json().get("tuples", [])]


def list_objects(user: str, relation: str, type_: str) -> list[str]:
    store_id, model_id = bootstrap()
    with _client() as client:
        response = client.post(
            f"/stores/{store_id}/list-objects",
            json={"type": type_, "relation": relation, "user": user, "authorization_model_id": model_id},
        )
        response.raise_for_status()
        return response.json().get("objects", [])
