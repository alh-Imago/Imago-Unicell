"""tests/vm/test_hexn_unit_model_v1.py -- the C++ model the ESP32 sketch uses to know what the Hex-N unit should answer (hexn_unit_model.h, WIDTH 18) against the Python model of arith_block_v9 on random configs and words, all nine modes. Requires g++."""
import os, random, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE)
from test_arith_block_v9_v1 import Model, TT  # noqa: E402


def test_cpp_model_equals_python_model():
    assert shutil.which("g++"), "g++ is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnum_"); exe = os.path.join(d, "u")
    c = subprocess.run(["g++", "-O1", "-o", exe, os.path.join(ROOT, "tests", "hexn_unit_model_host.cpp")], capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    rnd = random.Random(3); W = 18; M = (1 << W) - 1; lines = []; exp = []; m = Model(W)
    for k in range(4000):
        if k % 25 == 0:
            cd = rnd.choice([0, 1, 2, 3, 4, 5, 6, 7, 7]) | (rnd.randrange(256) << 8) | (rnd.choice(list(TT) + [0x123]) << 16) | (rnd.randrange(2) << 26)
            lines.append("c %x" % cd); m.clock(1, cd, 0, 0, 0)
        a = rnd.getrandbits(W) if rnd.random() < 0.8 else rnd.choice([0, 1, 2, 3, M, 1 << (W - 1)]); b = rnd.getrandbits(W) if rnd.random() < 0.6 else rnd.choice([0, 1, 2, 5, 17, 18, 19, 31, M])
        lines.append("w %x %x" % (a, b)); m.clock(0, 0, a, b, 1); exp.append(m.out)
    out = subprocess.run([exe], input="\n".join(lines) + "\n", capture_output=True, text=True).stdout.split()
    assert [int(x) for x in out] == exp
