"""Tests for the log-structured card level hexn_tier_v4 (fast table / SDRAM victim level / SD card as a log with an exact index in the SDRAM): the RTL against the SDRAM rule model and the behavioural SD card, and all 19 counters equal to the bit-true Python reference over the same pseudo-random PUT/GET sequence (then a flush)."""
import os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tier_ref_v4 as R
SRCS = ["rtl/tb_hexn_tier_v4.v", "rtl/hexn_tier_v4.v", "rtl/hexn_sdram_v1.v", "fpga/verilog/sd_spi_v1.v", "fpga/verilog/sd_card_model_v1.v", "rtl/sim/sdram_model_v1.v"]
def h32(x):
    m = (x * 0x9E3779B1) & 0xFFFFFFFF; m ^= m >> 15; m = (m * 0x85EBCA6B) & 0xFFFFFFFF; return m ^ (m >> 13)
def ref(KW, VW, FB, RAMB, LB, LOW, NK, STEPS):
    t = R.Tier4(KW, FB, RAMB, LB, LOW); MK = (1 << KW) - 1; MV = (1 << VW) - 1
    for n in range(STEPS):
        r = h32(n + 0x1111); ki = (r >> 4) % NK; kk = ((ki + 1) * 0x2545F491 & 0xFFFFFFFF) & MK
        if ((r >> 20) % 10) < 4: t.put(kk, h32(n + 0x5151) & MV)
        else: t.get(kk)
    t.flush(); return t.n
def sim(**params):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog and vvp are required"
    out = os.path.join(tempfile.mkdtemp(), "tier4.vvp")
    d = ["-Ptb_hexn_tier_v4.%s=%d" % (k, v) for k, v in params.items()]
    subprocess.run(["iverilog", "-g2012", "-o", out] + d + [os.path.join(ROOT, s) for s in SRCS], check=True, capture_output=True)
    return subprocess.run(["vvp", out], capture_output=True, text=True, timeout=3000).stdout
def check(**params):
    p = dict(KW=12, VW=12, FB=4, RAMB=4, LB=4, LOW=3, NK=120, STEPS=400); p.update(params)
    o = sim(**p)
    assert "TIER4 TEST PASS" in o, o[-1500:]
    c = {a: int(b) for a, b in re.findall(r"(\w+)=(\d+)", re.search(r"COUNTERS (.*)", o).group(1))}
    assert c == ref(p["KW"], p["VW"], p["FB"], p["RAMB"], p["LB"], p["LOW"], p["NK"], p["STEPS"]), (c, o[-600:])
    return c
def test_reference_behaves_like_a_dictionary_with_compaction():
    import random
    for LB, LOW, nk in ((6, 4, 800), (5, 3, 600)):
        random.seed(LB); t = R.Tier4(18, 4, 4, LB, LOW); d = {}; keys = random.sample(range(1 << 18), nk)
        for step in range(30000):
            k = random.choice(keys)
            if random.random() < 0.4: v = random.getrandbits(18); t.put(k, v); d[k] = v
            else:
                f, v = t.get(k)
                if f: assert v == d[k]
                elif k in d: assert t.n["log_full"] > 0
        assert t.n["gc_rd"] > 0
def test_rtl_counters_equal_reference():
    c = check()
    assert c["demote_card"] > 0 and c["card_wr"] > 0 and c["promote_card"] > 0 and c["card_get"] > 0
def test_rtl_compaction_and_log_full_counters_equal_reference():
    """A log of 8 blocks that is too small for the live entries: compaction runs, entries are dropped and counted, values never come back wrong."""
    c = check(LB=3, LOW=2, NK=400, STEPS=1500, FB=3, RAMB=3)
    assert c["gc_rd"] > 0 and c["log_full"] > 0
