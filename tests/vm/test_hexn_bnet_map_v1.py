"""Cross-check of sub/verilog/hexn_bnet_map_v1.v (iverilog) against Python: the two stored maps with the best overlap (shared / union) with the live map, and the live map itself (OR of the fire vectors). Needs iverilog: FAILS without it."""
import os, sys, random, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "..", "..", "sub", "verilog")
NB, M = 32, 8


def ref(maps, live):
    """the hardware's insertion logic replayed in Python (first of equal scores wins)"""
    i1 = u1 = i2 = u2 = 0; b1 = b2 = 0
    for i, m in enumerate(maps):
        a = bin(live & m).count("1"); u = bin(live | m).count("1")
        beats1 = u != 0 and (a * u1 > i1 * u or u1 == 0); beats2 = u != 0 and (a * u2 > i2 * u or u2 == 0)
        if beats1: i2, u2, b2, i1, u1, b1 = i1, u1, b1, a, u, i
        elif beats2: i2, u2, b2 = a, u, i
    return b1, b2, i1, u1, i2, u2


def independent_top2(maps, live):
    """independent check: the two highest Jaccard values (exact fractions) among all stored maps"""
    from fractions import Fraction
    v = sorted((Fraction(bin(live & m).count("1"), bin(live | m).count("1")) for m in maps if live | m), reverse=True); return v[0], v[1]


def test_matcher_matches_python(tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required"
    for seed in range(8):
        r = random.Random(seed); maps = [r.getrandbits(NB) & r.getrandbits(NB) | (1 << r.randrange(NB)) for _ in range(M)]; fv = [r.getrandbits(NB) & r.getrandbits(NB) & r.getrandbits(NB) for _ in range(4)]
        live = 0
        for f in fv: live |= f
        d = tmp_path / ("s%d" % seed); d.mkdir(); (d / "maps.hex").write_text("\n".join("%08x" % m for m in maps) + "\n"); (d / "fire.hex").write_text("\n".join("%08x" % f for f in fv) + "\n")
        subprocess.run(["iverilog", "-g2012", "-s", "tbm", "-o", str(d / "sim"), os.path.join(HERE, "hexn_bnet_map_v1_tb.v"), os.path.join(V, "hexn_bnet_map_v1.v")], check=True)
        out = subprocess.run(["vvp", str(d / "sim")], cwd=d, capture_output=True, text=True, check=True).stdout
        line = [l for l in out.splitlines() if l.startswith("R ")][0].split(); got = tuple(int(x) for x in line[1:7]); lv = int(line[7], 16)
        from fractions import Fraction
        assert (Fraction(got[2], got[3]), Fraction(got[4], got[5])) == independent_top2(maps, live)
        assert lv == live and got == ref(maps, live), "seed %d: hw %s live %x, python %s live %x" % (seed, got, lv, ref(maps, live), live)
