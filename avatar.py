import hashlib

GRAVATAR_BASE_URL = "https://www.gravatar.com/avatar/"


def _digest(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()


def gravatar_url(email: str, size: int = 80) -> str:
    """Gravatar URL that always resolves to *something* - `d=identicon`
    generates a pattern as a fallback for emails with no registered
    Gravatar photo, so this never 404s. Used as the final generated-avatar
    fallback; prefer gravatar_url_strict to check for a real photo first."""
    return f"{GRAVATAR_BASE_URL}{_digest(email)}?d=identicon&s={size}"


def gravatar_url_strict(email: str, size: int = 80) -> str:
    """Gravatar URL that 404s if the email has no photo actually
    registered, instead of generating an identicon - lets the frontend
    detect "no real Gravatar" via the image's onError and fall through to
    the next avatar source (see Avatar.tsx) rather than always winning
    with a generated pattern."""
    return f"{GRAVATAR_BASE_URL}{_digest(email)}?d=404&s={size}"
