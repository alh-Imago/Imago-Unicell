"""hexn_busnet_cost2_v1 (8 Nov 2026): cost of the MERGED design (serialisers, mergers, buses, tables, cells, feedback, map matcher), synthesised as a whole with yosys synth_xilinx. Alan 22:08, direction doc section 44. Synthesis counts only: no placement, no routing, no timing. Companion of hexn_busnet_cost_v1 (untouched).
Usage: python3 tools/hexn_busnet_cost2_v1.py"""
import os, re, subprocess, tempfile, math, shutil

HERE = os.path.dirname(os.path.abspath(__file__)); VD = os.path.join(HERE, "..", "sub", "verilog")
FILES = ("hexn_bnet_bus_v2.v", "hexn_bnet_ser_v1.v", "hexn_bnet_tbus_v1.v", "hexn_bnet_net_v1.v", "hexn_bnet_map_v1.v")
CHIP = dict(lut=597200, ff=597200, ramb36=955); BASE = dict(lut=19100, ff=14153, ramb36=10)


def synth(top, params):
    with tempfile.TemporaryDirectory(dir=os.environ.get("HEXN_SYNTH_TMP", tempfile.gettempdir())) as d:
        for f in FILES:
            t = open(os.path.join(VD, f)).read()
            if f.startswith(top):                       # the top module's own parameter defaults are replaced (chparam is not usable before elaboration here)
                for k, v in params.items(): t = re.sub(r"parameter %s = \d+" % k, "parameter %s = %d" % (k, v), t, count=1)
            open(os.path.join(d, f), "w").write(t)
        out = subprocess.run(["yosys", "-q", "-p", "read_verilog -sv %s; hierarchy -top %s; synth_xilinx -flatten -top %s; tee -o stat.txt stat" % (" ".join(FILES), top, top)], capture_output=True, text=True, cwd=d)
        if out.returncode: raise RuntimeError(out.stderr[-2500:])
        s = open(os.path.join(d, "stat.txt")).read()
    def cnt(pat): return sum(int(x) for x in re.findall(r"^\s*(\d+)\s+%s\b" % pat, s, re.M))
    return dict(lut=sum(cnt("LUT%d" % i) for i in range(1, 7)), ff=cnt("FDRE") + cnt("FDSE") + cnt("FDCE") + cnt("FDPE"), ramb36=cnt("RAMB36E1"), ramb18=cnt("RAMB18E1"),
                lutram=sum(cnt(p) for p in ("RAM32M", "RAM64M", "RAM32X1D", "RAM64X1D", "RAM128X1D", "RAM32X1S", "RAM64X1S", "RAM128X1S", "RAM256X1S", "RAM256X1D")), carry=cnt("CARRY4"), dsp=cnt("DSP48E1"))


def row(lab, r): print("   %-46s %8d %7d %7d %7d %8d %5d %5.2f%%" % (lab, r["lut"], r["ff"], r["ramb36"], r["ramb18"], r["lutram"], r["dsp"], 100.0 * r["lut"] / CHIP["lut"]))


def main():
    print("   %-46s %8s %7s %7s %7s %8s %5s %6s" % ("merged design (yosys, whole netlist)", "LUT", "FF", "RAMB36", "RAMB18", "LUTRAM", "DSP", "%LUT"))
    for g, per, sql in ((4, 16, 3), (4, 16, 5), (8, 8, 3), (16, 4, 3), (16, 4, 2)):
        r = synth("hexn_bnet_net_v1", dict(G=g, PER=per, NIN=48, FB=1, SQL=sql)); row("3 x 64 cells, %d buses of %d, sub-queue %d, with feedback" % (g, per, 1 << sql), r)
    r = synth("hexn_bnet_net_v1", dict(G=4, PER=16, NIN=48, FB=0, SQL=3)); row("3 x 64 cells, 4 buses of 16, sub-queue 8, NO feedback", r)
    for m in (16, 64):
        r = synth("hexn_bnet_map_v1", dict(NB=128, M=m, MW=int(math.log2(m)))); row("map matcher, 128-bit maps, %d stored maps" % m, r)


if __name__ == "__main__": main()
