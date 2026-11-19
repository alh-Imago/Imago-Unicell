"""Python answer for the example added in ledger #1419 (examples.py and examples_v2.py are left as they were)."""
M32 = 0xFFFFFFFF
def vcount_ref(inputs, arg, out_len): return [sum(1 for x in inputs if x > (arg & M32))]
