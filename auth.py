import logging
import os

from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from typing import Annotated
from urllib.parse import urlparse
from passlib.context import CryptContext  # pyright: ignore[reportMissingModuleSource]
from models.user_model import User
from schemas.user_schemas import Token
from avatar import gravatar_url_strict
from oauth import service as oauth_service
from oauth import keys as oauth_keys
from oauth.schemas import (
    ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyInfo, TrustedIssuerCreateRequest, TrustedIssuerInfo,
    SessionInfo, WebhookCreateRequest, WebhookCreateResponse, WebhookInfo,
    PasswordlessRequestRequest, PasswordlessRequestResponse, PasswordlessVerifyRequest,
)
from authz import service as authz
from ssrf_guard import is_public_hostname
import email_sender
import rate_limit
import google_oauth
import webhooks
import json
import secrets
from database import SessionLocal
from oauth.models import TrustedIssuer, WebhookEndpoint

logger = logging.getLogger("expense_tracker.auth")

router = APIRouter()


def _load_or_create_secret_key() -> str:
    """REST_JWT_SECRET_KEY signs the web-login JWT (password/Google/
    passwordless). A hardcoded fallback here would be checked into this
    public repo - anyone who reads the source could forge a valid login
    token for any user_id without ever authenticating. Prefer an explicit
    env var; otherwise generate one and persist it next to the OAuth RSA
    keys (oauth/keys.py uses the same OAUTH_KEY_DIR volume) so it survives
    container restarts instead of silently rotating - and invalidating
    every session - on every deploy."""
    env_value = os.environ.get('REST_JWT_SECRET_KEY')
    if env_value:
        return env_value

    key_dir = os.environ.get("OAUTH_KEY_DIR", os.path.join(os.path.dirname(__file__), "keys"))
    secret_path = os.path.join(key_dir, "rest_jwt_secret")
    if os.path.exists(secret_path):
        with open(secret_path) as f:
            return f.read().strip()

    os.makedirs(key_dir, exist_ok=True)
    generated = secrets.token_urlsafe(48)
    try:
        fd = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(generated)
        return generated
    except FileExistsError:
        # Lost the race with another worker process starting concurrently -
        # whoever won already wrote a value, so use that instead.
        with open(secret_path) as f:
            return f.read().strip()


SECRET_KEY = _load_or_create_secret_key()
ALGORITHM = 'HS256'



bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    jti = secrets.token_urlsafe(16)
    expires = datetime.now(timezone.utc) + expires_delta
    encode = {'sub': username, 'id': user_id, 'jti': jti, 'exp': expires}
    token = jwt.encode(encode, SECRET_KEY, algorithm = ALGORITHM)
    return token, jti


def _client_ip(request: Request) -> str | None:
    # Behind ngrok/a reverse proxy, the real client IP is in
    # X-Forwarded-For (first entry = original client) - same logic as
    # oauth/router.py's version of this helper.
    forwarded = request.headers.get('x-forwarded-for')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else None


def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    # Static API keys are a second, long-lived credential type for scripts and
    # automation where an interactive login isn't practical - accepted here
    # so the whole REST API works with either credential.
    if token.startswith(oauth_service.API_KEY_PREFIX):
        info = oauth_service.verify_api_key(token)
        if not info:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate API key')
        user = User.get_user(info['user_id'])
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate API key')
        return {'username': user.username, 'id': user.id}

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub', '')
        user_id: int = payload.get('id', 0)
        jti: str | None = payload.get('jti')

        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')

        # Makes "Revoke" on the Sessions & devices page actually invalidate
        # this specific token, instead of only hiding it from the list -
        # without this, a password/Google login's JWT would stay valid
        # until its natural 100-minute expiry regardless of revocation.
        if jti and oauth_service.is_web_session_revoked(jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Session has been revoked')

        return {'username': username, 'id': user_id}

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate token')


user_dependency = Annotated[dict, Depends(get_current_user)]

ACCESS_TOKEN_TTL = timedelta(minutes=100)


def _issue_and_record(request: Request, user) -> str:
    """Every REST/web login path (password, Google, passwordless) funnels
    through here: mints the JWT and records it as a session (see
    oauth_service.record_web_session) so it shows up in - and can actually
    be killed from - the Sessions & devices page, not just the OAuth
    authorization-code flow's own sessions."""
    token, jti = create_access_token(user.username, user.id, ACCESS_TOKEN_TTL)
    oauth_service.record_web_session(
        user_id=user.id, jti=jti, ttl=ACCESS_TOKEN_TTL,
        user_agent=request.headers.get('user-agent'), ip_address=_client_ip(request),
    )
    return token


@router.post("/token", response_model=Token)
async def login_for_access_token(request: Request, form_data: Annotated[OAuth2PasswordRequestForm,Depends()]):
    # Two keys, not one: an IP-keyed limit slows one attacker guessing many
    # usernames; a username-keyed limit slows credential-stuffing the same
    # account from many IPs. Checked before the password check itself so a
    # throttled caller doesn't get a free bcrypt comparison each time.
    client_ip = _client_ip(request) or "unknown"
    rate_limit.enforce(f"login:ip:{client_ip}", max_attempts=20, window_seconds=300)
    rate_limit.enforce(f"login:user:{form_data.username}", max_attempts=10, window_seconds=300)

    user = User.authenticate_user(form_data.username, form_data.password)

    if not user:
        logger.warning("failed login attempt for username=%s", form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')

    logger.info("login: user_id=%s username=%s", user.id, user.username)
    webhooks.dispatch_event("user.login", {"user_id": user.id, "username": user.username})

    token = _issue_and_record(request, user)

    return  {'access_token':token, 'token_type':'bearer'}


@router.get("/google/login")
def google_login():
    url, _state = google_oauth.build_authorize_url()
    return RedirectResponse(url)


@router.get("/google/callback")
def google_callback(request: Request, code: str, state: str):
    if not google_oauth.consume_state(state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid or expired OAuth state')

    try:
        google_access_token = google_oauth.exchange_code_for_access_token(code)
        userinfo = google_oauth.fetch_userinfo(google_access_token)
    except Exception:
        logger.exception("google oauth exchange failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Google sign-in failed')

    email = userinfo.get('email')
    if not email or not userinfo.get('email_verified'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Google account has no verified email')

    user = User.find_or_create_by_email(email, picture_url=userinfo.get('picture'))
    logger.info("google login: user_id=%s username=%s", user.id, user.username)
    webhooks.dispatch_event("user.login", {"user_id": user.id, "username": user.username})

    token = _issue_and_record(request, user)
    # Not /auth/callback: /auth/* is reserved for the backend rewrite on
    # the frontend's static site (see the frontend router's own comment),
    # so a request there never reaches the SPA at all.
    return RedirectResponse(f"{google_oauth.FRONTEND_URL}/login/callback?token={token}")


@router.post("/passwordless/request", response_model=PasswordlessRequestResponse)
def request_passwordless_login(request: Request, payload: PasswordlessRequestRequest):
    client_ip = _client_ip(request) or "unknown"
    rate_limit.enforce(f"passwordless-request:ip:{client_ip}", max_attempts=10, window_seconds=300)
    rate_limit.enforce(f"passwordless-request:user:{payload.username}", max_attempts=5, window_seconds=300)

    user = User.get_users()
    matched = next((u for u in user if u.username == payload.username), None)
    if matched:
        token = oauth_service.request_passwordless_login(matched.id)
        email_sender.send_passwordless_login_code(
            matched.email, token, int(oauth_service.PASSWORDLESS_TOKEN_TTL.total_seconds())
        )
    # Same response whether the username exists or not, and it never carries
    # the login code either way - a caller only ever learns "an email may
    # have gone out", never gets back something they could use to log in.
    # A different response (or a real token only when the user exists)
    # would let anyone who knows a username both enumerate accounts and log
    # in as them with zero credentials - which is exactly what this
    # endpoint used to do before email_sender.py existed.
    return PasswordlessRequestResponse(expires_in=int(oauth_service.PASSWORDLESS_TOKEN_TTL.total_seconds()))


@router.post("/passwordless/verify", response_model=Token)
def verify_passwordless_login(request: Request, payload: PasswordlessVerifyRequest):
    client_ip = _client_ip(request) or "unknown"
    rate_limit.enforce(f"passwordless-verify:ip:{client_ip}", max_attempts=20, window_seconds=300)

    user_id = oauth_service.verify_passwordless_login(payload.token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or expired login link')
    user = User.get_user(user_id)
    access_token = _issue_and_record(request, user)
    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(payload: ApiKeyCreateRequest, user: user_dependency):
    raw_key = oauth_service.issue_api_key(user_id=user['id'], name=payload.name)
    return ApiKeyCreateResponse(api_key=raw_key, name=payload.name)


@router.get("/api-keys", response_model=list[ApiKeyInfo])
def list_api_keys(user: user_dependency):
    return oauth_service.list_api_keys(user['id'])


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(key_id: str, user: user_dependency):
    if not oauth_service.revoke_api_key(user_id=user['id'], key_id=key_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='API key not found')


@router.post("/webhooks", response_model=WebhookCreateResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(payload: WebhookCreateRequest, user: user_dependency):
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an admin can register a webhook')
    _dev_hosts = ("http://localhost", "http://127.0.0.1", "http://host.docker.internal")
    if not (payload.url.startswith("https://") or payload.url.startswith(_dev_hosts)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='webhook url must be https (or localhost/host.docker.internal for dev)')
    if payload.url.startswith("https://") and not is_public_hostname(urlparse(payload.url).hostname):
        # An admin account is more trusted than an arbitrary CIMD client_id,
        # but a compromised/phished admin token shouldn't turn into a free
        # pivot into internal infrastructure via a webhook URL that resolves
        # there - see ssrf_guard.py.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='webhook url must resolve to a public address')
    secret = secrets.token_urlsafe(32)
    with SessionLocal() as db:
        row = WebhookEndpoint(
            url=payload.url, secret=secret, events=json.dumps(payload.events),
            created_by_user_id=user['id'],
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return WebhookCreateResponse(id=row.id, url=row.url, secret=secret, events=payload.events)


@router.get("/webhooks", response_model=list[WebhookInfo])
def list_webhooks(user: user_dependency):
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an admin can view webhooks')
    with SessionLocal() as db:
        rows = db.query(WebhookEndpoint).all()
        return [
            WebhookInfo(id=r.id, url=r.url, events=json.loads(r.events), active=r.active, created_at=r.created_at)
            for r in rows
        ]


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(webhook_id: int, user: user_dependency):
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an admin can remove a webhook')
    with SessionLocal() as db:
        row = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == webhook_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Webhook not found')
        db.delete(row)
        db.commit()


@router.get("/sessions", response_model=list[SessionInfo])
def list_sessions(user: user_dependency):
    return oauth_service.list_sessions(user['id'])


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(session_id: str, user: user_dependency):
    if not oauth_service.revoke_session(user_id=user['id'], session_id=session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found')


@router.get("/admin/{target_user_id}/sessions", response_model=list[SessionInfo])
def list_user_sessions(target_user_id: int, user: user_dependency):
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an admin can view another user\'s sessions')
    return oauth_service.list_sessions(target_user_id)


@router.delete("/admin/{target_user_id}/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_user_session(target_user_id: int, session_id: str, user: user_dependency):
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an admin can revoke another user\'s session')
    if not oauth_service.revoke_session(user_id=target_user_id, session_id=session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found')


@router.get("/me")
def get_my_permissions(user: user_dependency):
    db_user = User.get_user(user['id'])
    return {
        'username': user['username'],
        'id': user['id'],
        'is_admin': authz.is_admin(user['id']),
        'email': db_user.email if db_user else None,
        # Gravatar (email-derived) is tried first; fallback_avatar_url
        # (Google's photo, if this account ever signed in with Google) is
        # only used client-side if Gravatar 404s - see Avatar.tsx.
        'avatar_url': gravatar_url_strict(db_user.email) if db_user and db_user.email else None,
        'fallback_avatar_url': db_user.picture_url if db_user else None,
    }


@router.post("/admin/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def grant_admin(target_user_id: int, user: user_dependency):
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an existing admin can grant admin')
    authz.grant_admin(target_user_id)


@router.delete("/admin/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_admin(target_user_id: int, user: user_dependency):
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an existing admin can revoke admin')
    authz.revoke_admin(target_user_id)


@router.post("/admin/rotate-signing-key", status_code=status.HTTP_200_OK)
def rotate_signing_key(user: user_dependency):
    """Rotates the RSA key this server signs access tokens with - e.g.
    after a suspected key compromise. The retired key stays published in
    the JWKS (see oauth/keys.py), so access tokens already issued keep
    verifying until they expire naturally; nothing is revoked early."""
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an admin can rotate the signing key')
    new_kid = oauth_keys.rotate()
    logger.warning("signing key rotated by user_id=%s new_kid=%s", user['id'], new_kid)
    return {"kid": new_kid}


@router.get("/trusted-issuers", response_model=list[TrustedIssuerInfo])
def list_trusted_issuers(user: user_dependency):
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an admin can view trusted issuers')
    with SessionLocal() as db:
        rows = db.query(TrustedIssuer).all()
        return [
            TrustedIssuerInfo(
                issuer=r.issuer, jwks_url=r.jwks_url, subject_claim=r.subject_claim,
                allowed_client_ids=json.loads(r.allowed_client_ids) if r.allowed_client_ids else None,
                created_at=r.created_at,
            )
            for r in rows
        ]


@router.post("/trusted-issuers", response_model=TrustedIssuerInfo, status_code=status.HTTP_201_CREATED)
def add_trusted_issuer(payload: TrustedIssuerCreateRequest, user: user_dependency):
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an admin can add a trusted issuer')
    with SessionLocal() as db:
        if db.query(TrustedIssuer).filter(TrustedIssuer.issuer == payload.issuer).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='That issuer is already trusted')
        row = TrustedIssuer(
            issuer=payload.issuer, jwks_url=payload.jwks_url, subject_claim=payload.subject_claim,
            allowed_client_ids=json.dumps(payload.allowed_client_ids) if payload.allowed_client_ids else None,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return TrustedIssuerInfo(
            issuer=row.issuer, jwks_url=row.jwks_url, subject_claim=row.subject_claim,
            allowed_client_ids=payload.allowed_client_ids, created_at=row.created_at,
        )


@router.delete("/trusted-issuers/{issuer:path}", status_code=status.HTTP_204_NO_CONTENT)
def remove_trusted_issuer(issuer: str, user: user_dependency):
    if not authz.is_admin(user['id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only an admin can remove a trusted issuer')
    with SessionLocal() as db:
        row = db.query(TrustedIssuer).filter(TrustedIssuer.issuer == issuer).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Trusted issuer not found')
        db.delete(row)
        db.commit()



