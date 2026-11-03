#!/usr/bin/env python3
"""hexn_twins_v2 = hexn_twins_v1 (untouched) plus the LATCH twin (3 Nov 2026, Alan 14:30 'send a word on each pulse').
LatchTwin mirrors hexn_latch_core_v3 inside hexn_tile_lt_v2: the start flag of a word arriving on face W sets, on N clears, on S toggles (clear wins over set, set over toggle); each pulse sends ONE word, 1 if the new level is on and 0 if off, on E,
starting (pulse tick + 1); a pulse that comes less than 32 clocks after the last report changes the level but sends no word.  Checked against the RTL by tests/vm/test_hexn_latch_card_v1.py."""
from hexn_twins_v1 import *
import hexn_twins_v1 as _T1


class LatchTwin(_T1.Twin):
    INS = ("W", "N", "S")
    def __init__(s):
        super().__init__(); s.q = 0; s.next_ok = -10 ** 9
    def _arrive(s, t, ins):
        s.f = {k: bool(ins.get(k, (0, 0))[1]) for k in s.INS}
    def logic(s, t):
        st, cl, tg = s.f["W"], s.f["N"], s.f["S"]
        if not (st or cl or tg): return
        qn = 0 if cl else 1 if st else (1 - s.q if tg else s.q)
        s.q = qn
        if t >= s.next_ok:
            S = t + 1; s.sched["E"] = (S, [qn] + [0] * (W - 1)); s.next_ok = S + 31
