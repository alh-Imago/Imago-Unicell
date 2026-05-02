"""
pipeline_queue.py — Pipelined Input Queue with Parallel Reference Tracking

Implements the pipeline queue model described in the architecture discussion:

  - Input queue feeds a compute primitive continuously without waiting
    for the full pipeline depth to complete each time
  - A parallel reference shift register carries the step identity
    alongside the data through exactly pipeline_depth ticks
  - Reference and value emerge at the output in the same tick
  - Output table holds {ref: value} pairs — empty value means result
    pending, no ref means that pipeline slot ran idle
  - Out-of-order delivery: results are indexed by ref, not position
  - Dependencies tracked by ready_tick: a step referencing @foo waits
    until foo's result is in the output table before entering the queue

Reference shift register — bit-parallel PASS chains
=====================================================

For a reference number with B bits, B independent PASS chains run
alongside the compute pipeline, each chain pipeline_depth cells long.
All chains are armed and frozen together with the compute cells.

  bit 0 chain:  ref_in[0] → PASS → PASS → ... (D cells) → ref_out[0]
  bit 1 chain:  ref_in[1] → PASS → PASS → ... (D cells) → ref_out[1]
  ...
  bit B-1:      ref_in[B-1] → ... → ref_out[B-1]
  data:         a_in, b_in → [compute D ticks] → data_out

The sequencer reads ref_out[0..B-1] and data_out at the same tick,
reconstructs the reference number, writes {ref: value} to the table.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController

from controller import CellMapRecord
from gate_states import GS_PASS


# ── Queue and output slots ────────────────────────────────────────────────────

@dataclass
class QueueSlot:
    """
    One pending entry in the input queue.

    ref:         Reference number (encodes step identity, 0-based).
    variables:   Input values for this pipeline run {param: value}.
    result_name: What to call this result in named_results.
    ready_tick:  Earliest tick this can enter the pipeline.
                 0 = immediately. N = must wait until tick N
                 (e.g. a dependency lands at tick N).
    """
    ref:         int
    variables:   dict
    result_name: str
    ready_tick:  int = 0


@dataclass
class OutputSlot:
    """
    One entry in the output table.

    ref:         Reference number matching the input queue entry.
    result_name: Name for this result.
    value:       None until the pipeline delivers the result.
    tick_due:    Expected arrival tick (entry_tick + pipeline_depth).
    consumed:    True once a downstream step has read this value.
    """
    ref:         int
    result_name: str
    value:       Optional[int]
    tick_due:    int
    consumed:    bool = False

    @property
    def ready(self) -> bool:
        return self.value is not None and not self.consumed

    @property
    def overdue(self) -> bool:
        """True if expected tick passed but no value yet."""
        return self.value is None  # caller checks against current_tick


# ── Reference shift register ──────────────────────────────────────────────────

class RefShiftRegister:
    """
    A set of parallel PASS chains that carry a reference number
    through pipeline_depth ticks alongside the compute pipeline.

    Each bit of the reference gets its own chain. All chains are
    armed and frozen together with the compute cells.

    After pipeline_depth ticks, ref_out_addresses[i] carries bit i
    of the reference number that entered at ref_in_addresses[i].
    """

    def __init__(self,
                 ctrl:           "ImagoController",
                 pipeline_depth: int,
                 ref_bits:       int,
                 name:           str = "refshift",
                 alloc=None):
        self.ctrl           = ctrl
        self.pipeline_depth = pipeline_depth
        self.ref_bits       = ref_bits
        self.name           = name

        # Build one PASS chain per bit
        self.ref_in_addresses:  list[int] = []
        self.ref_out_addresses: list[int] = []
        self.region_ids:        list[str] = []
        self.all_cell_addresses: list[int] = []

        from ir import AddressAllocator
        if alloc is None:
            alloc = AddressAllocator()

        for bit in range(ref_bits):
            records = []
            addrs = [alloc.alloc() for _ in range(pipeline_depth + 1)]
            # chain: addrs[0] → addrs[1] → ... → addrs[depth]
            for i in range(pipeline_depth):
                records.append(CellMapRecord(GS_PASS, addrs[i], addrs[i+1]))

            rid = ctrl.load_map(records, f"{name}_bit{bit}")
            if rid is None:
                raise RuntimeError(f"RefShiftRegister: load_map failed for bit {bit}")
            ctrl.freeze(region_id=rid)

            self.ref_in_addresses.append(addrs[0])
            self.ref_out_addresses.append(addrs[-1])
            self.region_ids.append(rid)
            self.all_cell_addresses.extend(
                ctrl._regions[rid].cell_addresses)

        print(f"[REFSHIFT] '{name}': {ref_bits} chains × {pipeline_depth} cells "
              f"= {ref_bits * pipeline_depth} total cells")

    def load(self, ref: int) -> None:
        """
        Write a reference number into the shift register input.
        Call this at the same time as loading the compute pipeline inputs.
        The shift register must already be frozen; it will be thawed
        alongside the compute pipeline.
        """
        for bit in range(self.ref_bits):
            bit_val = (ref >> bit) & 1
            self.ctrl.array.bus[self.ref_in_addresses[bit]] = (bit_val, 0)

    def arm(self) -> None:
        """Assert start_flags on all shift register chains."""
        for rid in self.region_ids:
            self.ctrl.thaw(region_id=rid)

    def freeze(self) -> None:
        """Clear start_flags on all shift register chains."""
        for rid in self.region_ids:
            self.ctrl.freeze(region_id=rid)

    def read_output(self) -> Optional[int]:
        """
        Read the reference number currently at the output of the shift register.
        Returns None if not all output bits are present on the bus.
        """
        ref = 0
        for bit in range(self.ref_bits):
            entry = self.ctrl.array.bus.get(self.ref_out_addresses[bit])
            if entry is None:
                return None
            bit_val = entry[0] if isinstance(entry, tuple) else entry
            ref |= (bit_val & 1) << bit
        return ref

    def flush_cells(self) -> None:
        """Clear stale data from all shift register cells."""
        for addr in self.all_cell_addresses:
            cell = self.ctrl.array.cells.get(addr)
            if cell is not None and not cell.storage_mode:
                cell.data = None


# ── PipelinedSlot ─────────────────────────────────────────────────────────────

class PipelinedSlot:
    """
    A compute primitive slot with an attached reference shift register.

    The shift register runs in parallel with the compute pipeline.
    Inputs and references are loaded and armed together.
    Outputs and references are read together.

    queue_depth determines how many bits the reference uses:
      ref_bits = ceil(log2(queue_depth + 1))
    """

    def __init__(self,
                 ctrl:            "ImagoController",
                 region_id:       str,
                 input_addresses: dict[str, int],
                 output_address:  int,
                 pipeline_depth:  int,
                 cell_addresses:  list[int],
                 queue_depth:     int = 8,
                 name:            str = "slot"):
        self.ctrl            = ctrl
        self.region_id       = region_id
        self.input_addresses = input_addresses
        self.output_address  = output_address
        self.pipeline_depth  = pipeline_depth
        self.cell_addresses  = cell_addresses
        self.name            = name

        # Reference shift register — same depth as compute pipeline.
        # Uses a fresh allocator starting ABOVE the compute cells to
        # ensure no address collision between data and reference buses.
        self.ref_bits = max(1, math.ceil(math.log2(queue_depth + 1)))
        from ir import AddressAllocator
        # Start ref addresses well above the compute region
        ref_alloc = AddressAllocator()
        ref_alloc._next = 0x00080000   # high base — no overlap with compute
        self.ref_shift = RefShiftRegister(
            ctrl           = ctrl,
            pipeline_depth = pipeline_depth,
            ref_bits       = self.ref_bits,
            name           = f"{name}_ref",
            alloc          = ref_alloc,
        )

        # Input queue and output table
        self._input_queue:  list[QueueSlot]  = []
        self._output_table: list[OutputSlot] = []
        self._current_tick: int              = 0
        self._next_ref:     int              = 0   # auto-incrementing reference

    # ── Queue management ──────────────────────────────────────────────────────

    def enqueue(self, variables: dict, result_name: str,
                ready_tick: int = 0) -> int:
        """
        Add an entry to the input queue.
        Returns the reference number assigned to this entry.
        """
        ref = self._next_ref
        self._next_ref += 1
        self._input_queue.append(
            QueueSlot(ref=ref, variables=variables,
                      result_name=result_name, ready_tick=ready_tick)
        )
        return ref

    @property
    def queue_length(self) -> int:
        return len(self._input_queue)

    @property
    def output_table(self) -> list[OutputSlot]:
        return self._output_table

    def get_result(self, result_name: str) -> Optional[int]:
        """
        Look up a result by name. Returns value if ready, None if pending.
        Marks the slot consumed when read.
        """
        for slot in self._output_table:
            if slot.result_name == result_name and slot.ready:
                slot.consumed = True
                return slot.value
        return None

    def result_ready(self, result_name: str) -> bool:
        """True if a result with this name is in the output table with a value."""
        return any(s.result_name == result_name and s.ready
                   for s in self._output_table)

    # ── Execution ─────────────────────────────────────────────────────────────

    def tick(self) -> Optional[OutputSlot]:
        """
        Advance the pipeline by one tick.

          1. If a queued entry is ready (ready_tick <= current_tick),
             load it into the pipeline (and reference shift register).
          2. Tick the array.
          3. Check outputs — if both data_out and ref_out are live,
             capture the result into the output table.

        Returns the OutputSlot that was completed this tick, or None.
        """
        ctrl = self.ctrl

        # ── Load next queued input if ready ───────────────────────────────
        loaded_slot = None
        for i, q in enumerate(self._input_queue):
            if q.ready_tick <= self._current_tick:
                loaded_slot = self._input_queue.pop(i)
                break

        if loaded_slot is not None:
            # Freeze compute + shift register
            ctrl.freeze(region_id=self.region_id)
            self.ref_shift.freeze()

            # Flush stale cell data
            for phys in self.cell_addresses:
                cell = ctrl.array.cells.get(phys)
                if cell and not cell.storage_mode:
                    cell.data = None
            self.ref_shift.flush_cells()

            # Write data inputs
            for param, value in loaded_slot.variables.items():
                bus_addr = self.input_addresses.get(param)
                if bus_addr is not None:
                    ctrl.array.bus[bus_addr] = (value & 1, 0)

            # Write reference bits
            self.ref_shift.load(loaded_slot.ref)

            # Arm both together
            ctrl.thaw(region_id=self.region_id)
            self.ref_shift.arm()

            # Register expected output
            self._output_table.append(OutputSlot(
                ref         = loaded_slot.ref,
                result_name = loaded_slot.result_name,
                value       = None,
                tick_due    = self._current_tick + self.pipeline_depth,
            ))

        # ── Tick the array ────────────────────────────────────────────────
        ctrl.array.tick()
        self._current_tick += 1

        # ── Check for output ──────────────────────────────────────────────
        completed = None
        data_entry = ctrl.array.bus.get(self.output_address)
        ref_num    = self.ref_shift.read_output()

        if data_entry is not None and ref_num is not None:
            data_value = (data_entry[0] if isinstance(data_entry, tuple)
                          else data_entry)
            # Match ref_num to pending output table entry
            for out_slot in self._output_table:
                if (out_slot.ref == ref_num
                        and out_slot.value is None
                        and not out_slot.consumed):
                    out_slot.value = data_value
                    completed = out_slot
                    print(f"[PIPELINE] '{self.name}' tick {self._current_tick}: "
                          f"ref={ref_num} '{out_slot.result_name}'={data_value}")
                    break

        return completed

    def run_until_empty(self, max_ticks: int = 10_000) -> dict[str, int]:
        """
        Run tick() until all queued inputs have produced outputs.
        Returns {result_name: value} for all completed slots.
        """
        results = {}
        for _ in range(max_ticks):
            completed = self.tick()
            if completed:
                results[completed.result_name] = completed.value

            # Done when input queue empty and all output slots have values
            if (not self._input_queue
                    and all(s.value is not None for s in self._output_table)):
                break

        return results

    def purge_consumed(self) -> int:
        """Remove consumed output table entries. Returns count removed."""
        before = len(self._output_table)
        self._output_table = [s for s in self._output_table
                               if not s.consumed]
        return before - len(self._output_table)

    def status(self) -> dict:
        pending   = [s for s in self._output_table if s.value is None]
        ready     = [s for s in self._output_table if s.ready]
        consumed  = [s for s in self._output_table if s.consumed]
        return {
            "name":           self.name,
            "current_tick":   self._current_tick,
            "pipeline_depth": self.pipeline_depth,
            "ref_bits":       self.ref_bits,
            "queue_length":   len(self._input_queue),
            "output_pending": len(pending),
            "output_ready":   len(ready),
            "output_consumed":len(consumed),
        }

    def __repr__(self) -> str:
        return (f"PipelinedSlot('{self.name}' "
                f"depth={self.pipeline_depth} "
                f"queue={self.queue_length} "
                f"tick={self._current_tick})")


# ── Factory ───────────────────────────────────────────────────────────────────

def make_pipelined_slot(ctrl:        "ImagoController",
                         primitive:   str,
                         queue_depth: int = 8,
                         name:        str = "pipe") -> PipelinedSlot:
    """
    Allocate a pipelined primitive slot with reference shift register.

    primitive: gate op ("NOT", "PASS") or tile name ("INT32_ADD", etc.)
    queue_depth: how deep the input queue can be (determines ref_bits)
    """
    from ir import AddressAllocator

    GATE_OPS = {"NOT": 1, "PASS": 0}   # gate_state values

    if primitive in GATE_OPS:
        from gate_states import GS_NOT
        alloc    = AddressAllocator()
        in_addr  = alloc.alloc()
        out_addr = alloc.alloc()
        gs       = GATE_OPS[primitive]
        records  = [CellMapRecord(gs, in_addr, out_addr)]
        rid      = ctrl.load_map(records, name)
        if rid is None:
            raise RuntimeError(f"make_pipelined_slot: load failed for {primitive}")
        ctrl.freeze(region_id=rid)
        cell_addresses = ctrl._regions[rid].cell_addresses
        depth = 1

        return PipelinedSlot(
            ctrl            = ctrl,
            region_id       = rid,
            input_addresses = {"a": in_addr},
            output_address  = out_addr,
            pipeline_depth  = depth,
            cell_addresses  = cell_addresses,
            queue_depth     = queue_depth,
            name            = name,
        )

    # Tile primitive
    try:
        from fp_tiles import TileLibrary, TilePlacer
        lib    = TileLibrary()
        tile   = lib.get(primitive)
        placer = TilePlacer(base_address=0x00200000)
        records, in_a, in_b, out = placer.place(tile)

        # Explicit return PASS (Q5)
        alloc = AddressAllocator()
        return_addr = alloc.alloc()
        records = list(records) + [CellMapRecord(GS_PASS, out[0], return_addr)]
        depth = tile.metadata.pipeline_depth + 1

        rid = ctrl.load_map(records, name)
        if rid is None:
            raise RuntimeError(f"make_pipelined_slot: load failed for {primitive}")
        ctrl.freeze(region_id=rid)
        cell_addresses = ctrl._regions[rid].cell_addresses

        input_addresses = {}
        if in_a: input_addresses["a"] = in_a[0]
        if in_b: input_addresses["b"] = in_b[0]

        return PipelinedSlot(
            ctrl            = ctrl,
            region_id       = rid,
            input_addresses = input_addresses,
            output_address  = return_addr,
            pipeline_depth  = depth,
            cell_addresses  = cell_addresses,
            queue_depth     = queue_depth,
            name            = name,
        )

    except KeyError:
        raise ValueError(f"Unknown primitive: '{primitive}'")
