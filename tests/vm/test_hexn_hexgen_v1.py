"""tests/vm/test_hexn_hexgen_v1.py - the HEX pattern generator (tools/hexn_pattern_gen_hex_v1.py) end to end in the Verilog simulator (3 Nov 2026): plan on the hex planner -> icm-hexn-v4 program -> hexn_pattern_top at six faces -> config chain loaded -> words in, words out,
compared with the hex VM (hexn_vm_v7). Words must be equal; the start clock minus the VM tick must be the same constant for every word."""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_wrgrid_hex_v3 as H, hexn_icm_export_v4 as X, hexn_vm_v7 as V, hexn_pattern_gen_hex_v1 as G
N = H.Node9
MIX = {"UN": 2, "AL": 3, "JN": 4, "BR": 1, "MG": 1, "PR": 4}
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")


def _types(n, off, mix=MIX):
    H.OFFSET = off; wc = H.Grid12(n, n).work_cells(); seq = []; c = dict(mix)
    while any(c.values()):
        for k in list(c):
            if c[k]: seq.append(k); c[k] -= 1
    return {w: t for w, t in zip(wc, (seq + ["AL"] * len(wc))[:len(wc)])}


def rtl_run(ref, program, inputs, nclk=700):
    """inputs {name: [(start, word)]} -> {output name: [(start clock, word)]}"""
    words, widths = G.load_words(ref, program); bits = G.chain_bits(words, widths)
    R = ref["rows"]; d = tempfile.mkdtemp(prefix="hg_")
    try:
        open(os.path.join(d, "top.v"), "w").write(G.generate(ref))
        per = {}
        for nm, evs in inputs.items():
            r = program["pads_in"][nm][0]
            for s, w in evs:
                for i in range(32):
                    dd, ff = per.get(s + i, (0, 0))
                    if (w >> i) & 1: dd |= 1 << r
                    if i == 0: ff |= 1 << r
                    per[s + i] = (dd, ff)
        L = ["`timescale 1ns/1ps", "module tb; reg clk=0; always #5 clk=~clk; reg clear=0,cfg_en=0,cfg_in=0; reg [%d:0] wd=0, wf=0; wire [%d:0] ed, ef; wire co; integer t=0, i;" % (R - 1, R - 1),
             "hexn_pattern_top u (.clk(clk),.clear(clear),.w_d(wd),.w_f(wf),.e_d(ed),.e_f(ef),.cfg_en(cfg_en),.cfg_in(cfg_in),.cfg_out(co));",
             "reg [%d:0] chain; initial begin chain = %d'b%s; @(posedge clk); cfg_en=1; for(i=%d;i>=0;i=i-1) begin cfg_in=chain[i]; @(posedge clk); #1; end cfg_en=0; end" % (len(bits) - 1, len(bits), "".join(str(b) for b in bits), len(bits) - 1),
             "reg go=0; initial begin repeat (%d) @(posedge clk); go=1; end" % (len(bits) + 20),
             "always @(posedge clk) if (go) begin t<=t+1; if (t > 0) $display(\"T %0d %h %h\", t, ed, ef); end",
             "always @(posedge clk) if (go) begin", "  case (t+1)"]
        for c, (dd, ff) in sorted(per.items()): L.append("   %d: begin wd <= %d; wf <= %d; end" % (c, dd, ff))
        L += ["   default: begin wd <= 0; wf <= 0; end", "  endcase", "end", "initial begin #%d $finish; end endmodule" % ((len(bits) + nclk + 60) * 10)]
        open(os.path.join(d, "tb.v"), "w").write("\n".join(L))
        c = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "o.vvp"), os.path.join(d, "tb.v"), os.path.join(d, "top.v")] + G.FILES, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:800]
        out = subprocess.run(["vvp", os.path.join(d, "o.vvp")], capture_output=True, text=True).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    tr = {}
    for l in out.splitlines():
        if l.startswith("T "): _, t, ed, ef = l.split(); tr[int(t)] = (int(ed, 16), int(ef, 16))
    res = {}
    for nm, (r, _) in program["pads_out"].items():
        for t, (ed, ef) in sorted(tr.items()):
            if (ef >> r) & 1: res.setdefault(nm, []).append((t, sum(((tr.get(t + i, (0, 0))[0] >> r) & 1) << i for i in range(32))))
    return res


def _check(nodes, ins, outs, n=7, off=2, mix=MIX, vals=None):
    ct = _types(n, off, mix); P = H.plan10(nodes, ins, outs, n, n, ct, tries=40)
    ref = G.make_ref("t%d_%d" % (n, off), n, n, off, ct)
    prog = X.from_icm(X.to_icm(X.program_of(P, ct, ref["name"])))
    inp = vals or {k: 10 * (i + 3) for i, k in enumerate(ins)}
    vm = V.HexVM(prog).run(inp); rt = rtl_run(ref, prog, {k: [(2, v)] for k, v in inp.items()})
    assert all(vm[o] for o in outs)
    for o in outs:
        assert [w for _, w in rt.get(o, [])] == [w for _, w in vm[o]], (o, rt.get(o), vm[o])
    deltas = {rt[o][i][0] - vm[o][i][0] for o in outs for i in range(len(vm[o]))}
    assert len(deltas) == 1, deltas                                              # same constant offset for every word
    return deltas


def test_add_sub_in_rtl_equals_the_hex_vm():
    _check([N("a", "add", ["x", "y"]), N("r", "sub", ["a", "z"])], ["x", "y", "z"], ["r"])


def test_four_input_priority_in_rtl_equals_the_hex_vm():
    _check([N("p", "prio", ["x", "y", "z", "w"], cfg=dict(mask=15, ranks=(0, 1, 2, 3), mode=0))], ["x", "y", "z", "w"], ["p"])


def test_branch_merge_add_on_9x9_in_rtl_equals_the_hex_vm():
    mix = {"UN": 4, "AL": 5, "JN": 11, "BR": 4, "MG": 3}
    nodes = [N("br", "branch", ["x", "y"], ["lo", "hi"], cfg=dict(route_lt=1, route_eq=1, route_gt=2, emit=3)), N("m", "merge", ["lo", "hi"], cfg=dict(mode=2)), N("r", "add", ["m", "c"])]
    _check(nodes, ["x", "y", "c"], ["r"], n=9, off=1, mix=mix, vals=dict(x=30, y=50, c=7))


def test_shift_chain_with_chosen_faces_in_rtl_equals_the_hex_vm():
    nodes = [N("a", "add", ["x", "y"]), N("b", "shl", ["a"], k=2), N("r", "sub", ["b", "z"])]
    d = _check(nodes, ["x", "y", "z"], ["r"], n=7, off=1, vals=dict(x=100, y=37, z=5))
    print("RTL start clock minus VM tick:", d)
