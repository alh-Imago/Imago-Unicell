"""Python answers for the two cost-test programs vmmio.s and vnomem.s (ledger #1580; earlier example files untouched)."""
M32 = 0xFFFFFFFF
def vmmio_ref(inputs, arg, out_len): return [(inputs[0] + (arg & M32)) & M32] * 2
vnomem_ref = vmmio_ref
