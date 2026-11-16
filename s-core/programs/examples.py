"""Python answers for the example programs (used as "expect": "programs.examples:vmax_ref" in a job file)."""
M32 = 0xFFFFFFFF
def vmax_ref(inputs, arg, out_len): return [max(inputs) if inputs else 0]
def vprefix_ref(inputs, arg, out_len):
    s, out = 0, []
    for x in inputs: s = (s + x) & M32; out.append(s)
    return out
