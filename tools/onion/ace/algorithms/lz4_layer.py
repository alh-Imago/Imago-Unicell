"""
lz4_layer.py — LZ4 fast compression layer
───────────────────────────────────────────
LZ4 is a speed-first compressor: microsecond compression/decompression
at the cost of ratio. Use when throughput matters more than size.

Requires: pip install lz4

When to use (Strategist guidance):
  - Large files (> 50MB) where decompression speed is critical
  - Real-time streaming data ingestion
  - Intermediate/scratch archives that will be recompressed later
  - Already-structured data that LZMA won't help (binary blobs, packed structs)

When NOT to use:
  - Text/code/JSON  → LZMA gives 3-5× better ratio at acceptable speed
  - Sensor/numerical → Delta+LZ77+Huffman already optimal
  - Small files      → LZ4 frame header overhead (~11 bytes) not worth it
  - Already compressed → Raw is correct

Ratio vs speed tradeoff (typical):
  LZ77+Huffman : moderate ratio, slow (Python fallback) / fast (C ext)
  LZ4          : lower ratio (~25% worse), microsecond speed
  LZMA         : best ratio, 10-20× slower than LZ77

Format: lz4.frame output (self-framing, includes magic, length, checksum).
No extra header needed — lz4.frame is already self-describing.
"""

_AVAILABLE = False

try:
    import lz4.frame as _lz4
    _AVAILABLE = True
except ImportError:
    _lz4 = None


def compress(data: bytes) -> bytes:
    if not _AVAILABLE:
        raise RuntimeError(
            "LZ4 layer requires the lz4 package: pip install lz4"
        )
    if not data:
        return b""
    return _lz4.compress(data, compression_level=0)   # level=0 = fast mode


def decompress(data: bytes) -> bytes:
    if not _AVAILABLE:
        raise RuntimeError(
            "LZ4 layer requires the lz4 package: pip install lz4"
        )
    if not data:
        return b""
    return _lz4.decompress(data)


def available() -> bool:
    return _AVAILABLE


def backend_info() -> str:
    if _AVAILABLE:
        import lz4
        return f"lz4 {lz4.__version__} (fast mode, level=0)"
    return "lz4 NOT available (pip install lz4)"
