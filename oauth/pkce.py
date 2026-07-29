import base64
import hashlib
import hmac


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
    if not code_verifier or not (43 <= len(code_verifier) <= 128):
        return False


    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(computed_challenge, code_challenge)
