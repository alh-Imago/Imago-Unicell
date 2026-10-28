"""Board test top hexn_tang_tiertest_v1 in simulation: its serial report must show zero errors and counters equal to the bit-true Python reference run over the same arithmetic key/value sequence. parse_report/expected are also what to use on a real serial capture from the board."""
import os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tier_ref_v2 as R
def key(i, KW): return ((i + 1) * 0x2545F491 & 0xFFFFFFFF) & ((1 << KW) - 1)
def vof(i, VW): return (((i + 1) * 0x85EBCA6B & 0xFFFFFFFF) >> 7) & ((1 << VW) - 1)
def uof(i, VW): return vof(i, VW) ^ (0x2AAAA & ((1 << VW) - 1))
def expected(KW, VW, FB, BMB, RAMB, P, N, M):
    t = R.Tier(KW, FB, BMB, RAMB, P)
    for i in range(N): t.put(key(i, KW), vof(i, VW))
    for i in range(0, N, 7): t.put(key(i, KW), uof(i, VW))
    for i in range(N): t.get(key(i, KW))
    for i in range(M): t.get(key(i + N, KW))
    n = t.n; return [n["fast_put"], n["sd_put"], n["overflow"], n["fast_hit"], n["skip"], n["sd_get"], n["fp"], n["sd_rd"], n["sd_wr"], n["found"]]
def parse_report(text):
    """Text from the serial port (or the simulation) -> dict {0..15: int} from the lines 'R<hex>=<8 hex>'."""
    return {int(a, 16): int(b, 16) for a, b in re.findall(r"R([0-9A-F])=([0-9A-F]{8})", text)}
def sim(**params):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog and vvp are required"
    out = os.path.join(tempfile.mkdtemp(), "tt.vvp")
    d = ["-Ptb_hexn_tang_tiertest_v1.%s=%d" % (k, v) for k, v in params.items()]
    srcs = ["rtl/tb_hexn_tang_tiertest_v1.v", "rtl/hexn_tang_tiertest_v1.v", "rtl/hexn_tier_v2.v", "rtl/hexn_sdram_v1.v", "rtl/hexn_uart_v1.v", "rtl/sim/sdram_model_v1.v", "rtl/sim/rpll_model.v"]
    subprocess.run(["iverilog", "-g2012", "-o", out] + d + [os.path.join(ROOT, s) for s in srcs], check=True, capture_output=True)
    return subprocess.run(["vvp", out], capture_output=True, text=True, timeout=3000).stdout
def run(**kw):
    p = dict(KW=18, VW=18, FB=8, BMB=12, RAMB=12, P=8, N=300, M=150); p.update(kw)
    o = sim(**kw)
    assert "TIERTEST SIM DONE" in o, o[-1500:]
    r = parse_report(re.search(r"REPORT(.*)", o).group(1))
    assert len(r) == 16, r
    assert r[0] == r[1] == r[3] == 0, ("errors", r)
    got = [r[k] for k in range(6, 16)]
    assert got == expected(p["KW"], p["VW"], p["FB"], p["BMB"], p["RAMB"], p["P"], p["N"], p["M"]), (got, o[-600:])
    return r, o
def test_report_clean_and_counters_equal_reference():
    r, o = run()
    assert r[2] == 0 and r[8] == 0   # no known key lost, no overflow at these sizes
    assert "leds 000000" in o   # outputs are inverted: all six LEDs lit
def test_report_with_tiny_sdram_counts_overflow_not_wrong_values():
    """A small SDRAM region drops some puts: they must show as 'lost' (R2) equal to overflow-related misses, never as wrong values (R1) or false finds (R3)."""
    p = dict(KW=18, VW=18, FB=8, BMB=12, RAMB=9, P=2, N=300, M=150)
    o = sim(RAMB=6, P=2); r = parse_report(re.search(r"REPORT(.*)", o).group(1))
    assert r[1] == 0 and r[3] == 0 and r[8] > 0 and r[2] > 0 and r[2] <= r[8], r
    assert [r[k] for k in range(6, 16)] == expected(18, 18, 8, 12, 6, 2, 300, 150)
