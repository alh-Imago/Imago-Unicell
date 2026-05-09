# Neural Pond Design — UniCell v2
## LIF and Izhikevich Neurons in the Latch Model

*Design analysis: Grok (May 2026). Integration and gate_state mapping: Claudette.*

---

## Overview

UniCell cells can implement spiking neurons directly — each neuron is a small
cluster of cells in a pond, communicating via the wired-OR bus exactly like any
other pond computation. The same compiler, the same OS layer, the same .icm format.
Neural ponds sit alongside OS ponds, filesystem ponds, and compute ponds on the
same substrate — no special mode, no separate chip.

This document covers two designs:

1. **LIF (Leaky Integrate-and-Fire)** — 5 cells per neuron, latch model
2. **Izhikevich** — 8–12 cells per neuron, 20+ biologically realistic firing patterns

Both are for the **unicell-latch/** variant. The fixed 2-tick latency per cell
makes pipeline depth predictable, which matters for neuron timing.

---

## Why the Latch Model

The latch model is the right choice for neural ponds:

- **Fixed 2-tick latency per cell** — neuron timing is topologically deterministic
- **No edge-sensitivity concerns** — membrane integration doesn't need posedge/negedge awareness
- **PASS cell = 2-tick delay** — inserting a PASS cell anywhere adds exactly 2 ticks;
  refractory period length is set by PASS chain depth
- **Timing skew absorbed** — large neuron arrays don't suffer clock drift issues

The standard and edge variants work too, but latch is the cleanest model for
sustained, cyclic, spike-generating computation.

---

## Design 1: LIF Neuron — 5 Cells

*Revised design from Grok (May 2026). Reduces previous 6-cell version by
removing a redundant re-arm cell.*

### Cell layout

```
┌─────┬──────────────────┬──────────────────────────┬──────────────────────────┐
│ Cell │ Role             │ gate_state               │ Connections              │
├─────┼──────────────────┼──────────────────────────┼──────────────────────────┤
│ C0  │ Membrane latch   │ GS_LATCH_IN | LOOP_MODE  │ A←synaptic, B←leak(C1)  │
│     │                  │ | GS_PASS                │ out→C1,C2                │
│     │                  │ 0x02000400               │                          │
├─────┼──────────────────┼──────────────────────────┼──────────────────────────┤
│ C1  │ Leak + integrate │ GS_SYNC_WAIT | GS_OR_V2  │ A←membrane(C0)          │
│     │                  │ 0x00008024               │ B←synaptic spike input   │
│     │                  │                          │ out→C0                   │
├─────┼──────────────────┼──────────────────────────┼──────────────────────────┤
│ C2  │ Threshold        │ GS_SYNC_WAIT | GS_XNOR_V2│ A←membrane(C0)          │
│     │ comparator       │ 0x0000803C               │ B←threshold constant     │
│     │                  │                          │ out→C3                   │
├─────┼──────────────────┼──────────────────────────┼──────────────────────────┤
│ C3  │ Spike generator  │ GS_ONE_SHOT              │ A←threshold fire(C2)     │
│     │                  │ | GS_OUT_POSEDGE         │ out→downstream + C4      │
│     │                  │ 0x04001000               │                          │
├─────┼──────────────────┼──────────────────────────┼──────────────────────────┤
│ C4  │ Refractory latch │ GS_LATCH                 │ A←spike(C3)             │
│     │                  │ 0x00000800               │ out→inhibits C2          │
└─────┴──────────────────┴──────────────────────────┴──────────────────────────┘
```

### Cycle flow

```
posedge:   Synaptic spike arrives at C1 (B input)
           C0 membrane value arrives at C1 (A input) and C2 (A input)
           Threshold constant arrives at C2 (B input)

tick:      C1 fires: OR(membrane, synaptic) → updated membrane → bus
           C0 latches updated membrane (holds for next cycle via LOOP_MODE)
           C2 fires: XNOR(membrane, threshold) → 1 if membrane ≥ threshold
           If C2 fires → C3 fires ONE_SHOT spike to downstream cells and C4
           C4 latches spike signal → inhibits C2 for next cycle (refractory)

negedge:   Output buffers drain to bus
           Refractory clears after 1 cycle (C4 self-clears on next cycle)
```

### Key properties

- **Leak**: approximated as bitwise OR with a decaying mask; true shift-based leak
  needs an extra PASS/NOT cell for precision, or can be approximated in C1's gate tree
- **Threshold**: the `threshold constant` at C2's B input is pre-loaded by the
  controller — a fixed bus address holding the threshold value for this neuron type
- **ONE_SHOT**: C3 fires exactly once per threshold crossing, then locks until
  re-armed. Re-arm is triggered by C4's refractory clearing
- **GS_OUT_POSEDGE on C3**: ensures the spike reaches downstream cells on the
  next rising edge, giving them a full half-cycle to receive it before their B arrives

### Gate state values (exact)

```python
from gate_states import (GS_LATCH_IN, LOOP_MODE, GS_PASS, GS_SYNC_WAIT,
                         GS_OR_V2, GS_XNOR_V2, GS_ONE_SHOT, GS_OUT_POSEDGE,
                         GS_LATCH)

C0 = GS_LATCH_IN | LOOP_MODE | GS_PASS   # 0x02000400 — membrane latch
C1 = GS_SYNC_WAIT | GS_OR_V2             # 0x00008024 — integrate
C2 = GS_SYNC_WAIT | GS_XNOR_V2           # 0x0000803C — threshold compare
C3 = GS_ONE_SHOT | GS_OUT_POSEDGE        # 0x04001000 — spike
C4 = GS_LATCH                            # 0x00000800 — refractory
```

### Scale

| Target | Cells available | LIF neurons (5c each) |
|--------|----------------|----------------------|
| iCEBreaker (iCE40UP5K) | 64 | **12 neurons** |
| Kintex-7 XC7K480T | 1,500 | **300 neurons** |
| Mid-range FPGA (10k cells) | 10,000 | **2,000 neurons** |
| Future ASIC (500M cells) | 500,000,000 | **100 million neurons** |

---

## Design 2: Izhikevich Neuron — 8–12 Cells

The Izhikevich model (2003) reproduces 20+ biologically realistic cortical firing
patterns with just 4 parameters (a, b, c, d):

```
dv/dt = 0.04v² + 5v + 140 - u + I
du/dt = a(bv - u)
if v ≥ 30: v ← c, u ← u + d
```

It is the most efficient standard model for biological plausibility. The UniCell
implementation uses fixed-point approximations of the quadratic and recovery terms.

### Cell layout (10-cell reference design)

```
┌──────┬──────────────────────────┬──────────────────────────┬─────────────────────────────┐
│ Cell │ Role                     │ gate_state               │ Notes                       │
├──────┼──────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ V0   │ Membrane v — integrate   │ GS_SYNC_WAIT | GS_OR_V2  │ A←v_prev, B←synaptic I     │
│      │                          │ 0x00008024               │                             │
│ V1   │ Membrane v — latch       │ GS_LATCH_IN | LOOP_MODE  │ A←V0 out, loops to V0       │
│      │                          │ | GS_PASS  0x02000400    │ Holds v between cycles      │
├──────┼──────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ U0   │ Recovery u — update      │ GS_SYNC_WAIT | GS_OR_V2  │ A←u_prev, B←bv term        │
│      │                          │ 0x00008024               │ bv = b * v (pre-scaled)     │
│ U1   │ Recovery u — latch       │ GS_LATCH_IN | LOOP_MODE  │ A←U0 out, loops to U0       │
│      │                          │ | GS_PASS  0x02000400    │ Holds u between cycles      │
├──────┼──────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ T0   │ Threshold compare        │ GS_SYNC_WAIT | GS_XNOR_V2│ A←V1 (membrane), B←thresh  │
│      │                          │ 0x0000803C               │ Fires when v ≥ 30           │
│ T1   │ Spike generator          │ GS_ONE_SHOT              │ A←T0 fire                   │
│      │                          │ | GS_OUT_POSEDGE         │ Sends spike to downstream   │
│      │                          │ 0x04001000               │ and reset cells             │
├──────┼──────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ R0   │ v reset (v ← c)          │ GS_SYNC_WAIT | GS_AND_V2 │ A←spike(T1), B←c_const     │
│      │                          │ 0x00008007               │ Loads c into V1 on spike    │
│ R1   │ u reset (u ← u + d)      │ GS_SYNC_WAIT | GS_OR_V2  │ A←U1, B←d_const            │
│      │                          │ 0x00008024               │ Adds d to u on spike        │
├──────┼──────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ P0   │ Parameter store (a,b,c,d)│ GS_LATCH | LOOP_MODE     │ Pre-loaded by controller    │
│      │                          │ 0x00000C00               │ Shared or per-neuron        │
│ RF   │ Refractory               │ GS_LATCH                 │ A←spike(T1), inhibits T0    │
│      │                          │ 0x00000800               │ 1-cycle refractory          │
└──────┴──────────────────────────┴──────────────────────────┴─────────────────────────────┘
```

**Total: 10 cells.** Optimised designs reach 8 cells; high-precision designs use 12.

### The quadratic term

`0.04v²` in the Izhikevich equation is what differentiates it from LIF. In fixed-point
UniCell:

- `v²` is approximated via a shifted multiply using PASS chains and XOR/AND trees
- For practical use, `0.04v²` is small compared to `5v` until v approaches threshold;
  a 1-cell SHIFT_COUNTER approximation adds the quadratic acceleration near threshold
- Full precision needs an INT32_MUL tile (~517 cells) — only worthwhile if biological
  accuracy at sub-threshold dynamics matters more than neuron count

For most neural simulation purposes, the simplified 10-cell design without full
quadratic precision gives good firing pattern reproduction.

### Firing patterns supported

With parameters (a, b, c, d) pre-loaded into P0:

| Pattern | a | b | c | d | Notes |
|---------|---|---|---|---|-------|
| Regular spiking | 0.02 | 0.2 | -65 | 8 | Most excitatory cortical |
| Fast spiking | 0.1 | 0.2 | -65 | 2 | Inhibitory interneurons |
| Bursting | 0.02 | 0.2 | -50 | 2 | Intrinsic bursting |
| Chattering | 0.02 | 0.2 | -50 | 2 | Chattering cells |
| Low-threshold spiking | 0.02 | 0.25 | -65 | 2 | Low-threshold spiking |

Each neuron type is just a different set of constants pre-loaded into P0's bus address.
Different neuron types coexist freely in the same pond — heterogeneous networks cost
nothing extra at the architecture level.

### Scale

| Target | Cells available | Izhikevich neurons (10c each) |
|--------|----------------|------------------------------|
| iCEBreaker (iCE40UP5K) | 64 | **6 neurons** |
| Kintex-7 XC7K480T | 1,500 | **150 neurons** |
| Mid-range FPGA (10k cells) | 10,000 | **1,000 neurons** |
| Future ASIC (500M cells) | 500,000,000 | **50 million neurons** |

---

## UniCell vs Izhikevich Model — Honest Comparison

*From Grok's analysis (May 2026), with additions.*

| Aspect | Izhikevich in Software/GPU | UniCell Implementation |
|--------|---------------------------|----------------------|
| Biological plausibility | Very good (20+ firing patterns) | Good (most patterns, fixed-point approx) |
| Computational cost | Very low (~13 FLOPs/step) | Higher (many cells per neuron) |
| Cells per neuron | N/A (software) | 5 (LIF) / 8–12 (Izhikevich) |
| Precision | Floating-point | Fixed-point 32-bit |
| Sparsity handling | Good | Excellent (data-driven wired-OR) |
| Reconfigurability | Low (fixed equations) | Very high (runtime gate_state changes) |
| Scalability | Excellent on GPU | Excellent at massive scale |
| Heterogeneous networks | Requires software overhead | Free — different parameters per neuron |
| Mixed workloads | Requires separate processor | Native — same pond, same tick |
| Runtime adaptation | Requires host intervention | Direct — another cell writes gate_state |

### Where UniCell wins

**Sparsity is free.** In conventional simulation, sparse connectivity requires
software bookkeeping. On the wired-OR bus, cells that don't fire don't drive the bus —
silence costs nothing. Massively sparse networks (biological cortex is ~1% active
at any time) are the natural operating point.

**Heterogeneity costs nothing.** Every neuron having different (a,b,c,d) just means
different pre-loaded constants. No runtime branching, no lookup tables.

**Mixed workloads.** A pond running 150 Izhikevich neurons on the Kintex-7 is using
1,500 cells. The other cells on the same array can simultaneously run the OS, a
filesystem index, and a bridge router. No neuromorphic chip does this.

**Runtime reconfiguration.** `gate_state` is a 32-bit value that another cell can
write at runtime — via the standard bus write mechanism. A learning rule is another
cell cluster that observes spike activity and writes new gate_states. Hebbian learning,
STDP, neuromodulation: all expressible as pond computation.

### Where dedicated implementations win

**Raw throughput for pure neural simulation.** A GPU running optimised Izhikevich
code or a dedicated neuromorphic chip (Loihi 2, TrueNorth) will simulate more neurons
per watt for that specific task. UniCell is not trying to beat dedicated hardware at
its own game.

**Sub-threshold precision.** The quadratic `0.04v²` term is expensive in fixed-point
UniCell. For detailed sub-threshold dynamics research, a continuous-time simulator
is more appropriate.

### The actual differentiator

UniCell's value in neural simulation is not outperforming neuromorphic chips at spiking
networks. It is running spiking neural networks **as one workload among many on the
same substrate** — alongside OS primitives, symbolic reasoning, file search, and
whatever else the application needs. That combination is not available from any
conventional or neuromorphic architecture today.

---

## Implementation Notes

### Connecting neurons

Neurons communicate via the wired-OR bus: a spike from C3/T1 writes a 1 to an
output bus address. Any downstream neuron with that address as its synaptic input
(C1's B address) receives the spike naturally — no routing table, no arbitration.

Fan-out is free: one output address can be the synaptic input for hundreds of
downstream neurons simultaneously (they all read the same bus address).

Fan-in is free: multiple upstream neurons writing to the same downstream synaptic
address produce OR of their spikes — the wired-OR bus does the summing.

### Synaptic weights

In the simplest design, weights are binary (spike or no spike). Weighted synapses
need an additional cell per synapse that gates the spike through an AND tree with a
weight mask — adds 1–2 cells per weighted synapse.

### Refractory period

The 1-cycle refractory in both designs can be extended by replacing C4/RF with a
PASS chain: a chain of N PASS cells gives 2N ticks of refractory silence. For a
10ms refractory at 1MHz clock, that's 10,000 ticks = 5,000 PASS cells per neuron —
clearly impractical. In practice, the controller re-arms the ONE_SHOT cell at the
appropriate time, which is the correct architectural pattern.

### Loading a neural pond

```python
from gate_states import (GS_LATCH_IN, LOOP_MODE, GS_PASS, GS_SYNC_WAIT,
                         GS_OR_V2, GS_XNOR_V2, GS_ONE_SHOT, GS_OUT_POSEDGE,
                         GS_LATCH)
from controller import ImagoController, CellMapRecord

# Address scheme for one LIF neuron
MEMBRANE_ADDR  = 0x1000   # C0 output: current membrane value on bus
INTEGRATE_ADDR = 0x1001   # C1 output: updated membrane
SYNAPSE_ADDR   = 0x1002   # external spikes arrive here (C1's B input)
THRESHOLD_ADDR = 0x1003   # pre-loaded with threshold constant
SPIKE_ADDR     = 0x1004   # C3 output: spike (readable by downstream neurons)
REFRAC_ADDR    = 0x1005   # C4 output: refractory signal back to C2

records = [
    # C0: membrane latch — holds V, loops to itself
    CellMapRecord(GS_LATCH_IN | LOOP_MODE | GS_PASS,
                  input_address=INTEGRATE_ADDR,
                  output_address=MEMBRANE_ADDR),
    # C1: integrate — OR(membrane, synaptic input)
    CellMapRecord(GS_SYNC_WAIT | GS_OR_V2,
                  input_address=MEMBRANE_ADDR,
                  output_address=INTEGRATE_ADDR,
                  input_b_address=SYNAPSE_ADDR),
    # C2: threshold compare — XNOR(membrane, threshold)
    CellMapRecord(GS_SYNC_WAIT | GS_XNOR_V2,
                  input_address=MEMBRANE_ADDR,
                  output_address=0x1006,
                  input_b_address=THRESHOLD_ADDR),
    # C3: spike one-shot
    CellMapRecord(GS_ONE_SHOT | GS_OUT_POSEDGE,
                  input_address=0x1006,
                  output_address=SPIKE_ADDR),
    # C4: refractory latch
    CellMapRecord(GS_LATCH,
                  input_address=SPIKE_ADDR,
                  output_address=REFRAC_ADDR),
]

ctrl = ImagoController(cell_count=50)
rid  = ctrl.load_map(records, "lif_neuron",
                     known_values={THRESHOLD_ADDR: 1})  # threshold=1 (normalised)

# Inject a synaptic spike and step
result = ctrl.run(rid,
    inputs={SYNAPSE_ADDR: 1},
    capture_addresses=[SPIKE_ADDR]
)
print("Spike:", result.get(SPIKE_ADDR, 0))
```

---

## Relation to Existing Docs

- `docs/lif_neuron_reference.v` — standalone Verilog LIF module (v1-style, Grok April 2026).
  Kept as reference. The pond-native 5-cell design above supersedes it for v2.
- `docs/architecture_positioning.md` — LIF section with approximate 6-8 cell count.
  Today's analysis confirms 5 cells for LIF (latch model), 8–12 for Izhikevich.
- `MIGRATION_TODO.md` — Tier 6 items for neuromorphic guide still open.
  This document fulfils the design analysis portion; a full tutorial with working
  .icm examples is the remaining step.

---

*Last updated: 2026-05-09 — Grok design + Claudette gate_state mapping*
