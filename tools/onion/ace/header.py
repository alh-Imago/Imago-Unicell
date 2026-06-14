"""
header.py — Deterministic Archive Header
─────────────────────────────────────────
Binary layout (all integers big-endian):

OUTER HEADER (fixed 16 bytes):
  [4]  Magic          b'\\xONION'  (0x4F 0x4E 0x49 0x4F 0x4E = ONION)
                      Actually 5 bytes: O N I O N
  [1]  Format version 0x01
  [1]  Layer count    1–255
  [4]  Original size  uint32
  [4]  Original CRC32 uint32
  [1]  Flags          bit0=has_audit_block  bit1=encrypted

  Total fixed header: 5+1+1+4+4+1 = 16 bytes

PER-LAYER DESCRIPTOR (9 bytes each):
  [1]  Algorithm ID
  [4]  Compressed size  uint32
  [4]  Checksum CRC32   uint32

OPTIONAL AUDIT BLOCK (appended after all payload data):
  [4]  Audit magic  b'AUDT'
  [2]  JSON length  uint16
  [N]  UTF-8 JSON   the compression recipe
"""

import struct
import binascii
from typing import List

from .instruction import AlgoID, InstructionSet, LayerDescriptor

MAGIC          = b'ONION'
FORMAT_VERSION = 0x01

FLAG_HAS_AUDIT = 0x01
FLAG_ENCRYPTED = 0x02

HEADER_FIXED_SIZE  = 16          # 5+1+1+4+4+1
LAYER_DESC_SIZE    = 9           # 1+4+4
AUDIT_MAGIC        = b'AUDT'


def pack_header(iset: InstructionSet, include_audit: bool = True) -> bytes:
    """
    Serialise the archive outer header + layer descriptors.
    Layer compressed_size and checksum must be filled in by the Transformer
    before calling this.
    """
    active_layers = [l for l in iset.layers if not l.skipped]
    layer_count   = len(active_layers)

    flags = 0
    if include_audit:
        flags |= FLAG_HAS_AUDIT
    if iset.encrypt:
        flags |= FLAG_ENCRYPTED

    header = bytearray()
    header += MAGIC
    header += struct.pack(">B", FORMAT_VERSION)
    header += struct.pack(">B", layer_count)
    header += struct.pack(">I", iset.original_size)
    header += struct.pack(">I", iset.original_crc)
    header += struct.pack(">B", flags)

    for layer in active_layers:
        header += struct.pack(">B", layer.algo_id)
        header += struct.pack(">I", layer.compressed_size)
        header += struct.pack(">I", layer.checksum)

    return bytes(header)


def unpack_header(data: bytes) -> tuple[InstructionSet, int, bool]:
    """
    Parse the archive header from *data*.

    Returns
    -------
    (InstructionSet, payload_offset, has_audit_block)

    The payload starts at payload_offset bytes into *data*.
    """
    i = 0

    magic = data[i:i+5]; i += 5
    if magic != MAGIC:
        raise ValueError(f"Not an .onion archive (bad magic: {magic!r})")

    version = data[i]; i += 1
    if version != FORMAT_VERSION:
        raise ValueError(f"Unsupported format version: 0x{version:02x}")

    layer_count  = data[i]; i += 1
    original_size = struct.unpack_from(">I", data, i)[0]; i += 4
    original_crc  = struct.unpack_from(">I", data, i)[0]; i += 4
    flags         = data[i]; i += 1

    has_audit = bool(flags & FLAG_HAS_AUDIT)
    encrypted = bool(flags & FLAG_ENCRYPTED)

    iset = InstructionSet(
        original_size = original_size,
        original_crc  = original_crc,
        encrypt       = encrypted,
    )

    for _ in range(layer_count):
        algo_id         = data[i];                              i += 1
        compressed_size = struct.unpack_from(">I", data, i)[0]; i += 4
        checksum        = struct.unpack_from(">I", data, i)[0]; i += 4
        layer = LayerDescriptor(
            algo_id         = algo_id,
            compressed_size = compressed_size,
            checksum        = checksum,
        )
        iset.layers.append(layer)

    return iset, i, has_audit


def pack_audit(recipe: dict) -> bytes:
    """Serialise the audit block as JSON appended after the payload."""
    import json
    json_bytes = json.dumps(recipe, indent=2).encode("utf-8")
    return AUDIT_MAGIC + struct.pack(">H", len(json_bytes)) + json_bytes


def unpack_audit(data: bytes, payload_end: int) -> dict:
    """
    Read the audit block starting at *payload_end* in *data*.
    Returns the recipe dict, or {} if not present / malformed.
    """
    import json
    i = payload_end
    if i + 6 > len(data):
        return {}
    magic = data[i:i+4]; i += 4
    if magic != AUDIT_MAGIC:
        return {}
    json_len = struct.unpack_from(">H", data, i)[0]; i += 2
    try:
        return json.loads(data[i:i+json_len].decode("utf-8"))
    except Exception:
        return {}
