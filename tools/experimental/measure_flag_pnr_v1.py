#!/usr/bin/env python3
# STATUS (docs/STATUS_MAP.md, 9 Oct 2026): MEASUREMENT script; results are in the ledger. Re-runnable, not tested. Moved here from tools/.
"""tools/measure_flag_pnr_v1.py -- REAL place-and-route of every sub and flex cell, default vs `-nowidelut`, with a CREDIBLE Fmax (ledger #950).

Run: python3 tools/measure_flag_pnr_v1.py [--only cell,cell]     (needs yosys + yowasp-nextpnr-himbaechel-gowin; writes only under /tmp; sequential, minutes on one core)
Each cell is wrapped automatically from its own port list: every input is driven from a registered LFSR, every output is XOR-reduced into ONE registered LED pin, so the only
real IO is clk + led and the critical path is the cell's own logic between registers. (A first version of this tool built each BARE cell with its ports as IO; nextpnr then times
only register-to-register paths, and reported impossible Fmax values -- 874, 1,155, 1,493 MHz -- so that version's Fmax column was discarded and only its utilisation kept.)
Target: the Tang Nano 20K part (GW2AR-LV18QN88C8/I7, family GW2A-18C), 27 MHz. sub cells at their fixed 32 bits, flex at the card's native 18. CAVEATS: ONE run per config
(no seed sweep); Fmax is nextpnr's estimator against a modest target; single cells wrapped, not full designs; not silicon.
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/experimental/ -> repo root
sys.path.insert(0, os.path.join(ROOT, "tools"))
import flexsub_assemble_v1 as fsa  # noqa: E402

CST = 'IO_LOC "clk" 4;\nIO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=NONE;\nIO_LOC "led" 15;\nIO_PORT "led" IO_TYPE=LVCMOS33 DRIVE=8;\n'


def wrapper(path, module, fam):
    """pnr_wrap around `module`, built from its real header: widths are parsed, never guessed."""
    text = open(path).read()
    head = text[text.index("module"):text.index(");") + 2]
    ports = [(m.group(1), m.group(3), bool(m.group(2))) for m in (re.match(r"(input|output)\s+(?:wire\s+|reg\s+)?(\[[^\]]+\])?\s*(\w+)", s) for s in
             re.findall(r"(?:input|output)\s+(?:wire\s+|reg\s+)?(?:\[[^\]]+\]\s*)?\w+", head)) if m]
    has_width = bool(re.search(r"parameter\s+(?:\[[^\]]*\]\s*)?WIDTH", head))
    conns, decls, outs, off = [], [], [], 0
    for kind, name, multi in ports:
        if kind == "input":
            if name == "clk":
                e = "clk"
            elif name in ("rst", "freeze_in"):
                e = "1'b0"
            elif name == "cfg_valid":
                e = "cfgv"
            elif multi:
                e = f"l[{off % 224} +: 32]"; off += 32
            else:
                e = f"l[{off % 255}]"; off += 1
        else:
            w = "[31:0] " if multi else ""
            decls.append(f"  wire {w}o_{name};"); outs.append(f"o_{name}"); e = f"o_{name}"
        conns.append(f".{name}({e})")
    params = ["CELL_ID(16'd1)"] + ([f"WIDTH({18 if fam == 'flex' else 32})"] if has_width else [])
    reduce = " ^ ".join(f"(^{o})" for o in outs) or "1'b0"
    return ("module pnr_wrap(input clk, output reg led);\n  reg [255:0] l = 256'hACE1ACE1DEADBEEF0123456789ABCDEF5A5A5A5AC3C3C3C3F00FF00F12345678FEDCBA9876543210;\n"
            "  reg [7:0] cnt = 0; reg cfgv = 0;\n  always @(posedge clk) begin l <= {l[254:0], l[255]^l[253]^l[250]^l[245]}; cnt <= cnt + 1; cfgv <= (cnt == 3); end\n"
            + "\n".join(decls) + f"\n  {module} #({', '.join('.' + p for p in params)}) dut ({', '.join(conns)});\n  always @(posedge clk) led <= {reduce};\nendmodule\n")


def run(fam, cell, flag, tmp):
    base = os.path.join(tmp, f"{fam}_{cell}_{int(flag)}")
    rec = fsa.assemble_flexsub(fam, cell, 1, base, width_arg=18 if fam == "flex" else None, nowidelut=flag)
    module = fsa.cell_module(fsa.normalise_cell_name(cell), fam)
    files = [f for f in os.listdir(base) if f.endswith(".v") and not f.startswith("tb_") and f != rec["top"] + ".v"]
    open(os.path.join(base, "pnr_wrap.v"), "w").write(wrapper(os.path.join(base, module + ".v"), module, fam))
    open(os.path.join(base, "pnr.cst"), "w").write(CST)
    y = subprocess.run(["yosys", "-p", f"read_verilog -sv pnr_wrap.v {' '.join(files)}; hierarchy -top pnr_wrap; synth_gowin -top pnr_wrap{' -nowidelut' if flag else ''} -json w.json"],
                       cwd=base, capture_output=True, text=True)
    if not os.path.exists(os.path.join(base, "w.json")):
        return None
    t = subprocess.run(["yowasp-nextpnr-himbaechel-gowin", "--device", "GW2AR-LV18QN88C8/I7", "--vopt", "family=GW2A-18C", "--vopt", "cst=pnr.cst", "--json", "w.json", "--write", "w_r.json",
                        "--freq", "27", "--timing-allow-fail"], cwd=base, capture_output=True, text=True)
    t = t.stdout + t.stderr
    util = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s*Info:\s+(LUT4|MUX2_LUT5|MUX2_LUT6|MUX2_LUT7|MUX2_LUT8|ALU|DFF):\s+(\d+)/", t, re.M)}
    fm = re.findall(r"Max frequency for clock\s+'[^']*':\s+([\d.]+) MHz", t)
    if not fm:
        return None
    return util.get("LUT4", 0), sum(v for k, v in util.items() if k.startswith("MUX2")), util.get("ALU", 0), util.get("DFF", 0), float(fm[-1])


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    tmp = tempfile.mkdtemp(prefix="flagpnr_")
    print("real P&R of LFSR-wrapped cells, Tang Nano 20K, 27 MHz target.   columns: LUT4 / MUX2 / ALU / DFF / Fmax MHz   (the wrapper adds ~+256 DFF and a few LUT to every row)\n", flush=True)
    rows = []
    for fam in ("sub", "flex"):
        print(f"{fam.upper()} ({'fixed 32-bit' if fam == 'sub' else 'native 18-bit'}):", flush=True)
        for cell in fsa.cells_for(fam):
            if only and cell not in only:
                continue
            try:
                a, b = run(fam, cell, False, tmp), run(fam, cell, True, tmp)
            except Exception as e:
                print(f"  {cell:12s} (not built: {str(e)[:80]})", flush=True)
                continue
            if not a or not b:
                print(f"  {cell:12s} (no timing result: yosys or place-and-route did not complete)", flush=True)
                continue
            rows.append((fam, cell, a, b))
            print(f"  {cell:12s} default {a[0]:>5}/{a[1]:>5}/{a[2]:>3}/{a[3]:>4} {a[4]:>6.1f}   nowidelut {b[0]:>5}/{b[1]:>3}/{b[2]:>3}/{b[3]:>4} {b[4]:>6.1f}   "
                  f"LUT4 {a[0] / b[0] if b[0] else float('nan'):.2f}x  Fmax {b[4] / a[4]:.2f}x", flush=True)
    slower = [r for r in rows if r[3][4] < 0.95 * r[2][4]]
    print(f"\nSUMMARY: {len(rows)} cells; Fmax with the flag is more than 5% LOWER in {len(slower)}: {[(r[0], r[1], round(r[3][4] / r[2][4], 2)) for r in slower]}")
    print(f"         total LUT4 default {sum(r[2][0] for r in rows)}, nowidelut {sum(r[3][0] for r in rows)}")


if __name__ == "__main__":
    sys.exit(main())
