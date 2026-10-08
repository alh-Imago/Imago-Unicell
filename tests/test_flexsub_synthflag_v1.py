#!/usr/bin/env python3
"""tests/test_flexsub_synthflag_v1.py -- `synth_gowin -nowidelut` is the DEFAULT for the Gowin generators, decided by the card's MAN (ledger #951).

Run: python3 tests/test_flexsub_synthflag_v1.py      (needs yosys)
Alan, after the measurements of ledger #950: "overall for the sub and flex designs especially this should be the default switch, but in other cards this may not be available,
as noted with the Arria 10 rejection of the command ... this becomes the default setting." The card's MAN says what its synthesis toolchain supports and what the default is
(`synthesis.nowidelut.{supported,default}`); the assembler reads it, and assumes nothing about a vendor. Checked: (1) the default is ON where the MAN says so, in EVERY Gowin
generator path; (2) `--wide-lut` opts out and writes the historical line; (3) `--nowidelut` forces it on; (4) a MAN that says unsupported (the Arria 10) defaults OFF and
REFUSES the forced flag; (5) the two flags contradict; (6) the original Intel/Quartus path refuses both; (7) the flag really changes the synthesised netlist; (8) the choice and its
reason are recorded.
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


def synth_line(folder):
    ys = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".ys")][0]
    return re.search(r"^synth_gowin.*$", open(ys).read(), re.M).group(0)


def rec(folder):
    return json.load(open(os.path.join(folder, "ASSEMBLY.json")))


def stat_of(folder):
    ys = [f for f in os.listdir(folder) if f.endswith(".ys")][0]
    out = subprocess.run(["yosys", "-s", ys], cwd=folder, capture_output=True, text=True).stdout
    c = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s+(\w+)\s+(\d+)\s*$", out.split("Number of cells")[-1], re.M)}
    return sum(v for k, v in c.items() if re.fullmatch(r"LUT[1-4]", k)), sum(v for k, v in c.items() if k.startswith("MUX2_LUT"))


tmp = tempfile.mkdtemp(prefix="synthflag_")
chain = {"sub": ["-s", "sub", "-S", "nano", "--cells", "1"], "flex": ["-s", "flex", "-S", "nano", "--cells", "1"]}
icm = os.path.join(EX, "small_relay_chain.icm-hier.json")
paths = [("step-1 assembler, sub, Tang MAN", chain["sub"] + ["--man", TANG]), ("step-1 assembler, flex, Tang MAN", chain["flex"] + ["--man", TANG]),
         ("--icm, sub, Tang MAN", ["-s", "sub", "--icm", icm, "--man", TANG]), ("--icm, flex, Tang MAN", ["-s", "flex", "--icm", icm, "--man", TANG]),
         ("--icm, sub, NO MAN", ["-s", "sub", "--icm", icm]), ("--icm, flex, NO MAN", ["-s", "flex", "--icm", icm])]
dirs = {}
print("1-3. every Gowin generator path: ON by default, --wide-lut opts out, --nowidelut forces it")
for label, args in paths:
    for tag, extra in (("default", []), ("wide", ["--wide-lut"]), ("forced", ["--nowidelut"])):
        d = os.path.join(tmp, re.sub(r"\W+", "_", label) + "_" + tag)
        r = cli(*args, "--output", d, *extra)
        if r.returncode:
            check(f"{label} [{tag}] generates", False, r.stderr.strip()[:200])
            continue
        dirs[(label, tag)] = d
    if all((label, t) in dirs for t in ("default", "wide", "forced")):
        d, w, f = (synth_line(dirs[(label, t)]) for t in ("default", "wide", "forced"))
        ok = "-nowidelut" in d and "-nowidelut" not in w and "-nowidelut" in f
        recs = [rec(dirs[(label, t)]) for t in ("default", "wide", "forced")]
        ok = ok and recs[0]["synth_flags"] == "-nowidelut" and recs[1]["synth_flags"] == "(wide-LUT mapping)" and recs[2]["synth_flags"] == "-nowidelut"
        ok = ok and all(r_.get("synth_flags_reason") for r_ in recs)
        check(f"{label}: default -> -nowidelut; --wide-lut -> the historical line; --nowidelut -> forced; each recorded with its reason", ok, f"{d!r} / {w!r} / {f!r}")
hist = synth_line(dirs[("step-1 assembler, sub, Tang MAN", "wide")])
check("--wide-lut writes EXACTLY the historical line (so the old flow is fully recoverable)", re.fullmatch(r"synth_gowin -top \S+ -json \S+\.json", hist) is not None, hist)

print("4. a card whose MAN says the option is unsupported (the Arria 10) defaults OFF and REFUSES the forced flag")
for label, base in (("step-1 sub", chain["sub"]), ("step-1 flex", chain["flex"] + ["-w", "32"]), ("--icm sub", ["-s", "sub", "--icm", icm]), ("--icm flex", ["-s", "flex", "--icm", icm])):
    d = os.path.join(tmp, "a10_" + re.sub(r"\W+", "_", label))
    r = cli(*base, "--man", MUSTANG, "--output", d)
    check(f"Arria 10 MAN, {label}: default is OFF (the MAN says supported=False)", r.returncode == 0 and "-nowidelut" not in synth_line(d) and "supported=False" in rec(d)["synth_flags_reason"], r.stderr.strip()[:200])
    r = cli(*base, "--man", MUSTANG, "--nowidelut", "--output", d + "_f")
    check(f"Arria 10 MAN, {label}: forcing --nowidelut is REFUSED with the MAN's reason", r.returncode != 0 and "does not support" in r.stderr, r.stderr.strip()[:200])

print("5-6. contradictory flags; the original Intel/Quartus path refuses both")
r = cli(*chain["sub"], "--man", TANG, "--nowidelut", "--wide-lut", "--output", os.path.join(tmp, "both"))
check("--nowidelut together with --wide-lut is refused", r.returncode != 0 and "contradict" in r.stderr, r.stderr.strip()[:160])
for flag in ("--nowidelut", "--wide-lut"):
    r = cli("--man", MUSTANG, "--cells", "2", flag, "--output", os.path.join(tmp, "intel" + flag))
    check(f"the original Intel/Quartus path refuses {flag} (synth_intel_alm has no such option)", r.returncode != 0 and "synth_intel_alm" in r.stderr, r.stderr.strip()[:160])

print("7. the default really changes the synthesised netlist (the nano cell's wide-LUT mux trees disappear)")
for fam in ("sub", "flex"):
    on, off = stat_of(dirs[(f"step-1 assembler, {fam}, Tang MAN", "default")]), stat_of(dirs[(f"step-1 assembler, {fam}, Tang MAN", "wide")])
    check(f"{fam} nano cell: default {on[0]} LUT4 + {on[1]} MUX2_LUT; --wide-lut {off[0]} + {off[1]} -- no MUX2_LUT and far fewer LUT4 by default", on[1] == 0 and off[1] > 100 and on[0] * 3 < off[0], str((on, off)))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
