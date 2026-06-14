"""
lz77.py — LZ77 compression (C extension backed)
────────────────────────────────────────────────
Window   : 32768 bytes (15-bit offset, stored as offset-1)
Lookahead: 258 bytes  (8-bit length, stored as length-3)

Token format: 1 flag byte per group of 8 decisions.
  flag bit = 0  → literal byte
  flag bit = 1  → 3-byte back-reference:
                  byte0 = enc_off >> 7
                  byte1 = (enc_off & 0x7F) << 1 | enc_len >> 7
                  byte2 = enc_len & 0xFF
                  where enc_off = offset-1  (0..32767)
                        enc_len = length-3  (0..255)
"""

try:
    from . import _lz77_c as _backend
    _USING_C = True
except ImportError:
    _backend = None
    _USING_C = False


def compress(data: bytes) -> bytes:
    return _backend.compress(data) if _USING_C else _compress_py(data)


def decompress(data: bytes) -> bytes:
    return _backend.decompress(data) if _USING_C else _decompress_py(data)


def backend_info() -> str:
    return "C extension (_lz77_c) 32KB window" if _USING_C else "pure Python fallback"


# ── Pure-Python fallback ──────────────────────────────────────────────────────

WINDOW_SIZE   = 32768
MAX_MATCH_LEN = 258
MIN_MATCH_LEN = 3


def _find_match_py(data: bytes, pos: int, window_start: int):
    best_len, best_offset = 0, 0
    n = len(data)
    for start in range(window_start, pos):
        length = 0
        while (length < MAX_MATCH_LEN
               and pos + length < n
               and data[start + length] == data[pos + length]):
            length += 1
        if length >= MIN_MATCH_LEN and length > best_len:
            best_len    = length
            best_offset = pos - start
    return best_offset, best_len


def _compress_py(data: bytes) -> bytes:
    if not data:
        return b""
    out = bytearray()
    pos, n = 0, len(data)
    while pos < n:
        flag_pos = len(out)
        out.append(0x00)
        flag, tokens = 0, bytearray()
        for bit in range(8):
            if pos >= n:
                break
            window_start      = max(0, pos - WINDOW_SIZE)
            offset, match_len = _find_match_py(data, pos, window_start)
            if match_len >= MIN_MATCH_LEN:
                flag |= (1 << (7 - bit))
                enc_off = offset - 1           # 0..32767
                enc_len = match_len - MIN_MATCH_LEN  # 0..255
                tokens.append((enc_off >> 8) & 0x7F)
                tokens.append( enc_off       & 0xFF)
                tokens.append( enc_len       & 0xFF)
                pos += match_len
            else:
                tokens.append(data[pos])
                pos += 1
        out[flag_pos] = flag
        out.extend(tokens)
    return bytes(out)


def _decompress_py(data: bytes) -> bytes:
    if not data:
        return b""
    out, i, n = bytearray(), 0, len(data)
    while i < n:
        flag = data[i]; i += 1
        for bit in range(8):
            if i >= n:
                break
            if flag & (1 << (7 - bit)):
                if i + 2 >= n:
                    break
                b0, b1, b2 = data[i], data[i+1], data[i+2]; i += 3
                enc_off = ((b0 & 0x7F) << 8) | b1
                enc_len = b2
                offset  = enc_off + 1
                length  = enc_len + MIN_MATCH_LEN
                start   = len(out) - offset
                if start < 0:
                    raise ValueError(f"LZ77: invalid back-reference (offset={offset})")
                for k in range(length):
                    out.append(out[start + k])
            else:
                out.append(data[i]); i += 1
    return bytes(out)
