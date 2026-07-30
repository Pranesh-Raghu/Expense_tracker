import base64
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class SigningKeySet:
    """An RSA keypair, persisted to disk, exposed as a JWKS. Each instance is
    a fully independent identity (its own file, its own kid) - used both for
    this app's own OAuth AS and, separately, for the mock external IdP in
    mock_idp.py, so the two are genuinely distinct signers, not the same key
    wearing a different label."""

    def __init__(self, key_dir: str, filename: str, kid: str):
        self.key_dir = key_dir
        self.private_key_path = os.path.join(key_dir, filename)
        self.kid = kid
        self._private_key = self._load_or_create_private_key()
        self._public_key = self._private_key.public_key()

    def _generate_and_persist_key(self) -> rsa.RSAPrivateKey:
        os.makedirs(self.key_dir, exist_ok=True)
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        fd = os.open(self.private_key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(pem)
        return private_key

    def _load_or_create_private_key(self) -> rsa.RSAPrivateKey:
        if os.path.exists(self.private_key_path):
            with open(self.private_key_path, "rb") as f:
                return serialization.load_pem_private_key(f.read(), password=None)
        try:
            return self._generate_and_persist_key()
        except FileExistsError:
            with open(self.private_key_path, "rb") as f:
                return serialization.load_pem_private_key(f.read(), password=None)

    def get_signing_key_pem(self) -> bytes:
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def get_public_key_pem(self) -> bytes:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    @staticmethod
    def _int_to_base64url(value: int) -> str:
        byte_length = (value.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).rstrip(b"=").decode("ascii")

    def get_jwks(self) -> dict:
        public_numbers = self._public_key.public_numbers()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self.kid,
                    "n": self._int_to_base64url(public_numbers.n),
                    "e": self._int_to_base64url(public_numbers.e),
                }
            ]
        }


KEY_DIR = os.environ.get("OAUTH_KEY_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys"))
KEY_ID = "expense-tracker-oauth-key-1"

_signing_keys = SigningKeySet(KEY_DIR, "oauth_signing_key.pem", KEY_ID)

get_signing_key_pem = _signing_keys.get_signing_key_pem
get_public_key_pem = _signing_keys.get_public_key_pem
get_jwks = _signing_keys.get_jwks
