"""tests/vm/test_hexn_hexcard_v1.py - the assembled HEX card design (hexn_assemble_hex_v1: UART frame + crossing + six-face pattern) driven through its UART in iverilog like a PC: words equal the hex VM, ticks equal the VM tick + OFFSET (3 Nov 2026).
FRAME env var = frame version to test ('v1' default; 'v2' = the slim frame)."""
import os, random, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_wrgrid_hex_v3 as H, hexn_icm_export_v4 as X, hexn_vm_v7 as V, hexn_pattern_gen_hex_v1 as G, hexn_assemble_hex_v1 as A, hexn_card_sim_v1 as S
N = H.Node9
MIX = {"UN": 2, "AL": 3, "JN": 4, "BR": 1, "MG": 1, "PR": 4}
FRAME = os.environ.get("FRAME", "v2")
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")


def _types(n, off):
    H.OFFSET = off; wc = H.Grid12(n, n).work_cells(); seq = []; c = dict(MIX)
    while any(c.values()):
        for k in list(c):
            if c[k]: seq.append(k); c[k] -= 1
    return {w: t for w, t in zip(wc, (seq + ["AL"] * len(wc))[:len(wc)])}


@pytest.fixture(scope="module")
def card():
    ct = _types(7, 2); ref = G.make_ref("hexcard7", 7, 7, 2, ct); d = tempfile.mkdtemp(prefix="hc_")
    A.assemble(ref, d, frame=FRAME)
    yield d, ref, ct
    shutil.rmtree(d, ignore_errors=True)


def _case(kind):
    if kind == "prio4": return [N("p", "prio", ["x", "y", "z", "w"], cfg=dict(mask=15, ranks=(0, 1, 2, 3), mode=0))], ["x", "y", "z", "w"], ["p"]
    return [N("a", "add", ["x", "y"]), N("r", "sub", ["a", "z"])], ["x", "y", "z"], ["r"]


@pytest.mark.parametrize("kind", ["prio4", "addsub"])
def test_hex_card_through_the_uart_matches_the_hex_vm(card, kind):
    d, ref, ct = card; nodes, ins, outs = _case(kind)
    H.OFFSET = 2; P = H.plan10(nodes, ins, outs, 7, 7, ct, tries=40)
    prog = X.from_icm(X.to_icm(X.program_of(P, ct, ref["name"]))); H.OFFSET = 0
    rnd = random.Random(5); iv = {n: rnd.randrange(1 << 32) for n in ins}
    rows = prog["pads_in"]
    cmds = [("I",), ("W",), ("B", A.chain_image(ref, prog))] + [("D", rows[n][0], iv[n]) for n in ins] + [("G", sum(1 << rows[n][0] for n in ins)), ("wait", 700), ("L",)]
    r = S.CardSim(d, 8).run(cmds)
    assert r[0] == dict(pattern_id=ref["pattern_id"], rows=7) and r[1] == b"K" and r[2] == b"K"
    cap = V.HexVM(prog).run(iv)[outs[0]]; got = r[-1]
    assert got and [w for _, w, _ in got] == [w for _, w in cap], (got, cap)
    assert len({tk - t for (_, _, tk), (t, _) in zip(got, cap)}) == 1          # one constant offset for every word
    print("tick offset", got[0][2] - cap[0][0])
