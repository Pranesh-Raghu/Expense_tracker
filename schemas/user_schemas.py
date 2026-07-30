from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field
from typing import Optional

from avatar import gravatar_url_strict


# No `username` here on purpose: signup only collects email + password,
# and the username is generated server-side from the email's local part
# (see User.generate_username_from_email in models/user_model.py).
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

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

class DeleteResponse(BaseModel):
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str