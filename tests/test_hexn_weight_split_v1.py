"""Weights carried 8 bits at a time (1 Nov 2026): rtl/hexn_weight_split_v1.v beside hexn_weight_port_v1 and hexn_neural_v1. Simulation only (iverilog); nothing on a board.
1. Self-checks: 16 bytes leave in order (low then high per address) with random stalls; a fresh judge reassembled from them equals the original in three orders (in order, high first, random order and gaps); an incomplete pair is dropped and flagged, never written; a lone half is never written; a second save during sending is ignored and flagged.
2. The byte order equals the little-endian payload of the loadable item (tools/hexn_item_v1.py): the 16 saved bytes are the 7 weights as i16 plus the low 16 bits of the bias; a judge loaded from the ITEM's bytes ends with the same weights as the judge that was saved.
3. Mutations are caught."""
import os, sys, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); R = os.path.join(ROOT, "rtl")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_item_v1 as I
import pytest
pytestmark = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog missing")
SRC = ["hexn_weight_split_v1.v", "hexn_weight_port_v1.v", "tb_hexn_weight_split_v1.v", "hexn_neural_v1.v", "hexn_tanh512_v1.v"]


def build(tmp, split_src=None):
    files = [os.path.join(R, f) for f in SRC]
    if split_src is not None:
        p = tmp / "split_mut.v"; p.write_text(split_src); files[0] = str(p)
    out = str(tmp / "w.vvp"); r = subprocess.run(["iverilog", "-g2012", "-o", out] + files, capture_output=True, text=True); assert r.returncode == 0, r.stderr
    return out


def run(tmp, vvp, *args):
    return subprocess.run(["vvp", vvp] + list(args), capture_output=True, text=True, cwd=tmp).stdout


def test_split_selfcheck(tmp_path):
    o = run(tmp_path, build(tmp_path), "+MODE=0"); assert "ALL WEIGHT SPLIT TESTS PASS" in o and "FAIL" not in o, o


@pytest.mark.parametrize("seed", [1, 5])
def test_bytes_match_item_and_reload(tmp_path, seed):
    v = build(tmp_path); run(tmp_path, v, "+MODE=1", f"+SEED={seed}")
    rows = [tuple(int(t) for t in l.split()) for l in open(tmp_path / "bytes.txt")]; assert len(rows) == 16
    assert [(a, h) for a, h, _ in rows] == [(j // 2, j % 2) for j in range(16)]
    bs = bytes(b for _, _, b in rows); assert any(bs)
    words = [int.from_bytes(bs[2 * k:2 * k + 2], "little", signed=True) for k in range(8)]
    item = I.pack(I.T_WEIGHTS, I.weights_payload([words[:7]], [words[7]], 14), nin=7, wb=14, trained=b"sim")
    ok, why = I.validate(item, dict(nin=7, wb=14, lmax=0)); assert ok, why
    pl = I.unpack(item)["payload"]; assert pl[4:18] == bs[:14] and pl[18:20] == bs[14:16]    # same byte order as the item payload
    W, B, wb = I.read_weights(pl)
    ib = b"".join(w.to_bytes(2, "little", signed=True) for w in W[0]) + (B[0] & 0xFFFF).to_bytes(2, "little")
    (tmp_path / "bytes.hex").write_text("\n".join("%02x" % b for b in ib) + "\n")
    run(tmp_path, v, "+MODE=2", f"+SEED={seed}")
    got = [int(l) for l in open(tmp_path / "got_w.txt")]; assert got == words


def test_mutations_caught(tmp_path):
    src = open(os.path.join(R, "hexn_weight_split_v1.v")).read()
    a = "p_data <= {t_hi, t_lo};"; assert a in src
    assert "WEIGHT SPLIT FAILED" in run(tmp_path, build(tmp_path, src.replace(a, "p_data <= {t_lo, t_hi};")), "+MODE=0")                        # halves swapped
    b = "if ((have_lo || have_hi) && !same) err_pair <= 1'b1;"; assert b in src
    assert "WEIGHT SPLIT FAILED" in run(tmp_path, build(tmp_path, src.replace(b, "")), "+MODE=0")                                          # incomplete pair not flagged
    c = "if (t_lov && t_hiv) begin"; assert c in src
    assert "WEIGHT SPLIT FAILED" in run(tmp_path, build(tmp_path, src.replace(c, "if (t_lov || t_hiv) begin")), "+MODE=0")                 # writes on one half
    d = "b_half <= sh;"; assert d in src
    assert "WEIGHT SPLIT FAILED" in run(tmp_path, build(tmp_path, src.replace(d, "b_half <= ~sh;")), "+MODE=0")                            # wrong half flag
