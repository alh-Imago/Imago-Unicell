#!/usr/bin/env python3
"""tools/walker_card_v1.py -- ledger #1286: the Walker's first reading of a REAL programmed card, over the JTAG read-back the ICM runner already has.

Usage:  python3 tools/walker_card_v1.py FOLDER LOG [--from CELL]
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


def neighbours(m):
    """cell -> [(face of THIS cell, other cell)] from the edges: an edge from q to dst arrives on face F of dst, so dst has q on F and q has dst on the opposite face."""
    nb = {c["id"]: [] for c in m["cells"]}
    for e in m["edges"]:
        nb[e["to"]].append((e["face_at_to"], e["from"]))
        nb[e["from"]].append((OPP[e["face_at_to"]], e["to"]))
    return nb


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    folder, log = args[0], args[1]
    start = argv[argv.index("--from") + 1] if "--from" in argv else None
    d = json.load(open(os.path.join(folder, "design.json")))
    m = json.load(open(os.path.join(folder, "design_map.json")))
    label, w = read_snap(open(log).read())
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
    if magic_ok and same:
        nb = neighbours(m)
        byid = {c["id"]: c for c in m["cells"]}
        origin = start or (ents[0]["id"] if ents else m["cells"][0]["id"])
        print(f"== NEIGHBOURS, walking out from {origin} (from the MAP; not yet confirmed cell by cell by the card) ==")
        seen, q = {origin}, deque([origin])
        while q:
            c = q.popleft()
            row = ", ".join(f"{f}:{o}" for f, o in sorted(nb[c]))
            print(f"  {c} [{byid[c]['core']}, index {byid[c]['index']}, grid {byid[c]['row']},{byid[c]['col']}]  {row or '(no connections)'}")
            for _, o in sorted(nb[c]):
                if o not in seen:
                    seen.add(o)
                    q.append(o)
    return 0 if (magic_ok and same and counts_ok) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
