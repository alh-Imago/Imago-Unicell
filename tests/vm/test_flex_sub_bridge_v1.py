"""tests/vm/test_flex_sub_bridge_v1.py -- ledger #1112: the held word at a sub block's measure point as the interface to the handshake (flex) cells.

Chain: flex ram (source) -> flex_to_sub_v1 -> three SUB cells (add 1000, relay, add 234) -> sub_to_flex_v1 (catch + hold) -> flex ram (sink). Checked: every word comes out exactly once, in order, equal to
x + 1234, with and without a sink that stalls at random (the held word waits; the sub block is not given a second word); the measured period and latency; the negative control (admit a word
while one is still held: words are lost). Needs iverilog (fails loudly without it, #965)."""
import os
import shutil
import subprocess
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
V = os.path.join(ROOT, "sub", "verilog")
SRCS = ["tb_flex_sub_bridge_v1.v", "flex_sub_bridge_v1.v", "ram_cell_v4sa.v", "ram_cell_v4s.v", "adder_cell_v4s.v"]
EXTRA = [os.path.join(ROOT, "fpga", "verilog", "adder_v1.v")]


def sim(n, stall, bridge=None):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required (see current/START.md)"
    d = tempfile.mkdtemp()
    files = [os.path.join(V, f) for f in SRCS] + EXTRA
    if bridge:
        files[1] = bridge
    c = subprocess.run(["iverilog", "-g2012", f"-DN={n}", f"-DSTALL={stall}", "-o", os.path.join(d, "t")] + files, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[-500:]
    out = subprocess.run(["vvp", os.path.join(d, "t")], capture_output=True, text=True, timeout=300).stdout
    rows = [l.split() for l in out.splitlines() if l[:2] in ("I ", "O ")]
    return ([(int(r[2]), int(r[3])) for r in rows if r[0] == "I"], [(int(r[2]), int(r[3])) for r in rows if r[0] == "O"], out)


def test_every_word_arrives_once_in_order_and_equals_the_math():
    i, o, out = sim(40, 0)
    assert [v for v, _ in i] == [100 + 7 * k for k in range(40)]
    assert [v for v, _ in o] == [100 + 7 * k + 1234 for k in range(40)] and "END" in out


def test_a_stalling_sink_changes_nothing_but_time():
    i, o, out = sim(40, 1)
    assert [v for v, _ in o] == [100 + 7 * k + 1234 for k in range(40)] and "END" in out
    assert o[-1][1] > sim(40, 0)[1][-1][1]                         # the stalls cost clocks, not words


def test_measured_period_and_latency():
    i, o, _ = sim(20, 0)
    periods = {i[k + 1][1] - i[k][1] for k in range(len(i) - 1)}
    assert periods == {6}                                         # one word in flight: 1 word per 6 clocks (bridge in 1 + 3 sub cells + hold 1 + sink 1)
    assert o[0][1] - i[0][1] == 6                                 # latency from the flex word taken to the sink holding it


def test_negative_control_without_the_one_in_flight_gate_words_are_lost():
    src = open(os.path.join(V, "flex_sub_bridge_v1.v")).read()
    assert "in_valid & ~busy & ~rst" in src
    bad = os.path.join(tempfile.mkdtemp(), "bridge_bad.v")
    open(bad, "w").write(src.replace("in_valid & ~busy & ~rst", "in_valid & ~rst"))
    _, o, out = sim(40, 1, bridge=bad)
    assert [v for v, _ in o] != [100 + 7 * k + 1234 for k in range(40)] or "TIMEOUT" in out


def sim_std(n, stall):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required (see current/START.md)"
    d = tempfile.mkdtemp()
    files = [os.path.join(V, "tb_std_sub_bridge_v1.v"), os.path.join(V, "flex_sub_bridge_v1.v"), os.path.join(ROOT, "fpga", "verilog", "ram_cell_v4c.v"),
             os.path.join(V, "ram_cell_v4s.v"), os.path.join(V, "adder_cell_v4s.v")] + EXTRA
    c = subprocess.run(["iverilog", "-g2012", f"-DN={n}", f"-DSTALL={stall}", "-o", os.path.join(d, "t")] + files, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[-500:]
    out = subprocess.run(["vvp", os.path.join(d, "t")], capture_output=True, text=True, timeout=300).stdout
    rows = [l.split() for l in out.splitlines() if l[:2] in ("I ", "O ")]
    return [(int(r[2]), int(r[3])) for r in rows if r[0] == "O"], out


def test_the_same_bridge_unchanged_works_between_standard_v4c_cells_and_sub_math():
    # ledger #1113 (Alan: the bridge is for sub <-> ANY family): std arrived/fire/ack cells at both ends, adapter wiring only
    for stall in (0, 1):
        o, out = sim_std(40, stall)
        assert [v for v, _ in o] == [100 + 7 * k + 1234 for k in range(40)] and "END" in out
