"""tests/vm/test_hexn_frame_v5_v1.py - frame v5 (= v4 + the 'S' status command) around the 5x5 pattern in iverilog through the byte port: the normal commands still give the right word, and the status counters say what happened (chain bits shifted, one output pulse, bytes received). Also the host's status/probe decoding against a pretend card."""
import json, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_bytecard_sim_v1 as B, hexn_kxarr_v1 as K
REF = os.path.join(ROOT, "docs", "hex-n", "data", "hexrefs", "hex5.json"); VEC = os.path.join(ROOT, "docs", "hex-n", "data", "hexrefs", "vectors", "kx_vec_5.json")


@pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
def test_status_counters_and_word():
    ref = json.load(open(REF)); t = json.load(open(VEC))["tests"][0]; d = tempfile.mkdtemp(prefix="kx5_")
    try:
        os.system("HEXN_FRAME=v5 python3 %s sim %s %s > /dev/null" % (os.path.join(ROOT, "tools", "hexn_kxarr_v1.py"), REF, d))
        cmds = [("W",), ("B", bytes.fromhex(t["chain_hex"]))] + [("D", r, w) for r, w in t["inputs"]] + [("S",), ("G", t["mask"]), ("wait", 2000), ("S",), ("L",)]
        r = B.ByteSim(os.path.join(d, "src")).run(cmds)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    s1, s2, log = r[-4], r[-2], r[-1]
    assert [(a, w, k) for a, w, k in log] == [tuple(e) for e in t["expected"]]
    assert s1[4] | s1[5] << 8 == K.chain_len(ref) and s1[6] == 0 and s1[7] == 0       # chain bits shifted, no output yet
    assert s2[1] == 1 and s2[6] == 1 and s2[8] != 0 and s2[0] >> 4 == 1                # one word logged, one output pulse, trun set


def test_host_probe_decodes_status(monkeypatch):
    sys.path.insert(0, os.path.join(ROOT, "tools")); pytest.importorskip("serial"); import hexn_kxarr_host_v1 as H
    monkeypatch.setattr(H.time, "sleep", lambda s: None)
    class L:
        def __init__(s): s.out = bytearray()
        def write(s, b):
            if b == b"S": s.out += bytes([0x17, 1, 8, 13, 133, 2, 1, 0, 2, 0, 21, 108, 0])
            elif b[:1] in b"WBDG": s.out += b"K"
            elif b == b"L": s.out += bytes([0])
        def read(s, n): d = bytes(s.out[:n]); del s.out[:n]; return d
    lines = []; H.probe(L(), json.load(open(VEC)), lines.append)
    assert any("'cfg_bits': 645" in l for l in lines) and lines[-1] == "L count 0"
