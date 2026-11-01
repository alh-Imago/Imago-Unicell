"""tests/vm/test_hexn_chain_model_v1.py -- the C++ CHAIN model the ESP32 sketch uses (ChainModel in hexn_unit_model.h: four units, bsrc operand source, bypass bit) against the Python chain model of the simulation test (one arith_block_v10 model per unit, bypassed units skipped), on random configs including all bsrc values and bypass, and the five programs of test_hexn_open13_v1. Requires g++."""
import os, random, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE)
from test_arith_block_v9_v1 import TT  # noqa: E402
from test_hexn_open13_v1 import chain_model, cfg, PROGS  # noqa: E402


def test_cpp_chain_model_equals_python_chain_model():
    assert shutil.which("g++"), "g++ is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexncm_"); exe = os.path.join(d, "c")
    c = subprocess.run(["g++", "-O1", "-o", exe, os.path.join(ROOT, "tests", "hexn_chain_model_host.cpp")], capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    rnd = random.Random(9); W = 18; M = (1 << W) - 1; lines = []; exp = []
    sets = list(PROGS.values())
    for k in range(400):
        if k % 8 == 0 and k >= 8 * len(sets):
            cfgs = [cfg(rnd.randrange(8), step=rnd.randrange(256), topo=rnd.choice(list(TT) + [0x123]), held=rnd.randrange(2), bsrc=rnd.randrange(4), byp=int(rnd.random() < 0.3)) for _ in range(4)]
        elif k % 8 == 0: cfgs = sets[k // 8]
        if k % 8 == 0:
            f = chain_model(cfgs)
            for u, cw in enumerate(cfgs): lines.append("c %d %x" % (u, cw))
        for _ in range(10):
            a = rnd.getrandbits(W) if rnd.random() < 0.8 else rnd.choice([0, 1, 2, 3, M, 1 << (W - 1)]); x = rnd.getrandbits(W) if rnd.random() < 0.5 else rnd.choice([0, 1, 2, 5, 17, 18, 19, 31])
            lines.append("w %x %x" % (a, x)); exp.append(f(a, x))
    out = subprocess.run([exe], input="\n".join(lines) + "\n", capture_output=True, text=True).stdout.split()
    assert [int(v) for v in out] == exp
