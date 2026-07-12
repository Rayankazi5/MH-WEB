import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_key() -> bytes:
    raw = os.getenv("JOURNAL_ENCRYPTION_KEY", "")
    if not raw:
        # Dev fallback: deterministic 32-byte key — NEVER use in production
        return b"dev_key_32bytes_DO_NOT_USE_prod!"
    decoded = base64.b64decode(raw)
    if len(decoded) != 32:
        raise RuntimeError("JOURNAL_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return decoded


def encrypt(plaintext: str) -> str:
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt(ciphertext: str) -> str:
    key = _get_key()
    aesgcm = AESGCM(key)
    data = base64.b64decode(ciphertext)
    nonce, ct = data[:12], data[12:]
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
