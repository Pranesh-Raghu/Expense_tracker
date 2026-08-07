import re
import secrets
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import Column, Integer, String,Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database import Base, SessionLocal
from passlib.context import CryptContext
from validators.user_validators import validate_password_strength



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Set from Google's OAuth `picture` claim at login (see auth.py's
    # /auth/google/callback) - preferred over the Gravatar fallback when
    # present, since it's the user's actual photo rather than a generated
    # identicon. Null for accounts that have never signed in with Google.
    picture_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    
    
    # Data Access Object (DAO) Methods
    @staticmethod
    def generate_username_from_email(email: str, db) -> str:
        """Derives a unique username from the email's local part (before
        the @) - signup only collects email + password, so this is the
        only source of the username. Strips characters the DB column
        doesn't need to worry about; appends a numeric suffix on
        collision."""
        local_part = email.split('@', 1)[0].lower()
        base = re.sub(r'[^a-z0-9_.-]', '', local_part) or 'user'

        candidate = base
        suffix = 2
        while db.query(User).filter(User.username == candidate).first():
            candidate = f"{base}{suffix}"
            suffix += 1
        return candidate

    @staticmethod
    def create_user(user_credentials):

        with SessionLocal() as db:
           # `id` is an autoincrement primary key - the DB assigns it.
           # Computing it manually as "highest existing id + 1" (the old
           # code here) races under concurrent signups: two requests can
           # read the same max id before either commits, and the second
           # insert then fails with an unhandled 500 instead of a clean
           # signup. Same class of bug already fixed for Expense.create_expense.
           username = User.generate_username_from_email(user_credentials.email, db)
           hashed_password = pwd_context.hash(user_credentials.password)
           db_user = User(username = username,
                          email = user_credentials.email,
                          password = hashed_password,
                          )
           db.add(db_user)
           db.commit()
           db.refresh(db_user)
           return db_user

    @staticmethod
    def find_or_create_by_email(email: str, picture_url: Optional[str] = None):
        """For Google sign-in: matches an existing account by email
        (auto-linking a Google login to a password-based account with the
        same address), or creates a new one if none exists. Google-created
        accounts get a random, never-shown password - they're not meant to
        ever log in with a password, just to satisfy the NOT NULL column.

        `picture_url` (Google's OAuth `picture` claim) is refreshed on
        every login, in case the user's Google photo changed since last
        time."""
        with SessionLocal() as db:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                if picture_url and existing.picture_url != picture_url:
                    existing.picture_url = picture_url
                    db.commit()
                    db.refresh(existing)
                return existing

            # Same reasoning as create_user above: let the DB's autoincrement
            # assign `id` instead of racily computing it here.
            username = User.generate_username_from_email(email, db)
            db_user = User(
                username=username,
                email=email,
                password=pwd_context.hash(secrets.token_urlsafe(32)),
                picture_url=picture_url,
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user

    @staticmethod
    def get_users():
        with SessionLocal() as db:
         return db.query(User).all() or []

    @staticmethod
    def get_user(user_id: int):
        with SessionLocal() as db: 
           return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def update_user(user_credentials,user_id: int):
        with SessionLocal() as db:
         user = db.query(User).filter(User.id == user_id).first()
         if not user:
             return None  
                
         if 'username' in user_credentials:
            user.username = user_credentials['username']
         if 'email' in user_credentials:
            user.email = user_credentials['email']
         if 'password' in user_credentials:
            user.password = pwd_context.hash(user_credentials['password'])
            
         db.commit()
         db.refresh(user)
        
         return user

    # Only these columns are safe for a caller-supplied dict to touch. A raw
    # setattr(user, key, value) loop over an arbitrary dict would let a
    # caller overwrite `password` with a plaintext string (bypassing
    # pwd_context.hash entirely and locking the target out) or set columns
    # like `id` that were never meant to be client-writable.
    PARTIAL_UPDATE_FIELDS = {"username", "email", "password"}

    @staticmethod
    def update_partial_user(user_id: int, user_data):
        with SessionLocal() as db:

         user = db.query(User).filter(User.id == user_id).first()
         if not user:
             return None

         for key, value in user_data.items():
           if key not in User.PARTIAL_UPDATE_FIELDS:
               continue
           if key == "password":
               try:
                   value = validate_password_strength(value)
               except ValueError as exc:
                   raise HTTPException(status_code=422, detail=str(exc)) from exc
               value = pwd_context.hash(value)
           setattr(user, key, value)

         db.commit()
         db.refresh(user)
         return {"message": "User updated successfully", "user": user}
    
    @staticmethod
    def delete_user(user_id: int):
        with SessionLocal() as db:
         user = db.query(User).filter(User.id == user_id).first()
         if not user:
             return None

         db.delete(user)
         db.commit()
         
         return user
    
    
    @staticmethod
    def authenticate_user(identifier: str, password: str):
        """`identifier` may be a username or an email - since signup only
        ever shows the user their email (the username is generated and
        never surfaced), login has to accept either."""
        with SessionLocal() as db:
            user = (
                db.query(User)
                .filter((User.username == identifier) | (User.email == identifier))
                .first()
            )

            if not user:
                return False
            if not pwd_context.verify(password,user.password):
                return False
            return user
    
    
    
    