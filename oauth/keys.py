import base64
import os
import secrets
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class SigningKeySet:
    """An RSA keypair, persisted to disk, exposed as a JWKS - with rotation
    support: rotate() retires the current key (kept around, still published
    in the JWKS, so tokens already signed with it keep verifying) and starts
    signing new tokens with a freshly generated one. Each instance is a fully
    independent identity (its own file, its own kid) - used both for this
    app's own OAuth AS and, separately, for the mock external IdP in
    mock_idp.py, so the two are genuinely distinct signers, not the same key
    wearing a different label."""

    def __init__(self, key_dir: str, filename: str, kid: str):
        self.key_dir = key_dir
        self.private_key_path = os.path.join(key_dir, filename)
        # Where rotate() moves a retired private key: <filename>_retired/<kid>.pem.
        # Retired keys stay on disk (never deleted here) purely to keep
        # verifying tokens signed before the rotation - see get_jwks() and
        # get_public_key_pem_for_kid().
        self.retired_dir = os.path.join(key_dir, os.path.splitext(filename)[0] + "_retired")
        self.kid = self._load_current_kid(default=kid)
        self._private_key = self._load_or_create_private_key()
        self._public_key = self._private_key.public_key()

    # -- current key -----------------------------------------------------

    def _kid_marker_path(self) -> str:
        # Records which kid the on-disk private key currently corresponds
        # to, so a restart after rotate() picks up the rotated kid instead
        # of falling back to the constructor's original default.
        return self.private_key_path + ".kid"

    def _load_current_kid(self, *, default: str) -> str:
        marker = self._kid_marker_path()
        if os.path.exists(marker):
            with open(marker) as f:
                return f.read().strip() or default
        return default

    def _persist_current_kid(self) -> None:
        with open(self._kid_marker_path(), "w") as f:
            f.write(self.kid)

    @staticmethod
    def _encode_private_key(private_key: rsa.RSAPrivateKey) -> bytes:
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def _generate_and_persist_key(self) -> rsa.RSAPrivateKey:
        os.makedirs(self.key_dir, exist_ok=True)
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        fd = os.open(self.private_key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(self._encode_private_key(private_key))
        self._persist_current_kid()
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
        return self._encode_private_key(self._private_key)

    def get_public_key_pem(self) -> bytes:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    # -- rotation / retired keys ------------------------------------------

    def _retired_key_path(self, kid: str) -> str:
        return os.path.join(self.retired_dir, f"{kid}.pem")

    def _iter_retired(self):
        if not os.path.isdir(self.retired_dir):
            return
        for name in sorted(os.listdir(self.retired_dir)):
            if not name.endswith(".pem"):
                continue
            with open(os.path.join(self.retired_dir, name), "rb") as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None)
            yield name[: -len(".pem")], private_key.public_key()

    def rotate(self, new_kid: Optional[str] = None) -> str:
        """Retire the current key (still published for verification, no
        longer used to sign) and start signing with a brand new one. Safe to
        call at any time, e.g. after a suspected key compromise - existing
        access tokens signed with the retired key keep verifying via
        get_public_key_pem_for_kid()/the JWKS until they naturally expire;
        this doesn't revoke them early. Returns the new kid."""
        new_kid = new_kid or f"{self.kid}-{secrets.token_hex(4)}"
        if new_kid == self.kid:
            raise ValueError("new kid must differ from the current kid")

        os.makedirs(self.retired_dir, exist_ok=True)
        os.replace(self.private_key_path, self._retired_key_path(self.kid))

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        fd = os.open(self.private_key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(self._encode_private_key(private_key))

        self.kid = new_kid
        self._private_key = private_key
        self._public_key = private_key.public_key()
        self._persist_current_kid()
        return new_kid

    def get_public_key_pem_for_kid(self, kid: str) -> Optional[bytes]:
        """Looks up the verification key for a token's kid header, whether
        it's the current signer or one retired by a prior rotate() call."""
        if kid == self.kid:
            return self.get_public_key_pem()
        for retired_kid, public_key in self._iter_retired():
            if retired_kid == kid:
                return public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
        return None

    @staticmethod
    def _int_to_base64url(value: int) -> str:
        byte_length = (value.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).rstrip(b"=").decode("ascii")

    def _jwk_for(self, kid: str, public_key) -> dict:
        public_numbers = public_key.public_numbers()
        return {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": kid,
            "n": self._int_to_base64url(public_numbers.n),
            "e": self._int_to_base64url(public_numbers.e),
        }

    def get_jwks(self) -> dict:
        # Current key first, then every retired-but-not-yet-expired key, so
        # a verifier can validate a token signed by either without needing
        # to know a rotation happened.
        jwks_keys = [self._jwk_for(self.kid, self._public_key)]
        jwks_keys.extend(self._jwk_for(kid, public_key) for kid, public_key in self._iter_retired())
        return {"keys": jwks_keys}


KEY_DIR = os.environ.get("OAUTH_KEY_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys"))
KEY_ID = "expense-tracker-oauth-key-1"

_signing_keys = SigningKeySet(KEY_DIR, "oauth_signing_key.pem", KEY_ID)

get_signing_key_pem = _signing_keys.get_signing_key_pem
get_public_key_pem = _signing_keys.get_public_key_pem
get_public_key_pem_for_kid = _signing_keys.get_public_key_pem_for_kid
get_jwks = _signing_keys.get_jwks
rotate = _signing_keys.rotate


def get_current_kid() -> str:
    return _signing_keys.kid
