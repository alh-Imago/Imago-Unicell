"""tools/fp_compare_v1.py -- ledger #1009: a floating-point COMPARATOR from flex cells (Alan: "start on the compare").

    result = -1 (a < b), 0 (a == b), +1 (a > b), 2 (unordered: either input is a nan)       as a 32-bit word (-1 = 0xFFFFFFFF)

No rounding, no alignment, no normalise: a float's ORDER is the order of its signed magnitude, so
    key  = magnitude * (1 - 2 * sign)                 (the sign bit cleared, then the sign applied: -0 and +0 both become 0, so they are equal by themselves; the infinities are the largest keys)
    d    = key_a - key_b                              (as key_a + (0 - key_b): a constant is the only minuend)
    r    = [d >= 1] + [d >= 0] - 1                    (+1, 0, -1)
    nan  = [mag_a > INF] + [mag_b > INF] >= 1         (unordered: the result is 2)
One netlist, placed by `netplace_v1.place_net`. The keys are signed words, so the format must fit 31 bits for the difference not to wrap: fp16 and bfloat16 do, fp32 needs a split (open)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_add_v1 as fadd  # noqa: E402
import netplace_v1 as npl  # noqa: E402

M32 = 0xFFFFFFFF
shl, shr = fadd.shl, fadd.shr


def _operand(n, t, head, fmt):
    E, m, W = fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    INF = ((1 << E) - 1) << m
    P = lambda s: f"{t}.{s}"
    n.op(P("X"), "relay", [head])
    n.op(P("SG"), "relay", [P("X")], addon=shr(m + E))
    n.op(P("ML"), "relay", [P("X")], addon=shl(W - m - E))
    n.op(P("MG"), "relay", [P("ML")], addon=shr(W - m - E))             # the magnitude: the sign bit cleared
    n.op(P("N"), "cmp", [P("MG")], thr=INF + 1)                          # nan
    n.op(P("S2"), "relay", [P("SG")], addon=shl(1))
    n.op(P("K1"), "const", const=1)
    n.op(P("NS"), "sub", [P("K1"), P("S2")])                             # 1 - 2 * sign = +1 / -1
    n.op(P("KY"), "mul", [P("MG"), P("NS")])                             # the key


def build(fmt, heads):
    assert fmt.exp_bits + fmt.sig_bits <= 31, "the keys are signed words: the format must fit 31 bits (fp32 needs a split)"
    n = npl.Net()
    _operand(n, "A", heads["a"], fmt)
    _operand(n, "B", heads["b"], fmt)
    n.op("K0a", "const", const=0)
    n.op("NKB", "sub", ["K0a", "B.KY"])
    n.op("DF", "add", ["A.KY", "NKB"])
    n.op("C1", "cmp", ["DF"], thr=1)
    n.op("C0", "cmp", ["DF"], thr=0)
    n.op("RS", "add", ["C1", "C0"])
    n.op("KM", "const", const=M32)
    n.op("R", "add", ["RS", "KM"])                                       # -1 / 0 / +1
    n.op("US", "add", ["A.N", "B.N"])
    n.op("UC", "cmp", ["US"], thr=1)
    n.op("K0b", "const", const=0)
    n.op("NR", "sub", ["K0b", "R"])
    n.op("K2", "const", const=2)
    n.op("D2", "add", ["K2", "NR"])                                      # 2 - r
    n.op("MU", "mul", ["UC", "D2"])
    n.op("F", "add", ["R", "MU"])                                        # r, or 2 when unordered
    return n


def fp_compare(g, fmt, name="CMP", pads=None):
    """Build the comparator on grid g. Returns (entries {a, b}, exits {R}, consts, placed)."""
    ha, hb = f"{name}.AH", f"{name}.BH"
    g.add(ha, 6, 0)
    g.add(hb, 14, 0)
    n = build(fmt, {"a": ha, "b": hb})
    nm, consts, lanes, rest, nets_of = npl.place_net(g, f"{name}.N", n, {ha, hb}, 2, 10, 6, (pads or {}).get("N"))
    g.route_nets([(a, b, {"spread": True}) for a, b in lanes])
    rest()
    return {"a": ha, "b": hb}, {"R": nm["F"]}, consts, [(f"{name}.N", nets_of)]
