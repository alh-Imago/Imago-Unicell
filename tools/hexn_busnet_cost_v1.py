"""hexn_busnet_cost_v1 (8 Nov 2026): first cost estimate of the bus network on the Kintex card, and what it says about scale. Alan 21:32 (direction doc section 43).
Method: (1) the bus module sub/verilog/hexn_bnet_bus_v1.v (cross-checked against the Python model by tests/vm/test_hexn_bnet_bus_v1.py) is synthesised with yosys synth_xilinx for several shapes; LUT, flip-flop and block RAM counts are READ from the yosys report (synthesis only: not placed, not routed, no timing). (2) Totals for a three-layer net are assembled from those per-bus numbers. (3) Scale: how many cells per layer fit the chip's block RAM, with the table kept as a dense matrix (one row per source id).
Chip figures: XC7K480T, 597,200 LUT sites and 597,200 flip-flops as nextpnr counts them in this repository, 955 RAMB36 (35,205,120 RAM bits / 36,864). Base on the card today (nextpnr, section 4 of the base picture): about 19,100 LUT sites, 14,153 flip-flops, a few RAMB36 (1 KB library, 8 KB results RAM, 4 KB data RAM: reserve 10 here).
NOT included in any figure: the merger that lets several fired cells reach one bus queue (one push per clock per bus in the module), the fan-out wiring between layers, the JTAG host path to the tables, clock and I/O, routing congestion. Usage: python3 tools/hexn_busnet_cost_v1.py"""
import os, re, subprocess, sys, tempfile, math

HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "..", "sub", "verilog", "hexn_bnet_bus_v1.v")
CHIP = dict(lut=597200, ff=597200, ramb36=955); BASE = dict(lut=19100, ff=14153, ramb36=10)


def synth(per, nsrc, idw, ql, sync=1):
    top = "t_%d_%d_%d_%d" % (per, nsrc, idw, ql); cp = max(1, math.ceil(math.log2(per)))
    wrapper = """module %s(input wire clk, input wire tick, input wire push_v, input wire [%d:0] push_id, input wire wr_en, input wire [%d:0] wr_addr, input wire [%d:0] wr_data,
      input wire thw_en, input wire [%d:0] thw_idx, input wire [3:0] thw_val, input wire rclr, input wire [%d:0] rate_idx, output wire [7:0] rate_q, output wire [%d:0] fire, output wire [15:0] dropped);
      hexn_bnet_bus_v1 #(.PER(%d), .NSRC(%d), .IDW(%d), .QL(%d), .REFR(3), .SYNC(%d)) u(.*);
    endmodule""" % (top, idw - 1, idw - 1, per * 4 - 1, cp - 1, cp - 1, per - 1, per, nsrc, idw, ql, sync)
    # yosys here is the YoWASP build: it can only see the directory it runs in, so everything is copied there and named relatively
    with tempfile.TemporaryDirectory(dir=os.environ.get("HEXN_SYNTH_TMP", tempfile.gettempdir())) as d:
        open(os.path.join(d, "w.v"), "w").write(wrapper); open(os.path.join(d, "bus.v"), "w").write(open(V).read())
        out = subprocess.run(["yosys", "-q", "-p", "read_verilog -sv bus.v w.v; synth_xilinx -flatten -top %s; tee -o stat.txt stat" % top], capture_output=True, text=True, cwd=d)
        if out.returncode: raise RuntimeError(out.stderr[-2000:])
        s = open(os.path.join(d, "stat.txt")).read()
    def cnt(pat): return sum(int(x) for x in re.findall(r"^\s*(\d+)\s+%s\b" % pat, s, re.M))
    lut = sum(cnt("LUT%d" % i) for i in range(1, 7)); ff = cnt("FDRE") + cnt("FDSE") + cnt("FDCE") + cnt("FDPE")
    return dict(lut=lut, ff=ff, ramb36=cnt("RAMB36E1"), ramb18=cnt("RAMB18E1"), lutram=cnt("RAM32M") + cnt("RAM64M") + cnt("RAM32X1D") + cnt("RAM64X1D") + cnt("RAM128X1D") + cnt("RAM32X1S") + cnt("RAM64X1S") + cnt("RAM128X1S"), carry=cnt("CARRY4"))


def net_cost(groups, qdepth_log, per_cells=64, nin=48):
    per = per_cells // groups; idw1 = math.ceil(math.log2(nin + per_cells)); idw23 = math.ceil(math.log2(per_cells))
    b1 = synth(per, 1 << idw1, idw1, qdepth_log); b2 = synth(per, 1 << idw23, idw23, qdepth_log)
    tot = {k: groups * (b1[k] + 2 * b2[k]) for k in b1}; tot["buses"] = 3 * groups; tot["cells"] = 3 * per_cells; return tot, b1, b2


def scale(n, per=16, layers=3, nin=48):
    """dense tables: layer l bus has one row per source (layer 1: nin + n feedback sources; layers 2,3: n sources) of 4*per bits; RAMB36 holds 512 rows of up to 72 bits"""
    buses = n // per; rows1 = nin + n; rows = n
    r36 = buses * (math.ceil(rows1 / 512) + 2 * math.ceil(rows / 512)); return buses * 3, r36


def main():
    global B16
    B16 = synth(16, 128, 7, 3)
    print("1. Synthesis of one bus (yosys synth_xilinx, SYNC=1 so the table can map to block RAM)")
    print("   %-34s %6s %6s %7s %7s %8s %6s" % ("bus", "LUT", "FF", "RAMB36", "RAMB18", "LUTRAM", "CARRY4"))
    for per, nsrc, idw, ql in ((16, 128, 7, 3), (16, 64, 6, 3), (16, 64, 6, 5), (8, 128, 7, 3), (8, 64, 6, 3), (4, 128, 7, 3), (4, 64, 6, 3)):
        r = synth(per, nsrc, idw, ql); print("   %-34s %6d %6d %7d %7d %8d %6d" % ("%d cells, %d rows, queue %d" % (per, nsrc, 1 << ql), r["lut"], r["ff"], r["ramb36"], r["ramb18"], r["lutram"], r["carry"]))
    print("\n2. The 3 x 64 cell network (as in sections 41 and 42) assembled from those buses")
    print("   %-30s %7s %8s %7s %8s %7s %8s %9s" % ("shape", "buses", "LUT", "FF", "RAMB36", "RAMB18", "LUTRAM", "%LUT chip"))
    for groups, ql in ((4, 3), (4, 5), (8, 3), (8, 4), (16, 3), (16, 2)):
        t, b1, b2 = net_cost(groups, ql); print("   %-30s %7d %8d %7d %8d %7d %8d %8.2f%%" % ("%d buses/layer, queue %d" % (groups, 1 << ql), t["buses"], t["lut"], t["ff"], t["ramb36"], t["ramb18"], t["lutram"], 100.0 * t["lut"] / CHIP["lut"]))
    print("\n3. Scale: cells per layer N (3 layers, 16 cells per bus, dense tables in block RAM), from the 16-cell bus above (LUT %d, FF %d per bus, measured at 128 rows; the id width grows a little with N, not modelled)" % (B16["lut"], B16["ff"]))
    print("   %8s %8s %8s %10s %10s %9s %9s %9s" % ("N", "cells", "buses", "RAMB36", "% free RAM", "LUT", "% free LUT", "% free FF"))
    free = CHIP["ramb36"] - BASE["ramb36"]; fl = CHIP["lut"] - BASE["lut"]; ffr = CHIP["ff"] - BASE["ff"]
    for n in (64, 256, 512, 1024, 1536, 2048, 4096):
        b, r = scale(n); lut = b * B16["lut"]; ff = b * B16["ff"]; print("   %8d %8d %8d %10d %9.0f%% %9d %8.0f%% %8.0f%%" % (n, 3 * n, b, r, 100.0 * r / free, lut, 100.0 * lut / fl, 100.0 * ff / ffr))


if __name__ == "__main__": main()
