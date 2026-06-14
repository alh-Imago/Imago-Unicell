"""
aes256.py — AES-256-GCM Encryption Layer
─────────────────────────────────────────
Key derivation : PBKDF2-HMAC-SHA256, 600,000 iterations (OWASP 2023 minimum)
Salt           : 32 random bytes, stored in the layer payload
Nonce (IV)     : 12 random bytes, stored in the layer payload
Tag            : 16 bytes GCM authentication tag, stored after ciphertext

Payload layout:
  [32 bytes] salt
  [12 bytes] nonce
  [16 bytes] GCM tag
  [N bytes]  ciphertext

The password is never stored anywhere. Wrong password → GCM tag
verification will raise an exception on decompress.
"""

import os
import struct

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag

SALT_LEN       = 32
NONCE_LEN      = 12
TAG_LEN        = 16          # GCM tag is appended by cryptography lib
KDF_ITERATIONS = 600_000


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from a password + salt using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm  = hashes.SHA256(),
        length     = 32,
        salt       = salt,
        iterations = KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def compress(data: bytes, password: str = "") -> bytes:
    """Encrypt *data* with AES-256-GCM. Password must be non-empty."""
    if not password:
        raise ValueError("AES-256-GCM: password required for encryption")

    salt  = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key   = _derive_key(password, salt)

    aesgcm     = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)   # includes 16-byte GCM tag

    return salt + nonce + ciphertext


def decompress(data: bytes, password: str = "") -> bytes:
    """Decrypt *data*. Raises ValueError on wrong password or corrupted data."""
    if not password:
        raise ValueError("AES-256-GCM: password required for decryption")

    if len(data) < SALT_LEN + NONCE_LEN + TAG_LEN:
        raise ValueError("AES-256-GCM: payload too short — corrupted archive?")

    salt       = data[:SALT_LEN]
    nonce      = data[SALT_LEN:SALT_LEN + NONCE_LEN]
    ciphertext = data[SALT_LEN + NONCE_LEN:]         # includes tag at end

    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)

    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag:
        raise ValueError("AES-256-GCM: decryption failed — wrong password or corrupted data")
