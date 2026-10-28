"""Tests for the 4-level tier hexn_tier_v3 (fast table / SDRAM / SD card with presence counters and a write-back sector buffer): the RTL against the SDRAM rule model and the behavioural SD card, and all 17 counters equal to the bit-true Python reference run over the same pseudo-random PUT/GET sequence."""
import os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tier_ref_v3 as R
SRCS = ["rtl/tb_hexn_tier_v3.v", "rtl/hexn_tier_v3.v", "rtl/hexn_sdram_v1.v", "fpga/verilog/sd_spi_v1.v", "fpga/verilog/sd_card_model_v1.v", "rtl/sim/sdram_model_v1.v"]
NAMES = "fast_hit sdram_hit skip sd_get fp sd_blk_rd sd_blk_wr buf_hit promote_sdram promote_sd demote_sdram demote_sd sd_full found notfound put_update put_new".split()
def h32(x):
    m = (x * 0x9E3779B1) & 0xFFFFFFFF; m ^= m >> 15; m = (m * 0x85EBCA6B) & 0xFFFFFFFF; return m ^ (m >> 13)
def ref(KW, VW, FB, BMB, RAMB, SB, NK, STEPS):
    t = R.Tier3(KW, FB, BMB, RAMB, SB); MK = (1 << KW) - 1; MV = (1 << VW) - 1
    for n in range(STEPS):
        r = h32(n + 0x1111); ki = (r >> 4) % NK; kk = ((ki + 1) * 0x2545F491 & 0xFFFFFFFF) & MK
        if ((r >> 20) % 10) < 4: t.put(kk, h32(n + 0x5151) & MV)
        else: t.get(kk)
    t.flush(); return t.n
def sim(**params):
    for pth in SRCS: assert os.path.exists(os.path.join(ROOT, pth)), pth
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog and vvp are required"
    out = os.path.join(tempfile.mkdtemp(), "tier3.vvp")
    d = ["-Ptb_hexn_tier_v3.%s=%d" % (k, v) for k, v in params.items()]
    subprocess.run(["iverilog", "-g2012", "-o", out] + d + [os.path.join(ROOT, s) for s in SRCS], check=True, capture_output=True)
    return subprocess.run(["vvp", out], capture_output=True, text=True, timeout=3000).stdout
def check(**params):
    p = dict(KW=18, VW=18, FB=5, BMB=10, RAMB=5, SB=3, NK=300, STEPS=1500); p.update(params)
    o = sim(**params)
    assert "TIER3 TEST PASS" in o, o[-1500:]
    c = {a: int(b) for a, b in re.findall(r"(\w+)=(\d+)", re.search(r"COUNTERS (.*)", o).group(1))}
    assert c == ref(p["KW"], p["VW"], p["FB"], p["BMB"], p["RAMB"], p["SB"], p["NK"], p["STEPS"]), (c, o[-600:])
    return c
def test_reference_behaves_like_a_dictionary_when_nothing_overflows():
    import random
    random.seed(5); t = R.Tier3(18, 5, 10, 5, 6); d = {}; keys = random.sample(range(1 << 18), 700)
    for step in range(6000):
        k = random.choice(keys)
        if random.random() < 0.4: v = random.getrandbits(18); t.put(k, v); d[k] = v
        else:
            f, v = t.get(k); assert (k in d) == f and (not f or v == d[k])
    assert t.n["sd_full"] == 0
def test_rtl_counters_equal_reference_small():
    c = check(STEPS=250, NK=120)
    assert c["demote_sd"] > 0 and c["sd_blk_wr"] > 0 and c["promote_sd"] > 0
def test_rtl_sector_overflow_counted_not_wrong_values():
    """One card sector only (SB=0 would be one; use SB=1): sectors fill, entries are dropped and counted, values never come back wrong."""
    c = check(STEPS=500, NK=400, SB=1, RAMB=3, FB=3)
    assert c["sd_full"] > 0
