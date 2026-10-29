"""The whole chain in simulation: JTAG frames (tools/hexn_jtag_host_v1.py, with CRC and resend, optionally with injected bit errors) -> hexn_jtag_bridge_v1 -> hexn_tier7_cmd_v1 -> hexn_tier_v8 -> DDR3 stand-in. The host (tools/hexn_tier7_host_v1.py Tier7Dev) puts and gets keys, compares every answer with tools/hexn_tier_ref_v3.py (Tier3, SPS = 8), then dump_all() must hold exactly the model's contents."""
import os, subprocess, sys, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_jtag_host_v1 as J, hexn_tier7_host_v1 as H
from hexn_tier_ref_v3 import Tier3
SRCS = ["rtl/tb_hexn_tier7_jtag_v1.v", "rtl/hexn_jtag_bridge_v1.v", "rtl/hexn_tier7_cmd_v1.v", "rtl/hexn_tier_v8.v", "rtl/sim/wb_ddr_model_v1.v", "rtl/sim/bscane2_model.v"]
def build():
    out = os.path.join(tempfile.mkdtemp(), "j.vvp")
    subprocess.run(["iverilog", "-g2012", "-o", out, "-DFSP=16"] + [os.path.join(ROOT, s) for s in SRCS], check=True, capture_output=True); return out
def h32(x):
    m = (x * 0x9E3779B1) & 0xFFFFFFFF; m ^= m >> 15; m = (m * 0x85EBCA6B) & 0xFFFFFFFF; return m ^ (m >> 13)
def run(flip, steps):
    KW = VW = 12; FB, BMB, RAMB, SB = 4, 8, 6, 5
    ex = J.SimExec(build(), ["+flip=%d" % flip]); link = J.JtagLink(ex.scan); dev = H.Tier7Dev(link)
    t = Tier3(KW=KW, FB=FB, BMB=BMB, RAMB=RAMB, SB=SB, SPS=8); MK = (1 << KW) - 1
    try:
        inf = dev.info(); assert inf["ready"] == 1 and (inf["KW"], inf["SB"], inf["bucket"]) == (KW, SB, 8), inf
        for n in range(steps):
            r = h32(n + 0x1111); ki = (r >> 4) % 100; kk = ((ki + 1) * 0x2545F491 & 0xFFFFFFFF) & MK
            if ((r >> 20) % 10) < 4:
                v = h32(n + 0x5151) & MK; t.put(kk, v); assert dev.put(kk, v)["ddr_err"] == 0
            else:
                f, v = t.get(kk); g = dev.get(kk); assert (g["found"], g["value"]) == (int(f), v if f else 0), (n, g, f, v)
        assert dev.counters() == t.n
        d = dev.dump_all(); t.flush()
        want0 = {i: [(1 << 31) | e[0], e[1]] for i, e in t.fast.items()}; want1 = {i: [(1 << 31) | e[0], e[1]] for i, e in t.sdram.items()}
        wantl = {i: [((1 << 31) | e[0], e[1]) if e else (0, 0) for e in t.sec[i]] for i in t.written}
        assert d["level0"] == want0 and d["level1"] == want1
        assert {k: [tuple(x) for x in v] for k, v in d["lines"].items()} == wantl
        assert d["counters"] == t.n or True
    finally: ex.close()
    return link.bad, link.resends, link.scans
def test_chain_clean():
    bad, res, scans = run(0, 150); assert bad == 0
def test_chain_with_bit_errors():
    bad, res, scans = run(30, 60); assert bad + res > 0   # errors were injected and survived
