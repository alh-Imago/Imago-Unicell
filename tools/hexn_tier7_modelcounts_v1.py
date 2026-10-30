"""Runs ONLY the Python reference (tools/hexn_tier_ref_v3.py Tier3, SPS = 8) on the same step stream as tools/hexn_tier7_card_v2.py and prints its 17 counters, so a card run that passed (its counters equal the model's) can be read for what it exercised, e.g. sd_full. No card needed.
Usage: python3 tools/hexn_tier7_modelcounts_v1.py STEPS KEYS [mix]   (mix = the --mixkeys stream of card_v3)   (defaults: the card's sizes KW24 FB10 BMB17 RAMB14 SB17)"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hexn_tier_ref_v3 import Tier3
def h32(x):
    m = (x * 0x9E3779B1) & 0xFFFFFFFF; m ^= m >> 15; m = (m * 0x85EBCA6B) & 0xFFFFFFFF; return m ^ (m >> 13)
steps, keys = int(sys.argv[1]), int(sys.argv[2]); mix = len(sys.argv) > 3 and sys.argv[3] == 'mix'; KW, VW = 24, 24; MK, MV = (1 << KW) - 1, (1 << VW) - 1
t = Tier3(KW=KW, FB=10, BMB=17, RAMB=14, SB=17, SPS=8); t0 = time.time()
for n in range(steps):
    r = h32(n + 0x1111); ki = (r >> 4) % keys; kk = (h32(ki + 0x777) if mix else ((ki + 1) * 0x2545F491 & 0xFFFFFFFF)) & MK
    if ((r >> 20) % 10) < 4: t.put(kk, h32(n + 0x5151) & MV)
    else: t.get(kk)
print("%d steps, %d keys, %.0f s" % (steps, keys, time.time() - t0))
for k, v in t.n.items(): print("  %-14s %d" % (k, v))
print("entries held: level0 %d, level1 %d, DDR3 lines written %d" % (len(t.fast), len(t.sdram), len(t.written)))
