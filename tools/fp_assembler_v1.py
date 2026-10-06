"""tools/fp_assembler_v1.py -- ledger #989: PARAMETRIC floating-point building blocks made of flex cells (Alan: "make the fp assembler quite open ... the same design, in principle at least, could be used for larger or smaller fp units").

A block is a function  block(grid, fmt, name, r0, c0, ...) -> Block  that puts its cells on a flex_layout Grid (every position is relative to (r0, c0)) and returns its entries, exits and constants (cells whose preload must be
re-injected in the VM). Everything that depends on the number format comes from `FpFormat` (significand bits, exponent bits, word width) -- shift counts, thresholds, constants, stage counts are all computed from it, nothing is
hard-wired to fp32. Blocks (each proven in test_fp_blocks_v1.py in real RTL and in the VM, for fp32 AND a smaller format):

  normalise_chain  left-normalise an S-bit significand (K = bit_length(S-1) conditional-shift stages, shifts 2^(K-1)..1) and adjust the exponent:  NORM = v << lz,  EXPOUT = exp_in - lz   [#984]
  align_sticky     right-shift by an exponent difference d with the discarded bits collected as a sticky flag (K+1 two-word multiplier stages, the last one is the d >= 2^K clamp)   [#988]
                   the aligned word is  w >> (K+1+d)  where w = significand << (word - S):  the significand lands at bits (word-S-K-1+S-1 .. ) with `low` = word - S - (K+1) extra bits below its lsb
  round_rne        round-to-nearest-even of a word that carries the significand with `low` extra bits below it (guard = bit low-1, sticky = bits below it, optionally OR an external sticky flag)   [#984]

Larger formats need a wider WORD (the generator builds 32-bit cells today); smaller formats (half, bfloat16, custom) fit as they are. Timing (operands of one cell arriving in different hops) is balanced by the layout engine."""
import dataclasses
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flex_layout_v1 import Grid  # noqa: E402,F401

M32 = 0xFFFFFFFF


@dataclasses.dataclass(frozen=True)
class FpFormat:
    name: str
    sig_bits: int            # significand INCLUDING the hidden bit
    exp_bits: int
    word: int = 32

    @property
    def K(self):             # conditional-shift stages needed to normalise / align an S-bit significand
        return (self.sig_bits - 1).bit_length()

    @property
    def Ka(self):            # d bits for the align (shifts up to sig_bits + 2 matter; beyond, everything is lost)
        return (self.sig_bits + 2).bit_length()


FP32 = FpFormat("fp32", 24, 8)
FP16 = FpFormat("fp16", 11, 5)
BF16 = FpFormat("bfloat16", 8, 8)


@dataclasses.dataclass
class Block:
    name: str
    entries: dict
    exits: dict
    consts: dict             # cell -> value (preloaded constants; the VM needs them injected each item)
    extent: tuple            # (rows, cols) used, relative to the origin


def _p(name):
    return name + "."


# ------------------------------------------------------------------------------------------------------------------------------------------
def normalise_chain(g, fmt, name="N", r0=0, c0=0, pitch=9):
    """Left-normalise (value in the LOW sig_bits bits of the word) + exponent adjust. Entries: `V` (the significand), `EXPIN`; exits: `NORM`, `EXPOUT`, and per stage `r_s` bits (T cells) are internal."""
    S, K = fmt.sig_bits, fmt.K
    shifts = [1 << j for j in range(K - 1, -1, -1)]
    log2 = {1 << j: j for j in range(K)}
    smax = sum(shifts)
    consts, pre = {}, _p(name)
    R, C = (lambda r: r0 + r), (lambda c: c0 + c)
    for k, s in enumerate(shifts):
        o, p = pitch * k, pre + f"S{s}."
        g.add(p + "V", R(3), C(2 + o))
        g.add(p + "CMP", R(2), C(2 + o), "comparator", {"threshold": 1 << (S - s)})
        g.add(p + "T", R(3), C(4 + o), addon={"shift_en": 1, "direction": 1, "shift_amt": s - log2[s]})     # r_s << log2(s) from R1 (the comparator's four faces are full)
        g.add(p + "K", R(1), C(1 + o), preload=1 << s)
        g.add(p + "AD", R(1), C(2 + o), "adder")
        g.add(p + "SUBF", R(1), C(3 + o), "adder", {"subtract_mode": 1})
        g.add(p + "RS", R(2), C(3 + o), addon={"shift_en": 1, "direction": 0, "shift_amt": s})
        g.add(p + "R1", R(2), C(4 + o))
        g.add(p + "R2", R(1), C(4 + o))
        g.add(p + "MUL", R(0), C(3 + o), "mul")
        consts[p + "K"] = 1 << s
        for a, b in (("V", "CMP"), ("CMP", "AD"), ("K", "AD"), ("AD", "SUBF"), ("CMP", "RS"), ("RS", "R1"), ("R1", "R2"), ("R1", "T"), ("R2", "SUBF"), ("SUBF", "MUL")):
            g.link(p + a, p + b)
        g.minuend[p + "SUBF"] = p + "AD"
    first = lambda k: pre + f"S{shifts[k]}."
    for k in range(1, K):
        g.add(pre + f"A{k}", R(5), C(4 + pitch * k), "adder")
    for k in range(1, K):
        g.route(first(k) + "T", pre + f"A{k}")
    g.route(first(0) + "T", pre + "A1")
    for k in range(1, K - 1):
        g.route(pre + f"A{k}", pre + f"A{k + 1}")
    X = pitch * (K - 1) + 4
    g.add(pre + "E1", R(5), C(X + 2), "adder")
    g.route(pre + f"A{K - 1}", pre + "E1")
    g.add(pre + "EXPIN", R(6), C(X + 2))
    g.link(pre + "EXPIN", pre + "E1")
    g.add(pre + "E2", R(5), C(X + 4), "adder")
    g.route(pre + "E1", pre + "E2")
    g.add(pre + "C", R(6), C(X + 4), preload=(1 << 32) - smax)
    g.link(pre + "C", pre + "E2")
    g.add(pre + "EXPOUT", R(5), C(X + 5))
    g.link(pre + "E2", pre + "EXPOUT")
    consts[pre + "C"] = (1 << 32) - smax
    for k in range(K):
        g.route(first(k) + "V", first(k) + "MUL", avoid=[(R(0), C(4 + pitch * k))])
    for k in range(K - 1):
        g.route(first(k) + "MUL", first(k + 1) + "V")
    g.add(pre + "NORM", R(0), C(pitch * (K - 1) + 6))
    g.route(first(K - 1) + "MUL", pre + "NORM")
    return Block(name, {"V": first(0) + "V", "EXPIN": pre + "EXPIN"}, {"NORM": pre + "NORM", "EXPOUT": pre + "EXPOUT"}, consts, (7, pitch * (K - 1) + 8))


# ------------------------------------------------------------------------------------------------------------------------------------------
def align_sticky(g, fmt, name="AL", r0=0, c0=0, pitch=7, flip=False):
    """Align with sticky. Entries: `V` (w = significand << (word - S), top aligned), `D` (the exponent difference). Exits: `OUT` = w >> T and `STK` = (w mod 2^T != 0), T = (Ka+1) + (d mod 2^Ka) + 31*[d >= 2^Ka]."""
    Ka, word = fmt.Ka, fmt.word
    shifts = [1 << k for k in range(Ka)] + [word - 1]
    n = len(shifts)
    consts, pre = {}, _p(name)
    R, C = ((lambda r: r0 + 5 - r) if flip else (lambda r: r0 + r)), (lambda c: c0 + c)      # flip: the d bus at the BOTTOM of the band, the sticky lane at the top
    st = lambda k: pre + f"A{k}."
    for k, s in enumerate(shifts):
        c, p, last = pitch * k, st(k), k == n - 1
        g.add(pre + f"P{k}", R(0), C(1 + c))                                           # the d bus
        g.add(p + "E", R(1), C(1 + c))
        g.add(p + "B1", R(1), C(2 + c), addon=None if last else {"shift_en": 1, "direction": 0, "shift_amt": word - 1 - k})      # bit k of d -> bit 31
        g.add(p + "B2", R(1), C(3 + c), addon=None if last else {"shift_en": 1, "direction": 1, "shift_amt": 1})                 # -> bit 30 (the comparator is SIGNED)
        g.add(p + "BC", R(1), C(4 + c), "comparator", {"threshold": (1 << Ka) if last else 1 << (word - 2)})
        g.add(p + "BX", R(1), C(5 + c))
        kc = ((1 << (word - 1 - s)) - (1 << (word - 1))) & M32
        g.add(p + "K", R(2), C(4 + c), preload=kc)
        g.add(p + "KM", R(2), C(5 + c), "mul")                                          # b * Kc
        g.add(p + "C", R(1), C(6 + c), preload=1 << (word - 1))
        g.add(p + "ADF", R(2), C(6 + c), "adder")                                       # + 2^(word-1) = F = 2^(word-1-s*b)
        g.add(p + "V", R(3), C(5 + c))
        g.add(p + "MUL", R(3), C(6 + c), "mul", {"second_output": 1})
        g.add(p + "LS", R(4), C(6 + c), addon={"shift_en": 1, "direction": 1, "shift_amt": 1})
        g.add(p + "LC", R(5), C(6 + c), "comparator", {"threshold": 1})
        g.add(p + "SA", R(5), C(7 + c), "adder")
        consts[p + "K"], consts[p + "C"] = kc, 1 << (word - 1)
        g.link(pre + f"P{k}", p + "E")
        chain = ["E", "B1", "B2", "BC", "BX", "KM"]
        for a, b in list(zip(chain, chain[1:])) + [("K", "KM"), ("KM", "ADF"), ("C", "ADF"), ("ADF", "MUL"), ("V", "MUL"), ("MUL", "LS"), ("LS", "LC"), ("LC", "SA")]:
            g.link(p + a, p + b)
        if k == 0:
            g.add(p + "Z", R(4), C(7 + c), preload=0)
            consts[p + "Z"] = 0
            g.link(p + "Z", p + "SA")
    g.add(pre + "OUT", R(3), C(7 + pitch * (n - 1)))
    g.add(pre + "FIN", R(5), C(8 + pitch * (n - 1)), "comparator", {"threshold": 1})
    g.add(pre + "STK", R(5), C(9 + pitch * (n - 1)))
    for k in range(1, n):
        g.route(pre + f"P{k - 1}", pre + f"P{k}")
    for k in range(n - 1):
        g.route(st(k) + "MUL", st(k + 1) + "V", second=True)
    g.route(st(n - 1) + "MUL", pre + "OUT", second=True)
    for k in range(1, n):
        g.route(st(k - 1) + "SA", st(k) + "SA")
    g.link(st(n - 1) + "SA", pre + "FIN")
    g.link(pre + "FIN", pre + "STK")
    return Block(name, {"V": st(0) + "V", "D": pre + "P0"}, {"OUT": pre + "OUT", "STK": pre + "STK"}, consts, (9, pitch * (n - 1) + 10))


def align_total_shift(fmt, d):
    """Python reference: the total shift the align applies for exponent difference d."""
    return (fmt.Ka + 1) + (d & ((1 << fmt.Ka) - 1)) + ((fmt.word - 1) if d >= (1 << fmt.Ka) else 0)


# ------------------------------------------------------------------------------------------------------------------------------------------
def round_rne(g, fmt, name="RN", r0=0, c0=0, low=8, ext_sticky=False):
    """Round-to-nearest-even. The input word X carries the significand at bits low.. with `low` extra bits below its lsb: guard = bit low-1, sticky = (bits low-2..0 != 0) [OR an external 0/1 flag `STK` if ext_sticky].
    Entry `X` (and `STK`); exit `OUT` = (X >> low) + round_up (a carry out of the significand is left for the exponent step)."""
    word, pre = fmt.word, _p(name)
    R, C = (lambda r: r0 + r), (lambda c: c0 + c)
    one = {"shift_en": 1, "direction": 1, "shift_amt": 1}                    # >> 1: the isolated bit sits at bit 30, off the sign
    P = lambda s: pre + s
    g.add(P("XR"), R(3), C(1))
    g.add(P("XB"), R(3), C(2))
    g.add(P("SIG"), R(2), C(1), addon={"shift_en": 1, "direction": 1, "shift_amt": low})
    g.add(P("LBR"), R(4), C(1), addon={"shift_en": 1, "direction": 0, "shift_amt": word - 1 - low})
    g.add(P("LBR2"), R(5), C(1), addon=one)
    g.add(P("LBC"), R(5), C(5), "comparator", {"threshold": 1 << (word - 2)})
    g.add(P("GDR"), R(2), C(2), addon={"shift_en": 1, "direction": 0, "shift_amt": word - low})
    g.add(P("GDR2"), R(1), C(2), addon=one)
    g.add(P("GDC"), R(1), C(3), "comparator", {"threshold": 1 << (word - 2)})
    if low >= 2:
        g.add(P("STR"), R(3), C(3), addon={"shift_en": 1, "direction": 0, "shift_amt": word + 1 - low})
        g.add(P("STR2"), R(3), C(4), addon=one)
        g.add(P("STC"), R(3), C(5), "comparator", {"threshold": 1})
    e = 2 if ext_sticky else 0                                                 # an external sticky flag costs one adder + one comparator in the or-chain
    g.add(P("ADD1"), R(4), C(5), "adder")                                      # sticky + lsb
    g.add(P("ORC"), R(4), C(6), "comparator", {"threshold": 1})
    if ext_sticky:
        g.add(P("EXT"), R(5), C(7))
        g.add(P("ADDX"), R(4), C(7), "adder")                                  # (sticky OR lsb) + external sticky
        g.add(P("ORC2"), R(4), C(8), "comparator", {"threshold": 1})
    g.add(P("ADD2"), R(4), C(7 + e), "adder")                                  # guard + (sticky OR lsb)
    g.add(P("UPC"), R(4), C(8 + e), "comparator", {"threshold": 2})
    g.add(P("ADD3"), R(4), C(9 + e), "adder")                                  # sig + round_up
    g.add(P("OUT"), R(4), C(10 + e))
    links = [("XR", "SIG"), ("XR", "LBR"), ("XR", "XB"), ("XB", "GDR"), ("LBR", "LBR2"), ("GDR", "GDR2"), ("GDR2", "GDC"), ("ADD1", "ORC"), ("ADD2", "UPC"), ("UPC", "ADD3"), ("ADD3", "OUT")]
    links += [("ORC", "ADDX"), ("EXT", "ADDX"), ("ADDX", "ORC2"), ("ORC2", "ADD2")] if ext_sticky else [("ORC", "ADD2")]
    if low >= 2:
        links += [("XB", "STR"), ("STR", "STR2"), ("STR2", "STC"), ("STC", "ADD1")]
    for a, b in links:
        g.link(P(a), P(b))
    entries = {"X": P("XR")}
    if ext_sticky:
        entries["STK"] = P("EXT")
    g.route(P("LBR2"), P("LBC"))
    g.link(P("LBC"), P("ADD1"))
    g.route(P("GDC"), P("ADD2"))                                              # (the guard's lane runs along row 1, the significand's along row 0)
    g.route(P("SIG"), P("ADD3"), avoid=[(R(1), C(1))])
    return Block(name, entries, {"OUT": P("OUT")}, {}, (7, 12 + e))
