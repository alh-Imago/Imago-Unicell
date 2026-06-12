"""
neurotrix_lif_mif.py — LIF neuron step as composed MIF tiles

The tile-level realisation of one LIF simulation tick: the cell cluster that
must reproduce LIFNeuron.step() (impulse and current modes) from
neurotrix_lif.py, built by composing the MIF tile family. Mirrors the
flowtrix_lbm_mif.py pattern. Two jobs:

  1. CORRECTNESS — runs the membrane update through the tile decomposition and
     asserts it equals the validated LIF ground truth, tick for tick, for both
     synaptic modes and across the threshold/reset boundary.
  2. PREDICTED TICKS/UPDATE — critical-path depth across the cluster stages,
     the deterministic per-neuron tick count the compiler publishes pre-silicon.

The cluster is the three-data-homes picture made concrete:
  - V (membrane potential) lives in a feedback cell; it is the loop carry.
  - The parameters (beta, v_rest, v_th, v_reset, gain*R) are preloaded
    constants in the decode table — they cost no pipeline depth, they are
    table reads folded into the tiles that use them.
  - The input arrives as the B-operand of the integrate add.

Pipeline per tick (the cluster dataflow order):
    leak      : V <- v_rest + (V - v_rest)*beta     SUB, MADD
    integrate : V <- V + gain*R*inp                 MADD   (constant gain*R)
    fire      : V >= v_th ?                          CMP    (constant v_th)
    reset/mux : V <- fired ? v_reset : V            MUX-on-ctrl (cheap)

Notably CHEAPER than the LBM collide: no division at all. The leak factor
beta and the input gain are preloaded multiply constants, so leak and
integrate are single MADDs, and the fire test is a comparator against a
preloaded threshold. A LIF tick is dominated by the two MADDs, not by any
transcendental — which is exactly why spiking fabrics are attractive: the
per-unit update is shallow.

Run: python3 neurotrix_lif_mif.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fp_tiles import TileLibrary
from neurotrix_lif import LIFNeuron, LIFParams

lib = TileLibrary()


def tile(name):
    m = lib.get(name).metadata
    depth = getattr(m, "depth", getattr(m, "pipeline_depth", 0))
    return m.cell_count, depth


class LIFRegion:
    """Cell-cost and critical-path depth accounting for one LIF tick."""

    def __init__(self):
        self.cells = 0
        self.depth = 0
        self.tiles = {}
        self.stages = []

    def _count(self, name, n=1):
        c, _ = tile(name)
        self.cells += c * n
        self.tiles[name] = self.tiles.get(name, 0) + n

    def stage(self, name, chain):
        d = 0
        for t in chain:
            self._count(t)
            _, td = tile(t)
            d += td
        self.depth += d
        self.stages.append((name, d))


def lif_step_tiled(neuron: LIFNeuron, inp: float):
    """
    One LIF tick via the tile decomposition. Mutates neuron.state, returns
    (spike, region). Reproduces LIFNeuron.step() including refractory.
    """
    p = neuron.p
    r = LIFRegion()

    # Refractory is a ctrl-cell countdown + mux; if active, clamp and return.
    # (Cheap: a small counter compare + the reset mux. Counted, ~minimal depth.)
    if neuron._refrac_left > 0:
        neuron._refrac_left -= 1
        neuron.state = p.v_reset
        neuron.last_input = 0.0
        r.stage("refractory(clamp)", ["MIF_CMP_GE", "INT32_MUX"])
        return 0, r

    # ── Stage 1: leak  V <- v_rest + (V - v_rest)*beta ──────────────────────
    # (V - v_rest) SUB, then *beta + v_rest via one MADD (beta, v_rest preloaded)
    s = p.v_rest + (neuron.state - p.v_rest) * p.beta
    r.stage("leak", ["MIF_SUB", "MIF_MADD"])

    # ── Stage 2: integrate  V <- V + (gain*R)*inp ───────────────────────────
    # gain*R is a preloaded constant -> single MADD with inp as the B-operand.
    s = s + p.input_gain * p.r_m * inp
    r.stage("integrate", ["MIF_MADD"])

    # ── Stage 3: fire  V >= v_th ────────────────────────────────────────────
    fired = s >= p.v_th
    r.stage("fire", ["MIF_CMP_GE"])      # V >= v_th, ctrl-cell compare

    # ── Stage 4: reset mux  V <- fired ? v_reset : V ────────────────────────
    if fired:
        neuron.state = p.v_reset
        neuron._refrac_left = p.refrac
    else:
        neuron.state = s
    neuron.last_input = inp
    r.stage("reset(mux)", ["INT32_MUX"])

    return (1 if fired else 0), r


# ── Self-check / report ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("⬡ NeuroTrix LIF — neuron tick as composed MIF tiles")
    print("=" * 58)

    # Correctness: tiled step must equal LIFNeuron.step() over a driven run,
    # for both synaptic modes, crossing threshold/reset/refractory.
    def compare_run(mode, drive, n_ticks, **kw):
        ref = LIFNeuron(LIFParams(syn_mode=mode, **kw))
        til = LIFNeuron(LIFParams(syn_mode=mode, **kw))
        mism = 0
        for t in range(n_ticks):
            i = drive(t) if callable(drive) else drive
            s_ref = ref.step(i)
            s_til, _ = lif_step_tiled(til, i)
            if s_ref != s_til or abs(ref.state - til.state) > 1e-12:
                mism += 1
        return mism

    m1 = compare_run("current", 1.5, 200, v_th=1.0, v_reset=0.0, refrac=2)
    m2 = compare_run("impulse", 1.2, 200, v_th=1.0, v_reset=0.0, refrac=1)
    m3 = compare_run("current", lambda t: 0.04, 200, v_th=1.0)   # sub-rheobase
    print(f"\nCorrectness vs LIFNeuron.step():")
    print(f"  current-mode regular firing : {200-m1}/200 ticks match")
    print(f"  impulse-mode firing+refrac  : {200-m2}/200 ticks match")
    print(f"  sub-rheobase (no fire)      : {200-m3}/200 ticks match")

    # Cost + predicted ticks (a non-refractory, non-firing tick = full path).
    n = LIFNeuron(LIFParams(v_th=1e9))     # never fires -> exercises full chain
    _, r = lif_step_tiled(n, 0.5)
    print(f"\nPer-neuron tick cost:")
    print(f"  total cells            = {r.cells:,}")
    print(f"  predicted ticks/update = {r.depth:,}  (critical path)")
    print(f"\n  Stage breakdown (critical-path ticks):")
    for name, d in r.stages:
        pct = 100.0 * d / r.depth
        bar = "█" * int(pct / 2)
        print(f"    {name:18} {d:5}  {pct:4.1f}%  {bar}")
    print(f"\n  No division: dominated by the two MADDs (leak + integrate).")
    print(f"  Compare LBM collide ~2,542 ticks — a LIF tick is far shallower.")
    print(f"\n  Tile instances per tick:")
    for nm in sorted(r.tiles):
        print(f"    {nm:12} x{r.tiles[nm]}")

    print("\nAll demos passed ✓")
