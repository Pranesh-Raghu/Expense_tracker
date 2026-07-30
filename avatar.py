import hashlib

GRAVATAR_BASE_URL = "https://www.gravatar.com/avatar/"


def gravatar_url(email: str, size: int = 80) -> str:
    """Gravatar URL for an email address. `d=identicon` gives a generated
    avatar as a fallback for emails with no registered Gravatar, so this
    never 404s."""
    normalized = email.strip().lower().encode("utf-8")
    digest = hashlib.md5(normalized).hexdigest()
    return f"{GRAVATAR_BASE_URL}{digest}?d=identicon&s={size}"
