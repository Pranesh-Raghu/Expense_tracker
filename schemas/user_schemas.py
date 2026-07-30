from pydantic import BaseModel, ConfigDict, EmailStr, computed_field
from typing import Optional

from avatar import gravatar_url


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

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def avatar_url(self) -> str:
        return gravatar_url(self.email)

class DeleteResponse(BaseModel):
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str