#!/usr/bin/env python3
# STATUS (docs/STATUS_MAP.md, 9 Oct 2026): DEMO of a live-line generator (LIF neuron); no test of its own. Moved here from tools/.
"""tools/lif_demo_v1.py -- ledger #1030: show the LIF neuron working. The spike trains printed here come out of the GENERATED RTL of the flex cells (not from the Python reference); each line is
checked against the reference and the script says so.
  1. one neuron, 16 steps, constant input current swept: the f-I curve (leak, threshold, soft reset)
  2. two neurons coupled A -> B and B -> A (excitatory), A kicked once: the activity ping-pongs between them
  python3 tools/lif_demo_v1.py"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/experimental/ -> repo root
for sub in ("tools", "tests/vm"):
    sys.path.insert(0, os.path.join(ROOT, sub))
from fp_block_runner_v1 import run_rtl  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402
import lif_flex_v1 as L  # noqa: E402

K, TH = 3, 256
bar = lambda sp: "".join("|" if s else "." for s in sp)  # noqa: E731


def main():
    T = 16
    g = Grid(rows=40, cols=40 * T + 40)
    ent, ex, _ = L.lif_neuron(g, T, K, TH)
    g.balance(limit=400)
    cur = [0, 40, 60, 80, 100, 130, 160, 200, 256, 320, 400]
    ents = {ent[f"I{t}"]: list(cur) for t in range(T)}
    exits = {f"S{t}": ex[f"S{t}"] for t in range(T)}
    got = run_rtl(tempfile.mkdtemp(), "lifdemo1", g.records(), ents, exits, "plain", settle=40000, cycles=len(cur) * 300 + 20000)
    print(f"One LIF neuron ({len(g.nodes)} flex cells): leak v>>{K}, threshold {TH}, soft reset; constant input current, {T} steps")
    print(" current  spikes  train")
    ok = True
    for q, c in enumerate(cur):
        sp = [got[f"S{t}"][q] for t in range(T)]
        ref, _ = L.lif_ref([c] * T, K, TH)
        ok &= sp == ref
        print(f" {c:7d}  {sum(sp):6d}  {bar(sp)}")
    print(" matches the Python reference:", ok)
    T, W = 14, [[0, 300], [300, 0]]
    g = Grid(rows=70, cols=40 * T + 60)
    ent, ex, _ = L.lif_network(g, 2, T, W, K, TH)
    g.balance(limit=400)
    kick = [[400] + [0] * (T - 1), [0] * T]
    ents = {ent[(j, t)]: [kick[j][t]] for j in range(2) for t in range(T)}
    exits = {f"S{j}_{t}": ex[(j, t)] for j in range(2) for t in range(T)}
    got = run_rtl(tempfile.mkdtemp(), "lifdemo2", g.records(), ents, exits, "plain", settle=40000, cycles=30000)
    sp = [[got[f"S{j}_{t}"][0] for t in range(T)] for j in range(2)]
    ref, _ = L.net_ref(kick, W, K, TH)
    print(f"\nTwo coupled neurons ({len(g.nodes)} flex cells): A kicked once at step 0 with 400; A -> B weight {W[0][1]}, B -> A weight {W[1][0]}")
    print("  A ", bar(sp[0]))
    print("  B ", bar(sp[1]))
    print(" matches the Python reference:", sp == ref)
    return 0 if ok and sp == ref else 1


if __name__ == "__main__":
    sys.exit(main())
