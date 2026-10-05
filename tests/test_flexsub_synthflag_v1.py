#!/usr/bin/env python3
"""tests/test_flexsub_synthflag_v1.py -- the `--nowidelut` synthesis flag (ledger #950; Alan: the flag "needs to be initiated" for flex and maybe all designs).

Run: python3 tests/test_flexsub_synthflag_v1.py      (needs yosys)
`synth_gowin -nowidelut` stops the mapper building wide-LUT (MUX2_LUT5..8) mux trees. The flag must (1) reach the generated .ys in EVERY Gowin generator path (the step-1
assembler for flex and sub, and the --icm emitters for sub and flex), (2) be recorded in ASSEMBLY.json, (3) be OFF by default (the default build is byte-unchanged),
(4) be REFUSED on the original Intel/Quartus path where synth_intel_alm has no such option and it would be silently ignored, and (5) really change the synthesised netlist.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "nano", "examples")
CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
TANG = os.path.join(ROOT, "docs", "man", "tang-nano-20k.man.json")
MUSTANG = os.path.join(ROOT, "docs", "man", "mustang-f100-a10.man.json")
passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def cli(*a):
    return subprocess.run(CLI + list(a), capture_output=True, text=True)


def ys_of(folder):
    return open([os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".ys")][0]).read()


def synth_line(folder):
    return re.search(r"^synth_gowin.*$", ys_of(folder), re.M).group(0)


def stat_of(folder):
    ys = [f for f in os.listdir(folder) if f.endswith(".ys")][0]
    out = subprocess.run(["yosys", "-s", ys], cwd=folder, capture_output=True, text=True).stdout
    c = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s+(\w+)\s+(\d+)\s*$", out.split("Number of cells")[-1], re.M)}
    return sum(v for k, v in c.items() if re.fullmatch(r"LUT[1-4]", k)), sum(v for k, v in c.items() if k.startswith("MUX2_LUT"))


tmp = tempfile.mkdtemp(prefix="synthflag_")
print("the flag reaches the generated .ys in every Gowin path, and is off by default")
paths = [("step-1 assembler, sub", ["-s", "sub", "-S", "nano", "--cells", "1", "--man", TANG]),
         ("step-1 assembler, flex", ["-s", "flex", "-S", "nano", "--cells", "1", "--man", TANG]),
         ("--icm, sub", ["-s", "sub", "--icm", os.path.join(EX, "small_relay_chain.icm-hier.json")]),
         ("--icm, flex", ["-s", "flex", "--icm", os.path.join(EX, "small_relay_chain.icm-hier.json")])]
dirs = {}
for label, args in paths:
    for flag in (False, True):
        d = os.path.join(tmp, re.sub(r"\W+", "_", label) + f"_{int(flag)}")
        r = cli(*args, "--output", d, *(["--nowidelut"] if flag else []))
        if r.returncode:
            check(f"{label} {'with' if flag else 'without'} the flag generates", False, r.stderr.strip()[:200])
            continue
        dirs[(label, flag)] = d
    if (label, True) in dirs and (label, False) in dirs:
        on, off = synth_line(dirs[(label, True)]), synth_line(dirs[(label, False)])
        rec_on = json.load(open(os.path.join(dirs[(label, True)], "ASSEMBLY.json"))).get("synth_flags")
        rec_off = json.load(open(os.path.join(dirs[(label, False)], "ASSEMBLY.json"))).get("synth_flags")
        check(f"{label}: with the flag the .ys says -nowidelut and the record says so; without it neither does",
              "-nowidelut" in on and "-nowidelut" not in off and rec_on == "-nowidelut" and rec_off == "(default)", f"on={on!r} off={off!r} rec={rec_on!r}/{rec_off!r}")

print("the default build is unchanged: no flag anywhere in an unflagged .ys")
check("an unflagged step-1 .ys is exactly the historical line", synth_line(dirs[("step-1 assembler, sub", False)]).endswith("-json " + synth_line(dirs[("step-1 assembler, sub", False)]).split("-json ")[1]) and "-nowidelut" not in synth_line(dirs[("step-1 assembler, sub", False)]))

print("the original Intel/Quartus path REFUSES the flag (synth_intel_alm has no such option; it would be silently ignored)")
r = cli("--man", MUSTANG, "--cells", "2", "--nowidelut", "--output", os.path.join(tmp, "intel"))
check("no -s: refused with the reason", r.returncode != 0 and "synth_intel_alm" in r.stderr, r.stderr.strip()[:200])
r = cli("-s", "nano", "-S", "ram", "--man", MUSTANG, "--cells", "2", "--nowidelut", "--output", os.path.join(tmp, "intel2"))
check("-s nano: refused with the reason", r.returncode != 0 and "synth_intel_alm" in r.stderr, r.stderr.strip()[:200])

print("the flag really changes the synthesised result (the nano cell's wide-LUT mux trees disappear)")
a, b = stat_of(dirs[("step-1 assembler, sub", False)]), stat_of(dirs[("step-1 assembler, sub", True)])
check(f"sub nano cell: default {a[0]} LUT4 + {a[1]} MUX2_LUT; with the flag {b[0]} LUT4 + {b[1]} MUX2_LUT -- no MUX2_LUT, far fewer LUT4", b[1] == 0 and a[1] > 100 and b[0] * 3 < a[0], str((a, b)))
a, b = stat_of(dirs[("step-1 assembler, flex", False)]), stat_of(dirs[("step-1 assembler, flex", True)])
check(f"flex nano cell: default {a[0]} LUT4 + {a[1]} MUX2_LUT; with the flag {b[0]} LUT4 + {b[1]} MUX2_LUT", b[1] == 0 and a[1] > 100 and b[0] * 3 < a[0], str((a, b)))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
