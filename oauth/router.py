import os

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models.user_model import User
from oauth import cross_app_access, keys, service
from oauth.schemas import ClientRegistrationRequest, ClientRegistrationResponse
import rate_limit

JWT_BEARER_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ---------------------------------------------------------------------------
# RFC 8414 / RFC 9728 metadata + JWKS
# ---------------------------------------------------------------------------

@router.get("/.well-known/oauth-authorization-server")
def authorization_server_metadata():
    issuer = service.ISSUER
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "introspection_endpoint": f"{issuer}/oauth/introspect",
        "jwks_uri": f"{issuer}/.well-known/jwks.json",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token", JWT_BEARER_GRANT],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_basic"],
        "scopes_supported": ["expenses:read", "expenses:write"],
    }


# Protected resource metadata (RFC 9728) for the /mcp resource is served by
# FastMCP's RemoteAuthProvider itself (see mcp_server.py) - it owns the exact
# path convention (metadata URL reflects the resource's own path) and there's
# no value in this app maintaining a second, hand-written copy that could
# drift out of sync with it.


@router.get("/.well-known/jwks.json")
def jwks():
    return keys.get_jwks()


# ---------------------------------------------------------------------------
# Dynamic Client Registration (RFC 7591)
# ---------------------------------------------------------------------------

@router.post("/oauth/register", response_model=ClientRegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_client(payload: ClientRegistrationRequest):
    if payload.token_endpoint_auth_method not in ("none", "client_secret_basic"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported token_endpoint_auth_method")
    for uri in payload.redirect_uris:
        if not (uri.startswith("https://") or uri.startswith("http://localhost") or uri.startswith("http://127.0.0.1")):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"redirect_uri must be https (or localhost for dev): {uri}")
    return service.register_client(payload)


# ---------------------------------------------------------------------------
# Authorization endpoint: login + consent, then issue an authorization code
# ---------------------------------------------------------------------------

@router.get("/oauth/authorize", response_class=HTMLResponse)
async def authorize(
    request: Request,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    code_challenge_method: str,
    state: str | None = None,
    scope: str | None = None,
    resource: str | None = None,
):
    if response_type != "code":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_response_type")
    if code_challenge_method != "S256":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_request: code_challenge_method must be S256")

    client = await service.resolve_client(client_id)
    service.validate_redirect_uri(client, redirect_uri)

    return templates.TemplateResponse(request, "login.html", {
        "client_id": client_id,
        "client_name": getattr(client, "client_id", client_id),
        "redirect_uri": redirect_uri,
        "state": state or "",
        "scope": scope or "",
        "resource": resource or "",
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "error": None,
    })


@router.post("/oauth/authorize", response_class=HTMLResponse)
async def authorize_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    decision: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    state: str = Form(""),
    scope: str = Form(""),
    resource: str = Form(""),
):
    client = await service.resolve_client(client_id)
    service.validate_redirect_uri(client, redirect_uri)

    if decision != "approve":
        query = f"error=access_denied" + (f"&state={state}" if state else "")
        return RedirectResponse(url=f"{redirect_uri}?{query}", status_code=status.HTTP_302_FOUND)

    user = User.authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse(request, "login.html", {
            "client_id": client_id,
            "client_name": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scope,
            "resource": resource,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "error": "Invalid username or password",
        }, status_code=status.HTTP_401_UNAUTHORIZED)

    code = service.create_authorization_code(
        client_id=client_id,
        user_id=user.id,
        redirect_uri=redirect_uri,
        scope=scope or None,
        resource=resource or None,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

    query = f"code={code}" + (f"&state={state}" if state else "")
    return RedirectResponse(url=f"{redirect_uri}?{query}", status_code=status.HTTP_302_FOUND)


# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------

def _client_ip(request: Request) -> str | None:
    # Behind ngrok/a reverse proxy, the real client IP is in X-Forwarded-For
    # (first entry = original client); fall back to the direct connection.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/oauth/token")
async def token(
    request: Request,
    grant_type: str = Form(...),
    code: str | None = Form(None),
    redirect_uri: str | None = Form(None),
    code_verifier: str | None = Form(None),
    refresh_token: str | None = Form(None),
    assertion: str | None = Form(None),
    resource: str | None = Form(None),
    client_id: str = Form(...),
    client_secret: str | None = Form(None),
):
    ip_address = _client_ip(request)
    # IP-keyed slows one attacker hammering many clients/refresh tokens;
    # client-keyed slows guessing one client's secret or refresh tokens
    # from many IPs. Checked before resolving the client so a throttled
    # caller doesn't get a free client-secret comparison each time.
    rate_limit.enforce(f"oauth-token:ip:{ip_address or 'unknown'}", max_attempts=30, window_seconds=300)
    rate_limit.enforce(f"oauth-token:client:{client_id}", max_attempts=30, window_seconds=300)

    client = await service.resolve_client(client_id)
    service.verify_client_secret(client, client_secret)
    user_agent = request.headers.get("user-agent")

    if grant_type == "authorization_code":
        if not (code and redirect_uri and code_verifier):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_request: missing code/redirect_uri/code_verifier")
        grant = service.consume_authorization_code(
            code=code, client_id=client_id, redirect_uri=redirect_uri, code_verifier=code_verifier,
        )
        result = service.issue_token_pair(
            user_id=grant["user_id"], client_id=client_id, scope=grant["scope"], resource=grant["resource"],
            user_agent=user_agent, ip_address=ip_address,
        )
        return JSONResponse(result)

    if grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_request: missing refresh_token")
        result = service.refresh_token_grant(
            refresh_token=refresh_token, client_id=client_id, user_agent=user_agent, ip_address=ip_address,
        )
        return JSONResponse(result)

    if grant_type == JWT_BEARER_GRANT:
        # Cross-App Access (RFC 7523): exchange a signed identity assertion
        # from a trusted external issuer for a native token here - no
        # interactive login for this user at this server.
        if not assertion:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_request: missing assertion")
        verified = await cross_app_access.verify_identity_assertion(
            assertion, client_id=client_id, expected_audience=service.ISSUER,
        )
        user = User.get_users()
        matched = next((u for u in user if u.username == verified["subject"]), None)
        if not matched:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: no local account matches the asserted identity")
        result = service.issue_token_pair(
            user_id=matched.id, client_id=client_id, scope=None, resource=resource,
            user_agent=user_agent, ip_address=ip_address,
        )
        return JSONResponse(result)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_grant_type")


@router.post("/oauth/revoke")
def revoke(token: str = Form(...), token_type_hint: str | None = Form(None)):
    if token_type_hint == "refresh_token":
        service.revoke_refresh_token(token)
    else:
        service.revoke_access_token(token)
        service.revoke_refresh_token(token)
    return JSONResponse({}, status_code=status.HTTP_200_OK)


@router.post("/oauth/introspect")
def introspect(token: str = Form(...)):
    return service.introspect(token)
