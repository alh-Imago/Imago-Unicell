"""
packed_adder_cells.py — packed Kogge-Stone 32-bit adder modelled as a cell graph
on the NEW (silicon-proven) UniCell methodology functions.

Each KS prefix stage is:   G = G | (P & (G << span))   ;   P = P & (P << span)

The new cell does the "<< span" itself (stored in-shift before the gate), so the
shift is NOT a separate cell — it folds into the AND cell's methodology. That
collapses each stage's combine to:
    Gp = AND( P, G with stored in-shift=span )     # P & (G<<span)
    G  = OR ( G, Gp )                              # G | (above)
    P  = AND( P, P with stored in-shift=span )     # P & (P<<span)
= 3 cells/stage (one carries a stored shift on a fed operand). 5 stages = 15.
+ stage0: G0=AND(a,b), P0=XOR(a,b)                 # 2 cells
+ final:  carry=G<<1 (stored shift, folds into the XOR), sum=XOR(P0,carry)  # 1 cell
= 18 cells for the prefix+sum core (shift-folding saves vs the old ~21).

This module is the executable cell-graph reference: it simulates the graph using
ONLY operations the proven cell supports (gate + stored in-shift), so its output
must equal a+b. It is the model the .icm loader will emit and the silicon will run.
"""
from gate_states import GS_AND, GS_OR, GS_XOR

MASK32 = 0xFFFFFFFF


def _shl(v, s):
    return (v << s) & MASK32


class Cell:
    """One UniCell: a gate over (A, B) with an optional stored in-shift applied to
    a chosen operand BEFORE the gate (exactly the proven m_in_shift_en path)."""
    def __init__(self, gate, shift=0, shift_on=None):
        self.gate = gate          # GS_AND / GS_OR / GS_XOR
        self.shift = shift        # stored in-shift amount (0 = none)
        self.shift_on = shift_on  # 'A', 'B', or None — which operand is pre-shifted

    def eval(self, a, b):
        a &= MASK32
        b &= MASK32
        if self.shift_on == 'A':
            a = _shl(a, self.shift)
        elif self.shift_on == 'B':
            b = _shl(b, self.shift)
        if self.gate == GS_AND:
            return (a & b) & MASK32
        if self.gate == GS_OR:
            return (a | b) & MASK32
        if self.gate == GS_XOR:
            return (a ^ b) & MASK32
        raise ValueError(f"unsupported gate 0x{self.gate:03X}")


def build_adder_graph():
    """Return the cell graph (list of (name, Cell, inputs)) for a 32-bit packed add.
    inputs reference earlier node names or 'a'/'b' (the two operands)."""
    g = []
    # stage 0
    g.append(("G", Cell(GS_AND), ("a", "b")))      # G = a & b
    g.append(("P", Cell(GS_XOR), ("a", "b")))      # P = a ^ b  (also P0, the partial sum)
    # prefix stages: shift folds into the AND cell that pre-shifts its G/P operand
    for span in (1, 2, 4, 8, 16):
        gp = f"Gp{span}"
        gn = f"G{span}"
        pn = f"P{span}"
        prevG = "G" if span == 1 else f"G{span//2}"
        prevP = "P" if span == 1 else f"P{span//2}"
        # Gp = P & (G << span)  — stored in-shift=span on the G operand, then AND with P
        g.append((gp, Cell(GS_AND, shift=span, shift_on='B'), (prevP, prevG)))
        # G = G | Gp
        g.append((gn, Cell(GS_OR), (prevG, gp)))
        # P = P & (P << span) — stored in-shift=span on one P operand
        g.append((pn, Cell(GS_AND, shift=span, shift_on='B'), (prevP, prevP)))
    # final: carry = G<<1 (stored shift folds into the XOR's operand), sum = P0 ^ carry
    g.append(("SUM", Cell(GS_XOR, shift=1, shift_on='B'), ("P", "G16")))  # P0 ^ (G16<<1)
    return g


def run_adder_graph(a, b):
    """Evaluate the cell graph for a+b; returns the SUM node value."""
    vals = {"a": a & MASK32, "b": b & MASK32}
    for name, cell, ins in build_adder_graph():
        x = vals[ins[0]]
        y = vals[ins[1]]
        vals[name] = cell.eval(x, y)
    return vals["SUM"]


if __name__ == "__main__":
    import random, sys
    fails = 0
    cells = len(build_adder_graph())
    cases = [(0, 0), (1, 1), (0xFFFFFFFF, 1), (0x12345678, 0x9ABCDEF0),
             (0x0000FACE, 0x0000BEEF), (0xFFFFFFFF, 0xFFFFFFFF),
             (0x80000000, 0x80000000), (0xDEADBEEF, 0xCAFEF00D)]
    for a, b in cases:
        got = run_adder_graph(a, b)
        want = (a + b) & MASK32
        ok = "OK" if got == want else "FAIL"
        fails += got != want
        print(f"  {a:08X} + {b:08X} = {got:08X} (want {want:08X}) {ok}")
    for _ in range(5000):
        a = random.randint(0, MASK32)
        b = random.randint(0, MASK32)
        if run_adder_graph(a, b) != (a + b) & MASK32:
            fails += 1
    print(f"  + 5000 random cases: {'all pass' if fails == 0 else str(fails)+' FAIL'}")
    print(f"\nCell graph: {cells} cells (gate + stored-shift only — all proven on silicon)")
    print(">>> PASS — packed adder works on the new cell functions" if fails == 0
          else ">>> FAIL")
    sys.exit(0 if fails == 0 else 1)
