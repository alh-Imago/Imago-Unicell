# Neural Pond Tutorial

Building spiking neural networks in UniCell — step by step.

*For the full design analysis and Izhikevich comparison see
[neural_pond_design.md](neural_pond_design.md).*

---

## What a Neural Pond Is

A neural pond is an ordinary Pond whose cells implement spiking neuron
behaviour. There is no special mode, no separate chip, no extra configuration.
The wired-OR bus handles synaptic input naturally: any upstream neuron writing
to a synapse address delivers a spike. Multiple upstream neurons writing the
same address produce OR of their spikes — fan-in is free.

This means a neural pond sits alongside OS ponds, filesystem ponds, and
compute ponds on the same substrate, in the same tick, without mode-switching.
That is not possible on any conventional neuromorphic hardware.

---

## The 5-Cell LIF Neuron

The simplest practical spiking neuron: Leaky Integrate-and-Fire.

### Cell layout

| Cell | Role | gate_state | Value |
|------|------|-----------|-------|
| C0 | Membrane latch | GS_LATCH_IN \| LOOP_MODE \| GS_PASS | `0x02000400` |
| C1 | Integrate (leak + synapse) | GS_SYNC_WAIT \| GS_OR_V2 | `0x00008024` |
| C2 | Threshold compare | GS_SYNC_WAIT \| GS_XNOR_V2 | `0x0000803C` |
| C3 | Spike generator | GS_ONE_SHOT \| GS_OUT_POSEDGE | `0x04001000` |
| C4 | Refractory latch | GS_LATCH | `0x00000800` |

### Address scheme

```
0x1000  MEMBRANE_ADDR   — C0 output: current membrane value on bus
0x1001  INTEGRATE_ADDR  — C1 output: updated membrane (feeds C0)
0x1002  SYNAPSE_ADDR    — external spikes arrive here (C1 B-input)
0x1003  THRESHOLD_ADDR  — pre-loaded with threshold (default: 1)
0x1004  COMPARE_ADDR    — C2 output: 1 when membrane ≥ threshold
0x1005  SPIKE_ADDR      — C3 output: spike to downstream neurons
0x1006  REFRAC_ADDR     — C4 output: refractory signal
```

### Cycle flow

```
posedge:  Synaptic spike arrives at C1 B-input (SYNAPSE_ADDR)
          Current membrane arrives at C1 A-input (MEMBRANE_ADDR)
          Current membrane arrives at C2 A-input (MEMBRANE_ADDR)
          Threshold constant arrives at C2 B-input (THRESHOLD_ADDR)

negedge:  C1 fires: OR(membrane, synapse) → INTEGRATE_ADDR
          C0 latches updated membrane (LOOP_MODE keeps it armed)
          C2 fires: XNOR(membrane, threshold) → COMPARE_ADDR
          If C2=1: C3 fires ONE_SHOT spike → SPIKE_ADDR + REFRAC_ADDR
          C4 latches spike signal (refractory for next cycle)
```

---

## Quick Start — Run the Bundled Example

```python
import imago
imago.set_verbose(False)

vm = imago.VM(cell_count=50)
vm.load_example("lif_neuron")

# Pre-load threshold constant (threshold=1 means fires on any input)
vm.set("threshold", 1)

# Send a synaptic spike
result = vm.run(synapse=1)
print("spike:", result.get("spike"))    # 1 — neuron fired
print("membrane:", result.get("membrane"))

# Next tick — no spike, refractory clears
result2 = vm.run(synapse=0)
print("spike:", result2.get("spike"))   # 0 — refractory
```

---

## Build From Scratch in Python

```python
import imago_log; imago_log.set_level(imago_log.SILENT)
from gate_states import (GS_LATCH_IN, LOOP_MODE, GS_PASS, GS_SYNC_WAIT,
                         GS_OR_V2, GS_XNOR_V2, GS_ONE_SHOT, GS_OUT_POSEDGE,
                         GS_LATCH)
from controller import ImagoController, CellMapRecord

# Address scheme — one neuron
MEMBRANE_ADDR  = 0x1000
INTEGRATE_ADDR = 0x1001
SYNAPSE_ADDR   = 0x1002
THRESHOLD_ADDR = 0x1003
COMPARE_ADDR   = 0x1004
SPIKE_ADDR     = 0x1005

records = [
    # C0: membrane latch
    CellMapRecord(GS_LATCH_IN | LOOP_MODE | GS_PASS,
                  input_address=INTEGRATE_ADDR,
                  output_address=MEMBRANE_ADDR),
    # C1: integrate — OR(membrane, synapse)
    CellMapRecord(GS_SYNC_WAIT | GS_OR_V2,
                  input_address=MEMBRANE_ADDR,
                  output_address=INTEGRATE_ADDR,
                  input_b_address=SYNAPSE_ADDR),
    # C2: threshold compare — XNOR(membrane, threshold)
    CellMapRecord(GS_SYNC_WAIT | GS_XNOR_V2,
                  input_address=MEMBRANE_ADDR,
                  output_address=COMPARE_ADDR,
                  input_b_address=THRESHOLD_ADDR),
    # C3: spike one-shot
    CellMapRecord(GS_ONE_SHOT | GS_OUT_POSEDGE,
                  input_address=COMPARE_ADDR,
                  output_address=SPIKE_ADDR),
    # C4: refractory latch
    CellMapRecord(GS_LATCH,
                  input_address=SPIKE_ADDR,
                  output_address=0x1006),
]

ctrl = ImagoController(cell_count=50)
rid  = ctrl.load_map(records, "lif_neuron",
                     known_values={THRESHOLD_ADDR: 1})

# Send a spike
result = ctrl.run(rid,
    inputs={SYNAPSE_ADDR: 1},
    capture_addresses=[SPIKE_ADDR, MEMBRANE_ADDR]
)
print("Spike:", result.get(SPIKE_ADDR, 0))
print("Membrane:", result.get(MEMBRANE_ADDR, 0))
```

---

## Network of Two Neurons

Connect neuron A's spike output to neuron B's synapse input:

```python
# Neuron A: addresses 0x1000-0x1005
# Neuron B: addresses 0x2000-0x2005
# Connection: A.SPIKE_ADDR → B.SYNAPSE_ADDR

A_SPIKE   = 0x1005
B_SYNAPSE = 0x2002

# The connection is just an address match — no extra cells needed.
# A's C3 writes to A_SPIKE (0x1005).
# B's C1 listens on B_SYNAPSE (0x2002).
# To connect them: make B_SYNAPSE = A_SPIKE.
# Or add a single PASS cell to relay:

RELAY = CellMapRecord(GS_PASS,
    input_address=A_SPIKE,
    output_address=B_SYNAPSE)
```

Fan-out is free: A can connect to 100 downstream neurons just by having them
all listen on `A_SPIKE`. No routing table. No extra cells.

Fan-in is free: if neurons X, Y, and Z all write to `B_SYNAPSE`, B receives
OR of their spikes — the bus does the summing.

---

## Scale

| Target | Total cells | LIF neurons (5c each) |
|--------|------------|----------------------|
| iCEBreaker | 64 | 12 |
| Kintex-7 | 1,500 | 300 |
| Mid FPGA (10k) | 10,000 | 2,000 |
| ASIC (500M) | 500,000,000 | 100,000,000 |

---

## Synaptic Weights

Binary weights (spike or no spike) are free — the bus OR handles it.
Weighted synapses need one AND cell per synapse:

```python
# Weighted synapse: only pass spike if weight=1
WEIGHT_ADDR = 0x1010  # pre-loaded to 1 (excitatory) or 0 (inhibitory)

weighted = CellMapRecord(GS_SYNC_WAIT | GS_AND_V2,
    input_address=A_SPIKE,
    output_address=B_SYNAPSE,
    input_b_address=WEIGHT_ADDR)
```

One extra cell per weighted synapse. Unweighted synapses cost nothing.

---

## Refractory Period

The 1-cycle refractory in this design (C4 latch) prevents immediate re-firing.
For longer refractory periods, the controller re-arms C3 (ONE_SHOT) after the
desired number of cycles via a timed inject:

```python
# Re-arm C3 after 5-cycle refractory
# (Advanced: use a COUNTER_DECREMENT tile for automatic re-arm)
```

A COUNTER_DECREMENT tile provides automatic re-arming — see `fp_tiles.py`.

---

## The Izhikevich Neuron (8–12 cells)

For biological realism — 20+ firing patterns (regular spiking, fast spiking,
bursting, chattering) — see the 10-cell Izhikevich design in
[neural_pond_design.md](neural_pond_design.md).

The key parameters (a, b, c, d) are pre-loaded constants. Different neuron
types coexist freely in the same pond — just different constants per cluster.

---

## Why the Latch Model

Use `unicell-latch/` for neural ponds:

- **Fixed 2-tick latency per cell** — neuron timing is topologically
  deterministic. You know exactly how many ticks from spike-in to spike-out.
- **PASS cell = exactly 2 ticks delay** — path balancing is easy.
- **No edge-sensitivity** — membrane integration doesn't need posedge/negedge
  awareness.

The standard variant works too, but latch is the cleanest model for sustained,
cyclic, spike-generating computation.

---

## `.icm` File

The bundled `lif_neuron.icm` is a complete, loadable neural program:

```bash
imago run lif_neuron synapse=1 threshold=1
# → spike=1, membrane=1

imago run lif_neuron synapse=0 threshold=1
# → spike=0, membrane=0
```

Load into the workbench:
```bash
imago-workbench
# File panel → Load ICM → lif_neuron.icm
# Ports: synapse, threshold → set values → Run
```
