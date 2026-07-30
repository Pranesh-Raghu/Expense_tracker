import hashlib
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt

from geoip import city_for_ip
from passlib.context import CryptContext

from database import SessionLocal
from oauth import cimd, keys
from oauth.models import ApiKey, AuthorizationCode, OAuthClient, PasswordlessToken, RefreshToken, RevokedAccessToken
from oauth.pkce import verify_pkce

logger = logging.getLogger("expense_tracker.oauth")

API_KEY_PREFIX = "eak_"

ISSUER = os.environ.get("OAUTH_ISSUER") or "http://localhost:8000"
MCP_RESOURCE_URL = os.environ.get("MCP_RESOURCE_URL") or f"{ISSUER}/mcp"
ALLOW_INSECURE_HTTP_CIMD = os.environ.get("CIMD_ALLOW_INSECURE_HTTP", "false").lower() == "true"

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
AUTH_CODE_TTL = timedelta(minutes=5)

ALGORITHM = "RS256"

secret_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    # Naive on purpose - see the comment on oauth.models.utcnow().
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Client resolution: DCR-registered clients (DB) or CIMD clients (client_id URL)
# ---------------------------------------------------------------------------

class ResolvedClient:
    def __init__(self, client_id: str, redirect_uris: list[str], token_endpoint_auth_method: str,
                 grant_types: list[str], response_types: list[str], client_secret_hash: Optional[str],
                 is_cimd: bool):
        self.client_id = client_id
        self.redirect_uris = redirect_uris
        self.token_endpoint_auth_method = token_endpoint_auth_method
        self.grant_types = grant_types
        self.response_types = response_types
        self.client_secret_hash = client_secret_hash
        self.is_cimd = is_cimd


async def resolve_client(client_id: str) -> ResolvedClient:
    if cimd.is_cimd_client_id(client_id):
        try:
            metadata = await cimd.resolve_cimd_client(client_id, allow_insecure_http=ALLOW_INSECURE_HTTP_CIMD)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid_client: could not resolve client metadata document ({exc})",
            )
        return ResolvedClient(
            client_id=client_id,
            redirect_uris=metadata["redirect_uris"],
            token_endpoint_auth_method=metadata.get("token_endpoint_auth_method", "none"),
            grant_types=metadata.get("grant_types", ["authorization_code"]),
            response_types=metadata.get("response_types", ["code"]),
            client_secret_hash=None,
            is_cimd=True,
        )

    with SessionLocal() as db:
        client = db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()
        if not client:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_client: unknown client_id")
        return ResolvedClient(
            client_id=client.client_id,
            redirect_uris=json.loads(client.redirect_uris),
            token_endpoint_auth_method=client.token_endpoint_auth_method,
            grant_types=json.loads(client.grant_types),
            response_types=json.loads(client.response_types),
            client_secret_hash=client.client_secret_hash,
            is_cimd=False,
        )


def register_client(payload) -> dict:
    client_id = secrets.token_urlsafe(24)
    client_secret = None
    client_secret_hash = None

    if payload.token_endpoint_auth_method == "client_secret_basic":
        client_secret = secrets.token_urlsafe(32)
        client_secret_hash = secret_context.hash(client_secret)

    with SessionLocal() as db:
        db_client = OAuthClient(
            client_id=client_id,
            client_secret_hash=client_secret_hash,
            client_name=payload.client_name,
            redirect_uris=json.dumps(payload.redirect_uris),
            grant_types=json.dumps(payload.grant_types),
            response_types=json.dumps(payload.response_types),
            token_endpoint_auth_method=payload.token_endpoint_auth_method,
            scope=payload.scope,
        )
        db.add(db_client)
        db.commit()

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_id_issued_at": int(time.time()),
        "client_secret_expires_at": 0,
        "redirect_uris": payload.redirect_uris,
        "token_endpoint_auth_method": payload.token_endpoint_auth_method,
        "grant_types": payload.grant_types,
        "response_types": payload.response_types,
        "client_name": payload.client_name,
        "scope": payload.scope,
    }


def verify_client_secret(client: ResolvedClient, client_secret: Optional[str]) -> None:
    if client.token_endpoint_auth_method == "none":
        return
    if not client_secret or not client.client_secret_hash or not secret_context.verify(client_secret, client.client_secret_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_client: bad client_secret")


def validate_redirect_uri(client: ResolvedClient, redirect_uri: str) -> None:
    if redirect_uri not in client.redirect_uris:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_request: redirect_uri not registered for this client")


# ---------------------------------------------------------------------------
# Authorization code
# ---------------------------------------------------------------------------

def create_authorization_code(*, client_id: str, user_id: int, redirect_uri: str, scope: Optional[str],
                               resource: Optional[str], code_challenge: str, code_challenge_method: str) -> str:
    code = secrets.token_urlsafe(48)
    with SessionLocal() as db:
        db.add(AuthorizationCode(
            code=code,
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            resource=resource,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=_now() + AUTH_CODE_TTL,
            used=False,
        ))
        db.commit()
    return code


def consume_authorization_code(*, code: str, client_id: str, redirect_uri: str, code_verifier: str) -> dict:
    with SessionLocal() as db:
        record = db.query(AuthorizationCode).filter(AuthorizationCode.code == code).first()
        if not record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: unknown code")
        if record.used:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: code already used")
        if record.expires_at < _now():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: code expired")
        if record.client_id != client_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: client_id mismatch")
        if record.redirect_uri != redirect_uri:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: redirect_uri mismatch")
        if not verify_pkce(code_verifier, record.code_challenge, record.code_challenge_method):
            logger.warning("PKCE verification failed for client_id=%s", client_id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: PKCE verification failed")

        # Mark used immediately: authorization codes are single-use. Replay
        # of a used code is a strong signal of a stolen code and must fail.
        record.used = True
        db.commit()

        return {
            "user_id": record.user_id,
            "scope": record.scope,
            "resource": record.resource,
        }


# ---------------------------------------------------------------------------
# Access / refresh tokens
# ---------------------------------------------------------------------------

def issue_access_token(*, user_id: int, client_id: str, scope: Optional[str], resource: Optional[str]) -> str:
    from models.user_model import User  # imported lazily to avoid a module-load cycle

    now = _now()
    user = User.get_user(user_id)
    claims = {
        "iss": ISSUER,
        "sub": str(user_id),
        "username": user.username if user else "",
        "aud": resource or MCP_RESOURCE_URL,
        "client_id": client_id,
        "scope": scope or "",
        "iat": int(now.timestamp()),
        "exp": int((now + ACCESS_TOKEN_TTL).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(claims, keys.get_signing_key_pem(), algorithm=ALGORITHM, headers={"kid": keys.KEY_ID})


def issue_refresh_token(*, user_id: int, client_id: str, scope: Optional[str], resource: Optional[str],
                         user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> str:
    token = secrets.token_urlsafe(48)
    now = _now()
    with SessionLocal() as db:
        db.add(RefreshToken(
            token_hash=_hash_token(token),
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            resource=resource,
            expires_at=now + REFRESH_TOKEN_TTL,
            revoked=False,
            user_agent=user_agent,
            ip_address=ip_address,
            created_at=now,
            last_used_at=now,
        ))
        db.commit()
    return token


def issue_token_pair(*, user_id: int, client_id: str, scope: Optional[str], resource: Optional[str],
                      user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> dict:
    access_token = issue_access_token(user_id=user_id, client_id=client_id, scope=scope, resource=resource)
    refresh_token = issue_refresh_token(
        user_id=user_id, client_id=client_id, scope=scope, resource=resource,
        user_agent=user_agent, ip_address=ip_address,
    )
    logger.info("issued token pair: user_id=%s client_id=%s scope=%s ip=%s", user_id, client_id, scope, ip_address)
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
        "refresh_token": refresh_token,
        "scope": scope,
    }


def refresh_token_grant(*, refresh_token: str, client_id: str,
                         user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> dict:
    token_hash = _hash_token(refresh_token)
    with SessionLocal() as db:
        record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if not record or record.revoked:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: unknown or revoked refresh token")
        if record.expires_at < _now():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: refresh token expired")
        if record.client_id != client_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant: client_id mismatch")

        # Rotate: revoke the old refresh token so a captured, already-used
        # token can't be replayed after the legitimate client has rotated.
        record.revoked = True
        user_id, scope, resource = record.user_id, record.scope, record.resource
        db.commit()

    return issue_token_pair(
        user_id=user_id, client_id=client_id, scope=scope, resource=resource,
        user_agent=user_agent, ip_address=ip_address,
    )


# ---------------------------------------------------------------------------
# Sessions: one row per issued refresh token, with device/IP metadata
# ---------------------------------------------------------------------------

def list_sessions(user_id: int) -> list[dict]:
    with SessionLocal() as db:
        records = (
            db.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .order_by(RefreshToken.last_used_at.desc())
            .all()
        )
        return [
            {
                "session_id": r.token_hash[:12],
                "client_id": r.client_id,
                "user_agent": r.user_agent,
                "ip_address": r.ip_address,
                "city": city_for_ip(r.ip_address),
                "created_at": r.created_at,
                "last_used_at": r.last_used_at,
            }
            for r in records
        ]


def revoke_session(*, user_id: int, session_id: str) -> bool:
    with SessionLocal() as db:
        record = (
            db.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.token_hash.startswith(session_id))
            .first()
        )
        if not record:
            return False
        record.revoked = True
        db.commit()
        return True


def revoke_refresh_token(refresh_token: str) -> None:
    token_hash = _hash_token(refresh_token)
    with SessionLocal() as db:
        record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if record:
            record.revoked = True
            db.commit()
            logger.info("revoked refresh token: user_id=%s client_id=%s", record.user_id, record.client_id)


def revoke_access_token(access_token: str) -> None:
    try:
        claims = jwt.decode(access_token, keys.get_public_key_pem(), algorithms=[ALGORITHM], options={"verify_aud": False})
    except JWTError:
        return
    with SessionLocal() as db:
        db.add(RevokedAccessToken(
            jti=claims["jti"],
            expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc).replace(tzinfo=None),
        ))
        db.commit()
    logger.info("revoked access token: sub=%s client_id=%s jti=%s", claims.get("sub"), claims.get("client_id"), claims.get("jti"))


def decode_access_token(access_token: str, *, expected_resource: Optional[str] = None) -> dict:
    try:
        claims = jwt.decode(
            access_token,
            keys.get_public_key_pem(),
            algorithms=[ALGORITHM],
            audience=expected_resource or MCP_RESOURCE_URL,
            issuer=ISSUER,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"invalid_token: {exc}")

    with SessionLocal() as db:
        if db.query(RevokedAccessToken).filter(RevokedAccessToken.jti == claims["jti"]).first():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token: revoked")

    return claims


# ---------------------------------------------------------------------------
# API keys: static, long-lived credentials as an alternative to the OAuth flow
# ---------------------------------------------------------------------------

def issue_api_key(*, user_id: int, name: Optional[str]) -> str:
    raw_key = API_KEY_PREFIX + secrets.token_urlsafe(32)
    with SessionLocal() as db:
        db.add(ApiKey(key_hash=_hash_token(raw_key), user_id=user_id, name=name))
        db.commit()
    return raw_key


def verify_api_key(raw_key: str) -> Optional[dict]:
    if not raw_key.startswith(API_KEY_PREFIX):
        return None
    with SessionLocal() as db:
        record = db.query(ApiKey).filter(ApiKey.key_hash == _hash_token(raw_key)).first()
        if not record or record.revoked:
            return None
        record.last_used_at = _now()
        db.commit()
        return {"user_id": record.user_id, "name": record.name}


def list_api_keys(user_id: int) -> list[dict]:
    with SessionLocal() as db:
        records = db.query(ApiKey).filter(ApiKey.user_id == user_id, ApiKey.revoked.is_(False)).all()
        return [
            {"key_id": r.key_hash[:12], "name": r.name, "created_at": r.created_at, "last_used_at": r.last_used_at}
            for r in records
        ]


def revoke_api_key(*, user_id: int, key_id: str) -> bool:
    with SessionLocal() as db:
        record = (
            db.query(ApiKey)
            .filter(ApiKey.user_id == user_id, ApiKey.key_hash.startswith(key_id))
            .first()
        )
        if not record:
            return False
        record.revoked = True
        db.commit()
        return True


# ---------------------------------------------------------------------------
# Passwordless (magic-link) login
# ---------------------------------------------------------------------------

PASSWORDLESS_TOKEN_TTL = timedelta(minutes=10)


def request_passwordless_login(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with SessionLocal() as db:
        db.add(PasswordlessToken(
            token_hash=_hash_token(token), user_id=user_id,
            expires_at=_now() + PASSWORDLESS_TOKEN_TTL, used=False,
        ))
        db.commit()
    return token


def verify_passwordless_login(token: str) -> Optional[int]:
    with SessionLocal() as db:
        record = db.query(PasswordlessToken).filter(PasswordlessToken.token_hash == _hash_token(token)).first()
        if not record or record.used or record.expires_at < _now():
            return None
        # Single-use, same reasoning as authorization codes: mark used
        # immediately so a captured link can't be replayed.
        record.used = True
        db.commit()
        return record.user_id


def introspect(token: str) -> dict:
    try:
        claims = decode_access_token(token)
    except HTTPException:
        return {"active": False}
    return {
        "active": True,
        "scope": claims.get("scope"),
        "client_id": claims.get("client_id"),
        "sub": claims.get("sub"),
        "aud": claims.get("aud"),
        "exp": claims.get("exp"),
    }
