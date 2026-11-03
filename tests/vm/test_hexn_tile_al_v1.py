"""Tests for the aligned two-input tile (sub/verilog/hexn_tile_al_v1.v), 3 Nov 2026. Needs iverilog; fails (does not skip) without it."""
import os, random, shutil, subprocess, sys, tempfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tile_cfg_al_v1 as C

M = 0xFFFFFFFF


def run(word, a, b, extra=8, faces=4):
    d = tempfile.mkdtemp()
    try:
        rows = []
        w = C.width(faces)
        for i in range(w - 1, -1, -1):
            rows.append(0x2 | ((word >> i) & 1))
        rows.append(0)
        for i in range(32):
            rows.append((((a >> i) & 1) << 8) | ((i == 0) << 9) | (((b >> i) & 1) << 2) | ((i == 0) << 3))
        rows += [0] * extra
        open(d + "/s.hex", "w").write("\n".join("%04x" % r for r in rows) + "\n")
        subprocess.run(["iverilog", "-o", d + "/t", os.path.join(ROOT, "tests/hexn_tile_al_tb.v"),
                        os.path.join(ROOT, "sub/verilog/hexn_tile_al_v1.v"), os.path.join(ROOT, "sub/verilog/hexn_aligned_core_v1.v")], check=True)
        out = subprocess.run(["vvp", d + "/t", "+stim=" + d + "/s.hex", "+n=%d" % len(rows)], capture_output=True, text=True, check=True).stdout
        return [l.strip() for l in out.splitlines() if len(l.strip()) == 9 and set(l.strip()) <= set("01x")]
    finally:
        shutil.rmtree(d)


def word_at(lines, idx):  # E face: chars 1 = flag, 2 = data
    f = [l[1] for l in lines]
    s = f.index("1")
    return s, sum(int(lines[s + i][2]) << i for i in range(32))


def test_tools_present():
    assert shutil.which("iverilog") and shutil.which("vvp")


def test_pack_width_and_roundtrip():
    assert C.width(4) == 25
    w = C.pack({0: "W"}, "W", "N", ["E"], "xor")
    u = C.unpack(w)
    assert u["op"] == "xor" and u["sela"] == 3 and u["selb"] == 0 and u["result_to"] == [1] and u["route"][0] == 3


def test_ops_match_python():
    random.seed(7)
    fn = {"add": lambda a, b: (a + b) & M, "sub": lambda a, b: (a - b) & M, "and": lambda a, b: a & b,
          "or": lambda a, b: a | b, "xor": lambda a, b: a ^ b}
    for op, f in fn.items():
        for a, b in [(5, 9), (0xFFFFFFFF, 1), (0x80000000, 0x80000000), (random.getrandbits(32), random.getrandbits(32))]:
            lines = run(C.pack({}, "W", "N", ["E"], op), a, b)
            s, v = word_at(lines, 0)
            assert v == f(a, b), (op, hex(a), hex(b), hex(v))


def test_sub_borrow_wraps():
    lines = run(C.pack({}, "W", "N", ["E"], "sub"), 0, 1)
    assert word_at(lines, 0)[1] == M
