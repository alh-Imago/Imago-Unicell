#!/usr/bin/env python3
"""Capture REAL runs of the two VM grids (SuperGrid, the standard one; FlexGrid, the flex mirror) for the teaching manual's
"SuperGrid and FlexGrid" page. Small hand-built designs are run on both grids with the same injections; a feature x grid x width
matrix records what each grid accepts, warns about or refuses at construction. Nothing here is simulated Verilog: it is the Python VM.
Writes docs/teaching/grids_data.json.   Run: python3 docs/teaching/capture_grids_v1.py
"""
import json, os, sys, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(REPO, "nano"), os.path.join(REPO, "tools")]
import icm_v3 as v3
from icm_v3 import IcmV3Record as R
from unicell_super_automaton_v1 import SuperGrid
from flex_grid_v1 import FlexGrid
from vm_ai_port_v1 import VMSession

GRIDS = {"std": SuperGrid, "flex": FlexGrid}
MAXT = 60


def rec(i, r, c, core, cc=None, io=None, ad=None):
    return R(cell_id=i, row=r, col=c, core=core, core_config=cc or {}, addon_config=ad or {}, io_name=io, preload_value=None)


def drive(G, recs, sched, outs, width=32, kw=None, max_t=MAXT):
    """Build, inject on the stated ticks, tick, and read the output cells' words (reading frees the cell, as an ack would)."""
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        try:
            g = G(recs, width=width, **(kw or {}))
        except Exception as e:
            return {"refused": str(e)}
        got = []
        try:
            for t in range(max_t):
                for (tt, p, v) in sched:
                    if tt == t:
                        g.inject(*p, v)
                g.tick()
                for p in outs:
                    c = g.cells[tuple(p)]
                    if getattr(c, "ram_data_valid", False):
                        got.append({"tick": t + 1, "cell": list(p), "value": c.ram_data_reg})
                        c.ram_data_valid = False
        except Exception as e:
            return {"refused": str(e), "got": got}
    return {"got": got, "warn": [str(w.message) for w in ws]}


def pair(i, a, b):  # two input rams north and south of a centre cell (1,1)
    return [rec("A", 0, 1, "ram", {"downstream_mask": ["s"]}, "a"), rec("B", 2, 1, "ram", {"downstream_mask": ["n"]}, "b")]


OUT = lambda: rec("R", 1, 2, "ram", {"upstream_mask": ["w"]}, "r")
E = []


def exp(id, title, what, recs, runs, note="", outs=((1, 2),)):
    E.append({"id": id, "title": title, "what": what, "note": note, "outs": [list(o) for o in outs],
              "records": [{"id": r.cell_id, "row": r.row, "col": r.col, "core": r.core, "cfg": r.core_config, "ad": r.addon_config, "io": r.io_name} for r in recs],
              "runs": runs, "_recs": recs})


def R_(label, grid, sched, width=32, kw=None, recs=None):
    return {"label": label, "grid": grid, "sched": sched, "width": width, "kw": kw or {}, "recs": recs}


# --- 1. two words into a merging relay on the SAME tick
merge = [rec("X", 0, 1, "ram", {"downstream_mask": ["s"]}, "x"), rec("Y", 2, 1, "ram", {"downstream_mask": ["n"]}, "y"),
         rec("M", 1, 1, "ram", {"upstream_mask": ["n", "s"], "downstream_mask": ["e"]}), OUT()]
s = [(0, (0, 1), 1), (0, (2, 1), 2)]
exp("merge", "Two words reach one relay on the same tick",
    "X sends 1 and Y sends 2 at the same moment into a relay M that listens on two faces. The standard grid ORs what arrives in the same tick into one word. FlexGrid mirrors the flex merge core, whose mode you choose.",
    merge, [R_("SuperGrid", "std", s), R_("FlexGrid, merge_mode arbitrate", "flex", s, kw={"merge_mode": "arbitrate"}), R_("FlexGrid, merge_mode join-or", "flex", s, kw={"merge_mode": "join-or"})],
    "arbitrate is for ALTERNATIVE paths (take one, then the other); join-or is for HALVES of one item (wait for all, then OR). The standard grid has only the second behaviour, and without waiting.")

# --- 2. adder, both operands on the same tick
add = pair(0, 0, 0) + [rec("ADD", 1, 1, "adder", {"upstream_mask": ["n", "s"], "downstream_mask": ["e"]}), OUT()]
s = [(0, (0, 1), 7), (0, (2, 1), 5)]
exp("addsame", "Adder, both operands on the same tick",
    "A sends 7 and B sends 5 so that both reach the adder in one tick. The real flex cell takes one operand, then the other.",
    add, [R_("SuperGrid", "std", s), R_("FlexGrid", "flex", s)],
    "In the standard grid the two arrivals are ORed into one operand (7 OR 5 = 7) and the adder waits for a second that never comes: nothing leaves. That is the 'same-tick operand loss' on the DSL page. FlexGrid takes the lower face first, then the other, so it adds.")

# --- 3. subtract, same tick vs staggered
sub = pair(0, 0, 0) + [rec("ADD", 1, 1, "adder", {"upstream_mask": ["n", "s"], "downstream_mask": ["e"], "subtract_mode": 1}), OUT()]
exp("sub", "Subtract: order matters",
    "The same subtractor, with 7 and 5. Same tick: no order. One tick apart: first arrival minus second.",
    sub, [R_("SuperGrid, same tick", "std", [(0, (0, 1), 7), (0, (2, 1), 5)]), R_("FlexGrid, same tick", "flex", [(0, (0, 1), 7), (0, (2, 1), 5)]),
          R_("SuperGrid, A first (7 then 5)", "std", [(0, (0, 1), 7), (3, (2, 1), 5)]), R_("FlexGrid, A first (7 then 5)", "flex", [(0, (0, 1), 7), (3, (2, 1), 5)]),
          R_("SuperGrid, B first (5 then 7)", "std", [(0, (2, 1), 5), (3, (0, 1), 7)]), R_("FlexGrid, B first (5 then 7)", "flex", [(0, (2, 1), 5), (3, (0, 1), 7)])],
    "When the arrival order is set by the design, both grids agree (5 then 7 gives 5 - 7 = 4294967294, the 32-bit wrap). When it is not, the real cell has no rule, so FlexGrid refuses instead of guessing. The standard grid silently produces nothing.")

# --- 4. carry word
addc = pair(0, 0, 0) + [rec("ADD", 1, 1, "adder", {"upstream_mask": ["n", "s"], "downstream_mask": ["e"], "second_output": 1, "second_downstream_mask": ["w"]}), OUT(),
                        rec("C", 1, 0, "ram", {"upstream_mask": ["e"]}, "c")]
s = [(0, (0, 1), 0xFFFFFFFF), (3, (2, 1), 2)]
exp("carry", "The adder's carry word",
    "0xFFFFFFFF + 2 overflows 32 bits. With second_output on, the adder sends the sum (1) to the east and the carry (1) to the west. Operands are one tick apart so both grids can run it.",
    addc, [R_("SuperGrid", "std", s), R_("FlexGrid", "flex", s)],
    "Both agree. Since ledger #1036 the second output is part of the standard cells too; the FlexGrid class still carries an old flag, _ALLOWS_CARRY_MODE, that nothing reads any more (text search of nano/ and tools/).", outs=((1, 2), (1, 0)))

# --- 5. a shift amount that is not a standard tap
shiftcell = lambda ad: [rec("S", 0, 0, "ram", {"downstream_mask": ["e"]}, "s", ad), rec("O", 0, 1, "ram", {"upstream_mask": ["w"]}, "o")]
sh3 = shiftcell({"shift_en": 1, "shift_amt": 3, "direction": 0})
s = [(0, (0, 0), 0x2ABCD)]
exp("shift", "A shift the standard chain has no tap for",
    "A relay with a left shift of 3 on its output, fed 0x2ABCD. The standard add-on chain has coarse taps at 1, 2, 4, 8, 12, 16, 20, 24 and 28 plus a fine 0-3 stage. In flex the shift is pure wiring, so any amount works.",
    sh3, [R_("SuperGrid, width 32", "std", s), R_("FlexGrid, width 32", "flex", s), R_("SuperGrid, width 18", "std", s, 18), R_("FlexGrid, width 18", "flex", s, 18)],
    "Observed: at 32 bits the standard grid passed the word through unshifted for shift_amt 3 (no error), FlexGrid shifted it. At 18 bits the standard grid refuses every enabled add-on; FlexGrid runs it on 18 bits (and wraps at bit 17).", outs=((0, 1),))

# --- 6. width: the library adder at 32 and 18
f = v3.IcmV3File.load(os.path.join(REPO, "nano/library_std/add.icm.json"))
pos = {r.io_name: (r.row, r.col) for r in f.records if r.io_name}
libs = lambda a, b: [(0, pos["a"], a), (0, pos["b"], b)]
exp("width", "Word width: the library adder at 32 and 18 bits",
    "The 27-cell adder from the Composer's library, 200000 + 100000. At 32 bits the answer is 300000. At 18 bits the grid is 2^18 = 262144 wide, so it wraps to 300000 - 262144 = 37856.",
    f.records, [R_("SuperGrid, width 32", "std", libs(200000, 100000)), R_("FlexGrid, width 32", "flex", libs(200000, 100000)),
                R_("SuperGrid, width 18", "std", libs(200000, 100000), 18), R_("FlexGrid, width 18", "flex", libs(200000, 100000), 18),
                R_("FlexGrid, width 8", "flex", libs(200, 100), 8), R_("FlexGrid, width 36", "flex", libs(200000, 100000), 36)],
    "Plain relays, adders and multipliers behave the same in both. The difference is in what each will accept at other widths (the matrix below).", outs=(pos["r"],))
E[-1]["note2"] = "27 cells; drawn without the diagram"

# --- 7. a 3-way merge
m3 = [rec("X", 0, 1, "ram", {"downstream_mask": ["s"]}, "x"), rec("Y", 2, 1, "ram", {"downstream_mask": ["n"]}, "y"), rec("Z", 1, 0, "ram", {"downstream_mask": ["e"]}, "z"),
      rec("M", 1, 1, "ram", {"upstream_mask": ["n", "s", "w"], "downstream_mask": ["e"]}), OUT()]
s = [(0, (0, 1), 1), (0, (2, 1), 2), (0, (1, 0), 4)]
exp("merge3", "Three sources into one relay",
    "X, Y and Z send 1, 2 and 4 together into one relay.",
    m3, [R_("SuperGrid", "std", s), R_("FlexGrid, arbitrate", "flex", s, kw={"merge_mode": "arbitrate"}), R_("FlexGrid, join-or", "flex", s, kw={"merge_mode": "join-or"})],
    "Three-way arbitrate would be a tree of round-robin cores whose grant order FlexGrid does not mirror, so it is refused. join-or of any number of sources is mirrored.")

for e in E:
    for r in e["runs"]:
        recs = r.pop("recs") or e["_recs"]
        r["result"] = drive(GRIDS[r["grid"]], recs, [(t, tuple(p), v) for t, p, v in r["sched"]], e["outs"], r["width"], r["kw"])
        r["sched"] = [[t, list(p), v] for t, p, v in r["sched"]]
    del e["_recs"]

# --- the acceptance matrix: features built alone at several widths on each grid (construction only; refusals are the grid's own words)
FEATS = [
    ("relay", "A plain relay (ram)", [rec("X", 0, 0, "ram", {})], None),
    ("adder", "An adder", [rec("X", 0, 0, "adder", {})], None),
    ("nano7", "Nano gate, topology 0x7 (plain two-arrival gate)", [rec("X", 0, 0, "nano", {"topology": 7})], None),
    ("nano5", "Nano gate, topology 0x5 (no flex gate for it)", [rec("X", 0, 0, "nano", {"topology": 5})], None),
    ("nanordy", "Nano gate, topology 0x7 with ready=1", [rec("X", 0, 0, "nano", {"topology": 7, "ready": 1})], None),
    ("shift", "Left shift add-on (shift_amt 3)", [rec("X", 0, 0, "ram", {"downstream_mask": ["e"]}, "x", {"shift_en": 1, "shift_amt": 3, "direction": 0}), rec("O", 0, 1, "ram", {"upstream_mask": ["w"]}, "o")], "RUN"),
    ("mask", "Nibble mask add-on", [rec("X", 0, 0, "ram", {"downstream_mask": ["e"]}, "x", {"mask_en": 1, "nibble_mask": 15}), rec("O", 0, 1, "ram", {"upstream_mask": ["w"]}, "o")], "RUN"),
    ("invert", "Invert add-on", [rec("X", 0, 0, "ram", {"downstream_mask": ["e"]}, "x", {"invert_en": 1}), rec("O", 0, 1, "ram", {"upstream_mask": ["w"]}, "o")], "RUN"),
    ("lanecut", "Right shift with lane_cut", [rec("X", 0, 0, "ram", {"downstream_mask": ["e"]}, "x", {"shift_en": 1, "shift_amt": 2, "direction": 1, "lane_cut": 1}), rec("O", 0, 1, "ram", {"upstream_mask": ["w"]}, "o")], "RUN"),
    ("seq", "Sequencer", [rec("X", 0, 0, "sequencer", {})], None),
    ("acc", "Accumulator", [rec("X", 0, 0, "accumulator", {})], None),
    ("branch", "Branch", [rec("X", 0, 0, "branch", {})], None),
    ("pri", "Priority", [rec("X", 0, 0, "priority", {})], None),
    ("merge3a", "3-way merge, merge_mode arbitrate", m3, "arbitrate"),
    ("merge3j", "3-way merge, merge_mode join-or", m3, "join-or"),
    ("badmode", "Merge with merge_mode 'roundrobin'", merge, "roundrobin"),
]
WIDTHS = [32, 36, 18, 8, 4]
matrix = {"widths": WIDTHS, "feats": []}
for key, label, recs, mm in FEATS:
    row = {"key": key, "label": label, "cells": {}}
    for g in ("std", "flex"):
        for w in WIDTHS:
            kw = {"merge_mode": mm} if (mm and mm != "RUN" and g == "flex") else {}
            if mm == "RUN":
                r = drive(GRIDS[g], recs, [(0, (0, 0), 0x2ABCD)], [(0, 1)], w, {}, max_t=4)
                row["cells"][f"{g}/{w}"] = {"refused": r["refused"]} if "refused" in r else {"ok": 1}
                continue
            if mm and g == "std":
                row["cells"][f"{g}/{w}"] = {"na": "merge_mode is a FlexGrid option; SuperGrid has none"}
                continue
            r = drive(GRIDS[g], recs, [], [], w, kw, max_t=0)
            row["cells"][f"{g}/{w}"] = {"refused": r["refused"]} if "refused" in r else ({"warn": r["warn"][0]} if r.get("warn") else {"ok": 1})
    matrix["feats"].append(row)

# --- a session wrapped around either grid (the driver port takes any grid)
s1 = VMSession(FlexGrid(f.records, width=18))
s1.inject(*pos["a"], 7); s1.inject(*pos["b"], 5)
sess = {"grid": type(s1.grid).__name__, "width": s1.grid.width, "settled_ticks": s1.run_to_quiescence(), "r": s1.describe_cell(*pos["r"])["ram"]["data_reg"]}

data = {"experiments": E, "matrix": matrix, "session": sess,
        "constructors": {"std_sig": "SuperGrid(records, width=32)", "flex_sig": 'FlexGrid(records, width=32, merge_mode="arbitrate")',
                         "width_range": [v3 and 1, 64]}}
json.dump(data, open(os.path.join(HERE, "grids_data.json"), "w"), indent=1)
print("wrote grids_data.json", os.path.getsize(os.path.join(HERE, "grids_data.json")), "bytes")
for e in E:
    print("==", e["id"])
    for r in e["runs"]:
        x = r["result"]
        print("  ", r["label"], "->", ("REFUSED " + x["refused"][:90]) if "refused" in x else [(g["tick"], g["value"]) for g in x["got"]][:4] or "nothing")
for row in matrix["feats"]:
    print(row["key"], {k: ("R" if "refused" in v else "W" if "warn" in v else "-" if "na" in v else "ok") for k, v in row["cells"].items()})
print(sess)
