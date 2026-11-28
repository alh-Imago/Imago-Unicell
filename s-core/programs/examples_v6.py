"""Python answer for the divide-by-constant program vdivc.s (ledger #1590): (x * M mod 2^32) >> k with arg = (k << 27) | M.  Equal to x // d only for x up to divconst_v1.best(d)[2]."""
M32 = 0xFFFFFFFF
def vdivc_ref(inputs, arg, out_len): return [(((x * (arg & 0x7FFFFFF)) & M32) >> ((arg >> 27) & 31)) for x in inputs]
