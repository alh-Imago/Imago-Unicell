"""
test_neurotrix_lif.py — LIF reference model + generic StatefulUnit tests

Validates neurotrix_lif.py as ground truth for the eventual cell cluster:
  - subthreshold membrane trajectory matches the closed form (current mode)
  - threshold / fire / reset behave correctly at the rheobase boundary
  - refractory period suppresses firing and ignores input
  - regular-firing inter-spike interval is consistent under constant drive
  - synaptic mode (impulse vs current) changes the firing gain as specified
  - two-neuron chain: downstream input == weight * upstream output, and
    downstream never fires before upstream (the 'dataflow from upstream' claim)
  - the generic StatefulUnit base generalises: a second, non-neural instance
    (leaky-bucket rate limiter) runs on the same skeleton — substantiating
    'generic typed model for any schema', not just asserting it.

Run with: python3 test_neurotrix_lif.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from neurotrix_lif import (
    StatefulUnit, LIFNeuron, LIFParams, Synapse, run_chain,
)

results = []

def check(label, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    print(f"  [{status}] {label}")

def approx(a, b, eps=1e-9):
    return abs(a - b) < eps


print("Subthreshold dynamics (current mode)")
n = LIFNeuron(LIFParams(tau_m=20.0, dt=1.0, v_th=1e9, syn_mode="current"))
v0 = n.state
for _ in range(10):
    n.step(0.5)
check("V trajectory matches closed form (10 ticks)",
      approx(n.state, n.analytic_v(v0, 0.5, 10)))
# leak factor is exp(-dt/tau)
check("beta == exp(-dt/tau_m)",
      approx(n.p.beta, __import__("math").exp(-1.0/20.0)))
# steady state under constant current is v_rest + R*I
n2 = LIFNeuron(LIFParams(tau_m=5.0, v_th=1e9, syn_mode="current"))
for _ in range(500):
    n2.step(0.3)
check("steady state -> v_rest + R*I", approx(n2.state, 0.3, 1e-6))

print("\nThreshold / fire / reset")
n = LIFNeuron(LIFParams(v_th=1.0, v_reset=0.0, syn_mode="impulse"))
out_below = n.step(0.9)        # 0.9 < 1.0 -> no fire
check("below threshold: no spike", out_below == 0)
check("below threshold: V retained", n.state > 0)
out_at = n.step(0.2)           # 0.9*beta + 0.2 may or may not cross; force it:
n3 = LIFNeuron(LIFParams(v_th=1.0, v_reset=0.0, syn_mode="impulse"))
out = n3.step(1.0)             # exactly at threshold -> fire (>=)
check("at threshold (>=): spike emitted", out == 1)
check("after spike: V reset to v_reset", approx(n3.state, 0.0))
n4 = LIFNeuron(LIFParams(v_th=1.0, v_reset=0.3, syn_mode="impulse"))
n4.step(2.0)
check("reset goes to v_reset, not zero", approx(n4.state, 0.3))

print("\nRefractory period")
n = LIFNeuron(LIFParams(v_th=1.0, v_reset=0.0, refrac=3, syn_mode="impulse"))
first = n.step(2.0)            # fires
during = [n.step(2.0) for _ in range(3)]   # refractory: must NOT fire
after_clamp = n.state
check("fires on suprathreshold input", first == 1)
check("no firing during refractory window", sum(during) == 0)
check("V clamped at reset during refractory", approx(after_clamp, 0.0))
recovered = n.step(2.0)       # refractory over -> can fire again
check("fires again after refractory", recovered == 1)

print("\nRheobase boundary")
# Just-above vs just-below sustained current (current mode). Steady = R*I;
# fires iff steady can reach threshold. With leak, need R*I >= v_th.
hot = LIFNeuron(LIFParams(tau_m=20.0, v_th=1.0, syn_mode="current"))
cold = LIFNeuron(LIFParams(tau_m=20.0, v_th=1.0, syn_mode="current"))
hot_sp = sum(hot.step(1.05) for _ in range(300))   # steady 1.05 > 1.0 -> fires
cold_sp = sum(cold.step(0.95) for _ in range(300)) # steady 0.95 < 1.0 -> never
check("just above rheobase fires", hot_sp > 0)
check("just below rheobase never fires", cold_sp == 0)

print("\nRegular firing — consistent inter-spike interval")
n = LIFNeuron(LIFParams(tau_m=20.0, v_th=1.0, v_reset=0.0, syn_mode="current"))
spikes = [n.step(1.5) for _ in range(300)]
spike_ticks = [i for i, s in enumerate(spikes) if s]
isis = [b - a for a, b in zip(spike_ticks, spike_ticks[1:])]
check("multiple regular spikes", len(spike_ticks) >= 3)
check("inter-spike intervals constant",
      len(set(isis[1:])) <= 1 if len(isis) > 1 else True)

print("\nSynaptic mode changes firing gain")
imp = LIFNeuron(LIFParams(v_th=1.0, syn_mode="impulse"))
cur = LIFNeuron(LIFParams(v_th=1.0, syn_mode="current"))
check("impulse gain == 1", approx(imp.p.input_gain, 1.0))
check("current gain == (1-beta)", approx(cur.p.input_gain, 1.0 - cur.p.beta))
# single pulse of 1.0: impulse fires, current does not
check("single pulse fires in impulse mode", imp.step(1.0) == 1)
check("single pulse does NOT fire in current mode", cur.step(1.0) == 0)

print("\nTwo-neuron chain — dataflow from upstream")
up   = LIFNeuron(LIFParams(v_th=1.0, v_reset=0.0, refrac=1, syn_mode="current"))
down = LIFNeuron(LIFParams(v_th=1.0, v_reset=0.0, syn_mode="impulse"))
syn  = Synapse(weight=1.5)
up_s, down_s = run_chain(up, down, syn, drive_current=1.5, n_ticks=120)
check("upstream produces spikes", sum(up_s) > 0)
check("downstream produces spikes", sum(down_s) > 0)
check("downstream never fires before upstream has",
      all(any(up_s[:i+1]) for i, s in enumerate(down_s) if s))
# synapse arithmetic: postsynaptic current is exactly weight * spike
check("synapse transmits weight*spike",
      approx(syn.transmit(1), 1.5) and approx(syn.transmit(0), 0.0))

print("\nGeneric StatefulUnit generalises (non-neural instance)")
# A leaky-bucket rate limiter: SAME skeleton, different schema. State is a
# fill level that leaks at a fixed rate, integrates arrivals, and 'fires'
# (drops/overflows) when it exceeds capacity. Proves the base is not
# LIF-specific.
class LeakyBucket(StatefulUnit):
    def __init__(self, capacity, leak_rate):
        super().__init__(state=0.0)
        self.capacity = capacity
        self.leak_rate = leak_rate
    def leak(self, s):       return max(0.0, s - self.leak_rate)
    def integrate(self, s, inp): return s + inp
    def fire(self, s):       return s > self.capacity
    def emit(self, s, fired): return 1 if fired else 0   # 1 = overflow/drop
    def reset(self, s):      return self.capacity        # clamp at full

b = LeakyBucket(capacity=5.0, leak_rate=1.0)
# Steady arrivals below leak: never overflows.
under = sum(b.step(0.5) for _ in range(50))
check("leaky bucket under leak rate never overflows", under == 0)
# Burst above capacity: overflows, then clamps.
b2 = LeakyBucket(capacity=5.0, leak_rate=1.0)
burst = [b2.step(3.0) for _ in range(5)]
check("leaky bucket overflows on burst", sum(burst) > 0)
check("leaky bucket clamps at capacity after overflow", b2.state <= 5.0 + 1e-9)
check("same step() skeleton drives both LIF and LeakyBucket",
      isinstance(b, StatefulUnit) and isinstance(LIFNeuron(), StatefulUnit))

# ---- Results ----------------------------------------------------------------
print(f"\n{'='*55}")
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
