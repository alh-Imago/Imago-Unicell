"""Python answers for the examples added in ledger #1418 (programs/examples.py is left as it was)."""
M32 = 0xFFFFFFFF
def vmin_ref(inputs, arg, out_len): return [min(inputs) if inputs else 0]
def vxor_ref(inputs, arg, out_len): return [(x ^ (arg & M32)) & M32 for x in inputs]
