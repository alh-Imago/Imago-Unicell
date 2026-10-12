"""looped_cordic_v1.py -- ledger #1092: a LOOPED z-convergence CORDIC for the save / load / retarget proof (Alan, 12 Oct 2026: "a simple looped cordic").

The design is the existing 4-stage z-convergence pipeline (nano/examples/cordic_z_convergence.icm-hier.json, UNCHANGED) with its output fed back to its input by a
relay path round the outside, and one DRIFT adder in that path:  z_next = f(z) + DRIFT,  f = the four stages (z > 0: z - K else z + K; K = 45000, 26565, 14036, 7125).
Why the drift: without it the loop falls into the 2-value cycle -5856, 5668 within three passes (ledger #1090) and a state comparison at step 300 / 600 / 1000
would show the same state every time. With DRIFT = 1237 the orbit has no repeat in 1,200 steps (worked out in Python from the model below).
What had to change from the example to make it loop (found by running it, #1090): the two stage constants of each stage are `fixed_mode=1` (offered every tick,
never used up) so the second pass finds them; the zero reference stays a one-shot (the branch only needs it once). Nothing else in the stages changes.
One STEP = one pass round the loop: the value arriving at the feedback-entry cell. A pass takes 40 ticks.
Everything is expressed as flat icm-v3 records, so the same file goes to the VM, the Flex-Sub assembler (flex RTL) and the carrier builds.
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "examples"))
from hierarchical_icm_prototype_loader import load_hierarchical, flatten  # noqa: E402

KS = (45000, 26565, 14036, 7125)
DRIFT = 1237
Z0 = 50000
TICKS_PER_STEP = 40
SETTLE_TICKS = 10
FEEDBACK_ENTRY = (0, -2)            # the cell whose arrivals are the steps
M32 = 0xFFFFFFFF


def _s32(v):
    v &= M32
    return v - (1 << 32) if v >> 31 else v


def f(z):
    for k in KS:
        z = z - k if z > 0 else z + k
        z = _s32(z)
    return z


def model(n, z0=Z0, drift=DRIFT):
    """z after each of the first n passes round the loop (independent of every cell: plain Python)."""
    out, z = [], z0
    for _ in range(n):
        z = _s32(f(z) + drift)
        out.append(z)
    return out


def build_doc(drift=DRIFT):
    """The design as an icm-vix HIERARCHICAL document (the same format as the example, so the Flex-Sub assembler / project_assemble takes it as it is): the example's four stage
    patterns with their constants made `fixed_mode=1`, the last stage's output cell given an east output, and one new pattern `loop` holding the way back and the drift adder."""
    import json
    doc = json.load(open(os.path.join(HERE, "examples", "cordic_z_convergence.icm-hier.json")))
    doc = copy.deepcopy(doc)
    doc["description"] = ("ledger #1092: the 4-stage z-convergence CORDIC fed back to its input through a drift adder (DRIFT=%d); one step = one pass round the loop. "
                          "Built by nano/looped_cordic_v1.py from nano/examples/cordic_z_convergence.icm-hier.json." % drift)
    for name, pat in doc["patterns"].items():
        for c in pat["cells"]:
            if c["cell_id"] in ("const_pos", "const_neg"):
                c["core_config"]["fixed_mode"] = 1
            if name == "stage_3" and c["cell_id"] == "gather":
                c["core_config"]["downstream_mask"] = ["E"]
    cells = []

    def ram(cid, row, col, up, down):
        cells.append({"cell_id": cid, "rel_row": row, "rel_col": col, "core": "ram", "core_config": {"upstream_mask": [up], "downstream_mask": [down], "fixed_mode": 0}})
    path = [(0, 11, "W", "S"), (1, 11, "N", "S"), (2, 11, "N", "S"), (3, 11, "N", "W")] + [(3, c, "E", "W") for c in range(10, -2, -1)] + [(3, -2, "E", "N"), (2, -2, "S", "N"), (1, -2, "S", "N"), (0, -2, "S", "E")]
    for i, (row, col, up, down) in enumerate(path):
        if (row, col) == (3, 5):
            cells.append({"cell_id": "drift_add", "rel_row": 3, "rel_col": 5, "core": "adder", "core_config": {"upstream_mask": ["E", "S"], "downstream_mask": ["W"]}})
        else:
            ram("fb%d" % i, row, col, up, down)
    cells.append({"cell_id": "drift_const", "rel_row": 4, "rel_col": 5, "core": "ram", "core_config": {"downstream_mask": ["N"], "fixed_mode": 1}, "preload_value": drift & M32})
    doc["patterns"]["loop"] = {"cells": cells}
    doc["design_map"]["placements"].append({"instance": "lp", "pattern": "loop", "at": [0, 0]})
    doc["header"]["cell_count"] = 40 + len(cells)
    doc["header"]["cores_used"] = sorted(set(doc["header"]["cores_used"]))
    return doc


def save_icm(path, drift=DRIFT):
    import json
    with open(path, "w") as fh:
        json.dump(build_doc(drift), fh, indent=1)


def build_records(drift=DRIFT):
    import tempfile
    p = os.path.join(tempfile.mkdtemp(), "looped_cordic.icm-hier.json")
    save_icm(p, drift)
    recs, _ = flatten(load_hierarchical(p))
    return recs


def entry_value(grid):
    c = grid.cells[FEEDBACK_ENTRY]
    if getattr(c, "ram_data_valid", False):
        return _s32(c.ram_data_reg)
    return None


def run_steps(grid, n_steps, max_ticks=None):
    """tick the grid until n_steps NEW values have arrived at the feedback entry (counting from now); returns [(tick, value)]."""
    seen, ticks = [], 0
    last_valid = False
    limit = max_ticks or (n_steps + 2) * (TICKS_PER_STEP + 5)
    while len(seen) < n_steps and ticks < limit:
        grid.tick()
        ticks += 1
        v = entry_value(grid)
        if v is not None and not last_valid:
            seen.append((ticks, v))
        last_valid = v is not None
    return seen


def new_grid(grid_cls, drift=DRIFT, z0=Z0, **kw):
    recs = build_records(drift)
    g = grid_cls(recs, **kw)
    for _ in range(SETTLE_TICKS):
        g.tick()
    inp = next(r for r in recs if r.io_name == "z_input")
    g.inject(inp.row, inp.col, z0 & M32)
    return g, recs
