"""Hex-N cell v1 (draft v0.3 of docs/hex-n/walkthrough-v0.2.md): the RTL against an independent cycle-accurate Python model, on random configs and random flow, several windows each.
Requires iverilog. This pins the assumptions A1..A7 in rtl/hexn_cell_v1.v; it is not a decision about them."""
import os, random, shutil, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F, P, AW = 6, 4, 6
N = F * P
PL = 10            # clocks per phase (>= 7)


class Cell:
    def __init__(self, active, dr, code, thr, bias):
        self.a, self.d, self.c, self.thr, self.bias = active, dr, code, thr, bias
        self.fwd = [0] * F; self.fb = [0] * F; self.inany = [0] * F
        self.inany_r = [0] * F; self.fbok_r = [0] * F; self.reach_r = [0] * F; self.margin_r = [0] * F
        self.bc = [0] * N

    def tx(self, phase):
        out = []
        for f in range(F):
            for p in range(P):
                i = f * P + p; d, cd = self.d[i], self.c[i]
                sender = self.a[i] and ((d == 2) if phase else (d in (1, 3)))
                first = not any(self.a[f * P + q] and self.c[f * P + q] == 1 and self.d[f * P + q] != 0 for q in range(p))
                r, fo, ia = self.reach_r[f], self.fbok_r[f], self.inany_r[f]
                pas = {0: r and fo and ia, 1: r and first, 2: r and ((not ia) if p & 1 else ia), 3: False}[cd]
                out.append(int(bool(sender and pas and self.bc[i] < self.margin_r[f] + 1)))
        return out

    def clock(self, rx, phase, ph_start, win_end):
        fwd_n, fb_n, any_rx = list(self.fwd), list(self.fb), [0] * F
        for f in range(F):
            delta = 0
            for p in range(P):
                i = f * P + p; d = self.d[i]
                rl = self.a[i] and rx[i] and ((d == 3) if phase else (d in (0, 2)))
                if rl:
                    any_rx[f] = 1; delta += -1 if self.c[i] == 3 else 1
            if not phase:
                fwd_n[f] = min(max((0 if ph_start else self.fwd[f]) + delta, 0), (1 << AW) - 1)
            else:
                fb_n[f] = min(max(self.fb[f] + delta, 0), (1 << AW) - 1)
        if not phase:
            self.fwd = fwd_n
            if ph_start: self.fb = [0] * F; self.inany = any_rx
            else: self.inany = [a | b for a, b in zip(self.inany, any_rx)]
        else:
            self.fb = fb_n
        self.bc = [0 if ph_start else min(b + 1, 7) for b in self.bc]
        if win_end and phase:
            for f in range(F):
                te = self.thr[f] + self.bias; w = self.fwd[f]
                self.reach_r[f] = int(w >= te)
                self.margin_r[f] = max(min(w - te, 6), 0)
                self.fbok_r[f] = int(fb_n[f] != 0)
                self.inany_r[f] = self.inany[f]


def pack(vals, bits):
    return sum(v << (bits * i) for i, v in enumerate(vals))


def test_rtl_matches_model():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    rnd = random.Random(11)
    cases, expect = [], []
    for k in range(60):
        act = [int(rnd.random() < 0.85) for _ in range(N)]; dr = [rnd.randint(0, 3) for _ in range(N)]
        code = [rnd.randint(0, 3) for _ in range(N)]; thr = [rnd.randint(0, 5) for _ in range(F)]
        bias = rnd.choice([0, 0, 0, 1, 2])
        cell = Cell(act, dr, code, thr, bias)
        seq = []
        for w in range(3):
            for phase in (0, 1):
                for t in range(PL):
                    rx = [int(rnd.random() < 0.55) for _ in range(N)]
                    ps, we = int(t == 0), int(phase == 1 and t == PL - 1)
                    exp = cell.tx(phase)
                    seq.append((rx, phase, ps, we)); expect.append(exp)
                    cell.clock(rx, phase, ps, we)
        cases.append(((act, dr, code, thr, bias), seq))
    lines = []
    for (act, dr, code, thr, bias), seq in cases:
        lines.append(f"    rst = 1; @(posedge clk); #1 rst = 0; act = {N}'d{pack(act,1)}; dir_ = {2*N}'d{pack(dr,2)}; code = {2*N}'d{pack(code,2)}; thr = {F*AW}'d{pack(thr,AW)}; bias = 16'd{bias};")
        for rx, phase, ps, we in seq:
            lines.append(f"    rx = {N}'d{pack(rx,1)}; phase = {phase}; ph_start = {ps}; win_end = {we}; #3 $display(\"T %0d\", tx); @(posedge clk); #1;")
    tb = f"""`timescale 1ns/1ps
module tb; reg clk = 0, rst = 1, phase = 0, ph_start = 0, win_end = 0; always #5 clk = ~clk;
  reg [{N-1}:0] rx, act; reg [{2*N-1}:0] dir_, code; reg [{F*AW-1}:0] thr; reg [15:0] bias; wire [{N-1}:0] tx;
  hexn_cell_v1 #(.FACES({F}), .PAIRS({P}), .AW({AW})) U(.clk(clk), .rst(rst), .phase(phase), .ph_start(ph_start), .win_end(win_end), .rx(rx), .tx(tx),
     .cfg_active(act), .cfg_dir(dir_), .cfg_code(code), .cfg_thr(thr), .bias(bias));
  initial begin rx = 0; act = 0; dir_ = 0; code = 0; thr = 0; bias = 0; repeat (3) @(posedge clk); #1
{chr(10).join(lines)}
    $finish; end
endmodule
"""
    d = tempfile.mkdtemp(prefix="hexn1_")
    try:
        open(os.path.join(d, "tb.v"), "w").write(tb)
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v"), os.path.join(ROOT, "rtl", "hexn_cell_v1.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1000]
        res = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=600).stdout.split("\n")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    got = [int(l.split()[1]) for l in res if l.startswith("T ")]
    assert len(got) == len(expect), (len(got), len(expect))
    sent = 0
    for k, (g, e) in enumerate(zip(got, expect)):
        assert g == pack(e, 1), (k, g, pack(e, 1))
        sent += sum(e)
    assert sent > 200, sent          # the random cases really exercised the transmit path
