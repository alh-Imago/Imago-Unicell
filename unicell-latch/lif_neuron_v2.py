"""
lif_neuron_v2.py — Leaky Integrate-and-Fire neuron, UniCell latch model
Claudette v2.1 / unicell-latch variant

Ports the v1 standalone Verilog LIF (docs/lif_neuron_reference.v)
into a 6-cell UniCell pond using the latch model cell architecture.

Architecture
============

The LIF neuron is implemented as a pond of 6 cells connected on the
shared wired-OR bus. The 1-bit bus model maps naturally to the binary
LIF state machine:

    V=1  -- membrane above threshold (charged)
    V=0  -- membrane below threshold (discharged / leaky)

Cell layout
-----------

    Cell 0 -- MEMBRANE (latch + loop)
        GS_LATCH | LOOP_MODE | GS_PASS
        input:  ADDR_INTEG  (integrated value from Cell 2)
        output: ADDR_V      (membrane potential)
        Role: holds V, re-emits every tick (LOOP_MODE keeps it armed).

    Cell 1 -- LEAK (NOT gate)
        GS_NOT
        input:  ADDR_V
        output: ADDR_LEAK
        Role: 1-bit leak approximation. NOT(V) observable discharge signal.

    Cell 2 -- INTEGRATE (SYNC_WAIT + OR)
        GS_SYNC_WAIT | GS_OR_V2
        input A: ADDR_V
        input B: ADDR_SYN   (external synaptic input)
        output:  ADDR_INTEG
        Role: OR(V, spike_in). spike_in=1 charges membrane. spike_in=0 holds.

    Cell 3 -- SPIKE OUT (ONE_SHOT)
        GS_ONE_SHOT | GS_PASS
        input:  ADDR_V
        output: ADDR_SPIKE
        Role: fires once when V=1 arrives. Then disarms until re-armed.

    Cell 4 -- REFRACTORY LATCH (latch + loop + NOT)
        GS_LATCH | LOOP_MODE | GS_NOT
        input:  ADDR_SPIKE
        output: ADDR_REF
        Role: NOT(spike)=0 when firing. LOOP toggles back to 1 next tick.
              1-tick refractory window.

    Cell 5 -- REARM SIGNAL (PASS)
        GS_PASS
        input:  ADDR_REF
        output: ADDR_REARM
        Role: refractory-clear signal for pond manager to re-arm Cell 3.

Address map (base-relative)
---------------------------

    ADDR_SYN   = base + 0x00   (external: synaptic input)
    ADDR_V     = base + 0x10   (internal: membrane potential)
    ADDR_LEAK  = base + 0x20   (observable: leak signal)
    ADDR_INTEG = base + 0x30   (internal: integrated value)
    ADDR_SPIKE = base + 0x40   (external: spike output)
    ADDR_REF   = base + 0x50   (internal: refractory flag)
    ADDR_REARM = base + 0x60   (internal: rearm trigger)

Timing (latch model, chain_latency(n) = n+1 ticks)
---------------------------------------------------

    Tick 0:  synaptic input + V on bus
    Tick 1:  Cell 2 (INTEGRATE) fires -> ADDR_INTEG
    Tick 2:  Cell 0 (MEMBRANE) fires  -> ADDR_V
    Tick 3:  Cell 3 (SPIKE) fires     -> ADDR_SPIKE
    Tick 4:  Cell 4 (REFRACT) fires   -> ADDR_REF
    Tick 5:  refractory clears, Cell 3 can re-arm

    Spike-to-spike minimum interval: ~5 ticks.
    On iCEBreaker at 12MHz: ~417ns/tick -> spike interval ~2us.

Scaling
-------

    iCEBreaker (64 cells):  ~8 neurons  (6 cells + 2 inter-neuron wiring)
    Mid FPGA  (4000 cells): ~500 neurons
    500M cell ASIC:         ~60M neurons

Usage
-----

    from lif_neuron_v2 import LIFNeuron, LIFNeuronPond

    neuron = LIFNeuron(array, base_address=0x1000)
    neuron.build()

    neuron.stimulate()              # inject synaptic input
    for _ in range(6):
        array.tick_drain()

    print("spike:", neuron.spike()) # 1 if fired

    # Or: a pond of neurons
    pond = LIFNeuronPond(num_neurons=4, base_address=0x2000)
    pond.build(array)
    pond.connect(0, 1, array)       # wire neuron 0 -> neuron 1
    pond.stimulate(0, array)
"""

from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from unicell_array import UniCellArray
from unicell import FUNCTION_LOAD_PATTERN
from gate_states import (
    GS_PASS, GS_NOT, GS_LATCH,
    GS_NOR, GS_INVERT_OUT,
    GS_SYNC_WAIT, GS_OR_V2,
    LOOP_MODE,
)

# Address offsets within a neuron's base address block
_OFF_SYN   = 0x00
_OFF_V     = 0x10
_OFF_LEAK  = 0x20
_OFF_INTEG = 0x30
_OFF_SPIKE = 0x40
_OFF_REF   = 0x50
_OFF_REARM = 0x60

# Address block size per neuron
NEURON_ADDR_STRIDE = 0x80


class LIFNeuron:
    """
    Single Leaky Integrate-and-Fire neuron — 6 UniCell latch cells.

    Parameters
    ----------
    array        : UniCellArray to build into
    base_address : start of this neuron's bus address block
    """

    def __init__(self, array: UniCellArray, base_address: int = 0x1000):
        self.array    = array
        self.base     = base_address

        # External addresses
        self.addr_syn   = base_address + _OFF_SYN
        self.addr_spike = base_address + _OFF_SPIKE

        # Internal / observable addresses
        self.addr_v     = base_address + _OFF_V
        self.addr_leak  = base_address + _OFF_LEAK
        self.addr_integ = base_address + _OFF_INTEG
        self.addr_ref   = base_address + _OFF_REF
        self.addr_rearm = base_address + _OFF_REARM

        self._cell_addrs: list = []
        self._c3_addr: int = 0
        self._built = False

    def build(self) -> "LIFNeuron":
        """Allocate and configure all 6 cells."""
        a = self.array

        # Cell 0: Membrane latch — holds V, re-emits every tick
        c0 = a.allocate_cell()
        a.write_config(c0.address, [
            FUNCTION_LOAD_PATTERN,
            GS_LATCH | LOOP_MODE | GS_PASS,
            self.addr_integ,
            self.addr_v,
        ])
        a.assert_start_flag([c0.address])

        # Cell 1: Leak — NOT(V) -> ADDR_LEAK (observable discharge)
        # LOOP_MODE: re-arms after each fire so leak tracks V every tick.
        c1 = a.allocate_cell()
        a.write_config(c1.address, [
            FUNCTION_LOAD_PATTERN,
            GS_NOT | LOOP_MODE,
            self.addr_v,
            self.addr_leak,
        ])
        a.assert_start_flag([c1.address])

        # Cell 2: Integrate — SYNC_WAIT + OR(V, spike_in) -> ADDR_INTEG
        # LOOP_MODE: re-arms after each fire so it integrates every pulse.
        c2 = a.allocate_cell()
        a.write_config(c2.address, [
            FUNCTION_LOAD_PATTERN,
            GS_SYNC_WAIT | GS_OR_V2 | LOOP_MODE,
            self.addr_v,
            self.addr_integ,
        ])
        a.cells[c2.address].input_b_address = self.addr_syn
        a.assert_start_flag([c2.address])

        # Cell 3: Spike indicator — LATCH + LOOP + NOR + INVERT
        # NOR(V,V) = NOT(V). INVERT_OUT flips back to V.
        # Net: output mirrors V. When V=1, ADDR_SPIKE=1 (spike).
        #      When V=0, ADDR_SPIKE=0 (no spike).
        # LATCH holds the last value. LOOP_MODE keeps it armed every tick.
        # This gives a stable held-spike signal that downstream neurons can
        # wire to their ADDR_SYN — no ONE_SHOT re-arm cycle needed.
        c3 = a.allocate_cell()
        a.write_config(c3.address, [
            FUNCTION_LOAD_PATTERN,
            GS_LATCH | LOOP_MODE | GS_NOR | GS_INVERT_OUT,
            self.addr_v,
            self.addr_spike,
        ])
        a.assert_start_flag([c3.address])

        # Cell 4: Refractory — NOT+LATCH+LOOP, 1-tick window
        c4 = a.allocate_cell()
        a.write_config(c4.address, [
            FUNCTION_LOAD_PATTERN,
            GS_LATCH | LOOP_MODE | GS_NOT,
            self.addr_spike,
            self.addr_ref,
        ])
        a.assert_start_flag([c4.address])

        # Cell 5: Rearm signal — PASS(refractory_clear) -> ADDR_REARM
        # LOOP_MODE: stays armed to keep watching ADDR_REF each tick.
        c5 = a.allocate_cell()
        a.write_config(c5.address, [
            FUNCTION_LOAD_PATTERN,
            GS_PASS | LOOP_MODE,
            self.addr_ref,
            self.addr_rearm,
        ])
        a.assert_start_flag([c5.address])

        self._cell_addrs = [
            c0.address, c1.address, c2.address,
            c3.address, c4.address, c5.address,
        ]
        self._c3_addr = c3.address

        # Seed the membrane latch so LOOP_MODE starts cycling.
        # Write ADDR_INTEG=0 -> c0 reads it, outputs V=0 to ADDR_V.
        # This primes the feedback loop: c2 (SYNC_WAIT) can now receive
        # both A (V from c0) and B (spike_in from ADDR_SYN) on the next
        # stimulate() call.
        a.bus[self.addr_integ] = (0, 0)
        a.tick_drain()

        self._built = True
        return self

    def stimulate(self, value: int = 1):
        """
        Inject a synaptic input pulse. value=1 charges membrane.

        Only writes to ADDR_SYN. Cell 2 (SYNC_WAIT) will fire when it
        sees both V (from membrane latch c0's LOOP_MODE emission) and
        spike_in on its B input. Do not pre-write V=0 here — that
        would trigger the ONE_SHOT spike cell on a zero value and
        disarm it prematurely.
        """
        assert self._built, "Call build() first"
        self.array.bus[self.addr_syn] = (value, 0)

    def rearm(self):
        """
        No-op in v2: Cell 3 uses LATCH+LOOP_MODE and stays armed automatically.
        Kept for API compatibility with FPGABridge / bring-up scripts.
        """
        pass  # LATCH+LOOP_MODE: cell 3 never disarms

    def membrane(self) -> int:
        """Current membrane value (0 or 1)."""
        v = self.array.read_bus(self.addr_v)
        return v if v is not None else 0

    def spike(self) -> int:
        """Current spike output (0 or 1)."""
        s = self.array.read_bus(self.addr_spike)
        return s if s is not None else 0

    def refractory(self) -> int:
        """Current refractory flag (0=clear, 1=refractory blocked)."""
        r = self.array.read_bus(self.addr_ref)
        return r if r is not None else 0

    def cell_count(self) -> int:
        return len(self._cell_addrs)

    def __repr__(self):
        return (f"LIFNeuron(base={self.base:#010x}, cells={self.cell_count()}, "
                f"V={self.membrane()}, spike={self.spike()}, "
                f"built={self._built})")


class LIFNeuronPond:
    """
    A pond of LIF neurons.

    Parameters
    ----------
    num_neurons  : how many neurons to create
    base_address : start of address block (each neuron uses NEURON_ADDR_STRIDE)
    """

    def __init__(self, num_neurons: int = 4, base_address: int = 0x2000):
        self.num_neurons  = num_neurons
        self.base_address = base_address
        self.neurons: list = []

    def build(self, array: UniCellArray) -> "LIFNeuronPond":
        """Build all neurons into the array."""
        for i in range(self.num_neurons):
            base = self.base_address + i * NEURON_ADDR_STRIDE
            n = LIFNeuron(array, base_address=base)
            n.build()
            self.neurons.append(n)
        return self

    def stimulate(self, neuron_idx: int, array: UniCellArray, value: int = 1):
        """Inject synaptic input into one neuron."""
        self.neurons[neuron_idx].stimulate(value)

    def connect(self, src_idx: int, dst_idx: int, array: UniCellArray):
        """
        Wire src neuron's spike output to dst neuron's synaptic input.
        When src fires, dst Cell 2's B input sees the spike directly.
        No extra routing cells needed — wired-OR bus handles it.
        """
        src = self.neurons[src_idx]
        dst = self.neurons[dst_idx]
        dst_c2_addr = dst._cell_addrs[2]
        array.cells[dst_c2_addr].input_b_address = src.addr_spike

    def total_cells(self) -> int:
        return sum(n.cell_count() for n in self.neurons)

    def __repr__(self):
        return (f"LIFNeuronPond(neurons={self.num_neurons}, "
                f"base={self.base_address:#010x}, "
                f"total_cells={self.total_cells() if self.neurons else '?'})")
