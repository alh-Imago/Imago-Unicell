"""hexn_wrgrid_v8b - the v8 core MODEL with the BUFFERED ops (lt, min, max) put on the RTL's TIMING (3 Nov 2026, Alan 09:27: 'the timing in the planner is critical so should reflect the actual timing as best it can').
FINDING (ledger 3 Nov 12:00): the RTL join core (hexn_join_core_v2, inside the JN tile) emits lt ONE clock and min / max THREE clocks later than v8's behavioural Core, measured through the generated pattern on 8 tasks, constant across operand order and arrival gaps; the values were always right.
Here Core = v8's Core with its output (r, rs) delayed by LATE[op] clocks for lt / min / max; add / sub / and / or / xor and the unary ops are untouched (their offset to the RTL was already the same constant for every tile). delta() is re-derived by stepping THIS Core, so the planner's arrival times follow.
Everything else is v8's, re-exported: Fifo, UNARY7, SERIAL7, BUF7. v8 itself is untouched."""
import os, sys, random
from collections import deque
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hexn_wrgrid_v8 import Fifo, UNARY7, SERIAL7, BUF7, Core as _Core1

LATE = {"lt": 1, "min": 3, "max": 3}      # clocks the RTL is later than the v8 model; measured, see the module docstring


class Core(_Core1):
    def __init__(s, op, k, aligned=False):
        super().__init__(op, k, aligned)
        s._pipe = deque([(0, 0)] * LATE.get(op, 0))
    def step(s, a, af, b, bf):
        super().step(a, af, b, bf)
        if s._pipe:
            s._pipe.append((s.r, s.rs)); s.r, s.rs = s._pipe.popleft()


_CAL = {}
def delta(op, mode, k=0):
    """wout-visible tick of the first result bit minus the base tick (later operand start for a join, the input start otherwise); measured by stepping a core"""
    key = (op, mode, k)
    if key in _CAL: return _CAL[key]
    res = set()
    for ta, tb in ((10, 10), (10, 25), (25, 10)) if mode == "join" else ((10, 10),):
        c = Core(op, k, mode == "aligned"); rnd = random.Random(1); A = rnd.randrange(1 << 32); B = rnd.randrange(1 << 32); vis = None
        for t in range(1, 200):
            ia, ib = t - ta, t - tb
            a = (A >> ia) & 1 if 0 <= ia < 32 else 0; b = (B >> ib) & 1 if 0 <= ib < 32 else 0
            c.step(a, 1 if ia == 0 else 0, b, 1 if ib == 0 else 0)
            if c.rs and vis is None: vis = t + 1
        res.add(vis - max(ta, tb))
    assert len(res) == 1, (key, res)
    _CAL[key] = res.pop(); return _CAL[key]


