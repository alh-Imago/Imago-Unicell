#!/usr/bin/env python3
"""Capture REAL facts for the teaching manual's "Mixing families" tab: the generated flex -> SUB -> flex design is built by tools/project_assemble_v1.py from the example in
nano/examples/mixed_flex_sub_flex_v1.icm-hier.json and simulated with iverilog; the closed looped CORDIC is built as a flex ring and as a sub ring and run for a few laps.
Writes docs/teaching/mixed_data.json (embedded by the builder). Run: python3 docs/teaching/capture_mixed_v1.py   (needs iverilog)."""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ASM = [sys.executable, os.path.join(REPO, "tools", "project_assemble_v1.py")]
EX = os.path.join(REPO, "nano", "examples")
SV = os.path.join(REPO, "sub", "verilog")

def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode: raise SystemExit(r.stderr[-800:])
    return r.stdout

def sim(d, tb, defs, top_files=None):
    srcs = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".v")]
    exe = os.path.join(d, "t.vvp")
    run(["iverilog", "-g2012"] + defs + ["-o", exe, tb] + srcs)
    return run(["vvp", exe])

out = {"example": json.load(open(os.path.join(EX, "mixed_flex_sub_flex_v1.icm-hier.json")))["description"]}
d = tempfile.mkdtemp()
asm = run(ASM + ["-s", "flex", "--icm", os.path.join(EX, "mixed_flex_sub_flex_v1.icm-hier.json"), "--top", "mix", "--output", d]).strip().splitlines()
out["assembler_said"] = asm
out["assembly"] = json.load(open(os.path.join(d, "ASSEMBLY_mixed.json")))
tb = os.path.join(SV, "tb_mixed_flex_sub_flex_v1.v")
for stall in (0, 1):
    txt = sim(d, tb, ["-DTOP=mix", "-DN=8", f"-DSTALL={stall}"])
    rows = [l.split() for l in txt.splitlines() if l[:2] in ("I ", "O ")]
    out[f"stall{stall}"] = {"in": [[int(r[2]), int(r[3])] for r in rows if r[0] == "I"], "out": [[int(r[2]), int(r[3])] for r in rows if r[0] == "O"]}
def ring(fam, tbname, n, extra):
    dd = tempfile.mkdtemp()
    run(ASM + ["-s", fam, "--allow-rings", "--ring-steps", str(n), "--icm", os.path.join(EX, "looped_cordic_v1_closed_flex.icm-hier.json"), "--top", "ring", "--output", dd])
    txt = sim(dd, os.path.join(SV, tbname), ["-DTOP=ring", "-DZ0=50000", f"-DNSTEPS={n+3}", "-DMAXCYC=4000"] + extra)
    rs = [l.split() for l in txt.splitlines() if l.startswith("R ")]
    stop = [l for l in txt.splitlines() if l.startswith("S ")]
    return {"results": len(rs), "values": [int(r[2]) for r in rs], "clocks_per_step": int(rs[-1][3]), "stopped_after": int(stop[0].split()[2][2:]) if stop else None}
out["ring_flex"] = ring("flex", "tb_looped_cordic_closed_flex_v1.v", 5, [])
out["ring_sub"] = ring("sub", "tb_looped_cordic_closed_sub_v1.v", 5, [])
json.dump(out, open(os.path.join(HERE, "mixed_data.json"), "w"), indent=1)
print("wrote mixed_data.json:", {k: (v if not isinstance(v, dict) else list(v)[:3]) for k, v in out.items() if k != "assembly"})
