"""hexn_record_v1.py -- reference for the Hex-N guarded record v1 (docs/hex-n/GUARDED_RECORD_v1.md). Host side only. 1 Nov 2026."""
MAGIC = 0x4852; VERSION = 1
KINDS = {1: (256, 32), 2: (256, 32), 3: (256, 6), 4: (64, 8), 5: (64, 32), 6: (8, 16), 7: (64, 32)}      # kind -> (capacity in entries, entry width in bits)
M32 = 0xFFFFFFFF


def pack(kind, payload, struct_id=0):
    cap, wd = KINDS[kind]; n = len(payload)
    w = [(MAGIC << 16) | (VERSION << 8) | kind, (n << 16) | (wd << 8), struct_id & M32] + [int(p) & M32 for p in payload]
    return w + [sum(w) & M32]


def verify(rec, want_kind=None, struct_id=0):
    """Return (code, payload): code 0 ok, 1 bad magic/version/kind, 2 wrong geometry, 3 bad checksum, 4 truncated/too long/stray bits, 5 other structure."""
    if len(rec) < 4: return 4, None
    k = rec[0] & 0xFF
    if (rec[0] >> 16) != MAGIC or ((rec[0] >> 8) & 0xFF) != VERSION or k not in KINDS or (want_kind is not None and k != want_kind): return 1, None
    cap, wd = KINDS[k]; n = rec[1] >> 16
    if (rec[1] >> 8) & 0xFF != wd or (rec[1] & 0xFF) != 0 or n == 0 or n > cap: return 2, None
    if len(rec) != n + 4: return 4, None
    if sum(rec[:-1]) & M32 != rec[-1]: return 3, None
    if any(p >> wd for p in rec[3:-1]): return 4, None
    if rec[2] != (struct_id & M32): return 5, None
    return 0, list(rec[3:-1])
