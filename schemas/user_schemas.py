from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator
from typing import Optional

from avatar import gravatar_url_strict
from validators.user_validators import validate_password_strength


# No `username` here on purpose: signup only collects email + password,
# and the username is generated server-side from the email's local part
# (see User.generate_username_from_email in models/user_model.py).
class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def _check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def _check_password_strength(cls, value: Optional[str]) -> Optional[str]:
        return validate_password_strength(value) if value is not None else value

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    # Populated from the ORM attribute of the same name, but not exposed
    # directly - only via the fallback_avatar_url computed field below.
    picture_url: Optional[str] = Field(default=None, exclude=True)

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def avatar_url(self) -> str:
        # Gravatar (email-derived) is tried first; fallback_avatar_url is
        # only used client-side if this 404s - see frontend Avatar.tsx.
        return gravatar_url_strict(self.email)

    @computed_field
    @property
    def fallback_avatar_url(self) -> Optional[str]:
        return self.picture_url

# The "share with" picker (ShareExpenseDialog.tsx) needs every user's id
# and username, and every authenticated user needs that - it's not an
# admin-only capability. But the full UserResponse also carries email,
# which is PII a stranger has no business seeing just to pick a share
# target. This shape gives non-admin callers of GET /users/ the id/username/
# avatar they need without leaking email; admins still get UserResponse.
class UserPublic(BaseModel):
    id: int
    username: str
    # Only used to compute avatar_url below - never serialized.
    email: EmailStr = Field(exclude=True)
    picture_url: Optional[str] = Field(default=None, exclude=True)

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def avatar_url(self) -> str:
        return gravatar_url_strict(self.email)

    @computed_field
    @property
    def fallback_avatar_url(self) -> Optional[str]:
        return self.picture_url

class DeleteResponse(BaseModel):
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str