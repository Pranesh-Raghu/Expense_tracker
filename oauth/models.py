from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from database import Base


def utcnow() -> datetime:
    # Naive on purpose: MySQL's DATETIME type has no timezone concept, so a
    # tz-aware value written here comes back naive on read - comparing that
    # against a tz-aware "now" then raises TypeError. Keeping everything
    # naive-but-UTC avoids the mismatch.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OAuthClient(Base):
    """A client registered via Dynamic Client Registration (RFC 7591).

    Clients using Client ID Metadata Documents (CIMD) never get a row here -
    their identity lives at the client_id URL itself and is fetched live.
    """

    __tablename__ = "oauth_clients"

    client_id = Column(String(255), primary_key=True)
    client_secret_hash = Column(String(255), nullable=True)
    client_name = Column(String(255), nullable=True)
    redirect_uris = Column(Text, nullable=False)  # JSON-encoded list[str]
    grant_types = Column(Text, nullable=False)  # JSON-encoded list[str]
    response_types = Column(Text, nullable=False)  # JSON-encoded list[str]
    token_endpoint_auth_method = Column(String(64), nullable=False, default="none")
    scope = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class AuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"

    code = Column(String(255), primary_key=True)
    client_id = Column(String(1024), nullable=False)
    user_id = Column(Integer, nullable=False)
    redirect_uri = Column(String(1024), nullable=False)
    scope = Column(String(512), nullable=True)
    resource = Column(String(1024), nullable=True)
    code_challenge = Column(String(255), nullable=False)
    code_challenge_method = Column(String(16), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)


class RefreshToken(Base):
    __tablename__ = "oauth_refresh_tokens"

    token_hash = Column(String(255), primary_key=True)
    client_id = Column(String(1024), nullable=False)
    user_id = Column(Integer, nullable=False)
    scope = Column(String(512), nullable=True)
    resource = Column(String(1024), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)


class RevokedAccessToken(Base):
    """JTIs of access tokens revoked before their natural expiry."""

    __tablename__ = "oauth_revoked_access_tokens"

    jti = Column(String(255), primary_key=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class ApiKey(Base):
    """Long-lived static credentials, as an alternative to the OAuth flow.

    Meant for scripts/automation where an interactive authorize redirect
    isn't practical. Only the hash is stored - the raw key is shown once,
    at creation time, and never again.
    """

    __tablename__ = "api_keys"

    key_hash = Column(String(255), primary_key=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked = Column(Boolean, default=False)
