import re

from fastapi import HTTPException

MIN_PASSWORD_LENGTH = 8


def validate_user(user):
    if not user:
        raise HTTPException(status_code=404, detail="User not found")


def validate_password_strength(password: str) -> str:
    """Minimum bar for a new/changed password: long enough, and not just
    digits or just letters, to rule out the weakest guessable passwords.
    Without any rate limiting on login (see auth.py), a trivially-guessable
    password is the cheapest way into an account - this doesn't replace
    rate limiting, but it raises the floor.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("password must contain both letters and numbers")
    return password