"""Python answers for the programs of ledger #1598: vmulhu.s (high half of the product), vbyte.s (byte and halfword loads) and vbswap.s (byte and halfword stores)."""
M32 = 0xFFFFFFFF
def vmulhu_ref(inputs, arg, out_len): return [((x * (arg & M32)) >> 32) & M32 for x in inputs]
def _sx(v, bits): return v - (1 << bits) if v >> (bits - 1) else v
def vbyte_ref(inputs, arg, out_len):
    r = []
    for w in inputs:
        b = [(w >> (8 * i)) & 0xFF for i in range(4)]
        s = _sx(b[0], 8) + b[1] + _sx(b[2], 8) + b[3] + _sx(w & 0xFFFF, 16) + (w >> 16)
        r.append(s & M32)
    return r
def vbswap_ref(inputs, arg, out_len):
    if arg & M32: return [((w >> 16) | (w << 16)) & M32 for w in inputs]
    return [int.from_bytes((w & M32).to_bytes(4, 'little'), 'big') for w in inputs]
