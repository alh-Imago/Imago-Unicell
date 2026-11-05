"""tests/vm/test_hexn_base_v1.py - the Kintex BASE (judge + arrays + program library, tools/hexn_kxbase_v1.py, sub/verilog/hexn_base_ctl_v1.v) in iverilog through the JTAG byte port (5 Nov 2026). Simulation only: not built or run on a card.
Checks: base info and selector; a program written into the library and loaded from it into an array gives the same word and tick as the host loading the chain itself; the judge scores words loaded by the host (LOAD / BIAS / SCORE); AFTER mode (the array's output word goes to the judge by itself, nibbles limited to bins 0..11); two arrays of different shape in one design."""
import json, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_bytecard_sim_v1 as B
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
RD = os.path.join(ROOT, "docs", "hex-n", "data", "hexrefs")
J = lambda w: ("raw", b"J" + w.to_bytes(4, "little"), 1)
LOAD = lambda cls, addr, wt: (12 << 28) | (cls << 24) | (addr << 16) | (wt & 255)
BIAS = lambda b: (13 << 28) | (b & 0xffff)


def vec(n): return json.load(open(os.path.join(RD, "vectors", "kx_vec_%d.json" % n)))["tests"][0]


def build(refs):
    d = tempfile.mkdtemp(prefix="kxbase_"); os.system("python3 %s sim %s %s > /dev/null" % (os.path.join(ROOT, "tools", "hexn_kxbase_v1.py"), " ".join(os.path.join(RD, r) for r in refs), d))
    return d


def run_array(t, via_library, slot=0):
    chain = bytes.fromhex(t["chain_hex"]); cmds = [("W",)]
    if via_library: cmds += [("raw", b"Q" + bytes([slot]), 1, 6000)]
    else: cmds += [("B", chain)]
    return cmds + [("D", r, w) for r, w in t["inputs"]] + [("G", t["mask"]), ("wait", 2000), ("L",)]


@pytest.fixture(scope="module")
def one():
    d = build(["hex5.json"]); yield os.path.join(d, "src"); shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def two():
    d = build(["hex5.json", "hex6.json"]); yield os.path.join(d, "src"); shutil.rmtree(d, ignore_errors=True)


def test_info_library_and_judge(one):
    t = vec(5); chain = bytes.fromhex(t["chain_hex"])
    cmds = [("raw", b"N", 6), ("raw", b"A\x00", 1), ("raw", b"P\x00" + len(chain).to_bytes(2, "big") + chain, 1, 3000)] + run_array(t, True) + \
           [J(LOAD(1, 3, 5)), J(LOAD(0, 18, 7)), J(3 | (2 << 4)), ("raw", b"R", 6), ("raw", b"R", 6), J(BIAS(3)), J(3 | (2 << 4)), ("raw", b"R", 6)]
    r = B.ByteSim(one).run(cmds)
    assert r[0] == bytes([0x45, 0x53, 0x41, 0x42, 1, 4]) and r[1] == b"K" and r[2] == b"K"
    assert r[3] == b"K" and r[4] == b"K" and r[-9] and [list(e) for e in r[-9]] == t["expected"]           # library load gives the same word and tick as the host's own chain
    assert r[-5] == bytes([1, 7, 0, 5, 0, 0]) and r[-4] == bytes(6) and r[-1] == bytes([1, 7, 0, 5, 0x80, 0])        # s0 7, s1 5, no pred; empty; with bias 3: pred 1


def test_after_mode_scores_the_array_output_by_itself(one):
    t = vec(5)
    cmds = [("raw", b"A\x00", 1), ("raw", b"M\x03", 1), J(LOAD(1, 10, 9)), J(LOAD(0, 75, 20))] + run_array(t, False) + [("raw", b"R", 6)]
    r = B.ByteSim(one).run(cmds)
    word = t["expected"][0][1]; assert word == 0x6bdc696a                       # nibbles A 6 9 6 C D B 6 -> bins 10 6 9 6 11 11 11 6
    assert r[-2] and r[-1] == bytes([1, 0x14, 0, 9, 0, 0])                       # s1 = W1[sensor 0, bin 10] = 9, s0 = W0[sensor 4, bin 11] = 20


def test_two_arrays_one_design(two):
    t5, t6 = vec(5), vec(6); c5, c6 = bytes.fromhex(t5["chain_hex"]), bytes.fromhex(t6["chain_hex"])
    cmds = [("raw", b"N", 6), ("raw", b"P\x00" + len(c5).to_bytes(2, "big") + c5, 1, 3000), ("raw", b"P\x01" + len(c6).to_bytes(2, "big") + c6, 1, 3000),
            ("raw", b"A\x00", 1), ("I",)] + run_array(t5, True, 0) + [("raw", b"A\x01", 1), ("I",)] + run_array(t6, True, 1)
    r = B.ByteSim(two).run(cmds); ids = [x for x in r if isinstance(x, dict)]; logs = [x for x in r if isinstance(x, list)]
    assert r[0][4] == 2
    assert [(i["pattern_id"], i["rows"]) for i in ids] == [(0x3A7FD506, 5), (0x8F532C4A, 6)]
    assert [[list(e) for e in lg] for lg in logs] == [t5["expected"], t6["expected"]]
