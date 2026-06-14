"""
huffman.py — Canonical Huffman entropy coding (C extension backed)
───────────────────────────────────────────────────────────────────
Imports the compiled C extension (_huffman_c) for performance.
Falls back to pure Python if the extension is not available.

Build the extension:
    python build_ext.py build_ext --inplace
"""

try:
    from . import _huffman_c as _backend
    _USING_C = True
except ImportError:
    _backend = None
    _USING_C = False


def compress(data: bytes) -> bytes:
    if _USING_C:
        return _backend.compress(data)
    return _compress_py(data)


def decompress(data: bytes) -> bytes:
    if _USING_C:
        return _backend.decompress(data)
    return _decompress_py(data)


def backend_info() -> str:
    return "C extension (_huffman_c)" if _USING_C else "pure Python (fallback)"


# ── Pure-Python fallback ──────────────────────────────────────────────────────

import heapq
import struct
from collections import Counter
from typing import Dict, Tuple


class _Node:
    __slots__ = ("freq", "symbol", "left", "right")
    def __init__(self, freq, symbol=None, left=None, right=None):
        self.freq, self.symbol, self.left, self.right = freq, symbol, left, right
    def __lt__(self, other): return self.freq < other.freq


def _build_lengths(data: bytes) -> Dict[int, int]:
    counts = Counter(data)
    if len(counts) == 1:
        return {next(iter(counts)): 1}
    heap = [_Node(f, s) for s, f in counts.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        a, b = heapq.heappop(heap), heapq.heappop(heap)
        heapq.heappush(heap, _Node(a.freq + b.freq, left=a, right=b))
    lengths: Dict[int, int] = {}
    def walk(node, d):
        if node.symbol is not None: lengths[node.symbol] = d
        else: walk(node.left, d+1); walk(node.right, d+1)
    walk(heap[0], 0)
    return lengths


def _canonical_codes(lengths: Dict[int, int]) -> Dict[int, Tuple[int, int]]:
    sorted_syms = sorted(lengths, key=lambda s: (lengths[s], s))
    codes: Dict[int, Tuple[int, int]] = {}
    code, prev_len = 0, 0
    for sym in sorted_syms:
        L = lengths[sym]
        code <<= (L - prev_len)
        codes[sym] = (code, L)
        code += 1
        prev_len = L
    return codes


def _compress_py(data: bytes) -> bytes:
    if not data: return b""
    lengths = _build_lengths(data)
    codes   = _canonical_codes(lengths)
    hdr = bytearray()
    hdr += struct.pack(">H", len(lengths))
    for sym in sorted(lengths):
        hdr.append(sym); hdr.append(lengths[sym])
    hdr += struct.pack(">I", len(data))
    bits, nbits, stream = 0, 0, bytearray()
    for byte in data:
        code, L = codes[byte]
        bits = (bits << L) | code; nbits += L
        while nbits >= 8:
            nbits -= 8; stream.append((bits >> nbits) & 0xFF)
    if nbits: stream.append((bits << (8 - nbits)) & 0xFF)
    return bytes(hdr) + bytes(stream)


def _decompress_py(data: bytes) -> bytes:
    if not data: return b""
    i = 0
    sym_count = struct.unpack_from(">H", data, i)[0]; i += 2
    lengths: Dict[int, int] = {}
    for _ in range(sym_count):
        sym = data[i]; i += 1
        L   = data[i]; i += 1
        lengths[sym] = L
    total_symbols = struct.unpack_from(">I", data, i)[0]; i += 4
    codes    = _canonical_codes(lengths)
    decode   = {(c, L): s for s, (c, L) in codes.items()}
    max_len  = max(lengths.values()) if lengths else 0
    out      = bytearray()
    bits, nbits = 0, 0
    while len(out) < total_symbols:
        while nbits < max_len and i < len(data):
            bits = (bits << 8) | data[i]; i += 1; nbits += 8
        matched = False
        for L in range(1, min(nbits, max_len) + 1):
            candidate = (bits >> (nbits - L)) & ((1 << L) - 1)
            if (candidate, L) in decode:
                out.append(decode[(candidate, L)])
                nbits -= L; bits &= (1 << nbits) - 1
                matched = True; break
        if not matched: break
    return bytes(out)
