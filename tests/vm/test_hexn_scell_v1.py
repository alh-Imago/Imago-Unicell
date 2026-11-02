"""tests/vm/test_hexn_scell_v1.py -- the bit-serial multi-core hex cell (sub/verilog/hexn_scell_v1.v, UCC v2 prototype, 2 Nov 2026): add, subtract and xor on 16-bit words (20 random words each) and a route-only setting (output faces copy input faces, as a cross or a corner would) are right. The DELAY core is NOT function-tested. Requires iverilog."""
import os, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_scell_add_sub_logic_route():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnsc_")
    try:
        o = os.path.join(d, "o.vvp"); c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(ROOT, "tests", "hexn_scell_tb_v1.v"), os.path.join(ROOT, "sub", "verilog", "hexn_scell_v1.v")], capture_output=True, text=True); assert c.returncode == 0, c.stderr[:800]
        r = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=300).stdout
    finally: shutil.rmtree(d, ignore_errors=True)
    assert "add: 0 wrong" in r and "subtract: 0 wrong" in r and "logic xor: 0 wrong" in r and "route (copy a face to another face): 0 wrong" in r and "PASS" in r, r[-500:]
