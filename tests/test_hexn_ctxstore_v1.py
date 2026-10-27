"""Tests for the SDRAM-backed context store: the RTL (rtl/hexn_ctxstore_v1.v, with our SDRAM controller and the SDRAM model) against the bit-true model, on four streams, comparing every answer and all nine counters. Needs iverilog (FAILS without it)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_ctxstore_rtl_check_v1 as K
def _run(stream, n, seed, bb, cb):
    bad, mc = K.check(stream, n, seed, bb, cb); assert not bad, bad; return mc
def test_mixed(): assert _run("mixed", 1500, 5, 8, 4)["slot_evict"] > 0
def test_saturation(): assert _run("sat", 900, 1, 8, 4)["sd_wr"] == 8 * 600
def test_overflow(): assert _run("full", 2000, 6, 7, 3)["overflow"] > 0
def test_model_slots_and_weights():
    import hexn_ctxstore_v1 as C
    m = C.CtxStore(8, 4, 14)
    for i in range(300): m.obs(99, 1)                     # saturates: halves at 255
    f, sl = m.rd(99); assert f == 1 and sl[0][0] == 1 and sl[0][1] < 255
    for fid in range(2, 40): m.obs(99, fid)               # more followers than slots: replacement
    assert m.c["slot_evict"] > 0
