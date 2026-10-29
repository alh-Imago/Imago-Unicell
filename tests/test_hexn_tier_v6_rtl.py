"""RTL tests for hexn_tier_v6 with the RAM level reached through hexn_ddr3_port_v1 and a stand-in for the Kintex card's UberDDR3 Wishbone port (read-modify-write of 576-bit lines, pipelined acks, random stalls): the counters, every card byte and the restore results must equal the same bit-true reference as v5 (tools/hexn_tier_ref_v5.py), whatever the DDR latency."""
import os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tier_ref_v5 as R
SRCS = ["rtl/tb_hexn_tier_v6.v", "rtl/hexn_tier_v6.v", "rtl/hexn_ddr3_port_v1.v", "rtl/sim/wb_ddr_model_v1.v", "rtl/hexn_sdram_v1.v", "fpga/verilog/sd_spi_v1.v", "fpga/verilog/sd_card_model_v1.v", ]
def h32(x):
    m = (x * 0x9E3779B1) & 0xFFFFFFFF; m ^= m >> 15; m = (m * 0x85EBCA6B) & 0xFFFFFFFF; return m ^ (m >> 13)
def model(KW, VW, FB, RAMB, LB, LOW, NK, STEPS, MODE, CORRUPT=-1):
    t = R.Tier5(KW, FB, RAMB, LB, LOW); MK = (1 << KW) - 1; MV = (1 << VW) - 1; o = {}
    for n in range(STEPS):
        r = h32(n + 0x1111); ki = (r >> 4) % NK; kk = ((ki + 1) * 0x2545F491 & 0xFFFFFFFF) & MK
        if ((r >> 20) % 10) < 4: t.put(kk, h32(n + 0x5151) & MV)
        else: t.get(kk)
    if MODE == 0: t.flush()
    elif MODE == 1: assert t.save() >= 0
    if CORRUPT >= 0:
        raw = bytearray(t.card.get(CORRUPT, bytes(512))); raw[100] ^= 0xFF; t.card[CORRUPT] = bytes(raw)
    o["c1"] = [t.n[k] for k in R.NAMES]; o["b1"] = dict(t.card); o["n1"] = dict(t.n)
    if MODE >= 1:
        t.power_loss(); t.n = {k: 0 for k in R.NAMES}; t.restore(); o["c2"] = [t.n[k] for k in R.NAMES]; o["r"] = []
        for i in range(NK):
            f, v = t.get(((i + 1) * 0x2545F491 & 0xFFFFFFFF) & MK); o["r"].append((i, int(f), v if f else 0))
        o["c3"] = [t.n[k] for k in R.NAMES]; o["b2"] = dict(t.card); o["n3"] = dict(t.n); o["n2"] = {k: o["c2"][i] for i, k in enumerate(R.NAMES)}
    return o
def sim(**params):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog and vvp are required"
    out = os.path.join(tempfile.mkdtemp(), "t6.vvp")
    d = ["-Ptb_hexn_tier_v6.%s=%d" % (k, v) for k, v in params.items()]
    subprocess.run(["iverilog", "-g2012", "-o", out] + d + [os.path.join(ROOT, s) for s in SRCS], check=True, capture_output=True)
    return subprocess.run(["vvp", out], capture_output=True, text=True, timeout=3000).stdout
def check(**params):
    p = dict(KW=12, VW=12, FB=4, RAMB=4, LB=5, LOW=3, NK=120, STEPS=400, MODE=1, CORRUPT=-1, LAT=9, JIT=3, STALLP=4); p.update(params)
    o = sim(**p); assert "TIER6 TEST PASS" in o, o[-1500:]
    m = model(p["KW"], p["VW"], p["FB"], p["RAMB"], p["LB"], p["LOW"], p["NK"], p["STEPS"], p["MODE"], p["CORRUPT"])
    cnt = lambda tag: [int(x) for x in re.search(tag + r" ([\d ]+)", o).group(1).split()]
    blk = lambda tag: {int(a): bytes.fromhex(b) for a, b in re.findall(tag + r" (\d+) ([0-9a-f]+)", o)}
    def same(hw, md):
        for pos in range(1 << p["LB"]):
            assert hw.get(pos, bytes(512)) == md.get(pos, bytes(512)), ("card block differs", pos)
    assert cnt("COUNTERS1") == m["c1"], list(zip(R.NAMES, cnt("COUNTERS1"), m["c1"])); same(blk("BLK1"), m["b1"])
    if p["MODE"] >= 1:
        assert cnt("COUNTERS2") == m["c2"], list(zip(R.NAMES, cnt("COUNTERS2"), m["c2"]))
        assert [(int(a), int(b), int(c)) for a, b, c in re.findall(r"^R (\d+) (\d+) (\d+)$", o, re.M)] == m["r"]
        assert cnt("COUNTERS3") == m["c3"]; same(blk("BLK2"), m["b2"])
    return m
def test_flush_matches_reference_byte_for_byte():
    m = check(MODE=0)
    assert m["n1"]["tomb_wr"] > 0 and m["n1"]["card_wr"] > 0 and m["n1"]["promote_card"] > 0
def test_save_power_loss_restore_matches_reference():
    m = check(MODE=1)
    assert m["n2"]["replay_live"] > 0 and m["n2"]["scan_rd"] >= 32 and m["n1"]["drain_fast"] > 0 and m["n1"]["drain_sdram"] > 0
def test_crash_without_save_matches_reference():
    m = check(MODE=2)
    assert m["n2"]["replay_live"] > 0 and m["n2"]["replay_tomb"] > 0
def test_compaction_log_full_and_tombstones_match_reference():
    m = check(MODE=1, LB=3, LOW=3, NK=400, STEPS=1500, FB=3, RAMB=3)
    assert m["n1"]["gc_rd"] > 0 and m["n1"]["tomb_dropped"] > 0 and m["n1"]["log_full"] > 0
def test_damaged_block_is_counted_and_skipped_like_the_reference():
    m = check(MODE=2, LB=5, LOW=4, NK=200, STEPS=1500, FB=3, RAMB=3, CORRUPT=7)
    assert m["n2"]["bad_blocks"] == 1

def test_slow_ddr_with_many_stalls_gives_the_same_counters():
    m = check(MODE=1, LAT=30, JIT=3, STALLP=10)
    assert m["n1"]["promote_card"] > 0
