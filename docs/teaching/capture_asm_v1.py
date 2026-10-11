#!/usr/bin/env python3
"""Capture REAL facts about the four cell families for the teaching manual's Assembler tab.
Parses the Verilog files themselves (ports, parameters, which add-on blocks are instantiated, which
cell kinds exist per family) and runs tools/project_assemble_v1.py once per family route.
Writes docs/teaching/asm_data.json (embedded by the builder).  Run: python3 docs/teaching/capture_asm_v1.py
Sizes are NOT re-measured here (no yosys in this workspace): they are read from nano/card_fit_v1.py's
LUT4_PER_POSITION table and the Tang Nano MAN cost table, and labelled as quoted.
"""
import json, os, re, subprocess, sys, tempfile, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FV, SV = os.path.join(REPO, "fpga", "verilog"), os.path.join(REPO, "sub", "verilog")
TMP = tempfile.mkdtemp()
sys.path[:0] = [os.path.join(REPO, "nano"), os.path.join(REPO, "tools")]

def strip(t): return re.sub(r"/\*.*?\*/", "", re.sub(r"//.*", "", t), flags=re.S)

def parse_module(path, name):
    t = strip(open(path).read())
    m = re.search(r"module\s+" + name + r"\s*(#\s*\((.*?)\))?\s*\((.*?)\)\s*;", t, re.S)
    params = re.findall(r"parameter\s*(?:\[[^\]]*\])?\s*(\w+)\s*=\s*([^,\n)]+)", m.group(2) or "")
    ports = []
    for d, body in re.findall(r"\b(input|output)\s+(?:wire\s+|reg\s+)?((?:\[[^\]]+\]\s*)?[^;]*?)(?=\binput\b|\boutput\b|$)", m.group(3) + " input", re.S):
        w = re.match(r"\[([^\]]+)\]", body.strip()); width = w.group(1) if w else None
        names = [n.strip() for n in re.sub(r"\[[^\]]+\]", "", body).replace("\n", " ").split(",") if n.strip()]
        for n in names: ports.append({"dir": d, "name": n.split()[-1], "width": width})
    return params, ports, t

def bits(w):
    if w is None: return 1
    m = re.match(r"(\d+)\s*:\s*0", w)
    return int(m.group(1)) + 1 if m else None   # None = depends on a parameter

FAMS = [
 {"key": "v4",  "name": "Standalone", "tag": "v4",  "dir": FV, "suffix": "_cell_v4.v",  "adder": "adder_cell_v4"},
 {"key": "v4c", "name": "Carrier",    "tag": "v4c", "dir": FV, "suffix": "_cell_v4c.v", "adder": "adder_cell_v4c"},
 {"key": "v4s", "name": "Sub (stripped)", "tag": "v4s", "dir": SV, "suffix": "_cell_v4s.v", "adder": "adder_cell_v4s"},
 {"key": "v4sa","name": "Flex",       "tag": "v4sa","dir": SV, "suffix": "_cell_v4sa.v","adder": "adder_cell_v4sa"},
]
out = {"families": []}
for f in FAMS:
    kinds = sorted(n[:-len(f["suffix"])] for n in os.listdir(f["dir"]) if n.endswith(f["suffix"]) and not n.startswith("tb_"))
    # nano_gate_v4.v / nano_gate_v4c.v have a different suffix
    if f["key"] in ("v4", "v4c"):
        g = "nano_gate_" + f["tag"] + ".v"
        if os.path.exists(os.path.join(f["dir"], g)): kinds = sorted(kinds + ["nano_gate"])
    if f["key"] in ("v4s", "v4sa") and os.path.exists(os.path.join(f["dir"], "shift_stage_" + f["tag"] + ".v")):
        kinds = sorted(kinds + ["shift_stage"])
    path = os.path.join(f["dir"], f["adder"] + ".v")
    params, ports, text = parse_module(path, f["adder"])
    names = [p["name"] for p in ports]
    ins = [p for p in ports if p["dir"] == "input"]; outs = [p for p in ports if p["dir"] == "output"]
    def tot(ps):
        s = 0; sym = False
        for p in ps:
            b = bits(p["width"])
            if b is None: sym = True; b = 0
            s += b
        return s, sym
    ti, si = tot(ins); to, so = tot(outs)
    cfg = next((p for p in ports if p["name"] == "cfg_data"), None)
    feat = {
      "cardinal_ports": "data_in_n" in names,
      "ack": any(n.startswith("ack_") or n == "ack_in" for n in names),
      "ready": "ready_out" in names,
      "freeze": "freeze_in" in names,
      "live_reprogram": "program_in" in names,
      "cfg_bits": bits(cfg["width"]) if cfg else None,
      "width_param": any(k == "WIDTH" for k, v in params),
      "second_port_param": any(k == "SECOND_PORT" for k, v in params),
      "second_output": bool(re.search(r"second_output|SECOND_PORT", text)),
      "builds_in_addon_chain": bool(re.search(r"\b(nibble_mask_addon|shift_lane_addon|invert_addon)\w*\s+\w+\s*\(", text)),
    }
    tb = sum(1 for n in os.listdir(f["dir"]) if n.startswith("tb_") and re.search(r"_" + f["tag"] + r"(_|\.v)", n))
    out["families"].append({**{k: f[k] for k in ("key", "name", "tag")}, "kinds": kinds, "testbenches": tb,
        "adder_module": f["adder"], "adder_params": [list(p) for p in params],
        "adder_ports": {"inputs": len(ins), "outputs": len(outs), "in_bits": ti, "out_bits": to, "symbolic_width": si or so,
                        "names": names}, "features": feat})
# carrier: cores selectable + latch layout
ct = open(os.path.join(FV, "unicell_vix_carrier_v1.v")).read()
sel = re.findall(r"\b(SEL_[A-Z]+)\s*=\s*5'd(\d+)", ct)
out["carrier"] = {"module": "unicell_vix_carrier_v1", "selectable": sorted([[int(v), k[4:].lower()] for k, v in sel]),
                  "latch_bits": 160, "core_config_bits": 128,
                  "shells": sorted(n[:-len("_shell_v1c.v")] for n in os.listdir(FV) if n.endswith("_shell_v1c.v")),
                  "addon_blocks": sorted(set(n[:-5] for n in os.listdir(FV) if re.match(r"(nibble_mask|shift_lane|shift_fine|invert)_addon_v\d\.v$", n)))}
out["carrier"]["instantiates_addon_chain"] = bool(re.search(r"\b(nibble_mask_addon|shift_lane_addon|invert_addon)\w*\s+\w+\s*\(", strip(ct)))
out["carrier"]["extra_features"] = {"freeze_in": "freeze_in" in ct, "program_in": "program_in" in ct}
# the sub-family helper cells (shift / mask) exist as their own kinds
# --- quoted sizes
import card_fit_v1 as cf
tm = json.load(open(os.path.join(REPO, "docs/man/tang-nano-20k.man.json")))
out["sizes"] = {"unit": "LUT4 (yosys synth_gowin, synthesis only), quoted",
   "adder": {"v4": cf.LUT4_PER_POSITION["adder_full"], "v4c_core_lower_bound": cf.LUT4_PER_POSITION["adder_lean"],
             "v4s": 66, "v4s_source": "points ledger #898, not re-measured here",
             "v4sa_w32": tm["cell_costs"]["cells"]["adder"]["single_nowidelut"]["32"][0],
             "v4sa_w18": tm["cell_costs"]["cells"]["adder"]["single_nowidelut"]["18"][0],
             "v4sa_w4": tm["cell_costs"]["cells"]["adder"]["single_nowidelut"]["4"][0],
             "v4sa_fit": tm["cell_costs"]["fits"]["adder"]["lut4_vs_W_nowidelut"]["coeffs_high_to_low"]},
   "carrier_whole": cf.LUT4_PER_POSITION["vix_carrier_v1"],
   "standalone_full": {k[:-5]: v for k, v in cf.LUT4_PER_POSITION.items() if k.endswith("_full")},
   "standalone_lean": {k[:-5]: v for k, v in cf.LUT4_PER_POSITION.items() if k.endswith("_lean")},
   "tang_lut4_total": tm["device"]["logic"]["lut4_total"]}
# --- assembler routes
def run(args, name):
    o = os.path.join(TMP, name)
    r = subprocess.run([sys.executable, "tools/project_assemble_v1.py", *args, "--output", o], cwd=REPO, capture_output=True, text=True)
    res = {"cmd": "python3 tools/project_assemble_v1.py " + " ".join(args) + " --output DIR", "ok": r.returncode == 0, "err": r.stderr.strip()[-300:]}
    if r.returncode == 0:
        res["files"] = {f: sum(1 for _ in open(os.path.join(o, f), errors="replace")) for f in sorted(os.listdir(o))}
        res["stdout"] = r.stdout.strip().splitlines()[:4]
    return res
M = "docs/man/mustang-f100-a10.man.json"; T = "docs/man/tang-nano-20k.man.json"
out["routes"] = {
  "v4":   run(["--man", M, "--cells", "4", "-S", "adder_cell"], "r_v4"),
  "v4c":  run(["--man", M, "--cells", "4", "--shell", "vix"], "r_v4c"),
  "v4s":  run(["-s", "sub", "--icm", "nano/library_std/add.icm.json", "--man", T], "r_v4s"),
  "v4sa": run(["-s", "flex", "--icm", "nano/library_std/add.icm.json", "--man", T], "r_v4sa"),
}
# older lineage that the default (no -s) route can still array
out["older_shells"] = {k: run(["--man", M, "--cells", "4", "--shell", k], "o_" + k)["files"] for k in ("v3", "v4")}
# --- the flags: names and help text read from the tool's own --help; behaviour from real probe runs
h = subprocess.run([sys.executable, "tools/project_assemble_v1.py", "--help"], cwd=REPO, capture_output=True, text=True).stdout
opts = h.split("options:", 1)[1]
flags = []
for blk in re.split(r"\n(?=  -)", opts):
    lines = blk.strip("\n").splitlines()
    if not lines: continue
    head = lines[0].strip(); names = re.findall(r"(--?[A-Za-z][\w-]*)", head.split("  ")[0])
    helptxt = " ".join(([head[len(head.split("  ")[0]):].strip()] if "  " in head else []) + [l.strip() for l in lines[1:]]).strip()
    if names: flags.append({"names": names, "head": head.split("  ")[0].strip(), "help": helptxt})
out["flags"] = flags
A = "nano/library_std/add.icm.json"
PROBES = [
 ("icm_no_family", "a program file with no family", ["--icm", A, "--man", T]),
 ("w_with_sub", "-w with the sub family", ["-s", "sub", "--icm", A, "--man", T, "-w", "18"]),
 ("w_default_route", "-w on the carrier or standalone route", ["--man", M, "--cells", "4", "-w", "18"]),
 ("merge_mode_sub", "--merge-mode with the sub family", ["-s", "sub", "--icm", A, "--man", T, "--merge-mode", "arbitrate=x"]),
 ("chain_no_cells", "a chain with no --cells", ["-s", "flex", "-S", "adder", "--man", T]),
 ("chain_logiclock", "--logiclock on the flex chain route", ["-s", "flex", "-S", "adder", "--cells", "4", "--man", T, "--logiclock"]),
 ("icm_logiclock", "--logiclock on the flex program route", ["-s", "flex", "--icm", A, "--man", T, "--logiclock"]),
 ("nowidelut_mustang", "--nowidelut on the Mustang card", ["-s", "flex", "--icm", A, "--man", M, "--nowidelut"]),
 ("nowidelut_tang", "--nowidelut on the Tang Nano card", ["-s", "flex", "--icm", A, "--man", T, "--nowidelut"]),
 ("widelut_tang", "--wide-lut on the Tang Nano card", ["-s", "flex", "--icm", A, "--man", T, "--wide-lut"]),
 ("noalign_sub", "--no-align on the sub family", ["-s", "sub", "--icm", A, "--man", T, "--no-align"]),
 ("w8_flex", "-w 8 on the flex family", ["-s", "flex", "--icm", A, "--man", T, "-w", "8"]),
 ("mul_dsp_mustang", "--mul dsp on the Mustang card", ["-s", "sub", "--icm", "nano/library_std/mul.icm.json", "--man", M, "--mul", "dsp"]),
 ("shellfile_no_module", "--shell-file without --shell-module", ["--man", M, "--cells", "4", "--shell-file", "fpga/verilog/unicell_super_v7.v"]),
 ("yosys_probe", "--target yosys with -P", ["--man", M, "--cells", "4", "--target", "yosys", "-P"]),
 ("quartus_tang", "the Quartus array route with the Tang Nano card", ["--man", T, "--cells", "4", "-S", "adder_cell"]),
 ("yosys_ok", "--target yosys alone", ["--man", M, "--cells", "4", "--target", "yosys"]),
]
probes = []
for pid, label, a in PROBES:
    d = os.path.join(TMP, "p_" + pid)
    r = subprocess.run([sys.executable, "tools/project_assemble_v1.py", *a, "--output", d], cwd=REPO, capture_output=True, text=True)
    e = [l for l in r.stderr.strip().splitlines() if l.strip()]
    msg = (re.sub(r"^(project_assemble_v1\.py: )?error:\s*", "", e[-1]) if r.returncode and e else "")
    row = {"id": pid, "label": label, "args": a, "ok": r.returncode == 0, "message": msg[:260]}
    if r.returncode == 0 and os.path.isdir(d):
        fl = os.listdir(d); row["files"] = len(fl)
        row["sha"] = {f: hashlib.sha1(open(os.path.join(d, f), "rb").read()).hexdigest()[:10] for f in fl if f != "ASSEMBLY.json"}
        if os.path.exists(os.path.join(d, "ASSEMBLY.json")):
            asm = json.load(open(os.path.join(d, "ASSEMBLY.json")))
            row["built_width"] = asm.get("built_width"); row["synth_flags"] = asm.get("synth_flags"); row["pad_relay_cells"] = asm.get("pad_relay_cells")
            row["align"] = asm.get("align")
        ys = [f for f in os.listdir(d) if f.endswith(".ys")]
        if ys: row["ys_synth"] = [l for l in open(os.path.join(d, ys[0])).read().splitlines() if "synth_" in l][:1]
        qs = [f for f in os.listdir(d) if f.endswith(".qsf")]
        if qs: row["qsf_lines"] = sum(1 for _ in open(os.path.join(d, qs[0])))
    probes.append(row)
out["probes"] = probes
json.dump(out, open(os.path.join(HERE, "asm_data.json"), "w"), indent=1)
print("wrote asm_data.json")
for f in out["families"]: print(f["key"], len(f["kinds"]), f["testbenches"], f["adder_ports"]["inputs"], f["adder_ports"]["outputs"], f["adder_ports"]["in_bits"], f["adder_ports"]["out_bits"], f["features"])
print(out["carrier"]["selectable"], out["carrier"]["shells"][:3], out["carrier"]["addon_blocks"])
print({k: (v["ok"], len(v.get("files", {}))) for k, v in out["routes"].items()})
