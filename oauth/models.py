from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from database import Base


def utcnow() -> datetime:
    # Naive on purpose: MySQL's DATETIME type has no timezone concept, so a
    # tz-aware value written here comes back naive on read - comparing that
    # against a tz-aware "now" then raises TypeError. Keeping everything
    # naive-but-UTC avoids the mismatch.
    #
    # Every DateTime column below is declared plain - DateTime(), not
    # DateTime(timezone=True) - for the same reason: on Postgres (this app's
    # production DB; MySQL is local dev), timezone=True creates a real
    # TIMESTAMPTZ column, which interprets an inserted naive value as being
    # in the CONNECTION's current timezone before converting it to UTC for
    # storage. Since every value this app writes is already naive-but-UTC,
    # that interpretation is only correct by accident (if the connection's
    # timezone happens to be UTC) - a plain DateTime()/TIMESTAMP column does
    # no interpretation at all, storing exactly the value given, matching
    # MySQL's actual behavior on both databases instead of just one.
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
    created_at = Column(DateTime(), default=utcnow)


class AuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"

    # Despite the name, this holds a SHA-256 hash of the code, not the raw
    # value - see oauth/service.py's create_authorization_code /
    # consume_authorization_code, both of which hash it before writing/
    # querying. Kept the column name as-is (rather than code_hash, matching
    # token_hash/key_hash elsewhere) to avoid a schema migration for what's
    # a defense-in-depth improvement, not a fix for an actively exploitable
    # gap - PKCE's code_verifier (never persisted) is still required to
    # complete an exchange even with this value in hand.
    code = Column(String(255), primary_key=True)
    client_id = Column(String(1024), nullable=False)
    user_id = Column(Integer, nullable=False)
    redirect_uri = Column(String(1024), nullable=False)
    scope = Column(String(512), nullable=True)
    resource = Column(String(1024), nullable=True)
    code_challenge = Column(String(255), nullable=False)
    code_challenge_method = Column(String(16), nullable=False)
    expires_at = Column(DateTime(), nullable=False)
    used = Column(Boolean, default=False)


class RefreshToken(Base):
    __tablename__ = "oauth_refresh_tokens"

    token_hash = Column(String(255), primary_key=True)
    client_id = Column(String(1024), nullable=False)
    user_id = Column(Integer, nullable=False)
    scope = Column(String(512), nullable=True)
    resource = Column(String(1024), nullable=True)
    expires_at = Column(DateTime(), nullable=False)
    revoked = Column(Boolean, default=False)

    # Shared by every refresh token in one rotation lineage: the token
    # issued at login, and every token it rotates into afterward. Lets
    # refresh_token_grant() revoke a whole stolen lineage in one go when it
    # detects reuse, instead of only rejecting the single replayed request.
    # Nullable so rows written before this column existed keep working -
    # they just fall back to single-token revocation on reuse, not
    # family-wide (see refresh_token_grant).
    family_id = Column(String(64), nullable=True, index=True)

    # Session/device metadata, captured at issuance time from the request
    # that hit /oauth/token or /auth/token - lets a user see (and kill) each
    # of their logged-in devices individually, same idea as "active
    # sessions" in most real apps.
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(), default=utcnow)
    last_used_at = Column(DateTime(), default=utcnow)


class RevokedAccessToken(Base):
    """JTIs of access tokens revoked before their natural expiry."""

    __tablename__ = "oauth_revoked_access_tokens"

    jti = Column(String(255), primary_key=True)
    expires_at = Column(DateTime(), nullable=False)


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
    created_at = Column(DateTime(), default=utcnow)
    last_used_at = Column(DateTime(), nullable=True)
    revoked = Column(Boolean, default=False)


class TrustedIssuer(Base):
    """An external identity provider this server trusts for Cross-App Access
    (RFC 7523 JWT-bearer grant): a client already holding a signed identity
    assertion from one of these issuers can exchange it at /oauth/token for
    a native access token here, with no interactive login at this server.

    This is a genuine trust boundary, not a formality - only add an issuer
    here if you actually trust whoever controls its private key to assert
    who your users are.
    """

    __tablename__ = "oauth_trusted_issuers"

    issuer = Column(String(512), primary_key=True)
    jwks_url = Column(String(512), nullable=False)
    # Which claim in the assertion maps to our local username.
    subject_claim = Column(String(64), nullable=False, default="preferred_username")
    # JSON list of client_ids allowed to use this issuer; null/empty = any
    # registered (DCR or CIMD) client may.
    allowed_client_ids = Column(Text, nullable=True)
    created_at = Column(DateTime(), default=utcnow)


class WebhookEndpoint(Base):
    """A URL to notify when subscribed events happen. Payloads are signed
    with HMAC-SHA256 (see webhooks.py) so the receiver can verify a request
    genuinely came from this app and wasn't forged or replayed-with-edits.
    """

    __tablename__ = "webhook_endpoints"

    id = Column(Integer, primary_key=True)
    url = Column(String(1024), nullable=False)
    secret = Column(String(255), nullable=False)
    events = Column(Text, nullable=False)  # JSON list, e.g. ["expense.created", "expense.shared"]
    created_by_user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(), default=utcnow)
    active = Column(Boolean, default=True)


class PasswordlessToken(Base):
    """A one-time magic-link token, emailed to the account's address (see
    email_sender.py) - never returned in the /auth/passwordless/request
    response itself. Returning it there would let anyone who knows a
    username log in as them with zero credentials, which is exactly what
    this endpoint used to do before email_sender.py existed."""

    __tablename__ = "passwordless_tokens"

    token_hash = Column(String(255), primary_key=True)
    user_id = Column(Integer, nullable=False)
    expires_at = Column(DateTime(), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(), default=utcnow)
