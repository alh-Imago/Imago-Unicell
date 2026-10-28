"""Tests for the three-level store hexn_tier_v1 (fast table + presence bitmap + SDRAM): the RTL against the SDRAM rule-checking model, and its counters equal to the bit-true Python reference."""
import os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tier_ref_v1 as R
SRCS = ["rtl/tb_hexn_tier_v1.v", "rtl/hexn_tier_v1.v", "rtl/hexn_sdram_v1.v", "rtl/sim/sdram_model_v1.v"]
def sim(**params):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog and vvp are required"
    out = os.path.join(tempfile.mkdtemp(), "tier.vvp")
    d = []
    for k, v in params.items(): d += ["-Ptb_hexn_tier_v1.%s=%d" % (k, v)]
    subprocess.run(["iverilog", "-g2012", "-o", out] + d + [os.path.join(ROOT, s) for s in SRCS], check=True, capture_output=True)
    return subprocess.run(["vvp", out], capture_output=True, text=True, timeout=1800).stdout
def ref(KW, FB, BMB, RAMB, P, N, M):
    t = R.Tier(KW, FB, BMB, RAMB, P)
    k = lambda i: R.hash32(i + 1) & 0xFFFFFF
    for i in range(N): t.put(k(i), R.hash32(i + 0x9999))
    for i in range(0, N, 7): t.put(k(i), R.hash32(i + 0x7777))
    for i in range(N): t.get(k(i))
    for i in range(M): t.get(R.hash32(i + 100000) & 0xFFFFFF)
    return t.n
def check(**params):
    p = dict(KW=24, FB=8, BMB=12, RAMB=10, P=8, N=600, M=300); p.update(params)
    o = sim(**params)
    assert "TIER TEST PASS" in o, o[-1500:]
    c = dict((a, int(b)) for a, b in re.findall(r"(\w+)=(\d+)", re.search(r"COUNTERS (.*)", o).group(1)))
    assert c == ref(p["KW"], p["FB"], p["BMB"], p["RAMB"], p["P"], p["N"], p["M"]), (c, o[-800:])
    return c
def test_default_no_overflow_and_counters_match():
    c = check(RAMB=11, P=16)
    assert c["overflow"] == 0 and c["sd_put"] > 100 and c["skip"] > 0
def test_small_sdram_overflow_counters_match():
    c = check(RAMB=9, P=4)
    assert c["overflow"] > 0
def test_bitmap_saves_sdram_reads():
    """With a big bitmap most never-seen keys never touch the SDRAM; with a tiny bitmap they all do."""
    big = check(RAMB=11, P=16, BMB=14); small = check(RAMB=11, P=16, BMB=4)
    assert big["skip"] > small["skip"] and big["sd_rd"] < small["sd_rd"]
