"""
rle.py — Run-Length Encoding
─────────────────────────────
Encoding format (per token):
  • Literal run  : 0x00  <count 1–128>  <count bytes of literal data>
  • Repeated run : 0x01  <count 1–255>  <1 byte to repeat>

This avoids the classic RLE pitfall of expanding non-repetitive data by
using explicit literal runs for non-repetitive stretches.
"""

LITERAL  = 0x00
REPEATED = 0x01
MAX_RUN  = 255
MAX_LIT  = 128


def compress(data: bytes) -> bytes:
    if not data:
        return b""

    out = bytearray()
    i = 0
    n = len(data)

    while i < n:
        # ── Repeated run? ─────────────────────────────────────────────────
        b = data[i]
        run = 1
        while i + run < n and data[i + run] == b and run < MAX_RUN:
            run += 1

        if run >= 3:
            out.append(REPEATED)
            out.append(run)
            out.append(b)
            i += run
            continue

        # ── Literal run ───────────────────────────────────────────────────
        lit_start = i
        lit_count = 0
        while i < n and lit_count < MAX_LIT:
            # Peek ahead: if next ≥ 3 bytes are the same, stop the literal run
            peek_run = 1
            while i + peek_run < n and data[i + peek_run] == data[i] and peek_run < 3:
                peek_run += 1
            if peek_run >= 3:
                break
            i += 1
            lit_count += 1

        out.append(LITERAL)
        out.append(lit_count)
        out.extend(data[lit_start:lit_start + lit_count])

    return bytes(out)


def decompress(data: bytes) -> bytes:
    if not data:
        return b""

    out = bytearray()
    i = 0
    n = len(data)

    while i < n:
        token = data[i]; i += 1
        if token == REPEATED:
            count = data[i]; i += 1
            byte  = data[i]; i += 1
            out.extend(bytes([byte]) * count)
        elif token == LITERAL:
            count = data[i]; i += 1
            out.extend(data[i:i + count])
            i += count
        else:
            raise ValueError(f"RLE: unknown token 0x{token:02x} at offset {i-1}")

    return bytes(out)
