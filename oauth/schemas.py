from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ClientRegistrationRequest(BaseModel):
    """RFC 7591 dynamic client registration request."""

    redirect_uris: list[str] = Field(..., min_length=1)
    token_endpoint_auth_method: str = "none"  # "none" (public/PKCE) or "client_secret_basic"
    grant_types: list[str] = Field(default_factory=lambda: ["authorization_code", "refresh_token"])
    response_types: list[str] = Field(default_factory=lambda: ["code"])
    client_name: Optional[str] = None
    client_uri: Optional[str] = None
    scope: Optional[str] = None


class ClientRegistrationResponse(BaseModel):
    client_id: str
    client_secret: Optional[str] = None
    client_id_issued_at: int
    client_secret_expires_at: int = 0
    redirect_uris: list[str]
    token_endpoint_auth_method: str
    grant_types: list[str]
    response_types: list[str]
    client_name: Optional[str] = None
    scope: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class ApiKeyCreateRequest(BaseModel):
    name: Optional[str] = None


class ApiKeyCreateResponse(BaseModel):
    api_key: str
    name: Optional[str] = None


class ApiKeyInfo(BaseModel):
    key_id: str
    name: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None


class TrustedIssuerCreateRequest(BaseModel):
    issuer: str
    jwks_url: str
    subject_claim: str = "preferred_username"
    allowed_client_ids: Optional[list[str]] = None


class TrustedIssuerInfo(BaseModel):
    issuer: str
    jwks_url: str
    subject_claim: str
    allowed_client_ids: Optional[list[str]] = None
    created_at: datetime


class PasswordlessRequestRequest(BaseModel):
    username: str


class PasswordlessRequestResponse(BaseModel):
    token: str
    expires_in: int
    note: str = "No email service exists in this demo - this token would normally be emailed as a magic link, not returned here."


class PasswordlessVerifyRequest(BaseModel):
    token: str


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str]  # e.g. ["expense.created", "expense.shared"]


class WebhookCreateResponse(BaseModel):
    id: int
    url: str
    secret: str  # shown once, at creation - store it, it's needed to verify deliveries
    events: list[str]


class WebhookInfo(BaseModel):
    id: int
    url: str
    events: list[str]
    active: bool
    created_at: datetime


class SessionInfo(BaseModel):
    session_id: str
    client_id: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    last_used_at: datetime


class IntrospectionResponse(BaseModel):
    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    username: Optional[str] = None
    exp: Optional[int] = None
    aud: Optional[str] = None
    sub: Optional[str] = None
