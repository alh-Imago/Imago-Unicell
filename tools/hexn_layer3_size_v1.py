"""hexn_layer3_size_v1: how much memory does layer 3 need? (Python only; reads tools/hexn_layer3_v1.py, untouched; no RTL.) Alan, 27 Oct 2026: "move into the layer 3 side".
Runs the layer 3 model over the synthetic coupled world (3 channels) for several lengths and settings and counts what a hardware version would have to hold, with the tokenisation of store v5 (only known values get a table slot):
  snapshots  = distinct snapshots (one key per channel) seen as context elements  -> size of a snapshot-ID table
  moments    = distinct moments (sets of changes) seen as followers              -> size of a moment-ID table
  contexts   = distinct (length, mask, context) keys                             -> index slots
  entries    = distinct (context, follower) pairs                                -> entry slots
  rows(R=4)  = rows of 4 entry slots needed (a context with f followers takes ceil(f/4) rows) -> heap rows
Limit: the world is synthetic (four routines, one hidden light state, a drifting third channel), so the counts show the SHAPE of the demand (how it grows with context length and masks), not the demand of real data."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as V1
def count(n_routines, L, masks, seed=1):
    ev = V1.world(n_routines=n_routines, seed=seed); seq = V1.moments(ev); nch = 1 + max(c for _, c, _ in ev)
    ms = V1.Layer3(nch=nch, L=L, masks=masks); snaps = set(); moms = set()
    for i, mo in enumerate(seq):
        for c, k in mo: ms.feed(i * 1000, c, k)
        ms.flush(); moms.add(mo)
        if None not in ms.snap: snaps.add(tuple(ms.snap))
    ctxs = len(ms.tab); ents = sum(len(d) for d in ms.tab.values()); rows = sum(-(-len(d) // 4) for d in ms.tab.values())
    return dict(moments_seen=len(seq), snapshots=len(snaps), moment_ids=len(moms), contexts=ctxs, entries=ents, rows=rows)
if __name__ == "__main__":
    full = [(1, 1, 1)]; red = None
    print("%-34s %8s %9s %8s %9s %8s %7s" % ("setting", "moments", "snapshots", "momentID", "contexts", "entries", "rows"))
    for n in (400, 4000):
        for name, L, mk in (("L=2 full mask", 2, full), ("L=3 full mask", 3, full), ("L=4 full mask", 4, full), ("L=4 all masks", 4, red), ("L=6 all masks", 6, red)):
            d = count(n, L, mk); print("%-34s %8d %9d %8d %9d %8d %7d" % ("%d routines, %s" % (n, name), d["moments_seen"], d["snapshots"], d["moment_ids"], d["contexts"], d["entries"], d["rows"]))
    print("store v5 on the Tang holds 1,024 index slots, 512 rows, 2,048 entry slots (measured sizes: 14 BSRAM in the whole core).")
