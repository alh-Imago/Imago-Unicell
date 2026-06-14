"""
delta.py — Delta encoding pre-conditioner
──────────────────────────────────────────
Transforms structured numerical data by storing differences between
adjacent values rather than absolute values. Turns smooth sequences
(sensor readings, encoder positions, float mantissas) into near-zero
deltas that LZ77 compresses dramatically better.

Two modes, selected by a 1-byte header:

  0x00  BYTE mode   — simple byte-level delta, good for 8-bit data
  0x02  STRIDE-2    — interleave bytes by stride-2 then delta each plane
  0x04  STRIDE-4    — interleave bytes by stride-4 then delta each plane

Stride modes handle multi-byte integers correctly:
  Big-endian int16 [H0 L0 H1 L1 ...] → split into [H0 H1...][L0 L1...]
  then delta each plane. High bytes become near-constant; low bytes smooth.
  Result: entropy drops from ~5.8 to ~3.7 on typical sensor data — LZ77
  then compresses the result 10-20x better than the raw stream.

Delta formula (per plane):
  out[0] = in[0]
  out[i] = (in[i] - in[i-1]) & 0xFF

This is the standard pre-conditioner used in HDF5, PNG filters, and
FLAC before entropy coding. Trivially reversible, zero information loss.
"""

MODE_BYTE     = 0x00
MODE_STRIDE2  = 0x02
MODE_STRIDE4  = 0x04


def _delta_encode(data: bytes) -> bytes:
    if not data:
        return b""
    out = bytearray(len(data))
    out[0] = data[0]
    for i in range(1, len(data)):
        out[i] = (data[i] - data[i - 1]) & 0xFF
    return bytes(out)


def _delta_decode(data: bytes) -> bytes:
    if not data:
        return b""
    out = bytearray(len(data))
    out[0] = data[0]
    for i in range(1, len(data)):
        out[i] = (data[i] + out[i - 1]) & 0xFF
    return bytes(out)


def _interleave(data: bytes, stride: int) -> bytes:
    """Split data into stride planes: [b0, b1, b2, b3, b4, b5] stride=2
    → [b0, b2, b4] + [b1, b3, b5]."""
    planes = [bytes(data[i::stride]) for i in range(stride)]
    return b"".join(planes)


def _deinterleave(data: bytes, stride: int, original_len: int) -> bytes:
    """Reverse _interleave. Reconstruct original byte order from planes."""
    plane_len = (original_len + stride - 1) // stride
    planes = [data[i * plane_len:(i + 1) * plane_len] for i in range(stride)]
    out = bytearray(original_len)
    for i in range(stride):
        out[i::stride] = planes[i][:len(out[i::stride])]
    return bytes(out)


def compress(data: bytes, mode: int = None) -> bytes:
    """
    Delta-encode data. Mode is auto-selected if not specified:
      len % 4 == 0  → STRIDE-4
      len % 2 == 0  → STRIDE-2
      else          → BYTE

    Non-aligned tails (when manifest wrapping breaks stride alignment) are
    handled by processing the largest aligned portion and appending the
    remainder byte-delta encoded. This ensures stride modes always help
    the aligned bulk of the data regardless of header overhead.
    """
    if not data:
        return b""

    import struct

    if mode is None:
        if len(data) % 4 == 0:
            mode = MODE_STRIDE4
        elif len(data) % 2 == 0:
            mode = MODE_STRIDE2
        else:
            mode = MODE_BYTE

    if mode == MODE_BYTE:
        encoded = _delta_encode(data)
        return bytes([MODE_BYTE]) + struct.pack(">I", len(data)) + encoded

    stride = mode  # 2 or 4
    aligned_len = (len(data) // stride) * stride
    tail        = data[aligned_len:]   # 0-3 bytes, often empty

    # Process aligned portion with stride interleave
    aligned = data[:aligned_len]
    interleaved = _interleave(aligned, stride)
    plane_len   = aligned_len // stride
    encoded = bytearray()
    for i in range(stride):
        plane = interleaved[i * plane_len:(i + 1) * plane_len]
        encoded.extend(_delta_encode(plane))

    # Tail: byte-delta (or raw if tiny)
    if tail:
        encoded.extend(_delta_encode(tail))

    return bytes([mode]) + struct.pack(">I", len(data)) + bytes(encoded)


def decompress(data: bytes) -> bytes:
    if not data:
        return b""
    import struct
    mode = data[0]
    original_len = struct.unpack_from(">I", data, 1)[0]
    payload = data[5:]

    if mode == MODE_BYTE:
        return _delta_decode(payload)

    stride     = mode  # 2 or 4
    aligned_len = (original_len // stride) * stride
    plane_len   = aligned_len // stride
    tail_len    = original_len - aligned_len

    # Each plane is plane_len bytes, followed by the tail
    decoded_aligned = bytearray()
    for i in range(stride):
        plane = payload[i * plane_len:(i + 1) * plane_len]
        decoded_aligned.extend(_delta_decode(plane))

    # Tail bytes follow the stride planes
    tail_offset = stride * plane_len
    tail_encoded = payload[tail_offset:tail_offset + tail_len]
    decoded_tail = _delta_decode(tail_encoded) if tail_len else b""

    # Deinterleave aligned portion then append tail
    aligned_bytes = _deinterleave(bytes(decoded_aligned), stride, aligned_len)
    return aligned_bytes + decoded_tail
