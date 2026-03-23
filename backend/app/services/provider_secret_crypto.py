from __future__ import annotations

import base64
import hashlib
import hmac
import os

from app.core.config import settings

_VERSION_PREFIX = "v1:"


def _encryption_key() -> bytes:
    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()


def _build_keystream(key: bytes, nonce: bytes, size: int) -> bytes:
    chunks: list[bytes] = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < size:
        counter_bytes = counter.to_bytes(4, "big")
        chunks.append(hashlib.sha256(key + nonce + counter_bytes).digest())
        counter += 1
    return b"".join(chunks)[:size]


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


def encrypt_secret(secret: str) -> str:
    plaintext = secret.encode("utf-8")
    key = _encryption_key()
    nonce = os.urandom(16)
    ciphertext = _xor_bytes(plaintext, _build_keystream(key, nonce, len(plaintext)))
    mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    payload = base64.urlsafe_b64encode(nonce + ciphertext + mac).decode("ascii")
    return f"{_VERSION_PREFIX}{payload}"


def decrypt_secret(token: str) -> str:
    if not token.startswith(_VERSION_PREFIX):
        raise ValueError("Unsupported secret payload version")
    payload = base64.urlsafe_b64decode(token[len(_VERSION_PREFIX) :].encode("ascii"))
    if len(payload) < 48:
        raise ValueError("Malformed secret payload")
    nonce = payload[:16]
    mac = payload[-32:]
    ciphertext = payload[16:-32]
    key = _encryption_key()
    expected_mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("Secret payload signature mismatch")
    plaintext = _xor_bytes(ciphertext, _build_keystream(key, nonce, len(ciphertext)))
    return plaintext.decode("utf-8")


def mask_secret(secret: str) -> str:
    if len(secret) <= 4:
        return "*" * len(secret)
    if len(secret) <= 8:
        return f"{secret[:2]}...{secret[-2:]}"
    return f"{secret[:4]}...{secret[-4:]}"
