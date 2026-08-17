"""
test_neurotrix_lif_mif.py — LIF tile composition tests

Validates neurotrix_lif_mif.py: the LIF cell cluster built from MIF tiles must
reproduce LIFNeuron.step() exactly (both synaptic modes, across threshold,
reset, and refractory), and the tick accounting must be self-consistent.

Run with: python3 test_neurotrix_lif_mif.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from neurotrix_lif import LIFNeuron, LIFParams
from neurotrix_lif_mif import lif_step_tiled, LIFRegion

results = []
def check(label, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    print(f"  [{status}] {label}")


def run_match(mode, drive, n_ticks, **kw):
    """Return (mismatches, ref_spikes) comparing tiled vs ground-truth step."""
    ref = LIFNeuron(LIFParams(syn_mode=mode, **kw))
    til = LIFNeuron(LIFParams(syn_mode=mode, **kw))
    mism = 0
    ref_spikes = 0
    for t in range(n_ticks):
        i = drive(t) if callable(drive) else drive
        s_ref = ref.step(i)
        s_til, _ = lif_step_tiled(til, i)
        ref_spikes += s_ref
        if s_ref != s_til or abs(ref.state - til.state) > 1e-12:
            mism += 1
    return mism, ref_spikes


print("Tiled step matches ground truth")
m, sp = run_match("current", 1.5, 300, v_th=1.0, v_reset=0.0, refrac=2)
check("current-mode regular firing matches all ticks", m == 0)
check("current-mode actually fired (non-trivial run)", sp > 0)

m, sp = run_match("impulse", 1.2, 300, v_th=1.0, v_reset=0.0, refrac=3)
check("impulse-mode firing+refractory matches all ticks", m == 0)
check("impulse-mode actually fired", sp > 0)

m, _ = run_match("current", lambda t: 0.04, 200, v_th=1.0)
check("sub-rheobase (never fires) matches all ticks", m == 0)

# Single-pulse mode difference must survive the decomposition.
imp = LIFNeuron(LIFParams(v_th=1.0, syn_mode="impulse"))
cur = LIFNeuron(LIFParams(v_th=1.0, syn_mode="current"))
s_imp, _ = lif_step_tiled(imp, 1.0)
s_cur, _ = lif_step_tiled(cur, 1.0)
check("single pulse fires in impulse mode (tiled)", s_imp == 1)
check("single pulse does NOT fire in current mode (tiled)", s_cur == 0)

# Refractory: a burst that would fire every tick must be suppressed in-window.
n = LIFNeuron(LIFParams(v_th=1.0, v_reset=0.0, refrac=3, syn_mode="impulse"))
outs = [lif_step_tiled(n, 2.0)[0] for _ in range(5)]
check("tiled refractory suppresses firing in window", outs == [1, 0, 0, 0, 1])

print("\nTick accounting self-consistency")
n = LIFNeuron(LIFParams(v_th=1e9))      # full chain, no fire
_, r = lif_step_tiled(n, 0.5)
check("predicted ticks > 0", r.depth > 0)
check("stage depths sum to total critical path",
      sum(d for _, d in r.stages) == r.depth)
check("no MIF_DIV in a LIF tick (division-free)",
      "MIF_DIV" not in r.tiles)
check("leak+integrate (two MADDs) dominate the path",
      r.tiles.get("MIF_MADD") == 2)
# Structural determinism: predicted depth independent of input value.
_, r2 = lif_step_tiled(LIFNeuron(LIFParams(v_th=1e9)), 99.0)
check("predicted ticks independent of input (structural)", r2.depth == r.depth)
# A LIF tick is much shallower than the LBM collide (~2542) — sanity bound.
check("LIF tick far shallower than LBM collide", r.depth < 600)

# ---- Results ----------------------------------------------------------------
print(f"\n{'='*58}")
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
