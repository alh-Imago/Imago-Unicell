"""Save and load of the neural judge's weights (1 Nov 2026): rtl/hexn_weight_port_v1.v with rtl/hexn_neural_v1.v, the item format tools/hexn_item_v1.py. Simulation only (iverilog); nothing on a board.
1. Port self-checks (load/readback, snapshot equals live weights, a second judge restored from the saved words behaves identically, a request while a command is in flight is refused and flagged).
2. Full round trip: a judge learns 300 steps from blank, SAVE streams 8 words, Python packs them as a weights item (HXI1), validates it, unpacks it, a FRESH judge is loaded from it, and both give identical y and weights over 40 more commands.
3. A flipped bit in the item is refused before anything is loaded; mutations of the port (no guard, wrong address) are caught."""
import os, sys, shutil, subprocess, struct
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); R = os.path.join(ROOT, "rtl")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_item_v1 as I
import pytest
pytestmark = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog missing")
SRC = ["hexn_weight_port_v1.v", "tb_hexn_weight_port_v1.v", "hexn_neural_v1.v", "hexn_tanh512_v1.v"]


def build(tmp, port_src=None):
    files = [os.path.join(R, f) for f in SRC]
    if port_src is not None:
        p = tmp / "port_mut.v"; p.write_text(port_src); files[0] = str(p)
    out = str(tmp / "w.vvp"); r = subprocess.run(["iverilog", "-g2012", "-o", out] + files, capture_output=True, text=True); assert r.returncode == 0, r.stderr
    return out


def run(tmp, vvp, *args):
    return subprocess.run(["vvp", vvp] + list(args), capture_output=True, text=True, cwd=tmp).stdout


def test_port_selfcheck(tmp_path):
    o = run(tmp_path, build(tmp_path), "+MODE=0"); assert "ALL WEIGHT PORT TESTS PASS" in o and "FAIL" not in o, o


def roundtrip(tmp, vvp, seed=1, corrupt=False):
    run(tmp, vvp, "+MODE=1", f"+SEED={seed}")
    words = [int(l.split()[1]) for l in open(tmp / "saved.txt")]; assert len(words) == 8
    W, B = [words[:7]], [words[7]]
    item = I.pack(I.T_WEIGHTS, I.weights_payload(W, B, 14), usage=0, version=1, nin=7, wb=14, trained=b"sim")
    ok, why = I.validate(item, dict(nin=7, wb=14, lmax=0)); assert ok, why
    if corrupt:
        b = bytearray(item); b[-3] ^= 0x04; return I.validate(bytes(b), dict(nin=7, wb=14, lmax=0))
    W2, B2, wb = I.read_weights(I.unpack(item)["payload"]); assert wb == 14 and W2 == W and B2 == B
    (tmp / "load.hex").write_text("\n".join("%04x" % (v & 0xFFFF) for v in W2[0] + B2) + "\n")
    run(tmp, vvp, "+MODE=2", f"+SEED={seed}")
    return open(tmp / "ref_after.txt").read(), open(tmp / "got_after.txt").read(), words


def test_roundtrip_through_item(tmp_path):
    ref, got, words = roundtrip(tmp_path, build(tmp_path))
    assert len(ref.splitlines()) == 40 and ref == got
    assert any(w != 0 for w in words)   # it really learned something


def test_roundtrip_second_seed(tmp_path):
    ref, got, words = roundtrip(tmp_path, build(tmp_path), seed=7); assert ref == got and any(w != 0 for w in words)


def test_corrupt_item_refused(tmp_path):
    ok, why = roundtrip(tmp_path, build(tmp_path), corrupt=True); assert not ok and "checksum" in why


def test_mutations_caught(tmp_path):
    src = open(os.path.join(R, "hexn_weight_port_v1.v")).read()
    a = "if (idle && !running && !rd_start) begin w_wr <= 1'b1;"; assert a in src
    o = run(tmp_path, build(tmp_path, src.replace(a, "if (1'b1) begin w_wr <= 1'b1;")), "+MODE=0"); assert "WEIGHT PORT FAILED" in o     # no busy guard on load
    b = "w_addr <= in_addr;"; assert b in src
    o = run(tmp_path, build(tmp_path, src.replace(b, "w_addr <= in_addr ^ 4'd1;")), "+MODE=0"); assert "WEIGHT PORT FAILED" in o     # wrong address
    c = "snap <= w_flat;"; assert c in src
    o = run(tmp_path, build(tmp_path, src.replace(c, "snap <= {w_flat[15:0], w_flat[127:16]};")), "+MODE=0"); assert "WEIGHT PORT FAILED" in o     # rotated snapshot
