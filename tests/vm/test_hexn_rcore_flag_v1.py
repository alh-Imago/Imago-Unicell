"""tests/vm/test_hexn_rcore_flag_v1.py -- routing cell with a flag lane (sub/verilog/hexn_rcore_flag_v1.v), 4 and 6 faces: 200 random chain loads x 3 random input pairs; the flag lane follows the data lane's select; index FACES..7 reads 0; a mutant that routes the flag with the NEXT output's select is caught. Requires iverilog."""
import os, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "sub", "verilog", "hexn_rcore_flag_v1.v"); TB = os.path.join(ROOT, "tests", "hexn_rcore_flag_tb.v")


def _run(faces, src):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="rcflag_")
    try:
        open(os.path.join(d, "dut.v"), "w").write(src); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-P", "tb.FACES=%d" % faces, "-o", o, TB, os.path.join(d, "dut.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1000]
        return subprocess.run(["vvp", o], capture_output=True, text=True, timeout=300).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_four_and_six_faces():
    src = open(V).read()
    for faces in (4, 6):
        res = _run(faces, src); assert "PASS" in res and "FAIL" not in res, (faces, res[-600:])


def test_mutant_flag_with_wrong_select_is_caught():
    src = open(V).read().replace("fo_f[j] <= fx[cfg[3 * j +: 3]];", "fo_f[j] <= fx[cfg[3 * ((j + 1) % FACES) +: 3]];")
    assert src != open(V).read()
    assert "FAIL" in _run(4, src)
