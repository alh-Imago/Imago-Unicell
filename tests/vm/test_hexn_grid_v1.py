"""tests/vm/test_hexn_grid_v1.py -- the 4 x 4 grid of look-up cells with six hex faces (sub/verilog/hexn_grid_v1.v, UCC v2 prototype, 2 Nov 2026): five cells loaded through the shell form a bit-serial 8-bit adder (two copy cells, a sum cell, a carry cell that keeps the carry in its own output, and a delay cell); 40 back-to-back words give the right 9-bit sums, including 255 + 1 and 255 + 255. Three mutants (wrong E neighbour, mirrored odd rows, state feedback removed) are caught. Requires iverilog."""
import os, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "sub", "verilog", "hexn_grid_v1.v"); TB = os.path.join(ROOT, "tests", "hexn_grid_tb_v1.v")


def run(mut=None):
    d = tempfile.mkdtemp(prefix="hexngrid_")
    try:
        src = open(SRC).read()
        if mut: a, b = mut; assert a in src, a; src = src.replace(a, b)
        open(os.path.join(d, "g.v"), "w").write(src)
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", os.path.join(d, "o.vvp"), TB, os.path.join(d, "g.v")], capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1000]
        return subprocess.run(["vvp", os.path.join(d, "o.vvp")], capture_output=True, text=True, timeout=600).stdout
    finally: shutil.rmtree(d, ignore_errors=True)


def test_bit_serial_adder_from_five_cells():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    r = run(); assert "0 wrong of 40" in r and "PASS" in r, r[-600:]


def test_mutants_caught():
    for m in [("iE  = vE  ? r * C + c + 1 : ME", "iE  = vE  ? r * C + c - 1 : ME"),
              ("ODD = r % 2", "ODD = 1 - r % 2"),
              ("wire [6:0] a = { o[ME],", "wire [6:0] a = { 1'b0,")]:
        r = run(m); assert "FAIL" in r and "PASS" not in r, (m[0], r[-300:])
