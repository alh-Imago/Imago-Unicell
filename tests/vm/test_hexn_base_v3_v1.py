"""tests/vm/test_hexn_base_v3_v1.py - the Kintex BASE with DATA RAM and run-from-RAM (tools/hexn_kxbase_v3.py, sub/verilog/hexn_base_ctl_v3.v) in iverilog through the JTAG byte port (5 Nov 2026). Simulation only: not built or run on a card.
Small RAMs are built (data RAM DA = 4: 16 entries; results RAM RA = 3: 8 records, margin 2 = FULL at 6) so that the stop can be reached quickly.
Checks: entries stored with 'T' and run with 'H' give the same records as the host's own D and G; the run stops at a GO with 'F' when the results RAM is FULL and continues after a clear; with recording off the array's own log equals the vector (and no 'K' of the frame leaks to the host)."""
import json, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_bytecard_sim_v1 as B
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
RD = os.path.join(ROOT, "docs", "hex-n", "data", "hexrefs")


def vec(n, k=0): return json.load(open(os.path.join(RD, "vectors", "kx_vec_%d.json" % n)))["tests"][k]


def build(refs):
    d = tempfile.mkdtemp(prefix="kxbase3_")
    assert os.system("HEXN_DA=4 HEXN_RA=3 HEXN_RMARGIN=2 python3 %s sim %s %s > /dev/null" % (os.path.join(ROOT, "tools", "hexn_kxbase_v3.py"), " ".join(os.path.join(RD, r) for r in refs), d)) == 0
    return d


def entry_d(row, w): return bytes([row]) + w.to_bytes(4, "little") + bytes(3)
def entry_g(mask, wait): return bytes([0x80 | mask]) + wait.to_bytes(2, "little") + bytes(5)
def store(addr, entries): return b"T" + addr.to_bytes(2, "big") + len(entries).to_bytes(2, "big") + b"".join(entries)
def run(addr, n): return b"H" + addr.to_bytes(2, "big") + n.to_bytes(2, "big")
def entries(t, wait=2000, gos=1): return [entry_d(r, w) for r, w in t["inputs"]] + [entry_g(t["mask"], wait)] * gos
def load(t): return [("W",), ("B", bytes.fromhex(t["chain_hex"]))]


def recs(b):
    k = b[0]; assert len(b) == 1 + 8 * k
    return [dict(kind=b[1 + 8 * i] >> 7, row=b[1 + 8 * i] & 7, tick=int.from_bytes(b[2 + 8 * i:4 + 8 * i], "little"), word=int.from_bytes(b[4 + 8 * i:8 + 8 * i], "little"), idx=b[8 + 8 * i]) for i in range(k)]


def count(y): return y[0] | y[1] << 8


@pytest.fixture(scope="module")
def seven():
    d = build(["hex7_off2_mix.json"]); yield os.path.join(d, "src"); shutil.rmtree(d, ignore_errors=True)


def test_entries_run_from_the_ram_and_give_the_same_records(seven):
    t = vec(7); e = entries(t); n = len(e); exp = [tuple(x) for x in t["expected"]]
    cmds = [("raw", b"A\x00", 1)] + load(t) + [("raw", b"X\x03", 1), ("raw", store(0, e), 1, 3000), ("raw", run(0, n), 3, 9000), ("raw", b"Y", 7), ("raw", b"V\x08", 1 + 8 * len(exp), 6000)]
    r = B.ByteSim(seven).run(cmds)
    assert r[-3] == bytes([0x4b, n, 0]) and count(r[-2]) == len(exp) and r[-2][2] == 0           # 'K', all 5 entries executed, 4 records, nothing lost
    got = recs(r[-1]); assert [(x["row"], x["word"], x["tick"]) for x in got] == exp and [x["idx"] for x in got] == list(range(len(exp)))


def test_run_stops_at_a_go_when_the_results_ram_is_full_and_continues_after_a_clear(seven):
    t = vec(7); e = entries(t, gos=3); n = len(e); nd = len(t["inputs"]); exp = [tuple(x) for x in t["expected"]]; assert n == nd + 3
    cmds = [("raw", b"A\x00", 1)] + load(t) + [("raw", b"X\x03", 1), ("raw", store(0, e), 1, 3000), ("raw", run(0, n), 3, 16000), ("raw", b"Y", 7), ("raw", b"V\x08", 1 + 64, 9000),
                                             ("raw", b"X\x03", 1), ("raw", run(n - 1, 1), 3, 6000), ("raw", b"Y", 7)]
    r = B.ByteSim(seven).run(cmds)
    assert r[-6] == bytes([0x46, nd + 2, 0])                                                      # 'F': stopped at the third GO after nd + 2 entries
    assert count(r[-5]) == 8 and r[-5][3] & 1 == 1 and r[-5][2] == 0                               # 8 records, FULL, none lost
    got = recs(r[-4]); assert len(got) == 8 and [x["idx"] for x in got] == list(range(8))
    assert [(x["row"], x["word"], x["tick"]) for x in got[:4]] == exp == [(x["row"], x["word"], x["tick"]) for x in got[4:]]
    assert r[-3] == b"K" and r[-2] == bytes([0x4b, 1, 0]) and count(r[-1]) == 4                    # after the clear the last GO runs: 4 new records


def test_without_recording_the_arrays_own_log_equals_the_vector_and_no_frame_k_leaks(seven):
    t = vec(7, 1); e = entries(t, wait=1500); n = len(e)
    cmds = [("raw", b"A\x00", 1)] + load(t) + [("raw", store(3, e), 1, 3000), ("raw", run(3, n), 3, 8000), ("L",), ("raw", b"N", 6)]
    r = B.ByteSim(seven).run(cmds)
    assert r[-3] == bytes([0x4b, n, 0]) and [list(x) for x in r[-2]] == t["expected"] and r[-1][:4] == bytes([0x45, 0x53, 0x41, 0x42])
