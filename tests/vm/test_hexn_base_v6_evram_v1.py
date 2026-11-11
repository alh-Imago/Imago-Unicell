"""tests/vm/test_hexn_base_v6_evram_v1.py - the ON-CHIP EVENT RAM replayed into the speech chain (sub/verilog/hexn_base_ctl_v6.v, tools/hexn_kxbase_v6.py) in iverilog through the JTAG byte port (11 Nov 2026). Simulation only.
The bytes are made by the card's host tool (tools/hexn_chain_host_v2.py).
 1. RANDOM chain settings and recordings: stored with 'w', replayed with 'g', read with 'v': every window result equals the Python model (tools/hexn_chain_hw_v1.py); the 'u' queue stays empty during a replay; the same
    recordings then fed the v5 way ('k' start, 'e', 'u') give the same results (v5 commands unchanged); a second 'g' of a part of the RAM starts the result RAM again at word 0.
 2. THE KIT'S REAL DATA: the trained chain, all 300 recordings in the event RAM (26,677 bytes), one replay: 1,500 results, 262 right after window 3. The clock count of the replay is checked against the count worked out from the
    stream (events + fixed costs per window end and per start), so the speed figure the card will report is understood.
Long loads are sent with bytes 6 clocks apart instead of the bridge's 128 to keep the run short. Needs iverilog: FAILS (does not skip) without it."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, HERE)
import pytest
import hexn_bytecard_sim_v2 as B
import hexn_chain_hw_v1 as M
import hexn_chain_host_v1 as C
import hexn_chain_host_v2 as C2
from test_hexn_speech_chain_v1 import make_params, NWIN, STEPS, NL
from test_hexn_base_v5_chain_v1 import config_cmds
RD = os.path.join(ROOT, "docs", "hex-n", "data", "hexrefs"); KIT = os.path.join(ROOT, "fpga", "ypcb", "hexn_speech", "data")


@pytest.fixture(scope="module")
def src():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required"
    d = tempfile.mkdtemp(prefix="kxbase6_")
    assert os.system("HEXN_DA=4 HEXN_RA=3 HEXN_RMARGIN=2 python3 %s sim %s %s > /dev/null" % (os.path.join(ROOT, "tools", "hexn_kxbase_v6.py"), os.path.join(RD, "hex5.json"), d)) == 0
    yield os.path.join(d, "src"); shutil.rmtree(d, ignore_errors=True)


def words_of(b): return [b[4 * i:4 * i + 4] for i in range(len(b) // 4)]


def tup(r): return (r["win"], r["cls"], r["pred"], r["gap"], r["stop"])


def test_random_recordings_from_the_event_ram(src):
    P, r = make_params(23); evs = []
    for n in (0, 9, 30, 14, 45, 3): evs.append([(r.randrange(NWIN * STEPS), r.randrange(NL)) for _ in range(n)])
    recs = [[[(st % STEPS) * NL + ln for st, ln in sorted(e for e in ev if e[0] // STEPS == w)] for w in range(NWIN)] for ev in evs]
    want = [(w, q["cls"], q["pred"], q["gap"], q["stop"]) for ev in evs for w, q in enumerate(M.run_recording(P, ev))]
    img = C2.ram_image(recs); cfg = config_cmds(P); part = C2.ram_image(recs[:1]); tail = C2.ram_image(recs[4:])
    cmds = [("rawgap", b"".join(cfg), len(cfg), 6, 2000)]
    cmds += [("rawgap", c, 1, 6, 300) for c in C2.wcmds(img, 0, 100)]                                # several 'w' commands
    cmds += [("raw", C2.gcmd(0, len(img)), 7, 6000), ("raw", b"v\x00\x00" + bytes([len(want)]), 4 * len(want), 2000), ("raw", b"u", 6)]
    cmds += [("raw", C2.gcmd(len(img) - len(tail), len(tail)), 7, 3000), ("raw", b"v\x00\x00" + bytes([2 * NWIN]), 8 * NWIN, 1000)]      # the last two recordings only
    for rec in recs[:2]:                                                                             # the v5 way still works
        cmds.append(("raw", C.START, 1))
        for w in rec: cmds.append(("raw", C.ecmd(w), 1, 3000))
        cmds += [("raw", b"u", 6)] * NWIN
    res = B.ByteSim(src).run(cmds); n = 1 + len(C2.wcmds(img, 0, 100))
    assert res[0] == b"K" * len(cfg) and all(x == b"K" for x in res[1:n])
    g = C2.greply(res[n]); assert g["status"] == "K" and g["results"] == len(want)
    assert [tup(C2.word_result(w)) for w in words_of(res[n + 1])] == want
    assert res[n + 2] == bytes(6)                                                                    # nothing went to the 'u' queue
    g2 = C2.greply(res[n + 3]); assert g2["status"] == "K" and g2["results"] == 2 * NWIN
    assert [tup(C2.word_result(w)) for w in words_of(res[n + 4])] == want[4 * NWIN:]
    got = [tup(C.decode(x)) for x in res[n + 5:] if len(x) == 6]; assert got == want[:2 * NWIN]
    assert len({w[1] for w in want}) > 3 and len({w[2] for w in want}) > 2


def test_kit_from_the_event_ram(src):
    cfg = C.config_cmds(KIT); recs = C.recordings(os.path.join(KIT, "prog.hex")); lab = C.hexwords(os.path.join(KIT, "lab.hex")); img = C2.ram_image(recs)
    assert len(img) == 26677 and len(recs) == 300
    cmds = [("rawgap", b"".join(cfg), len(cfg), 6, 2000)] + [("rawgap", c, 1, 6, 300) for c in C2.wcmds(img)]
    cmds.append(("raw", C2.gcmd(0, len(img)), 7, 200000))
    vc = C2.vcmds(1500); cmds += [("raw", c, 4 * k, 6000) for c, k in vc]
    res = B.ByteSim(src).run(cmds); n = 1 + len(C2.wcmds(img))
    assert res[0] == b"K" * len(cfg) and all(x == b"K" for x in res[1:n])
    g = C2.greply(res[n]); assert g["status"] == "K" and g["results"] == 1500
    words = [w for x in res[n + 1:] for w in words_of(x)]; assert len(words) == 1500
    assert C2.score(words, lab) == 262
    nev = sum(len(w) for r in recs for w in r); print("replay clocks", g["clocks"], "events", nev)
    assert nev == 24877 and nev + 1500 * 40 < g["clocks"] < nev + 1500 * 60 + 300 * 6                # one clock per event, about 50 per window end
