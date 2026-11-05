#!/usr/bin/env python3
"""Kintex BASE generator v3 (5 Nov 2026: clone of hexn_kxbase_v2.py; uses hexn_base_ctl_v3 = data RAM and run-from-RAM; environment HEXN_DA, data RAM address bits, default 9). Earlier text of v2:) (5 Nov 2026: clone of hexn_kxbase_v1.py; uses hexn_frame_v7 and hexn_base_ctl_v3 = results RAM; environment HEXN_RA (record address bits, default 10) and HEXN_RMARGIN (default 16) set the results RAM size and the stop-and-flag margin). Earlier text:) (5 Nov 2026, Alan 10:53: judge and several pattern arrays in one bitstream; before / during / after as a program state).
Builds hexn_arr_core (the module the board top fpga/ypcb/hexn_arr/hexn_arr.v and the byte-port testbench already use) as: NARR copies of hexn_frame_v7 (one per pattern array, each with its own renamed pattern/xtop/frame modules so different patterns can sit in one design) + hexn_base_ctl_v3 (selector, 4-slot program library, judge hexn_scorer_v3 with an AFTER-mode queue). Commands: see sub/verilog/hexn_base_ctl_v3.v.
usage: hexn_kxbase_v3.py sim   REF1.json [REF2.json ...] OUTDIR   -> OUTDIR/src for iverilog
       hexn_kxbase_v3.py build BUILDDIR REF1.json [REF2.json ...]  -> BUILDDIR/gen_00_hexn_arr.v for the ypcb build flow (prebuild of fpga/ypcb/hexn_arr when HEXN_BASE is set)
Environment HEXN_NORAM (1, ram, srl) as in hexn_kxarr_v1.py; HEXN_LIBREG=1 also makes the program library flip-flops (default: one block RAM); for the judge's weight RAMs it makes them flip-flops (the open flow's inferred RAM32M is suspect). Nothing here touches a board."""
import json, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import hexn_pattern_gen_hex_v1 as P, hexn_kxarr_v1 as K
SV = os.path.join(ROOT, "sub", "verilog"); RV = os.path.join(ROOT, "rtl"); FV = os.path.join(ROOT, "fpga", "verilog")


def ren(text, names, i):
    for n in names: text = re.sub(r"\b%s\b" % n, "%s_a%d" % (n, i), text)
    return text


def read(f): return open(f).read()


def judge_text():
    t = read(os.path.join(FV, "hexn_scorer_v3.v"))
    if os.environ.get("HEXN_NORAM", "") in ("1", "ram"):
        t = t.replace("reg signed [7:0] m0 [0:127];", '(* ram_style = "registers" *) reg signed [7:0] m0 [0:127];').replace("reg signed [7:0] m1 [0:127];", '(* ram_style = "registers" *) reg signed [7:0] m1 [0:127];')
    return t


def ctl_text():
    t = read(os.path.join(SV, "hexn_base_ctl_v3.v"))
    if os.environ.get("HEXN_LIBREG") == "1":                                                   # library as flip-flops too (8,192 of them); by default it is block RAM
        t = t.replace('(* ram_style = "block" *) reg [7:0] lib [0:1023];', '(* ram_style = "registers" *) reg [7:0] lib [0:1023];')
    if os.environ.get("HEXN_LIBREG") == "1":
        t = t.replace('(* ram_style = "block" *) reg [63:0] res [0:(1<<RA)-1];', '(* ram_style = "registers" *) reg [63:0] res [0:(1<<RA)-1];').replace('(* ram_style = "block" *) reg [63:0] dat [0:(1<<DA)-1];', '(* ram_style = "registers" *) reg [63:0] dat [0:(1<<DA)-1];')
    if os.environ.get("HEXN_NORAM", "") in ("1", "ram"):
        t = t.replace("reg [31:0] af [0:3];", '(* ram_style = "registers" *) reg [31:0] af [0:3];').replace("reg [31:0] rq [0:7];", '(* ram_style = "registers" *) reg [31:0] rq [0:7];')
    return t


def parts(refs):
    """-> list of (name, text) in dependency order, the core text last"""
    out = []; seen = set(); nr = os.environ.get("HEXN_NORAM", "")
    fix = (lambda x: K.no_ram(x, nr)) if nr else (lambda x: x)
    for f in P.FILES + [os.path.join(SV, "hexn_cross_v2.v")]:
        if f not in seen: seen.add(f); out.append((os.path.basename(f), fix(read(f))))
    chb = []; inst = []
    for i, ref in enumerate(refs):
        pr = P.check_reference(ref)
        if pr: raise SystemExit("reference %d refused: %s" % (i, pr))
        pat = ren(P.generate(ref), ["hexn_pattern_top"], i)
        xt = ren(fix(read(os.path.join(SV, "hexn_xtop_v2.v"))), ["hexn_xtop_v2", "hexn_pattern_top"], i)
        fr = ren(fix(read(os.path.join(SV, "hexn_frame_v7.v"))), ["hexn_frame_v7", "hexn_xtop_v2"], i)
        out += [("pattern_a%d.v" % i, pat), ("xtop_a%d.v" % i, xt), ("frame_a%d.v" % i, fr)]
        chb.append(K.chain_len(ref) // 8 + (1 if K.chain_len(ref) % 8 else 0))
        inst.append("    hexn_frame_v7_a%d #(.ROWS(%d), .CHAIN_BITS(%d), .PATTERN_ID(32'h%s)) f%d (.clk(clk), .rx_d(a_rx_d), .rx_v(a_rx_v[%d]), .tx_dout(a_tx_d[%d +: 8]), .tx_s(a_tx_s[%d]), .tx_b(tx_b), .led(l%d), .o_v(a_ov[%d]), .o_d(a_od[%d +: 32]), .o_idle(a_idle[%d]), .o_t(a_ot[%d +: 16]), .o_r(a_or[%d +: 3]));"
                    % (i, ref["rows"], K.chain_len(ref), ref["pattern_id_hex"], i, i, 8 * i, i, i, i, 32 * i, i, 16 * i, 3 * i))
    n = len(refs)
    if n > 4: raise SystemExit("at most 4 arrays")
    chbp = "{%s}" % ", ".join("16'd%d" % c for c in reversed(chb + [0] * (4 - n)))
    core = ("`default_nettype none\n// hexn_arr_core (BASE): %d array(s) %s + judge + library, generated by tools/hexn_kxbase_v3.py; do not edit.\n"
            "module hexn_arr_core (input wire clk, input wire [7:0] rx_d, input wire rx_v, output wire [7:0] tx_dout, output wire tx_s, input wire tx_b, output wire [5:0] led);\n"
            "    wire [%d:0] a_rx_v; wire [7:0] a_rx_d; wire [%d:0] a_tx_d; wire [%d:0] a_tx_s, a_ov, a_idle; wire [%d:0] a_od; wire [%d:0] a_ot; wire [%d:0] a_or;\n"
            "%s\n"
            "    hexn_base_ctl_v3 #(.NARR(%d), .DA(%s), .RA(%s), .RMARGIN(%s), .CHB(%s)) ctl (.clk(clk), .rx_d(rx_d), .rx_v(rx_v), .tx_d(tx_dout), .tx_s(tx_s), .tx_b(tx_b), .a_rx_v(a_rx_v), .a_rx_d(a_rx_d), .a_tx_d(a_tx_d), .a_tx_s(a_tx_s), .a_ov(a_ov), .a_od(a_od), .a_idle(a_idle), .a_ot(a_ot), .a_or(a_or));\n"
            "    assign led = l0;\nendmodule\n")
    decl = "    " + "".join("wire [5:0] l%d; " % i for i in range(n)) + "\n"
    core = core % (n, ",".join(r["pattern_id_hex"] for r in refs), n - 1, 8 * n - 1, n - 1, 32 * n - 1, 16 * n - 1, 3 * n - 1, decl + "\n".join(inst), n, os.environ.get("HEXN_DA", "9"), os.environ.get("HEXN_RA", "10"), os.environ.get("HEXN_RMARGIN", "16"), chbp)
    out += [("hexn_scorer_v3.v", judge_text()), ("hexn_base_ctl_v3.v", ctl_text()), ("hexn_arr_core.v", core)]
    return out


def main():
    cmd = sys.argv[1]
    if cmd == "sim":
        outd = sys.argv[-1]; refs = [json.load(open(p)) for p in sys.argv[2:-1]]; src = os.path.join(outd, "src"); os.makedirs(src, exist_ok=True)
        for n, t in parts(refs): open(os.path.join(src, n), "w").write(t)
        print("sim sources in", src)
    elif cmd == "build":
        outd = sys.argv[2]; refs = [json.load(open(p)) for p in sys.argv[3:]]; os.makedirs(outd, exist_ok=True)
        txt = ["// ---- %s ----\n%s\n" % (n, t) for n, t in parts(refs)] + ["// ---- hexn_jtag_bridge_v1.v ----\n" + read(os.path.join(RV, "hexn_jtag_bridge_v1.v")) + "\n"]
        open(os.path.join(outd, "gen_00_hexn_arr.v"), "w").write("".join(txt)); print("wrote", os.path.join(outd, "gen_00_hexn_arr.v"), "base with", len(refs), "array(s)")
    else: raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
