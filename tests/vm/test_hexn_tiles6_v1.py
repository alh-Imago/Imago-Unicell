"""tests/vm/test_hexn_tiles6_v1.py - the eight Hex-N tiles at SIX FACES (3 Nov 2026, Alan 17:05: step H2 of docs/hex-n/HEXN_HEX_GRID_SCOPING_v1.md).
Method: the same configuration (same operands, results and timing) is run on the tile at FACES=4 (faces 3, 0 in, 1 out) and at FACES=6 on faces that do not exist at four (4 and 5 as operands, 4 and 5 as results).  The words and the START CLOCKS of the result must be identical, and the values must be right (a+b, a-b, ...).
Face numbers here are the tile's own indices; in the hex grid (tools/hexn_hexgeom_v1.py) they are 0 E, 1 SE, 2 SW, 3 W, 4 NW, 5 NE.  The priority tile has its four ports tied to face indices 3, 0, 2, 1 in the RTL (no select): it is tested only on those faces."""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_tile_cfg_v1 as CU, hexn_tile_cfg_al_v1 as CA, hexn_tile_cfg_jn_v1 as CJ, hexn_tile_cfg_mg_v1 as CM, hexn_tile_cfg_br_v1 as CB, hexn_tile_cfg_pr_v1 as CP, hexn_tile_cfg_pr_v2 as CP2, hexn_tile_cfg_sq_v1 as CS, hexn_tile_cfg_lt_v1 as CL
V = os.path.join(ROOT, "sub", "verilog")
FILES = [os.path.join(V, f) for f in ("hexn_rcore_flag_v3.v", "hexn_tile_v3.v", "hexn_unary_core_v2.v", "hexn_tile_al_v2.v", "hexn_aligned_core_v2.v", "hexn_tile_jn_v2.v", "hexn_join_core_v3.v", "hexn_tile_br_v2.v", "hexn_branch_core_v2.v",
                                               "hexn_tile_mg_v2.v", "hexn_merge_core_v2.v", "hexn_tile_pr_v1.v", "hexn_tile_pr_v2.v", "hexn_prio_core_v2.v", "hexn_tile_sq_v1.v", "hexn_seq_core_v2.v", "hexn_tile_lt_v2.v", "hexn_latch_core_v3.v")]
MASK = 0xFFFFFFFF


def run(module, F, word, width, events, nclk=160):
    """events [(face, start clock, word)]; returns {out face: [(start clock, word)]} (clock 1 = first clock after the chain is loaded)"""
    d = tempfile.mkdtemp(prefix="t6_")
    try:
        L = ["`timescale 1ns/1ps", "module tb; reg clk=0; always #5 clk=~clk; reg clear=0,cfg_en=0,cfg_in=0; reg [%d:0] fd=0, ff=0; wire [%d:0] od, of; wire co; integer t=0, i;" % (F - 1, F - 1),
             "%s #(.FACES(%d)) u (.clk(clk),.clear(clear),.fi_d(fd),.fi_f(ff),.fo_d(od),.fo_f(of),.cfg_en(cfg_en),.cfg_in(cfg_in),.cfg_out(co));" % (module, F),
             "reg [%d:0] word; initial begin word = %d'h%x; @(posedge clk); cfg_en=1; for(i=%d;i>=0;i=i-1) begin cfg_in=word[i]; @(posedge clk); #1; end cfg_en=0; end" % (width - 1, width, word, width - 1),
             "reg go=0; initial begin repeat (%d) @(posedge clk); go=1; end" % (width + 20),
             "always @(posedge clk) if (go) begin t<=t+1; if (t > 0) $display(\"T %0d %h %h\", t, od, of); end",
             "always @(posedge clk) if (go) begin"]
        per = {}
        for face, s, w in events:
            for i in range(32):
                c = s + i
                dd, ff = per.get(c, (0, 0))
                if (w >> i) & 1: dd |= 1 << face
                if i == 0: ff |= 1 << face
                per[c] = (dd, ff)
        L.append("  case (t+1)")
        for c, (dd, ff) in sorted(per.items()): L.append("   %d: begin fd <= %d; ff <= %d; end" % (c, dd, ff))
        L += ["   default: begin fd <= 0; ff <= 0; end", "  endcase", "end", "initial begin #%d $finish; end endmodule" % ((width + nclk + 60) * 10)]
        tb = os.path.join(d, "tb.v"); open(tb, "w").write("\n".join(L))
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-o", o, tb] + FILES, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:800]
        out = subprocess.run(["vvp", o], capture_output=True, text=True).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    tr = {}
    for l in out.splitlines():
        if l.startswith("T "): _, t, od, of = l.split(); tr[int(t)] = (int(od, 16), int(of, 16))
    res = {}
    for f in range(F):
        for t, (od, of) in tr.items():
            if (of >> f) & 1:
                w = sum(((tr.get(t + i, (0, 0))[0] >> f) & 1) << i for i in range(32)); res.setdefault(f, []).append((t, w))
    return res


def _first(res, f): return res.get(f, [])


# each case: (module, packer(F, fa, fb, fo, fo2), events(fa, fb), expected {role: [words]} on fo / fo2 as given by `outs`, width)
A, B = 0x1234567, 0x00ABCDE


def _cases():
    r7 = lambda F: {o: 7 for o in range(F)}
    return {
        "UN_shl": ("hexn_tile_v3", lambda F, fa, fb, fo, fo2: CU.pack(r7(F), fa, (fo,), "shl", 3, faces=F), CU.width, lambda fa, fb: [(fa, 3, A)], lambda fo, fo2: {fo: [(A << 3) & MASK]}),
        "AL_add": ("hexn_tile_al_v2", lambda F, fa, fb, fo, fo2: CA.pack(r7(F), fa, fb, (fo,), "add", faces=F), CA.width, lambda fa, fb: [(fa, 3, A), (fb, 3, B)], lambda fo, fo2: {fo: [(A + B) & MASK]}),
        "JN_sub": ("hexn_tile_jn_v2", lambda F, fa, fb, fo, fo2: CJ.pack(r7(F), fa, fb, (fo,), "sub", faces=F), CJ.width, lambda fa, fb: [(fa, 3, A), (fb, 9, B)], lambda fo, fo2: {fo: [(A - B) & MASK]}),
        "MG_arb": ("hexn_tile_mg_v2", lambda F, fa, fb, fo, fo2: CM.pack(r7(F), fa, fb, (fo,), 2, faces=F), CM.width, lambda fa, fb: [(fa, 3, A), (fb, 60, B)], lambda fo, fo2: {fo: [A, B]}),
        "BR_lt": ("hexn_tile_br_v2", lambda F, fa, fb, fo, fo2: CB.pack(r7(F), fa, fb, (fo,), (fo2,), 1, 1, 2, 3, 0, faces=F), CB.width, lambda fa, fb: [(fa, 3, 5), (fb, 3, 9)], lambda fo, fo2: {fo: [(5 - 9) & MASK]}),
        "BR_gt": ("hexn_tile_br_v2", lambda F, fa, fb, fo, fo2: CB.pack(r7(F), fa, fb, (fo,), (fo2,), 1, 1, 2, 3, 0, faces=F), CB.width, lambda fa, fb: [(fa, 3, 9), (fb, 3, 5)], lambda fo, fo2: {fo2: [4]}),
        "SQ": ("hexn_tile_sq_v1", lambda F, fa, fb, fo, fo2: CS.pack(r7(F), fa, (fo,), [111, 222, 333], 3, faces=F), CS.width, lambda fa, fb: [(fa, 3, 1), (fa, 60, 1)], lambda fo, fo2: {fo: [111, 222]}),
        "LT": ("hexn_tile_lt_v2", lambda F, fa, fb, fo, fo2: CL.pack(r7(F), fa, fb, 7, (fo,), faces=F), CL.width, lambda fa, fb: [(fa, 3, 1), (fb, 60, 1)], lambda fo, fo2: {fo: [1, 0]}),
    }


VARIANTS = [(6, 3, 0, 1, 2), (6, 5, 4, 1, 2), (6, 4, 5, 2, 0), (6, 3, 0, 5, 4), (6, 4, 2, 0, 5), (6, 5, 3, 4, 1)]


@pytest.mark.parametrize("name", list(_cases()))
def test_tile_at_six_faces_equals_four_faces(name):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    module, packer, width, events, expect = _cases()[name]
    def go(F, fa, fb, fo, fo2):
        res = run(module, F, packer(F, fa, fb, fo, fo2), width(F), events(fa, fb))
        want = expect(fo, fo2)
        for f, ws in want.items(): assert [w for _, w in _first(res, f)] == ws, (name, F, fa, fb, fo, fo2, res)
        used = list(want)[0]; s0 = min(s for _, s, _ in [(0, 3, 0)]); return [(t, w) for t, w in _first(res, used)]
    ref = go(4, 3, 0, 1, 2)
    for (F, fa, fb, fo, fo2) in VARIANTS:
        got = go(F, fa, fb, fo, fo2)
        assert got == ref, (name, "six faces", (fa, fb, fo, fo2), got, ref)


def test_priority_tile_at_six_faces_on_its_fixed_faces():
    assert shutil.which("iverilog")
    pk = lambda F: CP.pack({o: 7 for o in range(F)}, (1,), 7, (0, 1, 2, 3), 0, 0, (0, 0, 0, 0), faces=F)
    ev = [(3, 3, 111), (0, 3, 222)]
    a = run("hexn_tile_pr_v1", 4, pk(4), CP.width(4), ev); b = run("hexn_tile_pr_v1", 6, pk(6), CP.width(6), ev)
    assert a.get(1) and a.get(1) == b.get(1), (a, b)
    assert sorted(w for _, w in a[1]) == [111, 222]


def test_priority_tile_v2_ports_follow_the_selects_at_six_faces():
    """v2: the same priority configuration with its ports on faces (5, 4, 3, 2) gives the words and start clocks of the four-face reference on faces (3, 0, 2, 1); the default selects are the v1 mapping"""
    assert shutil.which("iverilog")
    pk = lambda F, ps, out: CP2.pack({o: 7 for o in range(F)}, (out,), 7, (0, 1, 2, 3), 0, 0, (0, 0, 0, 0), ps, faces=F)
    ref = run("hexn_tile_pr_v2", 4, pk(4, (3, 0, 2, 1), 1), CP2.width(4), [(3, 3, 111), (0, 3, 222), (2, 3, 333)])
    assert sorted(w for _, w in ref[1]) == [111, 222, 333]
    v1 = run("hexn_tile_pr_v1", 4, CP.pack({o: 7 for o in range(4)}, (1,), 7, (0, 1, 2, 3), 0, 0, (0, 0, 0, 0), faces=4), CP.width(4), [(3, 3, 111), (0, 3, 222), (2, 3, 333)])
    assert ref == v1, (ref, v1)                                   # default selects = the v1 tile
    for ps, out, faces_in in (((5, 4, 3, 2), 0, (5, 4, 3)), ((4, 5, 1, 0), 3, (4, 5, 1)), ((1, 3, 5, 4), 2, (1, 3, 5))):
        got = run("hexn_tile_pr_v2", 6, pk(6, ps, out), CP2.width(6), [(faces_in[0], 3, 111), (faces_in[1], 3, 222), (faces_in[2], 3, 333)])
        assert got.get(out) == ref[1], (ps, out, got, ref)
