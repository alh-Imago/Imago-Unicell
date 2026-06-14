"""
meta.py — Archive Metadata Block
──────────────────────────────────
The META block is an optional trailing block appended after the AUDT block.
It carries arbitrary key-value metadata plus optional HMAC-SHA256 signing.

Binary layout:
  [4 bytes]  Magic      b'META'
  [4 bytes]  Length     uint32 BE  (byte length of UTF-8 JSON that follows)
  [N bytes]  UTF-8 JSON flat key-value object

Reserved keys (auto-populated if not supplied):
  author        str   — free text
  created       str   — ISO 8601 UTC timestamp
  description   str   — free text
  tags          list  — list of strings
  version       str   — free text
  source_host   str   — hostname, auto-set from socket.gethostname()
  hmac_sha256   str   — hex HMAC-SHA256 of everything before this block

The HMAC signs: header + payload + audit_block (i.e. the archive up to but
not including the META block itself).  Key is the sign_key string encoded
as UTF-8. If no sign_key is supplied, hmac_sha256 is omitted.

Post-hoc edit: because META is a trailing block the payload never needs
recompression — strip old META, append new META. O(block size) not O(file).
"""

import hashlib
import hmac as _hmac
import json
import socket
import struct
import datetime
from typing import Any, Dict, Optional

MAGIC      = b'META'
MAGIC_SIZE = 4


# ── Pack / Unpack ─────────────────────────────────────────────────────────────

def pack(meta: Dict[str, Any]) -> bytes:
    """Serialise a metadata dict to a META block."""
    json_bytes = json.dumps(meta, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return MAGIC + struct.pack(">I", len(json_bytes)) + json_bytes


def unpack(data: bytes, offset: int = 0) -> Optional[Dict[str, Any]]:
    """
    Try to read a META block starting at *offset* in *data*.
    Returns the metadata dict, or None if no valid META block is found.
    """
    if offset + MAGIC_SIZE + 4 > len(data):
        return None
    if data[offset:offset + MAGIC_SIZE] != MAGIC:
        return None
    length = struct.unpack_from(">I", data, offset + MAGIC_SIZE)[0]
    start  = offset + MAGIC_SIZE + 4
    if start + length > len(data):
        return None
    try:
        return json.loads(data[start:start + length].decode('utf-8'))
    except Exception:
        return None


def block_size(data: bytes, offset: int) -> int:
    """Return total byte size of the META block at *offset*, or 0 if none."""
    if offset + MAGIC_SIZE + 4 > len(data):
        return 0
    if data[offset:offset + MAGIC_SIZE] != MAGIC:
        return 0
    length = struct.unpack_from(">I", data, offset + MAGIC_SIZE)[0]
    return MAGIC_SIZE + 4 + length


def is_meta(data: bytes, offset: int) -> bool:
    return (offset + MAGIC_SIZE <= len(data) and
            data[offset:offset + MAGIC_SIZE] == MAGIC)


# ── Auto-populate reserved keys ───────────────────────────────────────────────

def build(
    user_pairs: Dict[str, Any],
    archive_bytes_before_meta: bytes,
    sign_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a complete metadata dict:
      - auto-set created, source_host if not supplied
      - compute and append hmac_sha256 if sign_key is provided
    """
    meta: Dict[str, Any] = {}

    # Auto fields (only set if not explicitly supplied)
    if 'created' not in user_pairs:
        meta['created'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    if 'source_host' not in user_pairs:
        try:
            meta['source_host'] = socket.gethostname()
        except Exception:
            pass

    # User-supplied fields (overwrite auto fields if keys clash)
    meta.update(user_pairs)

    # HMAC — computed over everything before this META block
    if sign_key:
        sig = _hmac.new(
            sign_key.encode('utf-8'),
            archive_bytes_before_meta,
            hashlib.sha256,
        ).hexdigest()
        meta['hmac_sha256'] = sig

    return meta


# ── Verify HMAC ───────────────────────────────────────────────────────────────

def verify_hmac(
    meta: Dict[str, Any],
    archive_bytes_before_meta: bytes,
    sign_key: str,
) -> bool:
    """
    Return True if the HMAC in *meta* matches a fresh computation over
    *archive_bytes_before_meta* using *sign_key*.
    Raises ValueError if no hmac_sha256 key is present in meta.
    """
    if 'hmac_sha256' not in meta:
        raise ValueError("Archive has no HMAC signature to verify.")
    expected = _hmac.new(
        sign_key.encode('utf-8'),
        archive_bytes_before_meta,
        hashlib.sha256,
    ).hexdigest()
    # Constant-time comparison
    return _hmac.compare_digest(meta['hmac_sha256'], expected)


# ── Parse --meta key=value pairs from CLI ────────────────────────────────────

def parse_pairs(pairs: list) -> Dict[str, Any]:
    """
    Parse a list of "key=value" strings into a dict.
    Values that look like JSON arrays/objects are decoded;
    comma-separated values become lists (for tags).
    e.g. 'tags=cctv,void,june'  ->  {'tags': ['cctv', 'void', 'june']}
    """
    result: Dict[str, Any] = {}
    for pair in pairs:
        if '=' not in pair:
            raise ValueError(f"--meta value must be key=value, got: {pair!r}")
        key, _, val = pair.partition('=')
        key = key.strip()
        val = val.strip()
        # Try JSON decode first (handles arrays, numbers, booleans)
        try:
            result[key] = json.loads(val)
        except json.JSONDecodeError:
            # Comma-separated → list
            if ',' in val:
                result[key] = [v.strip() for v in val.split(',')]
            else:
                result[key] = val
    return result
