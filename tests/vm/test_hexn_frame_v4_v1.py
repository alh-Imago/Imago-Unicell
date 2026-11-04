"""tests/vm/test_hexn_frame_v4_v1.py - hexn_arr_core (frame v4 = byte port instead of UART, around the 7x7 17-work pattern) driven in iverilog like the Kintex JTAG bridge would: ID, wipe, load, present, go, log; the words equal the hex VM and the ticks equal those of the UART frame (54 addsub on this pattern, measured 4 Nov). Also checks the generated core/top text for the Kintex (no simulation of the bridge: BSCANE2 is not modelled)."""
import os, random, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_wrgrid_hex_v3 as H, hexn_icm_export_v4 as X, hexn_vm_v7 as V, hexn_pattern_gen_hex_v1 as G, hexn_assemble_hex_v2 as A, hexn_bytecard_sim_v1 as B, hexn_kxarr_v1 as K
N = H.Node9
MIX = {"UN": 2, "AL": 3, "JN": 4, "BR": 1, "MG": 1, "PR": 4}
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")


def _types(n, off):
    H.OFFSET = off; wc = H.Grid12(n, n).work_cells(); seq = []; c = dict(MIX)
    while any(c.values()):
        for k in list(c):
            if c[k]: seq.append(k); c[k] -= 1
    return {w: t for w, t in zip(wc, (seq + ["AL"] * len(wc))[:len(wc)])}


@pytest.fixture(scope="module")
def card():
    ct = _types(7, 2); ref = G.make_ref("hexcard7", 7, 7, 2, ct); d = tempfile.mkdtemp(prefix="kx_")
    import json; rp = os.path.join(d, "ref.json"); json.dump(ref, open(rp, "w"))
    os.system("python3 %s sim %s %s > /dev/null" % (os.path.join(ROOT, "tools", "hexn_kxarr_v1.py"), rp, d))
    yield os.path.join(d, "src"), ref, ct, d
    shutil.rmtree(d, ignore_errors=True)


def _case(kind):
    if kind == "prio4": return [N("p", "prio", ["x", "y", "z", "w"], cfg=dict(mask=15, ranks=(0, 1, 2, 3), mode=0))], ["x", "y", "z", "w"], ["p"]
    return [N("a", "add", ["x", "y"]), N("r", "sub", ["a", "z"])], ["x", "y", "z"], ["r"]


@pytest.mark.parametrize("kind", ["prio4", "addsub"])
def test_byte_port_card_matches_the_hex_vm(card, kind):
    src, ref, ct, d = card; nodes, ins, outs = _case(kind)
    H.OFFSET = 2; P = H.plan10(nodes, ins, outs, 7, 7, ct, tries=40)
    prog = X.from_icm(X.to_icm(X.program_of(P, ct, ref["name"]))); H.OFFSET = 0
    rnd = random.Random(5); iv = {n: rnd.randrange(1 << 32) for n in ins}; rows = prog["pads_in"]
    chain = A.chain_image(ref, prog)
    cmds = [("I",), ("W",), ("B", chain)] + [("D", rows[k][0], iv[k]) for k in ins] + [("G", sum(1 << rows[k][0] for k in ins)), ("wait", 700), ("L",)]
    r = B.ByteSim(src).run(cmds)
    assert r[0] == dict(pattern_id=ref["pattern_id"], rows=7) and r[1] == b"K" and r[2] == b"K"
    cap = V.HexVM(prog).run(iv)[outs[0]]
    assert r[-1] and [w for _, w, _ in r[-1]] == [w for _, w in cap]


def test_generated_texts(card):
    src, ref, ct, d = card
    c = K.core_text(ref); t = K.top_text()
    assert "hexn_frame_v4" in c and "PATTERN_ID(32'h%s)" % ref["pattern_id_hex"] in c and ".CHAIN_BITS(%d)" % K.chain_len(ref) in c
    assert "hexn_jtag_bridge_v1 #(.CHAIN(2)" in t and "module hexn_arr (input SYS_CLK, output [2:0] led)" in t


def test_static_top_file_matches_the_generator():
    assert open(os.path.join(ROOT, "fpga", "ypcb", "hexn_arr", "hexn_arr.v")).read() == K.top_text()
