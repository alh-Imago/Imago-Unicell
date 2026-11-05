"""tests/vm/test_hexn_base_v4_v1.py - the Kintex BASE with the WEIGHT STORE and the cross-index (tools/hexn_kxbase_v4.py, sub/verilog/hexn_base_ctl_v4.v) in iverilog through the JTAG byte port (5 Nov 2026). Simulation only: not built or run on a card.
Checks: the judge's weights are saved into a set ('O') and read back word for word ('r') in the judge's own load format; after the weights are overwritten, loading the set ('F') restores the judge's scores; a library slot tied to a set ('E') loads its weights before its program on 'Q' and on 'Z' (the judge's choice), an untied slot does not."""
import json, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_bytecard_sim_v1 as B
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
RD = os.path.join(ROOT, "docs", "hex-n", "data", "hexrefs")
J = lambda w: ("raw", b"J" + w.to_bytes(4, "little"), 1)
LOAD = lambda cls, addr, wt: (12 << 28) | (cls << 24) | (addr << 16) | (wt & 255)
SCORE = 3 | (2 << 4)
OLD = bytes([1, 7, 0, 5, 0, 0])            # s0 7, s1 5 with LOAD(1,3,5) and LOAD(0,18,7): as in the v1 base test
NEW = bytes([1, 11, 0, 9, 0, 0])           # with LOAD(1,3,9) and LOAD(0,18,11)


def chain5(): return bytes.fromhex(json.load(open(os.path.join(RD, "vectors", "kx_vec_5.json")))["tests"][0]["chain_hex"])


@pytest.fixture(scope="module")
def one():
    d = tempfile.mkdtemp(prefix="kxbase4_")
    assert os.system("HEXN_DA=4 HEXN_RA=3 HEXN_RMARGIN=2 python3 %s sim %s %s > /dev/null" % (os.path.join(ROOT, "tools", "hexn_kxbase_v4.py"), os.path.join(RD, "hex5.json"), d)) == 0
    yield os.path.join(d, "src"); shutil.rmtree(d, ignore_errors=True)


def test_save_read_back_overwrite_and_load(one):
    cmds = [J(LOAD(1, 3, 5)), J(LOAD(0, 18, 7)), J(SCORE), ("raw", b"R", 6),
            ("raw", b"O\x00", 1, 12000), ("raw", b"r\x00\x00\x06\x02", 8), ("raw", b"r\x00\x00\x24\x01", 4), ("raw", b"r\x00\x01\x00\x01", 4),
            J(LOAD(1, 3, 9)), J(LOAD(0, 18, 11)), J(SCORE), ("raw", b"R", 6),
            ("raw", b"F\x00", 1, 14000), J(SCORE), ("raw", b"R", 6)]
    r = B.ByteSim(one).run(cmds)
    assert r[3] == OLD and r[4] == b"K"
    w = [int.from_bytes(r[5][i:i + 4], "little") for i in (0, 4)]
    assert w == [LOAD(0, 3, 0), LOAD(1, 3, 5)]                                         # words 6 and 7 = class 0 and class 1 of address 3, in the judge's load format
    assert int.from_bytes(r[6], "little") == LOAD(0, 18, 7)                            # word 36 = class 0 of address 18
    assert int.from_bytes(r[7], "little") == 13 << 28                                  # word 256 = the BIAS word (bias 0)
    assert r[11] == NEW and r[12] == b"K" and r[14] == OLD                             # overwritten, then restored from the store


def test_cross_index_loads_the_weights_with_the_program(one):
    c = chain5(); P = lambda s: ("raw", b"P" + bytes([s]) + len(c).to_bytes(2, "big") + c, 1, 4000)
    cmds = [("raw", b"A\x00", 1), P(0), P(1), J(LOAD(1, 3, 5)), J(LOAD(0, 18, 7)), ("raw", b"O\x00", 1, 12000), J(LOAD(1, 3, 9)), J(LOAD(0, 18, 11)),
            ("raw", b"Q\x00", 1, 12000), J(SCORE), ("raw", b"R", 6),                  # untied: the program loads, the weights stay as they are
            ("raw", b"E\x00\x00", 1), ("raw", b"Q\x00", 1, 14000), J(SCORE), ("raw", b"R", 6),   # tied to set 0: the weights come back with the program
            J(LOAD(1, 3, 9)), J(LOAD(0, 18, 11)), ("raw", b"E\x01\x00", 1), ("raw", b"C\x00\x01", 1), J(SCORE),   # a judge result is waiting (not read)
            ("raw", b"Z", 1, 14000), J(SCORE), ("raw", b"R", 6), ("raw", b"U", 2)]
    r = B.ByteSim(one).run(cmds)
    assert r[5] == b"K" and r[8] == b"K" and r[10] == NEW                                # untied Q: K, weights unchanged
    assert r[11] == b"K" and r[12] == b"K" and r[14] == OLD                              # tied Q: K only after weights and program are in; weights restored
    assert r[17] == b"K" and r[18] == b"K" and r[19] == b"K"                             # E, C, score
    assert r[20] == b"K" and r[22] == OLD and r[23][1] == 1                              # Z chose a (tied) slot and restored the weights; one choice made
