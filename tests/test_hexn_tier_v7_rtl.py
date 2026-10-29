"""RTL tests for hexn_tier_v7 (LUT table -> block RAM -> DDR3 bucket lines of 8 entries) against tools/hexn_tier_ref_v3.py (Tier3 with SPS = 8): the 17 counters and every DDR3 line must be equal, after the run and after a final read of every key. The DDR3 side is wb_ddr_model_v1 (pipelined Wishbone, random stalls)."""
import os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from hexn_tier_ref_v3 import Tier3
NAMES = ["fast_hit", "sdram_hit", "skip", "sd_get", "fp", "sd_blk_rd", "sd_blk_wr", "buf_hit", "promote_sdram", "promote_sd", "demote_sdram", "demote_sd", "sd_full", "found", "notfound", "put_update", "put_new"]
SRCS = ["rtl/tb_hexn_tier_v7.v", "rtl/hexn_tier_v7.v", "rtl/sim/wb_ddr_model_v1.v"]
def h32(x):
    m = (x * 0x9E3779B1) & 0xFFFFFFFF; m ^= m >> 15; m = (m * 0x85EBCA6B) & 0xFFFFFFFF; return m ^ (m >> 13)
def line_hex(t, sec):
    v = 0
    for i, e in enumerate(t.sec.get(sec, [None] * 8) if sec in t.written else [None] * 8):
        if e is not None: v |= (((e[1] << 32) | (1 << 31) | e[0]) << (64 * i))
    return "%0144x" % v
def model(KW, VW, FB, BMB, RAMB, SB, NK, STEPS):
    t = Tier3(KW=KW, FB=FB, BMB=BMB, RAMB=RAMB, SB=SB, SPS=8); MK = (1 << KW) - 1; MV = (1 << VW) - 1; o = {}
    for n in range(STEPS):
        r = h32(n + 0x1111); ki = (r >> 4) % NK; kk = ((ki + 1) * 0x2545F491 & 0xFFFFFFFF) & MK
        if ((r >> 20) % 10) < 4: t.put(kk, h32(n + 0x5151) & MV)
        else: t.get(kk)
    t.flush(); o["c1"] = [t.n[k] for k in NAMES]; o["l1"] = [line_hex(t, s) for s in range(1 << SB)]; o["n1"] = dict(t.n)
    o["r"] = []
    for i in range(NK):
        f, v = t.get(((i + 1) * 0x2545F491 & 0xFFFFFFFF) & MK); o["r"].append((i, int(f), v if f else 0))
    t.flush(); o["c2"] = [t.n[k] for k in NAMES]; o["l2"] = [line_hex(t, s) for s in range(1 << SB)]; o["n2"] = dict(t.n)
    return o
def sim(**params):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog and vvp are required"
    out = os.path.join(tempfile.mkdtemp(), "t7.vvp")
    d = ["-Ptb_hexn_tier_v7.%s=%d" % (k, v) for k, v in params.items()]
    subprocess.run(["iverilog", "-g2012", "-o", out] + d + [os.path.join(ROOT, s) for s in SRCS], check=True, capture_output=True)
    return subprocess.run(["vvp", out], capture_output=True, text=True, timeout=3000).stdout
def check(**params):
    p = dict(KW=12, VW=12, FB=4, BMB=8, RAMB=6, SB=5, NK=120, STEPS=400, LAT=9, JIT=3, STALLP=4); p.update(params)
    o = sim(**p); assert "TIER7 TEST PASS" in o, o[-1500:]
    m = model(p["KW"], p["VW"], p["FB"], p["BMB"], p["RAMB"], p["SB"], p["NK"], p["STEPS"])
    cnt = lambda tag: [int(x) for x in re.search(tag + r" ([\d ]+)", o).group(1).split()]
    lines = lambda tag: {int(a): b for a, b in re.findall(tag + r" (\d+) ([0-9a-f]+)", o)}
    assert cnt("COUNTERS1") == m["c1"], list(zip(NAMES, cnt("COUNTERS1"), m["c1"]))
    hw = lines("LINES1"); assert [hw[i] for i in range(1 << p["SB"])] == m["l1"], [i for i in range(1 << p["SB"]) if hw[i] != m["l1"][i]]
    assert [(int(a), int(b), int(c)) for a, b, c in re.findall(r"^R (\d+) (\d+) (\d+)$", o, re.M)] == m["r"]
    assert cnt("COUNTERS2") == m["c2"], list(zip(NAMES, cnt("COUNTERS2"), m["c2"]))
    hw = lines("LINES2"); assert [hw[i] for i in range(1 << p["SB"])] == m["l2"]
    return m
def test_counters_and_lines_match_reference():
    m = check()
    n = m["n2"]; assert n["demote_sdram"] > 0 and n["demote_sd"] > 0 and n["promote_sd"] > 0 and n["promote_sdram"] > 0 and n["sd_blk_wr"] > 0 and n["sd_blk_rd"] > 0 and n["skip"] > 0
def test_full_lines_drop_entries_like_the_reference():
    m = check(NK=300, STEPS=1500, FB=3, RAMB=3, SB=3, KW=14, BMB=6)
    assert m["n2"]["sd_full"] > 0
def test_slow_ddr_with_many_stalls_gives_the_same_result():
    check(LAT=30, JIT=3, STALLP=10)
