import base64
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

KEY_DIR = os.environ.get("OAUTH_KEY_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys"))
PRIVATE_KEY_PATH = os.path.join(KEY_DIR, "oauth_signing_key.pem")
KEY_ID = "expense-tracker-oauth-key-1"


def _generate_and_persist_key() -> rsa.RSAPrivateKey:
    os.makedirs(KEY_DIR, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    fd = os.open(PRIVATE_KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(pem)
    return private_key


def load_or_create_private_key() -> rsa.RSAPrivateKey:
    if os.path.exists(PRIVATE_KEY_PATH):
        with open(PRIVATE_KEY_PATH, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    try:
        return _generate_and_persist_key()
    except FileExistsError:
        with open(PRIVATE_KEY_PATH, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)


_private_key = load_or_create_private_key()
_public_key = _private_key.public_key()


def get_signing_key_pem() -> bytes:
    return _private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_public_key_pem() -> bytes:
    return _public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _int_to_base64url(value: int) -> str:
    byte_length = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).rstrip(b"=").decode("ascii")


def get_jwks() -> dict:
    public_numbers = _public_key.public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": KEY_ID,
                "n": _int_to_base64url(public_numbers.n),
                "e": _int_to_base64url(public_numbers.e),
            }
        ]
    }
