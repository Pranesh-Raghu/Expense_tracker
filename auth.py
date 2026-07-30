import logging
import os

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from typing import Annotated
from passlib.context import CryptContext  # pyright: ignore[reportMissingModuleSource]
from models.user_model import User
from schemas.user_schemas import Token
from avatar import gravatar_url
from oauth import service as oauth_service
from oauth.schemas import (
    ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyInfo, TrustedIssuerCreateRequest, TrustedIssuerInfo,
    SessionInfo, WebhookCreateRequest, WebhookCreateResponse, WebhookInfo,
    PasswordlessRequestRequest, PasswordlessRequestResponse, PasswordlessVerifyRequest,
)
from authz import service as authz
import google_oauth
import webhooks
import json
import secrets
from database import SessionLocal
from oauth.models import TrustedIssuer, WebhookEndpoint

logger = logging.getLogger("expense_tracker.auth")

router = APIRouter()


SECRET_KEY = os.environ.get('REST_JWT_SECRET_KEY', 'dev-only-insecure-secret-change-me')
ALGORITHM = 'HS256'



bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm = ALGORITHM)



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

        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')

        return {'username': username, 'id': user_id}

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate token')


user_dependency = Annotated[dict, Depends(get_current_user)]

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm,Depends()]):

    user = User.authenticate_user(form_data.username, form_data.password)

    if not user:
        logger.warning("failed login attempt for username=%s", form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')

    logger.info("login: user_id=%s username=%s", user.id, user.username)
    webhooks.dispatch_event("user.login", {"user_id": user.id, "username": user.username})

    token = create_access_token(user.username, user.id, timedelta(minutes=100))

    return  {'access_token':token, 'token_type':'bearer'}


@router.get("/google/login")
def google_login():
    url, _state = google_oauth.build_authorize_url()
    return RedirectResponse(url)


@router.get("/google/callback")
def google_callback(code: str, state: str):
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

    user = User.find_or_create_by_email(email)
    logger.info("google login: user_id=%s username=%s", user.id, user.username)
    webhooks.dispatch_event("user.login", {"user_id": user.id, "username": user.username})

    token = create_access_token(user.username, user.id, timedelta(minutes=100))
    # Not /auth/callback: /auth/* is reserved for the backend rewrite on
    # the frontend's static site (see the frontend router's own comment),
    # so a request there never reaches the SPA at all.
    return RedirectResponse(f"{google_oauth.FRONTEND_URL}/login/callback?token={token}")


@router.post("/passwordless/request", response_model=PasswordlessRequestResponse)
def request_passwordless_login(payload: PasswordlessRequestRequest):
    user = User.get_users()
    matched = next((u for u in user if u.username == payload.username), None)
    # Same response whether the username exists or not - a different
    # response (404 vs 200) would let a caller enumerate valid usernames.
    if matched:
        token = oauth_service.request_passwordless_login(matched.id)
    else:
        token = "invalid"
    return PasswordlessRequestResponse(token=token, expires_in=int(oauth_service.PASSWORDLESS_TOKEN_TTL.total_seconds()))


@router.post("/passwordless/verify", response_model=Token)
def verify_passwordless_login(payload: PasswordlessVerifyRequest):
    user_id = oauth_service.verify_passwordless_login(payload.token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or expired login link')
    user = User.get_user(user_id)
    access_token = create_access_token(user.username, user.id, timedelta(minutes=100))
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
        'avatar_url': gravatar_url(db_user.email) if db_user and db_user.email else None,
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



