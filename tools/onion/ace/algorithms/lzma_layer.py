"""
lzma_layer.py — LZMA/LZMA2 compression layer
──────────────────────────────────────────────
Uses Python's stdlib lzma module — no external dependency.

Two presets available via the FORMAT parameter in the layer header:
  0x01  LZMA preset=1   fast compression, good ratio (3-4× better than LZ77+Huffman)
  0x06  LZMA preset=6   balanced (default — matches gzip-9 ratio, slower)

Format: 1-byte preset header + raw lzma stream.
  [1 byte]  preset used (for faithful decompression)
  [N bytes] lzma.compress() output (self-framing, includes its own header)

Strategist guidance:
  LZMA is worthwhile when:
    - entropy < 6.5  (has redundancy to exploit)
    - content is text, code, JSON, log files (structured repeated patterns)
    - file size > 10KB (LZMA header overhead ~100 bytes)
  LZMA is NOT worthwhile when:
    - entropy > 7.5  (already compressed/encrypted)
    - file is already small (< 2KB)
    - delta pre-conditioner already ran (LZ77+Huffman is sufficient after delta)

Speed note: LZMA preset=6 is ~10-20× slower than LZ77 on large files.
The Gain Monitor will prune it if it doesn't help.
"""

import lzma as _lzma

DEFAULT_PRESET = 6
FAST_PRESET    = 1


def compress(data: bytes, preset: int = DEFAULT_PRESET) -> bytes:
    """Compress with LZMA. preset: 1=fast, 6=balanced, 9=max."""
    if not data:
        return b""
    compressed = _lzma.compress(data, preset=preset)
    return bytes([preset]) + compressed


def decompress(data: bytes) -> bytes:
    """Decompress LZMA layer. Reads preset byte then decompresses."""
    if not data:
        return b""
    # preset byte is informational — lzma stream is self-framing
    payload = data[1:]
    return _lzma.decompress(payload)


def backend_info() -> str:
    return f"stdlib lzma (default preset={DEFAULT_PRESET})"
