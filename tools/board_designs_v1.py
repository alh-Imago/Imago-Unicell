#!/usr/bin/env python3
"""tools/board_designs_v1.py -- ledger #1124: self-checking Tang Nano 20K bitstreams of designs built from an ICM by `project_assemble_v1.py -s std` (Alan 13 Oct: "build a small-ish but workable design, test in the VM, then I run it on the card").
Reuses the #1118 package (board_loops_v1: wrapper, UART line, run scripts) unchanged; adds two tests:
  std_tree4 : a 4-input sum tree (nano/examples/reduction_tree4_exit_v1.icm-hier.json) on standalone v4 shells; 6 vectors of 4 words are loaded, the 6 sums must come out in order (negative numbers included).
  std_gen_ring : the looped CORDIC with its ring control GENERATED from the ICM (nano/std_ring_control_v1.py, offset measured, N=20), not the hand layout of #1116: 20 results, quiet, a release, one more.
Line: UCT <name> res=P|F n= e= bad= to= n0= st= last= sig= w=   (n0/st are the ring fields; the tree test passes with n0=0000 and st=3 because it has no release phase).
  python3 tools/board_designs_v1.py [--out DIR] [--seed N] [--no-pnr]"""
import argparse, json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import board_loops_v1 as BL
import board_tests_v1 as bt
import looped_cordic_v1 as L
import verilog_deps_v1 as vd

TREE = os.path.join(ROOT, "nano", "examples", "reduction_tree4_exit_v1.icm-hier.json")
RING = BL.ICM
VECS = [(1, 2, 3, 4), (100, -50, 7, 0), (-1, -2, -3, -4), (1000, 2000, 3000, 4000), (123456, -654321, 42, 17), (-2147483000, -1000, 5, 5)]
ASM = BL.ASM


def sums():
    out = []
    for v in VECS:
        s = sum(v) & 0xFFFFFFFF
        out.append(s)
    return out


def tree_dut(io, ne, nb):
    """ROM-scheduled loads: input k of vector j at clock 44 + 300 j + 4 k"""
    rows = []
    for j, v in enumerate(VECS):
        for k, x in enumerate(v):
            rows.append((44 + 300 * j + 4 * k, io["input_%d" % k], x & 0xFFFFFFFF))
    case = "\n".join("        8'd%d: begin lt = 32'd%d; lc = 16'd%d; lw = 32'd%d; end" % (i, t, c, w) for i, (t, c, w) in enumerate(rows))
    return ("    wire [31:0] od; wire tv;\n"
            "    reg [7:0] k = 8'd0; reg [31:0] lt; reg [15:0] lc; reg [31:0] lw;\n"
            "    always_comb begin lt = 32'hFFFFFFFF; lc = 16'd0; lw = 32'd0; case (k)\n" + case + "\n        default: ; endcase end\n"
            "    wire ldv = started && (k < 8'd%d) && (t == lt);\n"
            "    always @(posedge clk) if (ldv) k <= k + 8'd1;\n"
            "    DUTTOP dut (.clk(clk), .rst(rst), .ld_valid(ldv), .ld_cell(lc), .ld_word(lw), .tap_valid(tv), .tap_data(od),\n"
            "                .ext_arrived(%d'b0), .ext_ack_in(%d'b0), .ext_data_in({%d{1'b0}}), .ext_fire(), .ext_data_out());\n"
            "    wire cap = tv; wire stop_now = 1'b1;\n") % (len(rows), ne, ne, nb)


_orig = BL.loop_wrapper


def tree_wrapper(name, style, params, dut_top, exp, cpb, settle, timeout):
    if style != "tree":
        return _orig(name, style, params, dut_top, exp, cpb, settle, timeout)
    BL.DUT["tree"] = tree_dut(params["io"], params["ne"], params["nb"])
    src = _orig(name, "tree", {}, dut_top, exp, cpb, settle, timeout)
    a = "    if (!phase && cnt >= 16'd%d && quiet >= SETTLE) begin phase <= 1'b1; n0 <= cnt; st0 <= stop_now; relp <= 1'b1; quiet <= 32'd0; end\n" % BL.N
    b = "    if (phase && cnt >= 16'd%d && quiet >= SETTLE) begin done <= 1'b1; st1 <= stop_now; end\n" % len(exp)
    assert a in src and b in src
    src = src.replace(a, "    if (!phase && cnt >= 16'd%d && quiet >= SETTLE) begin phase <= 1'b1; st0 <= 1'b1; st1 <= 1'b1; done <= 1'b1; end\n" % len(exp)).replace(b, "")
    c = "(n0 == 16'd%d) && st0 && st1" % BL.N
    assert c in src
    return src.replace(c, "st0 && st1")


BL.loop_wrapper = tree_wrapper


def gen(args, out):
    r = subprocess.run(ASM + args + ["--output", out], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("generator: " + r.stderr[-600:])
    return json.load(open(os.path.join(out, "GRID.json")))


def deps_of(meta, g):
    d = set()
    for m in meta["shells"]:
        d |= set(vd.deps(m, [g, os.path.join(ROOT, "fpga", "verilog")]))
    return sorted(d)


def tests(work):
    out = []
    g = os.path.join(work, "gen_tree")
    meta = gen(["-s", "std", "--icm", TREE, "--tap-io", "output", "--top", "std_tree4"], g)
    ne = len(meta["ext"])
    out.append(("std_tree4", "4-input sum tree built from the ICM (-s std): 6 vectors of 4 words (negatives, and one sum that wraps around 32 bits) give the 6 sums in order", "loop", "std_tree4",
                [os.path.join(g, "std_tree4.v")] + deps_of(meta, g), ("tree", {"io": meta["io"], "ne": ne, "nb": 32 * ne}), sums()))
    g = os.path.join(work, "gen_ring")
    meta = gen(["-s", "std", "--icm", RING, "--allow-rings", "--ring-steps", str(BL.N), "--top", "std_gen_ring"], g)
    ne = len(meta["ext"])
    io = meta["io"]
    out.append(("std_gen_ring", "looped CORDIC ring on standalone shells with the ring control GENERATED from the ICM (offset %d, reference %d): exactly %d results, quiet, one release gives one more" % (meta["ring"]["offset"], meta["ring"]["reference"], BL.N),
                "loop", "std_gen_ring", [os.path.join(g, "std_gen_ring.v")] + deps_of(meta, g),
                ("std", {"z0": L.Z0 & 0xFFFFFFFF, "zi": io["z_input"], "rel": io["ring_release"], "ne": ne, "nb": 32 * ne}), L.model(BL.N + 1)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "fpga", "board_tests_designs"))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-pnr", action="store_true")
    a = ap.parse_args()
    a.out = os.path.abspath(a.out)
    os.makedirs(a.out, exist_ok=True)
    work = tempfile.mkdtemp(prefix="bdes_")
    results = []
    for name, what, kind, top, files, spec, exp in tests(work):
        print("== " + name, flush=True)
        r = BL.build(name, what, kind, top, files, spec, exp, [], a.out, not a.no_pnr, a.seed, work)
        print("   ok: %s   %s LUT4  Fmax %s" % (r["sim_line"], r.get("lut4", "-"), r.get("fmax_mhz", "-")), flush=True)
        results.append(r)
    for fn, txt in (("run_all.bat", bt.BAT), ("board_run.py", bt.RUNPY), ("board_collect.py", bt.COLLECT), ("run_one.sh", bt.ONE), ("run_all.sh", bt.SH)):
        txt = txt.replace("to=[01] last=", "to=[01](?: n0=[0-9A-F]{4} st=[0-9A-F])? last=").replace("to=\\d last=", "to=\\d(?: n0=[0-9A-F]{4} st=[0-9A-F])? last=")
        txt = txt.replace(BL.SH_OLD, BL.SH_NEW)
        p = os.path.join(a.out, fn)
        open(p, "w", newline="\r\n" if fn.endswith(".bat") else "\n").write(txt)
        if fn.endswith(".sh"):
            os.chmod(p, 0o755)
    rows = ["| test | what | LUT4 | FF | Fmax MHz |", "|---|---|---|---|---|"] + ["| `%s` | %s | %s | %s | %s |" % (r["name"], r["what"], r.get("lut4", ""), r.get("dff", ""), r.get("fmax_mhz", "")) for r in results]
    open(os.path.join(a.out, "README.md"), "w").write(
        "# Tang Nano 20K: designs built from an ICM on the standard line (ledger #1124)\n\nPower the card up cold, then `sudo ./run_all.sh` (or `run_all.bat`); results land in `board_results.txt` / `.csv`. LED1 = PASS, LED2 = FAIL, LED3 = finished, LED0 = heartbeat. Power it OFF between sessions.\n\n"
        + "\n".join(rows) + "\n\n`std_tree4`: 6 sums expected (e=0006), n0=0000 and st=3 are fixed (no release phase). `std_gen_ring`: e=0015 (21 = 20 then one after the release), n0=0014, st=3 as for std_ring.\n\n"
        "Honest limits: simulated (UART text decoded) and timing-closed at 27 MHz; not yet on the card. The expected words are computed here (sums) or from the model (CORDIC).\n")
    print("wrote %d tests to %s" % (len(results), a.out))


if __name__ == "__main__":
    main()
