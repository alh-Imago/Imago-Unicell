"""Ledger #1160: the flex <-> standard/carrier handshake adapters (sub/verilog/flex_std_adapter_v1.v) with REAL cells at both ends: std ram (v4c = carrier core, v4 = standalone shell) -> std_to_flex_v1 -> flex ram -> flex_to_std_v1 -> std ram.
40 words exactly once, in order, with and without random stalls, for both std variants; negative control: the std ack held as a LEVEL (instead of a one-clock pulse) deadlocks. Needs iverilog (fails loudly without it, #965)."""
import os, shutil, subprocess, tempfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
V, F = os.path.join(ROOT, "sub", "verilog"), os.path.join(ROOT, "fpga", "verilog")
ADDONS = [os.path.join(F, f) for f in ("nibble_mask_addon_v1.v", "shift_lane_addon_v1.v", "invert_addon_v1.v")]


def sim(ram, stall, adapter=None, n=40):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required (see current/START.md)"
    d = tempfile.mkdtemp()
    files = [os.path.join(V, "tb_flex_std_adapter_v1.v"), adapter or os.path.join(V, "flex_std_adapter_v1.v"), os.path.join(F, ram + ".v"), os.path.join(V, "ram_cell_v4sa.v")] + ADDONS
    c = subprocess.run(["iverilog", "-g2012", f"-DN={n}", f"-DSTALL={stall}", f"-DSTDRAM={ram}", "-o", os.path.join(d, "t")] + files, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[-600:]
    out = subprocess.run(["vvp", os.path.join(d, "t")], capture_output=True, text=True, timeout=300).stdout
    rows = [l.split() for l in out.splitlines() if l[:2] in ("I ", "O ")]
    return [int(r[2]) for r in rows if r[0] == "I"], [int(r[2]) for r in rows if r[0] == "O"], out


def test_words_cross_both_ways_exactly_once_in_order_for_std_and_carrier_cells():
    want = [100 + 7 * k for k in range(40)]
    for ram in ("ram_cell_v4c", "ram_cell_v4"):
        for stall in (0, 1):
            i, o, out = sim(ram, stall)
            assert i == want and o == want and "END" in out, (ram, stall, out[-200:])


def test_negative_control_a_held_level_ack_deadlocks():
    src = open(os.path.join(V, "flex_std_adapter_v1.v")).read()
    assert "assign std_ack    = std_fire & flex_ack;" in src
    bad = os.path.join(tempfile.mkdtemp(), "bad.v")
    open(bad, "w").write(src.replace("assign std_ack    = std_fire & flex_ack;", "assign std_ack    = flex_ack;"))
    i, o, out = sim("ram_cell_v4c", 0, adapter=bad)
    assert o != [100 + 7 * k for k in range(40)] and "TIMEOUT" in out
