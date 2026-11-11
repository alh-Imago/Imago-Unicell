"""tests/vm/test_hexn_base_v5_chain_v1.py - the speech chain behind the Kintex BASE controller (sub/verilog/hexn_base_ctl_v5.v, tools/hexn_kxbase_v5.py) in iverilog through the JTAG byte port (11 Nov 2026). Simulation only.
The bytes are made by the card's own host tool (tools/hexn_chain_host_v1.py), so the tool's formats are tested with the design.
 1. RANDOM chain parameters written with 'k', recordings fed with 'k' sel 7 (start) and 'e' (events + window end) at the bridge's byte spacing (128 clocks): every 'u' result must equal the exact-arithmetic Python model
    tools/hexn_chain_hw_v1.py (window, class, prediction, gap, stop flag). 'u' with nothing waiting returns n = 0 and zeros; a v4 command ('N') still answers as before.
 2. THE KIT'S REAL DATA (fpga/ypcb/hexn_speech/data: the trained chain and the 300 test recordings): settings and recordings sent from the host side, decision after window 3, compared with the labels: 262 right,
    the figure of the Python reference, of iverilog with the data baked in, and of the card (direction doc section 75).
To keep the run short the long loads are sent with bytes closer together than the bridge does (settings 6 clocks apart, events 16); the bridge's own spacing is used for the recordings of test 1.
Needs iverilog: FAILS (does not skip) without it."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, HERE)
import pytest
import hexn_bytecard_sim_v2 as B
import hexn_chain_hw_v1 as M
import hexn_chain_host_v1 as C
from test_hexn_speech_chain_v1 import make_params, NWIN, STEPS, NL
RD = os.path.join(ROOT, "docs", "hex-n", "data", "hexrefs"); KIT = os.path.join(ROOT, "fpga", "ypcb", "hexn_speech", "data")


def b8(v): return int(v) & 0xFF


def config_cmds(P):
    out = []
    for w in range(NWIN):
        for i, t in enumerate(P.wrom[w]):
            word = 0
            for c, x in enumerate(t): word |= (1 if x == 1 else 3 if x == -1 else 0) << (2 * c)
            out.append(C.kcmd(0, w * len(P.wrom[w]) + i, word))
    for w in range(NWIN): out.append(C.kcmd(1, w, sum(b8(P.thr[w][c]) << (8 * c) for c in range(M.NC))))
    for w in range(NWIN):
        for prev in range(M.A):
            for cls in range(M.A): out.append(C.kcmd(2, (w * M.A + prev) * M.A + cls, sum(b8(P.lp[c][w][prev][cls]) << (8 * c) for c in range(M.NC))))
    for i, x in enumerate(P.code + [P.gap]): out.append(C.kcmd(3, i, x & 0xFFFF))
    return out


@pytest.fixture(scope="module")
def src():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required"
    d = tempfile.mkdtemp(prefix="kxbase5_")
    assert os.system("HEXN_DA=4 HEXN_RA=3 HEXN_RMARGIN=2 python3 %s sim %s %s > /dev/null" % (os.path.join(ROOT, "tools", "hexn_kxbase_v5.py"), os.path.join(RD, "hex5.json"), d)) == 0
    yield os.path.join(d, "src"); shutil.rmtree(d, ignore_errors=True)


def test_random_chain_through_base_controller(src):
    P, r = make_params(11); recs = []
    for n in (0, 6, 25, 12, 40): recs.append([(r.randrange(NWIN * STEPS), r.randrange(NL)) for _ in range(n)])
    cfg = config_cmds(P); assert len(cfg) == 1576
    cmds = [("rawgap", b"".join(cfg), len(cfg), 6, 2000)]; want = []
    for ev in recs:
        cmds.append(("raw", C.START, 1))
        for w in range(NWIN): cmds.append(("raw", C.ecmd([(st % STEPS) * NL + ln for st, ln in sorted(e for e in ev if e[0] // STEPS == w)]), 1, 3000))
        cmds += [("raw", b"u", 6)] * NWIN
        want += [(w, q["cls"], q["pred"], q["gap"], q["stop"]) for w, q in enumerate(M.run_recording(P, ev))]
    cmds += [("raw", b"u", 6), ("raw", b"N", 6)]
    res = B.ByteSim(src).run(cmds)
    assert res[0] == b"K" * len(cfg)
    got = [C.decode(x) for x in res[1:-2] if len(x) == 6]
    assert len(got) == len(want) and all(g is not None and g["lost"] == 0 for g in got)
    assert [(g["win"], g["cls"], g["pred"], g["gap"], g["stop"]) for g in got] == want
    assert len({w[1] for w in want}) > 3 and len({w[2] for w in want}) > 2                  # the random case exercises several classes and predictions
    assert all(x == b"K" for x in res[1:-2] if len(x) == 1)
    assert C.decode(res[-2]) is None and res[-2] == bytes(6)                                # nothing waiting
    assert res[-1] == bytes([0x45, 0x53, 0x41, 0x42, 1, 4])                                 # 'N': id 0x42415345 little endian, 1 array, 4 library slots


def test_kit_recordings_fed_from_the_host_side(src):
    cfg = C.config_cmds(KIT); recs = C.recordings(os.path.join(KIT, "prog.hex")); lab = C.hexwords(os.path.join(KIT, "lab.hex"))
    assert len(cfg) == 1576 and len(recs) == 300 == len(lab)
    cmds = [("rawgap", b"".join(cfg), len(cfg), 6, 2000)]
    for r in recs:
        cmds.append(("rawgap", C.START + b"".join(C.ecmd(w) for w in r), 1 + NWIN, 16, 200))      # as the host tool sends a recording: start and the five windows in one write
        cmds.append(("rawgap", b"u" * NWIN, 6 * NWIN, 40, 100))                                         # a 6-byte reply takes about 18 clocks here; the bridge leaves 128
    res = B.ByteSim(src).run(cmds)
    assert res[0] == b"K" * len(cfg)
    ok = 0
    for i in range(300):
        assert res[1 + 2 * i] == b"K" * (1 + NWIN)
        rr = [C.decode(res[2 + 2 * i][6 * k:6 * k + 6]) for k in range(NWIN)]
        assert all(x is not None and x["lost"] == 0 for x in rr) and [x["win"] for x in rr] == list(range(NWIN))
        ok += (C.decide(rr, False)[0] == lab[i])
    assert ok == 262
