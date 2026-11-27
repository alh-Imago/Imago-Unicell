"""Python answer for the 32-bit multiply program vmul32.s (ledger #1576; examples.py, examples_v2.py and examples_v3.py are left as they were)."""
M32 = 0xFFFFFFFF
def vmul32_ref(inputs, arg, out_len): return [(x * (arg & M32)) & M32 for x in inputs]
