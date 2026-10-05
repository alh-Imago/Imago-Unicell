#!/usr/bin/env python3
"""tools/measure_synth_flow_v1.py -- REAL place-and-route of a cell under the default `synth_gowin` flow vs `-nowidelut` (ledger #949).

Run: python3 tools/measure_synth_flow_v1.py          (needs yosys and yowasp-nextpnr-himbaechel-gowin; ~2-3 minutes; writes only under /tmp)
Each cell is wrapped so only clk and one LED are real IO: an LFSR drives its inputs and the outputs are XOR-reduced to the LED, so the critical path is the cell
itself. Target: the Tang Nano 20K part from docs/man (GW2AR-LV18QN88C8/I7, family GW2A-18C), 27 MHz. Reports post-placement utilisation and nextpnr's own Fmax.
CAVEATS: ONE run per config (no seed sweep); Fmax is nextpnr's estimator against a modest 27 MHz target; a wrapper, not a full design; not silicon.
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB = os.path.join(ROOT, "sub", "verilog")
HDR = ("module pnr_wrap(input clk, output reg led);\n  reg [63:0] l = 64'hACE1ACE1DEADBEEF; reg [7:0] cnt = 0; reg cfgv = 0;\n"
       "  always @(posedge clk) begin l <= {l[62:0], l[63]^l[62]^l[60]^l[59]}; cnt <= cnt + 1; cfgv <= (cnt == 3); end\n  wire [31:0] y; wire v, ack;\n")
WRAP = {"mul": (HDR + "  mul_cell_v4s dut (.clk(clk), .rst(1'b0), .cfg_valid(cfgv), .cfg_data(32'h0), .in_a(l[31:0]), .in_b(l[63:32]), .valid_in(1'b1), .data_out(y), .valid_out(v));\n"
                "  always @(posedge clk) led <= ^y ^ v;\nendmodule\n", [f"{SUB}/mul_cell_v4s.v", f"{ROOT}/fpga/verilog/bitwise_multiplier_32bit.v"]),
        "nano": (HDR + "  nano_cell_v4sa dut (.clk(clk), .rst(1'b0), .freeze_in(1'b0), .cfg_valid(cfgv), .cfg_data({22'b0, l[41:32]}), .hold_in_data(l[31:0]), .load_hold(l[50]), "
                 ".flow_in_data({l[15:0], l[63:48]}), .valid_in(l[51]), .ack_out(ack), .data_out(y), .valid_out(v), .ack_in(l[52]));\n"
                 "  always @(posedge clk) led <= ^y ^ v ^ ack;\nendmodule\n", [f"{SUB}/nano_cell_v4sa.v"])}
CST = 'IO_LOC "clk" 4;\nIO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=NONE;\nIO_LOC "led" 15;\nIO_PORT "led" IO_TYPE=LVCMOS33 DRIVE=8;\n'


def main():
    tmp = tempfile.mkdtemp(prefix="synthflow_")
    open(f"{tmp}/pnr.cst", "w").write(CST)
    procs = []
    for cell, (text, files) in WRAP.items():
        open(f"{tmp}/wrap_{cell}.v", "w").write(text)
        for tag, flags in (("def", ""), ("nw", "-nowidelut")):
            n = f"{cell}_{tag}"
            cmd = (f"yosys -p 'read_verilog -sv wrap_{cell}.v {' '.join(files)}; hierarchy -top pnr_wrap; synth_gowin -top pnr_wrap {flags} -json {n}.json' > {n}.ylog 2>&1 && "
                   f"yowasp-nextpnr-himbaechel-gowin --device GW2AR-LV18QN88C8/I7 --vopt family=GW2A-18C --vopt cst=pnr.cst --json {n}.json --write {n}_r.json --freq 27 "
                   f"--timing-allow-fail > {n}.log 2>&1")
            procs.append(subprocess.Popen(cmd, shell=True, cwd=tmp))
    for p in procs:
        p.wait()
    print("real place-and-route on GW2AR-18 (Tang Nano 20K), 27 MHz target     [LUT4 / MUX2_LUT (all) / ALU / DFF]   Fmax")
    for cell in WRAP:
        for tag, lab in (("def", "default synth_gowin"), ("nw", "-nowidelut")):
            try:
                t = open(f"{tmp}/{cell}_{tag}.log", errors="replace").read()
                blk = t.split("Device utilisation:")[-1][:1000]
                u = {m.group(1).strip(): int(m.group(2)) for m in re.finditer(r"^\s*Info:\s+(\w[\w ]*?):\s+(\d+)/\s*\d+\s+\d+%", blk, re.M)}
                fm = re.findall(r"Max frequency for clock\s+'[^']*':\s+([\d.]+) MHz", t)
                mux = sum(v for k, v in u.items() if k.startswith("MUX2_LUT"))
                print(f"  {cell:5s} {lab:20s} {u.get('LUT4', '?'):>5} / {mux:>5} / {u.get('ALU', '?'):>3} / {u.get('DFF', '?'):>4}    {fm[-1] if fm else '?'} MHz")
            except FileNotFoundError:
                print(f"  {cell:5s} {lab:20s} (no log: yosys or nextpnr failed -- see {tmp}/{cell}_{tag}.ylog)")


if __name__ == "__main__":
    sys.exit(main())
