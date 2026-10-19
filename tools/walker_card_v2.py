#!/usr/bin/env python3
"""tools/walker_card_v2.py -- CLONE of walker_card_v1.py (ledger #1289: reads the WIRE WITNESSES from the card, from design_map_v2 / runner v5 folders, and marks which neighbour connections the card itself saw a word cross). Original text, ledger #1286: the Walker's first reading of a REAL programmed card, over the JTAG read-back the ICM runner already has.

Usage:  python3 tools/walker_card_v2.py FOLDER LOG [LOG ...] [--from CELL]   (several logs = several runs; what the card saw in any of them counts)
  FOLDER  a build folder made by project_assemble_v4 (has design.json and design_map.json)
  LOG     the output of `run_read.sh` (or `run_vectors.sh`) from that folder, i.e. SNAP lines read from the card
It does three things and says plainly which is which:
  1. WHAT THE CARD SAYS: the runner magic, the design fingerprint in the read-back, the entry and exit counts. These come from the card.
  2. WHAT THE FOLDER'S MAP SAYS: cells, which cell is on which face of which, from design_map.json (made by the generator that wrote the Verilog).
  3. THE COMPARISON: same design or not (fingerprint), and whether the card's entry/exit counts match the map. The per-cell neighbours are printed from the MAP; the card has not
     confirmed them one by one (that needs the discovery-mode hardware, which is not built). Nothing here is claimed as discovered by the card beyond items 1 and 3.
Exit code 0 only if the card shows the runner and the SAME design."""
import json, os, re, sys
from collections import deque

OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def read_snap(text):
    snaps = {m.group(1): [int(x, 16) for x in m.group(2).split()] for m in re.finditer(r"SNAP\s+(\S+)\s+((?:[0-9a-fA-F]{8}\s*)+)", text)}
    if not snaps:
        raise SystemExit("no SNAP lines in the log")
    label = "result" if "result" in snaps else list(snaps)[-1]
    return label, snaps[label]


def witness_bits(m, d, words):
    """From the card's witness words: {edge k -> seen}, {cell k -> seen}, using the numbering in design_map.json['witness']. None if this folder has no witnesses."""
    wm, lay = m.get("witness"), d["layout"]
    if not wm or not lay.get("nwit"):
        return None
    ws = words[lay["wit"]: lay["wit"] + lay["nwit"]]
    bit = lambda k: (ws[k // 32] >> (k % 32)) & 1
    return {e["k"]: bit(e["k"]) for e in wm["edges"]}, {c["k"]: bit(c["k"]) for c in wm["cells"]}


def build_shape(m, d, seen_edge, seen_cell, nruns, witnessed, origin=None):
    """The card's SHAPE (ledger #1289): the same top-level fields as shape_extract_v1 / walker_sim_v1.to_shape (shape_version, card_id, generated, cells, edges), so the Composer and the
    mirror can read it, plus what the card itself witnessed. `instance` is the design's cell id (unique; several cells can share one grid site, e.g. a merge core and its ram).
    `seen_on_card` / `confirmed_by_card` are True/False when the card's wire witnesses were read, None when this folder has none. Directions: an edge arrives on face F of the
    receiving cell, so the sending cell has the receiver on the opposite face."""
    import datetime
    cellk = {c["id"]: c["k"] for c in m.get("witness", {}).get("cells", [])}
    edgek = {(e["from"], e["to"], e["slot"]): e["k"] for e in m.get("witness", {}).get("edges", [])}
    cells = []
    for c in m["cells"]:
        cells.append({"instance": c["id"], "module_type": c["core"], "cell_id": c["index"], "role": c["role"], "row": c["row"], "col": c["col"], "entry": c["entry"], "exit": c["exit"],
                      "seen_on_card": (bool(seen_cell.get(cellk[c["id"]])) if (witnessed and c["id"] in cellk) else None)})
    edges, used = [], {}
    for e in m["edges"]:                       # map edges and witness edges are the same connections in the same order per (from, to); match them one to one
        key = (e["from"], e["to"])
        cands = [k for (f, t, sl), k in sorted(edgek.items(), key=lambda kv: kv[1]) if (f, t) == key]
        n = used.get(key, 0); used[key] = n + 1
        k = cands[n] if n < len(cands) else None
        edges.append({"from": {"instance": e["from"], "direction": OPP[e["face_at_to"]]}, "to": {"instance": e["to"], "direction": e["face_at_to"]}, "side_by_side": e["side_by_side"],
                      "confirmed_by_card": (bool(seen_edge.get(k)) if (witnessed and k is not None) else None)})
    conf = [x["confirmed_by_card"] for x in edges]
    return {"shape_version": "1.0", "card_id": d.get("card_id") or d.get("proj"), "generated": datetime.date.today().isoformat(), "source_file": m.get("source"), "top_module": d.get("dut"),
            "git_commit": None, "discovery_method": "card_wire_witness_v1", "design_fingerprint": m["fingerprint"], "runs_read": nruns, "origin": origin,
            "edges_confirmed": sum(1 for x in conf if x), "edges_not_exercised": sum(1 for x in conf if x is False), "cells": cells, "edges": edges}


def read_card_shape(path):
    """Load a SHAPE written by build_shape and check it is whole: returns {"cells": {instance: cell}, "edges": [...], "confirmed": set of (from, to), "complete": bool}.
    This is what a mirror reads to take the card's own layout, cell by cell, and to know which connections the card has actually shown."""
    sh = json.load(open(path))
    if sh.get("shape_version") != "1.0" or sh.get("discovery_method") != "card_wire_witness_v1":
        raise ValueError("not a card-witnessed SHAPE (shape_version 1.0, discovery_method card_wire_witness_v1)")
    cells = {c["instance"]: c for c in sh["cells"]}
    for e in sh["edges"]:
        for side in ("from", "to"):
            if e[side]["instance"] not in cells:
                raise ValueError("edge names a cell that is not in the SHAPE: %s" % e[side]["instance"])
    conf = {(e["from"]["instance"], e["to"]["instance"]) for e in sh["edges"] if e["confirmed_by_card"]}
    return {"cells": cells, "edges": sh["edges"], "confirmed": conf, "complete": all(e["confirmed_by_card"] for e in sh["edges"]), "header": {k: v for k, v in sh.items() if k not in ("cells", "edges")}}


def neighbours(m):
    """cell -> [(face of THIS cell, other cell)] from the edges: an edge from q to dst arrives on face F of dst, so dst has q on F and q has dst on the opposite face."""
    nb = {c["id"]: [] for c in m["cells"]}
    for e in m["edges"]:
        nb[e["to"]].append((e["face_at_to"], e["from"]))
        nb[e["from"]].append((OPP[e["face_at_to"]], e["to"]))
    return nb


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    start = argv[argv.index("--from") + 1] if "--from" in argv else None
    shape_out = argv[argv.index("--shape") + 1] if "--shape" in argv else None
    args = [a for a in args if a not in (start, shape_out)]
    folder, logs = args[0], args[1:]
    d = json.load(open(os.path.join(folder, "design.json")))
    m = json.load(open(os.path.join(folder, "design_map.json")))
    runs = [read_snap(open(lg).read()) for lg in logs]
    label, w = runs[-1]
    lay, nw = d["layout"], d["nw"]
    if len(w) != nw:
        print(f"FAIL: expected {nw} words, got {len(w)} (is the right bitstream loaded?)")
        return 1
    magic_ok = w[0] == 0x52554E31
    fpc = "%08x" % w[lay["ebuf"]]
    same = fpc == m["fingerprint"]
    print(f"== WHAT THE CARD SAYS ({label} read) ==")
    print(f"  runner magic {w[0]:08X} {'OK' if magic_ok else 'WRONG - the runner is not loaded'}; run {w[3] & 255}; design fingerprint {fpc}")
    ne, nx = (w[2] >> 16) & 255, w[2] & 255
    print(f"  entries {ne}, exits {nx}")
    print(f"== WHAT THE FOLDER'S MAP SAYS ==")
    ents = [c for c in m["cells"] if c["entry"]]
    exs = [c for c in m["cells"] if c["exit"]]
    print(f"  {len(m['cells'])} cells, {len(m['edges'])} connections, entries {[c['entry'] for c in ents]}, exits {[c['exit'] for c in exs]}, fingerprint {m['fingerprint']}")
    print("== COMPARISON ==")
    print(f"  design on the card {'IS' if same else 'IS NOT'} this folder's design (fingerprint {fpc} vs {m['fingerprint']})")
    counts_ok = (ne, nx) == (len(ents), len(exs))
    print(f"  entry/exit counts card {ne}/{nx} vs map {len(ents)}/{len(exs)}: {'match' if counts_ok else 'DIFFERENT'}")
    wit = None
    seen_edge, seen_cell = {}, {}
    if magic_ok and same:
        for _, ww in runs:
            if len(ww) == nw and ("%08x" % ww[lay["ebuf"]]) == m["fingerprint"]:
                got = witness_bits(m, d, ww)
                if got:
                    wit = True
                    for k, v in got[0].items():
                        seen_edge[k] = seen_edge.get(k, 0) | v
                    for k, v in got[1].items():
                        seen_cell[k] = seen_cell.get(k, 0) | v
    bad = []
    if wit:
        cellk = {c["id"]: c["k"] for c in m["witness"]["cells"]}
        print(f"== WHAT THE CARD SAW ON ITS WIRES ({len(runs)} run(s) read) ==")
        done = [e for e in m["witness"]["edges"] if seen_edge[e["k"]]]
        print(f"  {len(done)} of {len(m['witness']['edges'])} connections carried a word; {sum(seen_cell.values())} of {len(seen_cell)} cells offered an output")
        for e in m["witness"]["edges"]:           # an edge can only carry a word if its source offered one
            if seen_edge[e["k"]] and e["from"] in cellk and not seen_cell[cellk[e["from"]]]:
                bad.append(e)
        for e in bad:
            print(f"  INCONSISTENT: {e['from']} -> {e['to']} carried a word but {e['from']} never offered one")
        idle = [e for e in m["witness"]["edges"] if not seen_edge[e["k"]]]
        if idle:
            print(f"  not exercised by what was read (neither confirmed nor refuted): " + ", ".join(f"{e['from']}->{e['to']}" for e in idle))
    elif magic_ok and same:
        print("== NO WIRE WITNESSES in this folder's read-back (made before runner v5) ==")
    if magic_ok and same:
        seen_pair = set()
        if wit:
            seen_pair = {(e["from"], e["to"]) for e in m["witness"]["edges"] if seen_edge[e["k"]]}
        nb = neighbours(m)
        byid = {c["id"]: c for c in m["cells"]}
        origin = start or (ents[0]["id"] if ents else m["cells"][0]["id"])
        print(f"== NEIGHBOURS, walking out from {origin} (from the MAP; '*' = the card itself saw a word cross that connection) ==")
        seen, q = {origin}, deque([origin])
        while q:
            c = q.popleft()
            row = ", ".join(f"{f}:{o}" + ("*" if ((c, o) in seen_pair or (o, c) in seen_pair) else "") for f, o in sorted(nb[c]))
            print(f"  {c} [{byid[c]['core']}, index {byid[c]['index']}, grid {byid[c]['row']},{byid[c]['col']}]  {row or '(no connections)'}")
            for _, o in sorted(nb[c]):
                if o not in seen:
                    seen.add(o)
                    q.append(o)
    ok = bool(magic_ok and same and counts_ok and not bad)
    if shape_out:
        if ok:
            sh = build_shape(m, d, seen_edge, seen_cell, len(runs), bool(wit), origin)
            json.dump(sh, open(shape_out, "w"), indent=1)
            print(f"== SHAPE written to {shape_out}: {len(sh['cells'])} cells, {len(sh['edges'])} connections, {sh['edges_confirmed']} confirmed by the card, {sh['edges_not_exercised']} not exercised ==")
        else:
            print("== SHAPE NOT written: the card is not shown to be running this folder's design (or its witnesses are inconsistent) ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
