#!/usr/bin/env python3
"""tests/test_flexsub_icm_netlist_v1.py -- ICM-VIX netlist extraction for the Flex-Sub assembler (step 2, slice 1).

Run: python3 tests/test_flexsub_icm_netlist_v1.py
Checks the derived netlist of the three shipped ICM-VIX examples, and -- the load-bearing one -- that
the static operand-order estimate (hop depth) agrees with what the REAL VM does at every adder that
receives both operands.
"""
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("nano", "tools", ""):
    sys.path.insert(0, os.path.join(ROOT, sub) if sub else ROOT)
import flexsub_icm_netlist_v1 as nl  # noqa: E402
import unicell_super_automaton_v1 as vm  # noqa: E402

EX = os.path.join(ROOT, "nano", "examples")
passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def vm_first_arrivals(path, drive):
    """For each adder, the VM's actual (A source, B source) -- the wrapped deliver records which
    arrival face landed in operand A and which in B (faces: 0..3 = N,S,E,W, icm_v3._DIR_BITS)."""
    doc, recs, cells, edges, inputs, outputs, ext, w = nl.extract(path)
    pos2id = {(r.row, r.col): r.cell_id for r in recs}
    seen = collections.OrderedDict()
    h = vm._CORE_HANDLERS["adder"]
    orig = h.deliver

    def wrapped(self, arrivals, injected):
        matched = sorted(d for d in arrivals if (self.adder_upstream_mask >> vm._DIR_BIT[d]) & 1)
        was_a = self.adder_a_arrived
        res = orig(self, arrivals, injected)
        if matched:
            seen.setdefault(pos2id[(self.row, self.col)], {}).setdefault("B" if was_a else "A", matched)
        return res
    h.deliver = wrapped
    try:
        grid = vm.SuperGrid(recs)
        drive(grid, recs)
    finally:
        h.deliver = orig
    face_src = {c: {face: src for src, face in inputs[c]["in"]} for c in seen}
    return {c: {k: [face_src[c]["NSEW"[d]] for d in v] for k, v in r.items()} for c, r in seen.items()}, nl.hop_depths(cells, edges)[0], inputs


def drive_tree(grid, recs):
    for k, r in enumerate(sorted([r for r in recs if r.io_name and r.io_name.startswith("input_")], key=lambda r: r.io_name)):
        grid.inject(r.row, r.col, k + 1)
    for _ in range(40):
        grid.tick()


def drive_cordic(grid, recs):
    inp = next(r for r in recs if r.io_name == "z_input")
    for _ in range(6):
        grid.tick()
    grid.inject(inp.row, inp.col, 50000)
    for _ in range(60):
        grid.tick()


print("relay chain")
r = nl.analyse(os.path.join(EX, "small_relay_chain.icm-hier.json"))
check("8 cells, 7 edges, 1 input, 1 output, no merges/fan-out/two-operand",
      (r["cells"], r["edges"]) == (8, 7) and len(r["findings"].get("entry", [])) == 1
      and len(r["findings"].get("exit", [])) == 1 and not any(r["findings"].get(k) for k in ("merge", "fan_out", "two_operand")))
check("every cell maps cleanly onto a Flex-Sub cell", r["clean_cells"] == 8, str(r["blocked_cells"]))

print("parallel reduction tree")
r = nl.analyse(os.path.join(EX, "parallel_reduction_tree.icm-hier.json"))
check("12 cells, 11 edges, 4 inputs, 1 output", (r["cells"], r["edges"]) == (12, 11)
      and len(r["findings"]["entry"]) == 4 and len(r["findings"]["exit"]) == 1)
check("3 adders, each with 2 sources, none tied",
      len(r["findings"]["two_operand"]) == 3 and all("TIED" not in x and "2 sources" in x for x in r["findings"]["two_operand"]))

print("cordic z-convergence")
r = nl.analyse(os.path.join(EX, "cordic_z_convergence.icm-hier.json"))
check("40 cells, 43 edges (branch routes followed, not just downstream_mask)", (r["cells"], r["edges"]) == (40, 43), f"{r['cells']}/{r['edges']}")
check("12 constant sources (preload_value), 0 undriven, 0 pins in, 1 observed output",
      len(r["findings"]["constant"]) == 12 and not r["findings"].get("undriven")
      and not r["findings"].get("entry") and len(r["findings"]["exit"]) == 1)
check("7 merges (OR glue), 4 branch fan-outs", len(r["findings"]["merge"]) == 7 and len(r["findings"]["fan_out"]) == 4)
check("all 8 adders have exactly 2 sources (none mis-read as single-stream)",
      len(r["findings"]["two_operand"]) == 8 and all("2 sources" in x for x in r["findings"]["two_operand"]))
bp = [v["branch_ports"] for v in r["cell_verdicts"].values() if v["core"] == "branch"]
check("all 4 branches representable on v4sa: low/equal -> out1 (S), high -> out2 (N)",
      len(bp) == 4 and all(b["faces->ports"] == {"S": "out1", "N": "out2"} and b["route_bits"] == {"low": 1, "equal": 1, "high": 2} for b in bp), str(bp[:1]))
check("advisory connection check raised no warnings on any shipped example",
      not [w for w in r["warnings"]], str(r["warnings"][:2]))

print("operand order: static estimate vs the REAL VM")
for name, drive in (("parallel_reduction_tree", drive_tree), ("cordic_z_convergence", drive_cordic)):
    actual, depth, inputs = vm_first_arrivals(os.path.join(EX, f"{name}.icm-hier.json"), drive)
    done = {c: v for c, v in actual.items() if "A" in v and "B" in v}
    ok = bool(done)
    for c, v in done.items():
        srcs = [s for s, _ in inputs[c]["in"]]
        first = min(srcs, key=lambda s: depth[s])
        ok = ok and len({depth[s] for s in srcs}) == 2 and v["A"] == [first]
    check(f"{name}: estimate matches the VM at all {len(done)} adders that received both operands", ok, str(done))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
