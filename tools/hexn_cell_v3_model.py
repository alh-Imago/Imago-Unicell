"""Hex-N cell v3 MODEL: the DECISION-TABLE cell (Python only, VM; no RTL).  Alan, 21 Oct 2026: a cell with 6 input faces whose COMBINATIONS lead to different paths, each scored by the goal.
Cell v2 adds every input into one total, so 'faces A,B,C' and 'faces D,E,F' look the same.  Here the cell remembers WHICH faces had input and looks the combination up in a learned table.
Assumptions (C1..C4, to be corrected if wrong):
  C1  per face, 'in' = some active receiving lane of that face carried a 1 during the forward phase of the window (cleared at the start of each window).
  C2  at the end of each window the 6-bit combination of those flags indexes a table of 64 entries; an entry holds, for each of the 6 faces, an output level 0..3 (2 bits): 64 x 6 x 2 = 768 bits per cell.
  C3  in the NEXT window every sending lane of face f (active, direction lets it send in this phase) fires a burst of LEN[level] clocks: LEN = (0, 2, 4, 6).  The burst length is the 'how much'.
  C4  the lane settings active/direction stay as in v2; the gate codes AND/OR/XOR/NOT and the threshold, bias and accumulators are not used (the table replaces them).
cfg = (active[N], dir[N], table[64][6])."""
import importlib.util, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sp = importlib.util.spec_from_file_location("hexn_v2m", os.path.join(ROOT, "tools", "hexn_cell_v2_model.py"))
_m = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_m)
F, P, N = _m.F, _m.P, _m.N
LEN = (0, 2, 4, 6)


class TableCell:
    def __init__(self, active, dr, table):
        self.a, self.d, self.t = active, dr, table
        self.snd = [[bool(self.a[i] and (d in (1, 3))) for i, d in enumerate(self.d)], [bool(self.a[i] and d == 2) for i, d in enumerate(self.d)]]
        self.rcv = [[i for i in range(N) if self.a[i] and self.d[i] in (0, 2)], [i for i in range(N) if self.a[i] and self.d[i] == 3]]
        self.fin = [0] * F; self.out = [0] * F; self.bc = 0

    def tx(self, phase):
        snd = self.snd[phase]; out = [0] * N
        for i in range(N):
            if snd[i] and self.bc < LEN[self.out[i // P]]: out[i] = 1
        return out

    def clock(self, rx, phase, ph_start, win_end):
        if ph_start and not phase: self.fin = [0] * F
        if not phase:
            for i in self.rcv[0]:
                if rx[i]: self.fin[i // P] = 1
        self.bc = 0 if ph_start else min(self.bc + 1, 7)
        if win_end and phase:
            combo = sum(b << f for f, b in enumerate(self.fin)); self.out = list(self.t[combo])
