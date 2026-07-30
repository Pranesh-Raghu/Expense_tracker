import os

from fastapi import APIRouter, Depends, status, HTTPException
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from typing import Annotated
from passlib.context import CryptContext  # pyright: ignore[reportMissingModuleSource]
from models.user_model import User
from schemas.user_schemas import Token
from oauth import service as oauth_service
from oauth.schemas import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyInfo, TrustedIssuerCreateRequest, TrustedIssuerInfo, SessionInfo
from authz import service as authz
import json
from database import SessionLocal
from oauth.models import TrustedIssuer

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')

    token = create_access_token(user.username, user.id, timedelta(minutes=100))

    return  {'access_token':token, 'token_type':'bearer'}


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


@router.get("/sessions", response_model=list[SessionInfo])
def list_sessions(user: user_dependency):
    return oauth_service.list_sessions(user['id'])


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(session_id: str, user: user_dependency):
    if not oauth_service.revoke_session(user_id=user['id'], session_id=session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found')


@router.get("/me")
def get_my_permissions(user: user_dependency):
    return {'username': user['username'], 'id': user['id'], 'is_admin': authz.is_admin(user['id'])}


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



