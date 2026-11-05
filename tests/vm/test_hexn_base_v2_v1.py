"""tests/vm/test_hexn_base_v2_v1.py - the Kintex BASE with the RESULTS RAM (tools/hexn_kxbase_v2.py, sub/verilog/hexn_base_ctl_v2.v + hexn_frame_v7.v) in iverilog through the JTAG byte port (5 Nov 2026). Simulation only: not built or run on a card.
A small results RAM is built (RA = 3: 8 records, margin 2 = FULL at 6 records) so that stop-and-flag can be reached quickly.
Checks: records of a run (array, row, tick, word, index) equal the array's own log; stop and flag (FULL, refusal of 'G' with 'F', lost 0 with the margin, clear and run again); judge results are recorded next to the array words; v1 commands still answer."""
import json, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_bytecard_sim_v1 as B
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
RD = os.path.join(ROOT, "docs", "hex-n", "data", "hexrefs")
J = lambda w: ("raw", b"J" + w.to_bytes(4, "little"), 1)
LOAD = lambda cls, addr, wt: (12 << 28) | (cls << 24) | (addr << 16) | (wt & 255)


def vec(n, k=0): return json.load(open(os.path.join(RD, "vectors", "kx_vec_%d.json" % n)))["tests"][k]


def build(refs):
    d = tempfile.mkdtemp(prefix="kxbase2_"); env = dict(os.environ, HEXN_RA="3", HEXN_RMARGIN="2")
    assert os.system("%s python3 %s sim %s %s > /dev/null" % (" ".join("%s=%s" % (k, env[k]) for k in ("HEXN_RA", "HEXN_RMARGIN")), os.path.join(ROOT, "tools", "hexn_kxbase_v2.py"), " ".join(os.path.join(RD, r) for r in refs), d)) == 0
    return d


def run_array(t):
    return [("W",), ("B", bytes.fromhex(t["chain_hex"]))] + [("D", r, w) for r, w in t["inputs"]] + [("G", t["mask"]), ("wait", 2000), ("L",)]


def recs(b):
    k = b[0]; assert len(b) == 1 + 8 * k
    return [dict(kind=b[1 + 8 * i] >> 7, array=(b[1 + 8 * i] >> 5) & 3, row=b[1 + 8 * i] & 7, tick=int.from_bytes(b[2 + 8 * i:4 + 8 * i], "little"), word=int.from_bytes(b[4 + 8 * i:8 + 8 * i], "little"), idx=b[8 + 8 * i]) for i in range(k)]


def status(b): return dict(count=b[0] | b[1] << 8, lost=b[2], full=b[3] & 1, armed=(b[3] >> 1) & 1, rp=b[4] | b[5] << 8, refused=b[6])


@pytest.fixture(scope="module")
def seven():
    d = build(["hex7_off2_mix.json"]); yield os.path.join(d, "src"); shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def one():
    d = build(["hex5.json"]); yield os.path.join(d, "src"); shutil.rmtree(d, ignore_errors=True)


def test_records_equal_the_arrays_own_log(seven):
    t = vec(7)
    cmds = [("raw", b"N", 6), ("raw", b"A\x00", 1), ("raw", b"Y", 7), ("raw", b"X\x03", 1)] + run_array(t)[:-2] + [("wait", 2000), ("raw", b"Y", 7), ("raw", b"V\x08", 1 + 8 * len(t["expected"]), 6000), ("raw", b"Y", 7), ("raw", b"V\x08", 1)]
    r = B.ByteSim(seven).run(cmds); n = len(t["expected"])
    assert r[0] == bytes([0x45, 0x53, 0x41, 0x42, 1, 4]) and r[1] == b"K"
    assert status(r[2])["count"] == 0 and status(r[2])["armed"] == 0 and r[3] == b"K"          # not armed before X: nothing recorded
    s = status(r[-4]); assert s["count"] == n and s["lost"] == 0 and s["full"] == 0 and s["armed"] == 1 and s["rp"] == 0
    got = recs(r[-3]); assert [(x["row"], x["word"], x["tick"]) for x in got] == [tuple(e) for e in t["expected"]]
    assert all(x["kind"] == 0 and x["array"] == 0 for x in got) and [x["idx"] for x in got] == list(range(n))
    s = status(r[-2]); assert s["rp"] == n and s["count"] == n and r[-1] == bytes([0])          # the read pointer moved; nothing more to read


def test_stop_and_flag_refuses_the_next_run_and_loses_nothing(seven):
    t = vec(7); n = len(t["expected"]); assert n == 4
    cmds = [("raw", b"A\x00", 1), ("raw", b"X\x03", 1)] + run_array(t)[:-2] + [("wait", 2000), ("raw", b"Y", 7)] + run_array(t)[:-2] + [("wait", 2000), ("raw", b"Y", 7),
            ("raw", b"G" + bytes([t["mask"]]), 1), ("raw", b"Y", 7), ("raw", b"V\x08", 1 + 64, 9000), ("raw", b"X\x03", 1), ("raw", b"Y", 7)] + run_array(t)[:-2] + [("wait", 2000), ("raw", b"Y", 7)]
    r = B.ByteSim(seven).run(cmds)
    ys = [x for x in r if isinstance(x, bytes) and len(x) == 7]; assert len(ys) == 5
    s1, s2, s3, s4, s5 = [status(y) for y in ys]
    assert s1["count"] == 4 and s1["full"] == 0                                                     # 4 of 8: below 8 - 2
    assert s2["count"] == 8 and s2["full"] == 1 and s2["lost"] == 0 and s2["refused"] == 0           # the second run fills it; the margin kept every word
    refused = [x for x in r if x == b"F"]; assert len(refused) == 1                                  # a third start is refused with 'F'
    assert s3["refused"] == 1 and s3["count"] == 8 and s3["full"] == 1
    v = [x for x in r if isinstance(x, bytes) and len(x) == 65][0]; got = recs(v); assert len(got) == 8 and [x["idx"] for x in got] == list(range(8))
    assert [(x["row"], x["word"], x["tick"]) for x in got[:4]] == [tuple(e) for e in t["expected"]] == [(x["row"], x["word"], x["tick"]) for x in got[4:]]
    assert s4["count"] == 0 and s4["full"] == 0 and s4["refused"] == 0 and s5["count"] == 4        # X clears; a new run is accepted


def test_judge_results_are_recorded_beside_the_words(one):
    t = vec(5)
    cmds = [("raw", b"A\x00", 1), ("raw", b"X\x03", 1), ("raw", b"M\x03", 1), J(LOAD(1, 10, 9)), J(LOAD(0, 75, 20))] + run_array(t)[:-2] + [("wait", 3000), ("raw", b"R", 6), ("raw", b"Y", 7), ("raw", b"V\x04", 17, 6000)]
    r = B.ByteSim(one).run(cmds)
    assert r[-3] == bytes([1, 0x14, 0, 9, 0, 0])                                                      # the judge's result, as v1
    assert status(r[-2])["count"] == 2
    got = recs(r[-1]); assert len(got) == 2
    w = [x for x in got if x["kind"] == 0][0]; j = [x for x in got if x["kind"] == 1][0]
    assert (w["row"], w["word"], w["tick"]) == tuple(t["expected"][0]) and j["word"] == 0x00090014 and j["tick"] == 0
