# Typed Neural Computation in UniCell

## Overview

A typed neural region is a compute region where the bridge contract is
applied at the boundary before data enters. Every value inside the region
— membrane potential, synaptic weight, firing threshold, decay constant —
is expressed in the domain format declared by the contract.

This is distinct from:
- `lif_neuron.icm` — untyped LIF, raw bus values, no format contract
- Conventional ANN — backprop, floating point tensors, no physical typing
- Neuromorphic hardware — event-driven but format-agnostic

---

## The Existing LIF (Untyped)

`imago/examples/lif_neuron.icm` — 5 cells, raw integer values:

```
C0: membrane store  (latch_in, holds membrane potential as raw integer)
C1: integrator      (AND — adds input to membrane)
C2: comparator      (XOR — compares membrane to threshold)
C3: spike           (preload_sel — fires when comparator triggers)
C4: refractory      (latch_in — holds refractory state 1 cycle)
```

Works correctly. Validated. Unchanged.
The synapse input receives whatever arrives on the bus — no type checking.

---

## TYPED_LIF_MIF — Typed LIF in MIF Format

`TYPED_LIF_MIF` is the format-typed variant. The bridge contract is applied
at the region boundary before data enters. All values are MIF pairs.

### Naming Convention

```
TYPED_LIF_MIF
  TYPED  — format-typed variant, not the raw untyped lif_neuron.icm
  LIF    — Leaky Integrate-and-Fire (standard neuroscience term)
  MIF    — the format contract (MathTrix Internal Float)
```

Future variants follow the same pattern:
```
TYPED_LIF_SI     — typed LIF in SI_Physics format
TYPED_LIF_DNA    — typed LIF in DNA format (for sequence processing)
```

### Structure

Each value is a MIF pair (ctrl cell + mant cell):

```
PRELOADED at configure time (preloaded-A pattern):
  w_ctrl, w_mant    — synaptic weight      (default 1.0)
  d_ctrl, d_mant    — decay factor         (default 0.9)
  t_ctrl, t_mant    — firing threshold     (default 0.5)

RUNTIME inputs (typed by bridge contract):
  x_ctrl, x_mant    — input signal (MIF, from bridge)
  v_ctrl, v_mant    — membrane potential (MIF, latch_in)

COMPUTE:
  weighted = MIF_MUL(weight, x)        weight × input
  v_decay  = MIF_MUL(decay, v)         leaky membrane
  v_new    = MIF_ADD(v_decay, weighted) integrate
  spike    = MIF_CMP_GT(v_new, theta)  threshold check

OUTPUTS:
  spike    — 1-bit, fires when v_new > threshold
  v_new    — MIF pair, new membrane potential (latch_in)
```

### Why MIF Format

The bridge contract ensures the input arrives as a MIF pair. The weight,
decay, and threshold are preloaded as MIF constants at configure time.
All arithmetic uses MIF tiles — the data never leaves MIF format inside
the region. The output carries the MIF contract forward.

Reconfiguring weight, decay, or threshold requires writing to the
preloaded cells only — no cell map recompile. This is how a typed neural
region is trained: configure transactions update the preloaded-A values.

---

## The Bridge Contract at the Region Boundary

Before data enters a TYPED_LIF_MIF region, the bridge contract is applied:

```python
# Example: MathTrix laplacian output → TYPED_LIF_MIF region
bridge = reg.find_bridge("SI_Physics", "SI_Physics",
                          source_context="bulk_fluid")
# → SI_NAVIER_STOKES_TEMP or SI_FOURIER_HEAT
# User verifies, compiler places bridge, records selection permanently
```

The bridge contract ensures:
1. The input is in MIF format (not raw integer, not IEEE-754 float)
2. The physical context is compatible with MIF arithmetic
3. The selection is recorded in the model metadata permanently

---

## Training a Typed Neural Region

Training = updating preloaded-A values (weight, decay, threshold).

No cell map recompile needed. A configure transaction writes new values
to the preloaded cells. The region immediately operates with new weights.

```python
# Pseudocode — training step
for epoch in range(n_epochs):
    # Forward pass — fabric runs the cell map
    output = region.run(typed_input)

    # Compute gradient (external to fabric)
    grad_w = compute_gradient(output, target)

    # Update weight — single configure transaction per cell
    new_weight_mif = mif_encode(current_weight - lr * grad_w)
    region.reconfigure_preload(w_ctrl, new_weight_mif.ctrl)
    region.reconfigure_preload(w_mant, new_weight_mif.mant)
    # No recompile. No new cell map. Immediate effect.
```

The fabric does the forward pass. The host does the gradient. The
preloaded-A mechanism delivers the updated weight in one transaction.

---

## Typed Neural Cascade

Multiple TYPED_LIF_MIF neurons in series — each receives the spike
output of the previous, typed by the same contract throughout:

```
[Typed input — MIF, bulk_fluid context]
      ↓  bridge contract verified
[TYPED_LIF_MIF — neuron 0]
      ↓  spike (1-bit) + v_new (MIF)
[TYPED_LIF_MIF — neuron 1]
      ↓  spike + v_new
[TYPED_LIF_MIF — neuron 2]
      ↓  typed output
```

The contract propagates through the cascade. Every neuron in the chain
operates on data that has been typed from the moment it entered the region.

Compare to `lif_cascade.icm` — the untyped cascade works identically at
the cell level. The difference is that TYPED_LIF_MIF carries a semantic
guarantee about what the data represents.

---

## What This Is Not

- **Not AGI** — a typed LIF region is a typed signal processor
- **Not a general neural network** — no backprop, no gradient descent
  (training is via preloaded-A configure transactions)
- **Not a biological neuron** — LIF is a standard simplified model
- **Not a claim about consciousness** — typing data is not cognition

What it is: a formal mechanism for ensuring that a spiking neural
region receives physically typed data, operates on it in the declared
format, and produces output that carries that type forward. The semantic
contract makes the computation honest about what it represents.

---

## Files

```
fp_tiles.py                        — TYPED_LIF_MIF tile definition
imago/examples/lif_neuron.icm      — original untyped LIF (unchanged)
imago/examples/lif_cascade.icm     — original untyped cascade (unchanged)
imago/examples/typed_lif_mif.icm   — typed LIF example (MIF format)
cell_format.py                     — BridgeContract, FormatRegistry
docs/PAPER_DRAFT.md                — semantic contract paper section
```

---

*See also: FORMAT_DEFINITION_GUIDE.md, cell_format.py BridgeContract*
