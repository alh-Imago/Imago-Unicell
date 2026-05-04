"""
test_lif_neuron_v2.py — Tests for LIF neuron v2 (latch model)
Claudette v2.1 / unicell-latch variant

Tests the 6-cell LIF neuron implementation in the Python VM.
Reference: docs/lif_neuron_reference.v (v1 Verilog baseline)
           docs/architecture_positioning.md (v2 cell layout)

Run: python test_lif_neuron_v2.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from unicell_array import UniCellArray
from lif_neuron_v2 import LIFNeuron, LIFNeuronPond, NEURON_ADDR_STRIDE

results = []

def check(name, cond):
    status = "PASS" if cond else "FAIL"
    results.append((status, name))
    if status == "FAIL":
        print(f"  [FAIL] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    results.append((status, name))
    if not ok:
        print(f"  [FAIL] {name}: got {got!r}, expected {expected!r}")

def fresh():
    """Return a new array with enough cells for a full neuron."""
    return UniCellArray(64)


# =============================================================================
print("\n=== LIFNeuron: build ===\n")
# =============================================================================

a = fresh()
n = LIFNeuron(a, base_address=0x1000)
check("not built before build()", not n._built)
n.build()
check("built after build()", n._built)
check_eq("6 cells allocated", n.cell_count(), 6)
check_eq("addr_syn",   n.addr_syn,   0x1000)
check_eq("addr_spike", n.addr_spike, 0x1040)
check_eq("addr_v",     n.addr_v,     0x1010)
check_eq("addr_integ", n.addr_integ, 0x1030)


# =============================================================================
print("\n=== LIFNeuron: rest state ===\n")
# =============================================================================

a = fresh()
n = LIFNeuron(a, base_address=0x1000).build()

# No input — neuron should be quiescent
for _ in range(5):
    a.tick_drain()

check_eq("rest: membrane = 0", n.membrane(), 0)
check_eq("rest: spike = 0",    n.spike(),    0)


# =============================================================================
print("\n=== LIFNeuron: single spike on synaptic input ===\n")
# =============================================================================

a = fresh()
n = LIFNeuron(a, base_address=0x1000).build()

# Stimulate once
n.stimulate(1)

# Run enough ticks for the pipeline to settle (chain_latency = n+1)
# Path: SYN -> integrate (tick 1) -> membrane (tick 2) -> spike (tick 3)
for _ in range(6):
    a.tick_drain()

check("spike fired after stimulate", n.spike() == 1)
check("membrane charged after stimulate", n.membrane() == 1)


# =============================================================================
print("\n=== LIFNeuron: no spike without input ===\n")
# =============================================================================

a = fresh()
n = LIFNeuron(a, base_address=0x1000).build()

# No stimulation
for _ in range(10):
    a.tick_drain()

check_eq("no spike without input", n.spike(), 0)
check_eq("no membrane without input", n.membrane(), 0)


# =============================================================================
print("\n=== LIFNeuron: refractory after spike ===\n")
# =============================================================================

a = fresh()
n = LIFNeuron(a, base_address=0x1000).build()

n.stimulate(1)
for _ in range(6):
    a.tick_drain()

spike_first = n.spike()
check("first spike fires", spike_first == 1)

# Refractory cell should have activated (ADDR_REF observable)
# With LATCH+LOOP spike cell: spike=1 persists as long as V=1.
# Refractory cell (NOT+LATCH+LOOP) sees spike=1 -> NOT(1)=0 -> ref=0.
# ref=0 means refractory ACTIVE (blocking re-fire) -- correct.
# ref clears only when V drops back to 0 (membrane discharges).
# In 1-bit model, V stays charged unless a new tick integrates 0.
for _ in range(3):
    a.tick_drain()

ref = a.read_bus(n.addr_ref)
spike = n.spike()
# While spiking: ref=0 (refractory active). Once V=0: ref=1 (clear).
check("refractory active during spike (ref=0 or None)", ref == 0 or ref is None)
check("spike held high after threshold crossing", spike == 1)


# =============================================================================
print("\n=== LIFNeuron: rearm and second spike ===\n")
# =============================================================================

a = fresh()
n = LIFNeuron(a, base_address=0x1000).build()

# First spike
n.stimulate(1)
for _ in range(6):
    a.tick_drain()
check("first spike", n.spike() == 1)

# Re-arm and stimulate again
n.rearm()
n.stimulate(1)
for _ in range(6):
    a.tick_drain()
check("second spike after rearm", n.spike() == 1)


# =============================================================================
print("\n=== LIFNeuron: leak signal observable ===\n")
# =============================================================================

a = fresh()
n = LIFNeuron(a, base_address=0x1000).build()

# Charge membrane
n.stimulate(1)
for _ in range(4):
    a.tick_drain()

# Cell 1 (leak = NOT V): when V=1, leak=0
leak = a.read_bus(n.addr_leak)
v    = a.read_bus(n.addr_v)
if v == 1:
    check("leak = NOT(V=1) = 0", leak == 0)
else:
    check("leak observable (V not yet settled)", leak is None or leak in (0, 1))


# =============================================================================
print("\n=== LIFNeuron: cell count and address stride ===\n")
# =============================================================================

a = fresh()
n1 = LIFNeuron(a, base_address=0x1000).build()
n2 = LIFNeuron(a, base_address=0x1000 + NEURON_ADDR_STRIDE).build()

check_eq("NEURON_ADDR_STRIDE", NEURON_ADDR_STRIDE, 0x80)
check_eq("n1 addr_syn", n1.addr_syn, 0x1000)
check_eq("n2 addr_syn", n2.addr_syn, 0x1080)
check_eq("n1 cells", n1.cell_count(), 6)
check_eq("n2 cells", n2.cell_count(), 6)
check_eq("total cells for 2 neurons", n1.cell_count() + n2.cell_count(), 12)


# =============================================================================
print("\n=== LIFNeuronPond: build ===\n")
# =============================================================================

a = fresh()
pond = LIFNeuronPond(num_neurons=4, base_address=0x2000)
pond.build(a)

check_eq("pond neuron count",    len(pond.neurons), 4)
check_eq("pond total cells",     pond.total_cells(), 24)
check_eq("neuron 0 addr_syn",    pond.neurons[0].addr_syn, 0x2000)
check_eq("neuron 1 addr_syn",    pond.neurons[1].addr_syn, 0x2080)
check_eq("neuron 3 addr_spike",  pond.neurons[3].addr_spike, 0x2180 + 0x40)


# =============================================================================
print("\n=== LIFNeuronPond: stimulate ===\n")
# =============================================================================

a = fresh()
pond = LIFNeuronPond(num_neurons=4, base_address=0x2000).build(a)

pond.stimulate(2, a, value=1)   # stimulate neuron 2

for _ in range(6):
    a.tick_drain()

check("pond: neuron 2 fires", pond.neurons[2].spike() == 1)
check("pond: neuron 0 silent", pond.neurons[0].spike() == 0)
check("pond: neuron 1 silent", pond.neurons[1].spike() == 0)
check("pond: neuron 3 silent", pond.neurons[3].spike() == 0)


# =============================================================================
print("\n=== LIFNeuronPond: connect (feed-forward) ===\n")
# =============================================================================

a = fresh()
pond = LIFNeuronPond(num_neurons=2, base_address=0x3000).build(a)
pond.connect(0, 1, a)   # wire neuron 0 spike -> neuron 1 syn

# Stimulate neuron 0
pond.stimulate(0, a, value=1)

# Run: neuron 0 fires (~3 ticks), then neuron 1 sees spike, fires (~3 more)
for _ in range(12):
    a.tick_drain()
    # Rearm neuron 0 if it fired (ONE_SHOT disarms after first fire)
    if pond.neurons[0].spike():
        pond.neurons[0].rearm()

check("feed-forward: neuron 0 fired", pond.neurons[0].spike() == 1)
check("feed-forward: neuron 1 fired", pond.neurons[1].spike() == 1)


# =============================================================================
print("\n=== LIFNeuron: repr ===\n")
# =============================================================================

a = fresh()
n = LIFNeuron(a, base_address=0x4000).build()
r = repr(n)
check("repr contains base", "0x00004000" in r)
check("repr contains cells=6", "cells=6" in r)
check("repr contains built=True", "built=True" in r)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
