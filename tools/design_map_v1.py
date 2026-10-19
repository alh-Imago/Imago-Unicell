#!/usr/bin/env python3
"""tools/design_map_v1.py -- ledger #1285: the NEIGHBOUR MAP of a generated flex design, written next to the build so the Walker can use it.

The map says, for the design as BUILT (after the generator has absorbed merge relays, lowered branches and so on): every cell (ICM id, the CELL_ID index it has in the Verilog,
core, row/col in the ICM grid, role), every connection (from cell, to cell, the face of the receiving cell it arrives on, and whether the two cells are really side by side in the
ICM grid on that face), the entries and exits by name, and a 32-bit fingerprint of all that. It is made by the same generator code that writes the Verilog, so it is what was built.
It is NOT proof of what is on a card: the Walker compares it with what the programmed card reports (ledger #551: a compile-time map is never trusted as ground truth alone).
Usage: python3 tools/design_map_v1.py ICM_FILE OUTPUT_FOLDER [--family flex]      (writes OUTPUT_FOLDER/design_map.json and prints the fingerprint)"""
import hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "nano")); sys.path.insert(0, os.path.join(ROOT, "tools"))
import flexsub_icm_generate_v3 as g  # noqa: E402
import flexsub_icm_flex_v3 as ff  # noqa: E402

_DELTA = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}


def build_map(icm_path, family="flex", merge_mode="arbitrate", **kw):
    p = g.plan(icm_path, family=family, **kw)
    ff.emit_top_flex("map_top", p, merge_mode)        # the emitter adds the merge cores in front of multi-source cells on its own copy; v3 leaves that graph in ff.LAST_BUILT
    b = ff.LAST_BUILT
    order, cells, idx = b["order"], b["cells"], b["idx"]          # idx = the CELL_ID the emitter gives each cell
    p = dict(p, inputs=b["inputs"])
    pos = {c: (cells[c].row, cells[c].col) for c in order}
    def slice_of(c):            # a wiring-tile slice is part of ONE native cross/corner tile instance, not a cell with its own CELL_ID
        wt = (cells[c].core_config or {}).get("wire_tile")
        return wt["tile"] if (wt and cells[c].core == "ram" and g.NATIVE_WIRING_TILES) else None
    role = {}
    for c in order:
        role[c] = ("tile-slice" if slice_of(c) else "constant" if c in p["const"] else "one-shot" if c in p["oneshots"] else "hold" if c in p["holds"] else "level" if g.is_level(cells[c]) else "cell")
    exits = set(p["exits"])
    cl = [{"id": c, "index": None if slice_of(c) else idx[c], "tile": slice_of(c), "core": cells[c].core, "row": pos[c][0], "col": pos[c][1], "role": role[c],
           "entry": ff._pname(cells[c].io_name, c) if (not p["inputs"].get(c) and c not in p["const"] and c not in p["oneshots"] and cells[c].core != "sequencer" and c not in exits) else None,
           "exit": ff._pname(cells[c].io_name, c) if c in exits else None} for c in order]
    edges = []
    for dst in order:
        for face, lst in p["inputs"].get(dst, {}).items():
            for q, f_at_dst in lst:
                dr, dc = _DELTA[f_at_dst]
                edges.append({"from": q, "to": dst, "face_at_to": f_at_dst, "side_by_side": (pos[dst][0] + dr, pos[dst][1] + dc) == pos[q], "same_site": pos[dst] == pos[q]})
    note = "second-port cells (adder carry / mul high word) get a merge core per consumer inside the emitter on a private copy of the connections; those merge cores' own connections are not in this map" if p.get("second_ports") else ""
    core = {"family": family, "note": note, "source": os.path.basename(icm_path), "cells": cl, "edges": edges}
    fp = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()[:8]
    core["fingerprint"] = fp
    core["fingerprint_note"] = "first 32 bits of sha256 over family, source, cells and edges"
    return core


def write_map(icm_path, folder, family="flex", merge_mode="arbitrate", **kw):
    m = build_map(icm_path, family, merge_mode, **kw)
    json.dump(m, open(os.path.join(folder, "design_map.json"), "w"), indent=1)
    return m


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    m = write_map(a[0], a[1], rings=True)
    print("design_map.json written:", len(m["cells"]), "cells,", len(m["edges"]), "connections, fingerprint", m["fingerprint"],
          "| side by side:", sum(1 for e in m["edges"] if e["side_by_side"]), "same site (merge core):", sum(1 for e in m["edges"] if e["same_site"]), "of", len(m["edges"]))
