#!/usr/bin/env python3
"""hexn_open_emu_v1: A PYTHON MODEL OF THE OPEN UNIT BEHIND THE GATEWAY TEXT PROTOCOL (new file 1 Nov 2026). For testing the PC side (hexn_open_host_v1, the front-end tool) without hardware.
It models what stages 1 to 4b do to registers, the scratch RAM, the table spaces, the presets and the raw word stream with one or two judges, using the bit-exact scorer reference (hexn_scorer_ref_v1). It does NOT model the games, the display, the pins' electrical side or timing:
what it proves is that the host side sends the right words in the right order; what the hardware does with them is proven by the Verilog simulations and the board runs."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_scorer_ref_v1 as R
from hexn_open_host_v1 import POOL, UNIT_ID
class EmuLink:
    def __init__(self):
        self.reg = {i: 0 for i in range(32)}; self.reg[0] = UNIT_ID
        self.scratch = [0] * 1024; self.spaces = {}; self.presets = [0] * 64; self.presets[0] = 1; self.presets[8] = 2; self.presets[16] = 3; self.presets[24] = 3; self.presets[30] = 1
        self.W = [np.zeros((2, 8, 16), dtype=int), np.zeros((2, 8, 16), dtype=int)]; self.bias = [0, 0]
        self.copy_go = 0; self.raw_go = 0; self.psel_applied = 0; self.eff = None; self.nres = 0; self.log = []; self.pin_level = [1] * 16
    def _eff(self, i, k):          # effective setting: from the active preset, else the register
        return self.eff[k] if self.eff else None
    def mode(self): return (self.presets[(self.eff_n - 1) * 8] & 3) if getattr(self, "eff_n", 0) else self.reg[16] & 3
    def jc_start(self): return (self.presets[(self.eff_n - 1) * 8 + 6] & 7) if getattr(self, "eff_n", 0) else self.reg[28] & 7
    def status(self):
        lv = sum(b << i for i, b in enumerate(self.pin_level))
        return (lv << 16) | (self.nres << 8) | ((1 if getattr(self, "eff_n", 0) else 0) << 7) | (1 << 5) | self.mode()
    def cmd(self, line):
        t = line.split(); c = t[0]
        if c == "ID": return "OK %08X" % self.reg[0]
        if c == "R": r = int(t[1], 16); return "OK %08X" % (self.status() if r == 10 else self.reg[r])
        if c == "W": self.write_reg(int(t[1], 16), int(t[2], 16)); return "OK"
        if c == "WW":
            a = int(t[1], 16); w = [int(x, 16) for x in t[2:]]
            assert 0 < len(w) <= 255, "gateway limit"; self.scratch[a:a + len(w)] = w; return "OK %d" % len(w)
        if c == "RW":
            a = int(t[1], 16); n = int(t[2], 16); assert 1 <= n <= 255; return "OK " + " ".join("%08X" % x for x in self.scratch[a:a + n])
        if c == "SPD": return "OK"
        return "ERR unknown command"
    def write_reg(self, r, v):
        self.log.append((r, v)); self.reg[r] = v & 0xFFFFFFFF
        if r == 29:
            self.eff_n = v if 1 <= v <= 8 else 0
        if r == 19 and v != self.copy_go:
            self.copy_go = v; sp = self.reg[17] >> 28; cnt = self.reg[17] & 0xFFFF; w = self.scratch[:cnt]
            if sp == 5: assert cnt <= 64; self.presets[:cnt] = w
            else: self.spaces[sp] = list(w)
        if r == 23 and v != getattr(self, "restore_seen", 0):
            self.restore_seen = v; self.presets = [0] * 64; self.presets[0] = 1; self.presets[8] = 2; self.presets[16] = 3; self.presets[24] = 3; self.presets[30] = 1; self.spaces = {}
        if r == 25 and v != self.raw_go:
            self.raw_go = v
            if self.mode() == 3: self.run_raw()
    def run_raw(self):
        ctl = self.reg[24]; cnt = ctl & 0xFFFF; ob = ctl >> 16 & 0xFFF; jc = self.jc_start(); o = 0; self.nres = 0
        for i in range(cnt):
            w = self.scratch[i]; t = w >> 28
            if t == 14: jc = w & 7; continue
            if t == 15: continue
            if t >= 12: tg = {0: [0], 1: [1], 2: [0, 1]}.get(jc >> 1 & 3, [0])
            else: tg = [0, 1] if jc & 1 else [0]
            for j in tg:
                if t < 12: self.scratch[ob + o] = R.score(self.W[j], self.bias[j], [w >> (4 * k) & 15 for k in range(8)])[0]; o += 1; self.nres = min(255, self.nres + 1)
                elif t == 12: self.W[j][w >> 24 & 1][w >> 20 & 7][w >> 16 & 15] = (w & 255) - (256 if w & 128 else 0)
                elif t == 13: self.bias[j] = (w & 0xFFFF) - (65536 if w & 0x8000 else 0)
