"""
neurotrix_lif.py — Leaky Integrate-and-Fire reference model (ground truth)

This is the single-site reference for a LIF neuron, the way flow.collide() is
the single-site reference for an LBM tile: exact Python dynamics that the
eventual NOR cell-cluster must reproduce, tick for tick.

It is written in two layers on purpose:

  StatefulUnit  — the GENERIC typed stateful unit. A cluster that holds typed
                  state, evolves it autonomously (leak), aggregates streamed
                  input into it (integrate), tests a fire condition, emits an
                  output, and resets. The base class is agnostic to WHAT the
                  state is — scalar, vector, a FormatDefinition-typed value.
                  This is the temporal complement to cell_format.py: a
                  FormatDefinition says what data IS; a StatefulUnit says how
                  state EVOLVES over time.

  LIFNeuron     — the concrete instance. State is a scalar membrane potential.
                  Fills in the five rule slots with the leaky integrate-and-
                  fire equations.

Why the split matters: the LIF update IS the three-primitive reduction from
the paper (§9.2) made temporal —
    hold state        -> the membrane potential V persists across ticks
    aggregate input   -> I = sum of weighted incoming spikes (wired-OR fan-in)
    apply threshold   -> fire when V >= V_th
So LIF is not a special case bolted on; it is the canonical demonstration of
the thesis with time as an explicit axis. Any other schema that holds state,
folds in streamed input, and emits on a rule (accumulator-with-overflow,
leaky-bucket rate limiter, moving-average detector, a typed FSM) is the SAME
skeleton with different slot fillings.

THREE KINDS OF DATA, THREE HOMES (the design question that motivated this):
  - state (V)        -> ONE persistent feedback cell, loops to itself
  - parameters       -> preloaded constants in the decode table (threshold,
                        leak factor, reset) — never travel on the bus
  - streamed input   -> arrives as the B-input each tick (the upstream model's
                        spikes, weighted and summed). Combinational structure
                        cells transforming it hold NO persistent state, so
                        there is nothing in them to overwrite.

DATAFLOW COMES FROM UPSTREAM: I(t) for a neuron is the resolved spike output
of its presynaptic neighbours. External data enters ONLY at the input-layer
boundary (injection / inlet); every downstream neuron is fed by upstream
spikes through the wiring. The two-arrival model enforces ordering for free:
a neuron holds V (A) and cannot fire before its input (B) arrives.

TIME vs PROPAGATION (the distinction the reference must keep straight):
  - simulation time : V leaks, threshold checked, refractory counts down —
                      once per timestep (one call to step()).
  - spike propagation: a spike moving one hop to a downstream neuron — topology.
Conflating them makes the timing validation lie. step() is one simulation
tick; wiring two units chains propagation.

Run: python3 neurotrix_lif.py
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field


# ── Generic typed stateful unit ───────────────────────────────────────────────

class StatefulUnit:
    """
    A typed stateful compute unit: hold state, leak, integrate input, fire,
    reset. Subclass and fill the five rule slots. The base sequences them.

    The per-tick pipeline (this IS the cell-cluster dataflow order):

        held_state
          -> leak(state)            autonomous self-evolution
          -> integrate(state, in)   fold streamed input into state
          -> fired = fire?(state)   test the condition
          -> out = emit(state, fired)
          -> state = reset(state) if fired else state
          -> (new state loops back to the feedback cell)

    state may be any type. The base never inspects it; only the rule slots do.
    """

    def __init__(self, state):
        self.state = state          # persistent — the one thing that survives a tick

    # ── rule slots (override) ────────────────────────────────────────────────
    def leak(self, state):
        """Autonomous evolution with no input. Default: identity (no leak)."""
        return state

    def integrate(self, state, inp):
        """Fold this tick's streamed input into state. Default: add."""
        return state + inp

    def fire(self, state) -> bool:
        """Predicate: does the unit emit this tick? Default: never."""
        return False

    def emit(self, state, fired):
        """Output value on the wire this tick. Default: the fire bit."""
        return 1 if fired else 0

    def reset(self, state):
        """State after a fire. Default: unchanged."""
        return state

    # ── the sequenced tick ───────────────────────────────────────────────────
    def step(self, inp):
        """
        Advance ONE simulation tick with streamed input `inp`.
        Returns the emitted output. Mutates self.state.
        """
        s = self.leak(self.state)
        s = self.integrate(s, inp)
        fired = self.fire(s)
        out = self.emit(s, fired)
        self.state = self.reset(s) if fired else s
        return out


# ── Concrete: Leaky Integrate-and-Fire neuron ─────────────────────────────────

@dataclass
class LIFParams:
    """The 'rules to compare with' — preloaded constants, never on the bus."""
    tau_m:    float = 20.0    # membrane time constant (ms)
    dt:       float = 1.0     # simulation timestep (ms)
    v_rest:   float = 0.0     # resting potential
    v_th:     float = 1.0     # firing threshold
    v_reset:  float = 0.0     # post-spike reset potential
    r_m:      float = 1.0     # membrane resistance (scales input current)
    refrac:   int   = 0       # refractory period in ticks (0 = none)
    syn_mode: str   = "impulse"  # "impulse" | "current" — see note below

    # Synaptic input mode — the modelling fork the reference forces open:
    #   "impulse": a spike dumps its full weight onto V this tick (delta
    #              synapse). Standard for spike-driven NETWORKS; discrete
    #              events work as events. Gain = 1.
    #   "current": input is a sustained current density over the tick; charge
    #              delivered is (1-beta)*R*I — exact for CONSTANT injected
    #              current. Use for the external drive at the input boundary,
    #              and the only mode for which analytic_v (closed form) holds.
    # The choice is not cosmetic: it changes the steady state and the firing
    # gain by a factor of (1-beta). State it per model.

    @property
    def beta(self) -> float:
        """Leak factor per tick: exp(-dt/tau_m). Preloaded multiply constant."""
        return math.exp(-self.dt / self.tau_m)

    @property
    def input_gain(self) -> float:
        """Charge per unit R*I delivered in one tick, per synaptic mode."""
        return 1.0 if self.syn_mode == "impulse" else (1.0 - self.beta)


class LIFNeuron(StatefulUnit):
    """
    Leaky integrate-and-fire neuron.

    State is the scalar membrane potential V. Subthreshold dynamics:
        tau_m dV/dt = -(V - V_rest) + R*I(t)
    Exact discrete step for piecewise-constant input over dt:
        V <- V_rest + R*I + (V - V_rest - R*I) * beta,   beta = exp(-dt/tau_m)
    On V >= V_th: emit a spike, V <- V_reset, enter refractory for `refrac`
    ticks (during which input is ignored and V is clamped at reset).
    """

    def __init__(self, params: LIFParams | None = None):
        self.p = params or LIFParams()
        super().__init__(state=self.p.v_rest)
        self._refrac_left = 0       # refractory countdown (own persistent state)
        self.last_input = 0.0       # bookkeeping for the exact-leak form

    def step(self, inp):
        """
        One simulation tick. `inp` is the input CURRENT this tick (already the
        weighted sum of upstream spikes — that summation is the fan-in tree,
        not this unit's job).

        Pipeline (matches the cell-cluster dataflow order):
          leak  : V <- v_rest + (V - v_rest)*beta
          add   : V <- V + gain * R * inp
          fire  : V >= v_th ?
          reset : V <- v_reset, arm refractory
        """
        p = self.p

        # Refractory: clamp at reset, ignore input, count down. No fire.
        if self._refrac_left > 0:
            self._refrac_left -= 1
            self.state = p.v_reset
            self.last_input = 0.0
            return 0

        # leak (autonomous) then integrate (streamed input) — the two stages
        # are deliberately separate so the cell cluster mirrors them.
        s = p.v_rest + (self.state - p.v_rest) * p.beta
        s = s + p.input_gain * p.r_m * inp

        fired = s >= p.v_th
        if fired:
            self.state = p.v_reset
            self._refrac_left = p.refrac
        else:
            self.state = s
        self.last_input = inp
        return 1 if fired else 0

    # Closed-form trajectory under CONSTANT current (syn_mode='current' only,
    # subthreshold, no spikes). V(n) after n ticks from v0:
    #   steady = v_rest + R*I ; V(n) = steady + (v0 - steady)*beta^n
    def analytic_v(self, v0: float, inp: float, n: int) -> float:
        p = self.p
        steady = p.v_rest + p.r_m * inp
        return steady + (v0 - steady) * (p.beta ** n)


# ── A two-neuron chain: 'dataflow comes from the upstream model' ───────────────

class Synapse:
    """A single weighted connection. Output spike * weight = postsynaptic current."""
    def __init__(self, weight: float):
        self.weight = weight

    def transmit(self, spike: int) -> float:
        return self.weight * spike


def run_chain(upstream: LIFNeuron, downstream: LIFNeuron,
              synapse: Synapse, drive_current, n_ticks: int):
    """
    Run upstream driven by `drive_current` (external injection at the input
    boundary), feed its spikes through `synapse` into downstream. This is the
    moment the upstream's spike train STOPS being injected and BECOMES the
    downstream's input. Returns (upstream_spikes, downstream_spikes).
    """
    up_spikes, down_spikes = [], []
    for t in range(n_ticks):
        i_ext = drive_current(t) if callable(drive_current) else drive_current
        s_up = upstream.step(i_ext)
        i_down = synapse.transmit(s_up)        # upstream output -> downstream input
        s_down = downstream.step(i_down)
        up_spikes.append(s_up)
        down_spikes.append(s_down)
    return up_spikes, down_spikes


# ── Demo / self-check ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("⬡ NeuroTrix LIF reference")
    print("=" * 55)

    # 1. Subthreshold relaxation matches the closed form (current mode).
    n = LIFNeuron(LIFParams(tau_m=20.0, dt=1.0, v_th=1e9, syn_mode="current"))
    v0 = n.state
    I = 0.5
    for t in range(10):
        n.step(I)
    analytic = n.analytic_v(v0, I, 10)
    print(f"\nSubthreshold leak (current mode, 10 ticks, I=0.5):")
    print(f"  simulated V = {n.state:.6f}")
    print(f"  analytic  V = {analytic:.6f}")
    print(f"  match: {abs(n.state - analytic) < 1e-9}")

    # 2. Constant drive above rheobase -> regular firing (current mode).
    n = LIFNeuron(LIFParams(tau_m=20.0, dt=1.0, v_th=1.0, v_reset=0.0,
                            refrac=2, syn_mode="current"))
    spikes = [n.step(1.5) for _ in range(100)]
    n_spikes = sum(spikes)
    print(f"\nRegular firing (current I=1.5, 100 ticks, refrac=2):")
    print(f"  spikes = {n_spikes}")
    print(f"  first spike at tick = {spikes.index(1) if 1 in spikes else None}")

    # 3. Below rheobase -> never fires (current mode).
    n = LIFNeuron(LIFParams(tau_m=20.0, dt=1.0, v_th=1.0, r_m=1.0,
                            syn_mode="current"))
    sub = [n.step(0.04) for _ in range(200)]   # steady 0.04 << 1.0
    print(f"\nSub-rheobase (current I=0.04): spikes = {sum(sub)} (expect 0)")

    # 4. Two-neuron chain: upstream drives downstream via a synapse.
    #    Upstream: sustained external current (current mode) -> regular firing.
    #    Downstream: spike-driven (impulse mode) -> each upstream spike of
    #    weight 1.5 > threshold 1.0 drives it over one tick later. The
    #    'dataflow from upstream' becomes a delayed echo you can see.
    up   = LIFNeuron(LIFParams(tau_m=20.0, v_th=1.0, v_reset=0.0,
                               refrac=1, syn_mode="current"))
    down = LIFNeuron(LIFParams(tau_m=20.0, v_th=1.0, v_reset=0.0,
                               syn_mode="impulse"))
    syn  = Synapse(weight=1.5)
    up_s, down_s = run_chain(up, down, syn, drive_current=1.5, n_ticks=120)
    print(f"\nTwo-neuron chain (upstream current I=1.5, weight=1.5, 120 ticks):")
    print(f"  upstream spikes   = {sum(up_s)}")
    print(f"  downstream spikes = {sum(down_s)}")
    print(f"  downstream never fires before upstream: "
          f"{all(any(up_s[:i+1]) for i,s in enumerate(down_s) if s)}")

    print("\nAll demos passed ✓")
