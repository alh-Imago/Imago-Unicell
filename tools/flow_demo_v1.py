#!/usr/bin/env python3
"""tools/flow_demo_v1.py -- ledger #1033: the flow medium working. Profiles printed here come out of the GENERATED RTL; each run is checked against the exact reference and for conservation.
A slug of fluid (4000) starts in cell 1 of a closed row of cells; three runs of the same hardware:
  standard   no commands: diffusion only (spreads both ways, the walls reflect it)
  pumped     the same pump command on every cell all the time: a steady drift to the right on top of the diffusion
  instructed a command SCHEDULE: pump cells 1-3 for the first steps, then stop: the slug is pushed along, then left to spread
  python3 tools/flow_demo_v1.py"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("tools", "tests/vm"):
    sys.path.insert(0, os.path.join(ROOT, sub))
from fp_block_runner_v1 import run_rtl  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402
import flow_flex_v1 as F  # noqa: E402

N, T = 7, 8


def main():
    g = Grid(rows=N * 30 + 20, cols=T * 120 + 40)
    ent, ex, _ = F.flow_medium(g, N, T)
    g.balance(limit=400)
    c0 = [0, 4000, 0, 0, 0, 0, 0]
    runs = {"standard (no commands)": [[0] * N] * T,
            "pumped (command 4 everywhere, always)": [[4] * N] * T,
            "instructed (pump cells 1-3 at 6, steps 0-3 only)": [[6 if 1 <= i <= 3 and t < 4 else 0 for i in range(N)] for t in range(T)]}
    vec = list(runs.values())
    ents = {ent[("C", i)]: [c0[i]] * len(vec) for i in range(N)}
    ents.update({ent[("A", i, t)]: [v[t][i] for v in vec] for i in range(N - 1) for t in range(T)})
    names = {k: f"X{n}" for n, k in enumerate(ex)}
    got = run_rtl(tempfile.mkdtemp(), "flowdemo", g.records(), ents, {names[k]: c for k, c in ex.items()}, "plain", settle=80000, cycles=len(vec) * 900 + 60000)
    print(f"Flow medium: {N} cells x {T} steps = {len(g.nodes)} flex cells; diffusion hands 1/8 to each neighbour, the pump hands command/8 to the right")
    ok = True
    for q, (title, cm) in enumerate(runs.items()):
        ref = F.flow_ref(c0, cm)
        print(f"\n{title}\n  step " + "".join(f"{'cell ' + str(i):>7}" for i in range(N)) + "   total")
        print(f"  {0:4d} " + "".join(f"{x:7d}" for x in c0) + f"   {sum(c0)}")
        for t in range(T):
            prof = [got[names[(i, t)]][q] for i in range(N)]
            ok &= prof == ref[t] and sum(prof) == sum(c0)
            print(f"  {t + 1:4d} " + "".join(f"{x:7d}" for x in prof) + f"   {sum(prof)}")
    print("\nall profiles match the reference and the total is conserved:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
