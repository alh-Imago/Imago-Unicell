"""Hex-N cell v2 MODEL (Python only; no RTL yet). Clone of the v1 model in tests/test_hexn_cell_v1.py with ONE change, chosen by Alan on 20 Oct:
the faces of a cell feed ONE decision (the original intent: lanes are the dendrites of one neuron).

What changes against v1 (new assumptions, marked B1..B4 so they can be corrected):
  B1  one forward total and one feedback total for the whole cell: every active receiving lane on every face adds 1 (NEGATIVE lanes subtract 1) to the same total.
  B2  one threshold per cell (plus the shared bias).  cfg = (active[N], dir[N], code[N], [thr], bias)
  B3  reach / margin / feedback-agrees / any-input are worked out once per cell, at the end of each window, as in v1 (A2..A5 unchanged).
  B4  transmit gates as in v1 but with the cell-level conditions; CHOOSE still picks the lowest-numbered such lane WITHIN a face; STEER still goes by lane parity.
Everything else (phases, burst of 1+margin clocks, saturation at 2^AW-1, floor at 0) is as v1.
Note: one neuron gives ONE decision, so every sending lane of a cell that passes its gate fires the same burst; telling classes apart needs several cells."""
import importlib.util, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sp = importlib.util.spec_from_file_location("hexn_t", os.path.join(ROOT, "tests", "test_hexn_cell_v1.py"))
_m = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_m)
F, AW = _m.F, _m.AW
P, N = _m.P, _m.N


class MixCell:
    def __init__(self, active, dr, code, thr, bias):
        self.a, self.d, self.c, self.thr, self.bias = active, dr, code, thr[0], bias
        self.fwd = self.fb = 0; self.inany = self.inany_r = self.fbok_r = self.reach_r = self.margin_r = 0
        self.bc = 0                       # one shared clock counter (identical for every lane, as in the RTL)
        # static per-lane facts, worked out once (speed only; the behaviour is unchanged)
        self.first = [not any(self.a[f * P + q] and self.c[f * P + q] == 1 and self.d[f * P + q] != 0 for q in range(p)) for f in range(F) for p in range(P)]
        self.snd = [[bool(self.a[i] and (d in (1, 3))) for i, d in enumerate(self.d)], [bool(self.a[i] and d == 2) for i, d in enumerate(self.d)]]
        self.rcv = [[i for i in range(N) if self.a[i] and self.d[i] in (0, 2)], [i for i in range(N) if self.a[i] and self.d[i] == 3]]

    def tx(self, phase):
        r, fo, ia = self.reach_r, self.fbok_r, self.inany_r
        burst = self.bc < self.margin_r + 1
        snd = self.snd[phase]
        if not (r and burst): return [0] * N
        out = []
        for i in range(N):
            if not snd[i]: out.append(0); continue
            cd = self.c[i]
            pas = (fo and ia) if cd == 0 else (self.first[i] if cd == 1 else ((not ia) if (i % P) & 1 else ia) if cd == 2 else False)
            out.append(int(bool(pas)))
        return out

    def clock(self, rx, phase, ph_start, win_end):
        delta = 0; any_rx = 0
        for i in self.rcv[phase]:
            if rx[i]:
                any_rx = 1; delta += -1 if self.c[i] == 3 else 1
        cap = (1 << AW) - 1
        if not phase:
            self.fwd = min(max((0 if ph_start else self.fwd) + delta, 0), cap)
            if ph_start: self.fb = 0; self.inany = any_rx
            else: self.inany |= any_rx
        else:
            self.fb = min(max(self.fb + delta, 0), cap)
        self.bc = 0 if ph_start else min(self.bc + 1, 7)
        if win_end and phase:
            te = self.thr + self.bias
            self.reach_r = int(self.fwd >= te); self.margin_r = max(min(self.fwd - te, 6), 0)
            self.fbok_r = int(self.fb != 0); self.inany_r = self.inany
