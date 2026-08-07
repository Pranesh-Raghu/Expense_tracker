import base64
import hashlib
import hmac
import re

# RFC 7636 §4.1: 43-128 characters, unreserved URL charset only.
_CODE_VERIFIER_RE = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")


def verify_pkce(code_verifier: str, code_challenge: str, code_challenge_method: str) -> bool:
    """Verify a PKCE code_verifier against the stored code_challenge.

    OAuth 2.1 requires PKCE on every authorization code grant. Only S256 is
    accepted: the "plain" method offers no protection against an attacker who
    can observe the authorization request (e.g. via a malicious app on the
    same device intercepting the redirect), which is exactly the threat PKCE
    exists to stop.
    """
    if code_challenge_method != "S256":
        return False
    # Checks the full RFC-mandated charset, not just length - a verifier
    # with any non-ASCII character would otherwise reach .encode("ascii")
    # below and raise UnicodeEncodeError, which - uncaught here and
    # uncaught by oauth/service.py's caller - used to surface as an
    # unhandled 500 on /oauth/token instead of a clean invalid_grant.
    if not _CODE_VERIFIER_RE.match(code_verifier or ""):
        return False

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(computed_challenge, code_challenge)
