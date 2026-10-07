"""tools/fp_mul_v1.py -- ledger #1008: a floating-point MULTIPLIER from flex cells (Alan: "start on the fp16 side, that should give you shape first").

    result = a * b   in any of the five IEEE rounding modes (build-time `rounding`), subnormals, zeros, inf, nan, overflow

Algorithm (no branch, no data-dependent routing; every step is a cell that exists today; the same blocks as the adder):
  unpack     per operand: sign, effective exponent ee = max(e, 1), significand with its hidden bit (hidden = [e >= 1]), and the flags of the special values            (netlist N1)
  product    P = sigA * sigB  (S + S bits: it fits ONE 32-bit word for fp16 -- fp32 needs split partial products, a later step)
  exponent   E1 = eeA + eeB - (bias - 1): the biased exponent the result has if the product's top bit (bit 2S-1) is set
  underflow  D = (1 - E1) * [E1 <= 0]: when the exponent is below the smallest normal the product is shifted RIGHT by D with the lost bits kept as a sticky flag (`align_sticky`, #988);
             unlike the adder, a product that falls below the smallest normal LOSES bits, so this step is new
  normalise  `normalise_chain_clamped` (#1006) on the aligned word, exponent budget E1 + D: shift = min(leading zeros, E1 + D - 1);  X = (NORM << 1) + sticky                   (netlist N3)
  round      `round_mode` (#1007), the sticky in bit 0, `low` = 16 bits under the significand
  finish     pack = ((EXPOUT - 1) * nonzero << m) + rounded significand (a rounding carry lands in the exponent field), overflow to the infinity or the largest finite number by mode and
             sign, the special values, the sign (the xor of the signs, ALWAYS: a zero or an underflowed product keeps it)                                                          (netlist N2)
The three netlists are placed by `netplace_v1.place_net` (Alan's rule: each path its own line, a cross where lines meet); the three blocks are hand-laid assemblies; the lanes between them are routed.
Subtracts always take a CONSTANT as the minuend (it arrives first by construction), everything else is a plain adder."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_assembler_v1 as fa  # noqa: E402
import fp_add_v1 as fadd  # noqa: E402
import netplace_v1 as npl  # noqa: E402
from flex_layout_v1 import Grid, LayoutError  # noqa: E402

M32 = 0xFFFFFFFF
shl, shr = fadd.shl, fadd.shr


def _unpack(n, t, head, fmt):
    """Netlist ops for one operand (tag t) whose raw word enters at the external cell `head`. Returns nothing; the cells are t.SG (sign 0/1), t.SIG (significand with hidden bit), t.EE (effective exponent),
    t.C (inf or nan), t.N (nan), t.Z (zero), t.CH (hidden bit)."""
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    INF = ((1 << E) - 1) << m
    P = lambda s: f"{t}.{s}"
    n.op(P("X"), "relay", [head])
    n.op(P("SG"), "relay", [P("X")], addon=shr(m + E))
    n.op(P("ML"), "relay", [P("X")], addon=shl(W - m - E))             # the sign dropped, the exponent at the top
    n.op(P("EV"), "relay", [P("ML")], addon=shr(W - E))
    n.op(P("MG"), "relay", [P("ML")], addon=shr(W - m - E))            # the magnitude (sign cleared)
    n.op(P("FL"), "relay", [P("ML")], addon=shl(E))
    n.op(P("F"), "relay", [P("FL")], addon=shr(W - m))
    n.op(P("CH"), "cmp", [P("EV")], thr=1)                              # hidden bit = [e >= 1]
    n.op(P("HD"), "relay", [P("CH")], addon=shl(m))
    n.op(P("SIG"), "add", [P("F"), P("HD")])
    n.op(P("K1a"), "const", const=1)
    n.op(P("NC"), "sub", [P("K1a"), P("CH")])                           # 1 - hidden: the constant is the minuend, it arrives first
    n.op(P("EE"), "add", [P("EV"), P("NC")])                            # max(e, 1)
    n.op(P("C"), "cmp", [P("MG")], thr=INF)                             # inf or nan
    n.op(P("N"), "cmp", [P("MG")], thr=INF + 1)                         # nan
    n.op(P("NZ"), "cmp", [P("MG")], thr=1)
    n.op(P("K1b"), "const", const=1)
    n.op(P("Z"), "sub", [P("K1b"), P("NZ")])                            # zero


def build_n1(fmt, heads, rounding):
    """The front netlist: both unpacks, the product, the exponent sum, the underflow shift amount, the sign, the flags of the special values."""
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    bias = (1 << (E - 1)) - 1
    INF = ((1 << E) - 1) << m
    n = npl.Net()
    _unpack(n, "A", heads["a"], fmt)
    _unpack(n, "B", heads["b"], fmt)
    n.op("PRD", "mul", ["A.SIG", "B.SIG"])
    n.op("O.PV", "relay", ["PRD"], addon=shl(W - 2 * S))                # the product, top aligned (the align block's input)
    n.op("ES", "add", ["A.EE", "B.EE"])
    n.op("KE", "const", const=(-(bias - 1)) & M32)
    n.op("E1", "add", ["ES", "KE"])                                      # the biased exponent if the product's top bit is set
    n.op("C1", "cmp", ["E1"], thr=1)                                     # E1 >= 1
    n.op("K1c", "const", const=1)
    n.op("NE", "sub", ["K1c", "E1"])                                     # 1 - E1
    n.op("K1d", "const", const=1)
    n.op("UR", "sub", ["K1d", "C1"])                                     # 1 - [E1 >= 1] = [E1 <= 0]
    n.op("DD", "mul", ["NE", "UR"])
    n.op("O.D", "relay", ["DD"])                                         # the right shift: 0, or 1 - E1
    n.op("XE", "add", ["E1", "DD"])
    n.op("O.EXPIN", "relay", ["XE"])                                     # the exponent budget of the normalise: E1, or 1 when the product was shifted
    # the sign of the product: the xor of the signs, always
    n.op("XS", "add", ["A.SG", "B.SG"])
    n.op("X1", "cmp", ["XS"], thr=1)
    n.op("X2", "cmp", ["XS"], thr=2)
    n.op("K0a", "const", const=0)
    n.op("NX2", "sub", ["K0a", "X2"])
    n.op("SGN", "add", ["X1", "NX2"])
    n.op("O.SGR", "relay", ["SGN"])                                      # to the round block (rup / rdn)
    n.op("O.SGF", "relay", ["SGN"])                                      # to the finish
    # the special values: any inf / nan input; nan = a nan input, or inf * 0
    n.op("CS", "add", ["A.C", "B.C"])
    n.op("SPC", "cmp", ["CS"], thr=1)
    n.op("O.SPEC", "relay", ["SPC"])
    n.op("IZ1", "mul", ["A.C", "B.Z"])
    n.op("IZ2", "mul", ["A.Z", "B.C"])
    n.op("NS1", "add", ["A.N", "B.N"])
    n.op("NS2", "add", ["IZ1", "IZ2"])
    n.op("NS3", "add", ["NS1", "NS2"])
    n.op("NF", "cmp", ["NS3"], thr=1)
    n.op("NQ", "relay", ["NF"], addon=shl(m - 1))                        # the quiet bit
    n.op("ZSH", "relay", ["SGN"], addon=shl(m + E))
    n.op("KIZ", "const", const=INF)
    n.op("Z1", "add", ["ZSH", "KIZ"])
    n.op("ZW", "add", ["Z1", "NQ"])
    n.op("O.ZW", "relay", ["ZW"])                                        # the word a special result becomes: sign, infinity, quiet bit if nan
    return n


def build_n3(norm, stk):
    """X = (NORM << 1) + STK: the sticky of the underflow shift goes into bit 0, under everything the round looks at. `norm`, `stk`: the external cells."""
    n = npl.Net()
    n.op("SH1", "relay", [norm], addon=shl(1))
    n.op("STKR", "relay", [stk])                                         # (a lane from outside enters a row at its FIRST cell: every external source gets its own relay)
    n.op("O.X", "add", ["SH1", "STKR"])
    return n


def build_n2(fmt, rounding, rout, expout, sgn, spec, zw):
    """The finish: pack, overflow, specials, sign. The arguments after `rounding` are the external cells it reads."""
    E, m, W = fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    INF = ((1 << E) - 1) << m
    n = npl.Net()
    n.op("RO", "relay", [rout])
    n.op("EXR", "relay", [expout])
    n.op("SPR", "relay", [spec])
    n.op("ZWR", "relay", [zw])
    n.op("NZC", "cmp", ["RO"], thr=1)                                    # the rounded significand is not zero
    n.op("KM1", "const", const=M32)
    n.op("ADDR", "add", ["EXR", "KM1"])                                 # EXPOUT - 1
    n.op("MULE", "mul", ["ADDR", "NZC"])
    n.op("SHE", "relay", ["MULE"], addon=shl(m))
    n.op("MAG", "add", ["RO", "SHE"])                                    # the packed magnitude (the rounding carry is in the exponent field)
    n.op("OV", "cmp", ["MAG"], thr=INF)                                  # overflow: the exponent field reaches the infinity pattern
    n.op("K0b", "const", const=0)
    n.op("NM", "sub", ["K0b", "MAG"])
    n.op("SGX", "relay", [sgn])
    # the value an overflow becomes: the infinity, or the largest finite number when the mode rounds that sign toward zero (rtz: always; rup: negative; rdn: positive)
    if rounding in ("rne", "rna", "rtz"):
        n.op("KIS", "const", const=INF - (1 if rounding == "rtz" else 0))
        n.op("D1", "add", ["KIS", "NM"])
    elif rounding == "rup":
        n.op("KI2", "const", const=INF)
        n.op("DS", "sub", ["KI2", "SGX"])                                # INF - sign
        n.op("D1", "add", ["DS", "NM"])
    else:
        n.op("KI3", "const", const=INF - 1)
        n.op("DS", "add", ["KI3", "SGX"])                                # INF - 1 + sign
        n.op("D1", "add", ["DS", "NM"])
    n.op("M1X", "mul", ["OV", "D1"])
    n.op("FF", "add", ["MAG", "M1X"])
    n.op("SW", "relay", ["SGX"], addon=shl(m + E))
    n.op("F1", "add", ["FF", "SW"])
    n.op("K0c", "const", const=0)
    n.op("NF1", "sub", ["K0c", "F1"])
    n.op("D2", "add", ["ZWR", "NF1"])
    n.op("M2X", "mul", ["SPR", "D2"])
    n.op("F", "add", ["F1", "M2X"])
    return n


def fp_mul(g, fmt, name="MUL", rounding="rne", pads=None):
    """Build the multiplier on grid g. Returns (entries {a, b}, exits {R}, consts, placed) where `placed` lists the placed netlists (for the tie / order padding loop)."""
    if rounding not in fa.ROUND_MODES:
        raise ValueError(f"rounding {rounding!r}: one of {fa.ROUND_MODES}")
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    pads = pads or {}
    fal = fa.FpFormat(fmt.name + ".al", 2 * S, E, W)                    # the product (2S bits) is aligned by the underflow shift
    sn = W - (fal.Ka + 1)                                               # ... and lands with its top bit at bit sn - 1
    fnr = fa.FpFormat(fmt.name + ".nr", sn, E, W)
    low = sn + 1 - S                                                    # bits under the significand after X = (NORM << 1) + sticky
    consts, placed = {}, []
    ha, hb = f"{name}.AH", f"{name}.BH"
    g.add(ha, 6, 0)
    g.add(hb, 14, 0)
    n1 = build_n1(fmt, {"a": ha, "b": hb}, rounding)
    nm1, c1, lanes1, rest1, map1 = npl.place_net(g, f"{name}.N1", n1, {ha, hb}, 2, 10, 6, pads.get("N1"))
    consts.update(c1)
    placed.append((f"{name}.N1", map1))
    edge = max(c for _, c in (g.pos(q) for q in g.nodes)) + 8
    al = fa.align_sticky(g, fal, f"{name}.AL", 2, edge)
    consts.update(al.consts)
    edge2 = edge + al.extent[1] + 4
    nr = fa.normalise_chain_clamped(g, fnr, f"{name}.NR", 2, edge2)
    consts.update(nr.consts)
    edge3 = edge2 + nr.extent[1] + 6
    n3 = build_n3(nr.exits["NORM"], al.exits["STK"])
    nm3, c3, lanes3, rest3, map3 = npl.place_net(g, f"{name}.N3", n3, {nr.exits["NORM"], al.exits["STK"]}, 2, edge3 + 4, edge3, pads.get("N3"))
    consts.update(c3)
    placed.append((f"{name}.N3", map3))
    edge4 = max(c for _, c in (g.pos(q) for q in g.nodes)) + 8
    rnd = fa.round_mode(g, fmt, rounding, f"{name}.RND", 2, edge4, low=low)
    consts.update(rnd.consts)
    edge5 = edge4 + rnd.extent[1] + 6
    n2 = build_n2(fmt, rounding, rnd.exits["OUT"], nr.exits["EXPOUT"], nm1["O.SGF"], nm1["O.SPEC"], nm1["O.ZW"])
    ext2 = {rnd.exits["OUT"], nr.exits["EXPOUT"], nm1["O.SGF"], nm1["O.SPEC"], nm1["O.ZW"]}
    nm2, c2, lanes2, rest2, map2 = npl.place_net(g, f"{name}.N2", n2, ext2, 2, edge5 + 4, edge5, pads.get("N2"))
    consts.update(c2)
    placed.append((f"{name}.N2", map2))
    nets = [(nm1["O.PV"], al.entries["V"]), (nm1["O.D"], al.entries["D"]), (al.exits["OUT"], nr.entries["V"]), (nm1["O.EXPIN"], nr.entries["EXPIN"]),
            (nm3["O.X"], rnd.entries["X"])]
    if "SGN" in rnd.entries:
        nets.append((nm1["O.SGR"], rnd.entries["SGN"]))
    kw = {"spread": True}
    allnets = [(a, b, kw) for a, b in lanes1 + lanes3 + lanes2] + nets
    g.route_nets(allnets)
    for rr in (rest1, rest3, rest2):
        rr()
    return {"a": ha, "b": hb}, {"R": nm2["F"]}, consts, placed
