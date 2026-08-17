from packed_shift_adder import packed_ks_add, _shl, _shr, MASK32
import random

# One KS stage decomposed into UniCell gate-cell ops, two ways.
# Cell model: each cell does ONE 2-operand gate. shift_in shifts the INCOMING
# operand BEFORE the gate; shift_out shifts the RESULT AFTER the gate.

def stage_input_shift(G, P, span):
    # cell1: AND with B=G shifted-in by span   -> t = P & (G<<span)
    t = (P & _shl(G, span)) & MASK32
    # cell2: OR                                -> G' = G | t
    Gn = (G | t) & MASK32
    # cell3: AND with B=P shifted-in by span   -> P' = P & (P<<span)
    Pn = (P & _shl(P, span)) & MASK32
    return Gn, Pn

def stage_output_shift_only(G, P, span):
    # No input shift allowed. Best we can do: gate first, shift the RESULT.
    # cell1: AND P&G, then shift the output left by span -> (P&G)<<span
    t = _shl((P & G) & MASK32, span) & MASK32
    Gn = (G | t) & MASK32
    Pn = _shl((P & P) & MASK32, span) & MASK32   # (P&P)<<span = P<<span
    return Gn, Pn

def full_add_via(stage_fn, a, b):
    G = a & b; P = a ^ b; P0 = P
    for span in (1,2,4,8,16):
        G, P = stage_fn(G, P, span)
    carry = _shl(G, 1)
    return (P0 ^ carry) & MASK32

random.seed(1)
in_ok = out_ok = 0
N = 20000
for _ in range(N):
    a = random.randint(0, MASK32); b = random.randint(0, MASK32)
    ref = (a + b) & MASK32
    if full_add_via(stage_input_shift, a, b) == ref: in_ok += 1
    if full_add_via(stage_output_shift_only, a, b) == ref: out_ok += 1

print(f"  reference = (a+b) mod 2^32")
print(f"  INPUT-shift  (mask->gate, shift on B before gate): {in_ok}/{N} correct")
print(f"  OUTPUT-shift only (gate then shift the result):     {out_ok}/{N} correct")
# Show the algebra on one value so it's not just a pass/fail
G, P = 0x00F0_00F0, 0x0F0F_0F0F
print(f"\n  P & (G<<4)  = 0x{(P & _shl(G,4))&MASK32:08X}   <- what the stage needs")
print(f"  (P & G)<<4  = 0x{_shl((P&G),4)&MASK32:08X}   <- what output-shift gives")
print("  -> not equal: shifting after the AND multiplies the mask too, wrong bits survive")
