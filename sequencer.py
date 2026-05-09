"""
sequencer.py — Command Table and ProgramSequencer

Implements the hybrid execution model: a fixed pool of pre-allocated
primitive cells driven by a sequential command table.

Architecture
============

Traditional spatial compilation produces a full cell map per program —
every operation gets its own cells, all fire simultaneously where
independent. This maximises parallelism but uses cells proportional to
program size.

The sequencer model separates the WHAT (the command table) from the HOW
(the pre-allocated primitive pool):

  Resource manifest   — which primitives this program needs, and the
                        maximum quantity needed simultaneously. Allocated
                        once at load time. Cells sit armed and waiting.

  Command table       — the program as a sequence of rows, each saying:
                        which primitive, which variables, how many
                        instances run in parallel, when it's done.

  Pointer cell        — a storage cell holding the current step index.
                        Advances after each step completes.

  Sequencer           — reads the pointer, fetches the row, loads
                        variables into the primitive pool via lock/load/run,
                        waits for the completion condition, captures the
                        result, advances the pointer, repeats.

Parallelism
===========

The parallel_count field in each CommandRow identifies how many compute
modules this step uses simultaneously. If parallel_count=3, three
instances of the primitive are loaded and fired at once with different
variable sets. The resource manifest pre-allocates the maximum needed
so no allocation happens at runtime.

The compiler can fill parallel_count automatically by walking the IR
dependency graph — nodes at the same depth with no dependency between
them are independent and can run in one parallel step.

Completion
==========

completion_cycles tells the sequencer how many ticks to wait before
reading the result and advancing the pointer. For known tiles this is
the tile's pipeline_depth. For -1 (AUTO), the sequencer waits until
the result address appears on the bus (the run_loop() model).

The completion condition can also be a callable returning True when done,
for more complex cases.

Hybrid decision
===============

The compiler decides per-function:
  - Many independent paths → spatial compilation (full cell map)
  - Sequential with some parallel steps → command table
  - Strictly sequential → command table, parallel_count=1 everywhere

The sequencer handles the second and third cases.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Union, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController

from controller import CellMapRecord
from gate_states import GS_PASS, GS_NOT


# ── Completion condition sentinel ─────────────────────────────────────────────

AUTO = -1   # Wait for result address to appear on bus (run_loop model)


# ── CommandRow ────────────────────────────────────────────────────────────────

@dataclass
class CommandRow:
    """
    One step in a program's command table.

    label:             Human-readable name for this step (debug/trace).
    primitive:         What to compute. One of:
                         - A tile name: "INT32_ADD", "INT32_EQ", etc.
                         - A gate op:   "NOT", "PASS", "AND", "OR", "XOR"
                         - "NOOP":      advance pointer, do nothing.
    variables:         Input values for this step. Dict of {name: value}.
                       Names must match the primitive's input interface.
    parallel_count:    How many instances of this primitive run in
                       parallel this step. Default 1.
                       parallel_count=3 with variables={"a":[1,0,1],"b":[0,1,1]}
                       fires three instances simultaneously.
    completion_cycles: Ticks to wait before reading result and advancing.
                       AUTO (-1): wait until result_name address fires.
                       0: result is available immediately (no pipeline).
    result_name:       Name to store the result under for use by later
                       steps. None means result is not captured.
    """
    label:             str
    primitive:         str
    variables:         dict                  = field(default_factory=dict)
    parallel_count:    int                   = 1
    completion_cycles: int                   = AUTO
    result_name:       Optional[str]         = None

    def to_dict(self) -> dict:
        return {
            "label":             self.label,
            "primitive":         self.primitive,
            "variables":         self.variables,
            "parallel_count":    self.parallel_count,
            "completion_cycles": self.completion_cycles,
            "result_name":       self.result_name,
        }


# ── ResourceManifest ──────────────────────────────────────────────────────────

@dataclass
class ResourceManifest:
    """
    Declares what a program needs pre-allocated in the array.

    primitives: dict of {primitive_name: max_concurrent_instances}
    e.g. {"NOT": 1, "INT32_ADD": 2} means: always have one NOT cell
    and two INT32_ADD tiles loaded and ready.

    The sequencer allocates these once at load_program() time.
    No further allocation happens during execution.
    """
    primitives: dict = field(default_factory=dict)   # name → max count

    def max_instances(self, primitive: str) -> int:
        return self.primitives.get(primitive, 1)

    def all_primitives(self) -> list[str]:
        return list(self.primitives.keys())


# ── PrimitiveSlot ─────────────────────────────────────────────────────────────

class PrimitiveSlot:
    """
    One pre-allocated primitive instance in the array.

    Wraps a set of CellMapRecord entries loaded into the controller.
    Tracks:
      - region_id: the controller region holding these cells
      - input_addresses: where to write input values
      - output_address: where to read the result
      - pipeline_depth: ticks from input to output
      - in_use: whether this slot is currently executing
    """

    def __init__(self,
                 region_id:       str,
                 input_addresses: dict[str, int],
                 output_address:  int,
                 pipeline_depth:  int,
                 cell_addresses:  list[int]):
        self.region_id        = region_id
        self.input_addresses  = input_addresses   # {param_name: bus_addr}
        self.output_address   = output_address
        self.pipeline_depth   = pipeline_depth
        self.cell_addresses   = cell_addresses
        self.in_use           = False

    def __repr__(self) -> str:
        return (f"PrimitiveSlot(region={self.region_id} "
                f"out=0x{self.output_address:X} "
                f"depth={self.pipeline_depth} "
                f"in_use={self.in_use})")


# ── ProgramSequencer ──────────────────────────────────────────────────────────

class ProgramSequencer:
    """
    Executes a command table against a pre-allocated primitive pool.

    Usage:
        seq = ProgramSequencer(ctrl)
        seq.load_program(manifest, commands)
        results = seq.run()

    The sequencer:
      1. Allocates primitive slots from the manifest (once at load time)
      2. For each CommandRow:
           a. Acquire the right slot(s)
           b. freeze → write variables → thaw (lock/load/run)
           c. Wait for completion_cycles ticks (or AUTO: wait for output)
           d. Capture result into named_results dict
           e. Advance the pointer
      3. Returns the named_results dict when all steps complete
    """

    def __init__(self, ctrl: "ImagoController"):
        self.ctrl = ctrl
        self._slots:         dict[str, list[PrimitiveSlot]] = {}
        self._named_results: dict[str, int]                 = {}
        self._commands:      list[CommandRow]               = []
        self._pointer:       int                            = 0
        self._loaded:        bool                           = False
        self._trace:         list[dict]                     = []   # execution log

    # ── Program loading ───────────────────────────────────────────────────────

    def load_program(self, manifest: ResourceManifest,
                     commands: list[CommandRow]) -> None:
        """
        Pre-allocate primitive slots and load the command table.

        Allocates one slot per instance in the manifest. Each slot is
        a fully configured set of cells in the controller's array,
        starting frozen (start_flag cleared).
        """
        self._commands      = commands
        self._named_results = {}
        self._pointer       = 0
        self._trace         = []
        self._slots         = {}

        for primitive, count in manifest.primitives.items():
            self._slots[primitive] = []
            for i in range(count):
                slot = self._allocate_slot(primitive, f"{primitive}_{i}")
                if slot is not None:
                    self._slots[primitive].append(slot)
                    print(f"[SEQ] Allocated {primitive} slot {i}: "
                          f"region={slot.region_id} "
                          f"out=0x{slot.output_address:X}")

        self._loaded = True
        print(f"[SEQ] Program loaded: {len(commands)} steps, "
              f"{sum(len(v) for v in self._slots.values())} primitive slots")

    def _allocate_slot(self, primitive: str,
                       name: str) -> Optional[PrimitiveSlot]:
        """
        Allocate one primitive slot in the array.

        For gate primitives (NOT, PASS): allocates a single cell.
        For tile primitives (INT32_ADD etc.): places the tile.
        """
        from gate_states import GS_NOT, GS_PASS, GS_AND_V2 as GS_AND, GS_OR_V2 as GS_OR, GS_XOR_V2 as GS_XOR

        # Simple gate primitives — single cell
        GATE_OPS = {
            "NOT":  GS_NOT,
            "PASS": GS_PASS,
        }

        if primitive in GATE_OPS:
            from ir import AddressAllocator
            alloc = AddressAllocator()
            in_addr  = alloc.alloc()
            out_addr = alloc.alloc()
            gs = GATE_OPS[primitive]
            records = [CellMapRecord(gs, in_addr, out_addr)]
            rid = self.ctrl.load_map(records, name)
            if rid is None:
                return None
            self.ctrl.freeze(region_id=rid)
            cell_addresses = self.ctrl._regions[rid].cell_addresses
            return PrimitiveSlot(
                region_id       = rid,
                input_addresses = {"a": in_addr},
                output_address  = out_addr,
                pipeline_depth  = 1,
                cell_addresses  = cell_addresses,
            )

        # NOOP — no cells needed
        if primitive == "NOOP":
            return PrimitiveSlot(
                region_id       = "__noop__",
                input_addresses = {},
                output_address  = 0,
                pipeline_depth  = 0,
                cell_addresses  = [],
            )

        # Tile primitives — use the tile library
        try:
            from fp_tiles import TileLibrary, TilePlacer
            lib   = TileLibrary()
            tile  = lib.get(primitive)
            placer = TilePlacer(base_address=0x00200000)
            records, in_a, in_b, out = placer.place(tile)

            # Add explicit return PASS cell (Q5)
            from ir import AddressAllocator
            alloc = AddressAllocator()
            return_addr = alloc.alloc()
            records = list(records) + [
                CellMapRecord(GS_PASS, out[0], return_addr)
            ]

            rid = self.ctrl.load_map(records, name)
            if rid is None:
                return None
            self.ctrl.freeze(region_id=rid)
            cell_addresses = self.ctrl._regions[rid].cell_addresses

            # Build input address map
            input_addresses = {}
            if in_a:
                input_addresses["a"] = in_a[0]
            if in_b:
                input_addresses["b"] = in_b[0]

            return PrimitiveSlot(
                region_id       = rid,
                input_addresses = input_addresses,
                output_address  = return_addr,
                pipeline_depth  = tile.metadata.pipeline_depth + 1,
                cell_addresses  = cell_addresses,
            )

        except KeyError:
            print(f"[SEQ] Unknown primitive: '{primitive}'")
            return None

    # ── Execution ─────────────────────────────────────────────────────────────

    def run(self, max_steps: Optional[int] = None,
            trace: bool = False) -> dict[str, int]:
        """
        Execute all command rows in sequence.

        Returns named_results dict: {result_name: value} for all steps
        that have a result_name set.

        max_steps: safety limit (default: len(commands) * 10)
        trace:     if True, record tick-level execution log in self._trace
        """
        if not self._loaded:
            raise RuntimeError("load_program() must be called before run()")

        limit = max_steps or len(self._commands) * 10
        steps_run = 0

        while self._pointer < len(self._commands) and steps_run < limit:
            row = self._commands[self._pointer]
            self._execute_row(row, trace=trace)
            steps_run += 1

        if steps_run >= limit:
            print(f"[SEQ] WARNING: step limit {limit} reached")

        print(f"[SEQ] Program complete: {steps_run} steps executed")
        return dict(self._named_results)

    def step(self, trace: bool = False) -> Optional[dict]:
        """
        Execute one command row and advance the pointer.
        Returns the result dict for that step, or None if program ended.
        """
        if not self._loaded or self._pointer >= len(self._commands):
            return None
        row = self._commands[self._pointer]
        result = self._execute_row(row, trace=trace)
        return result

    def _execute_row(self, row: CommandRow,
                     trace: bool = False) -> dict:
        """Execute one CommandRow. Returns {result_name: value} or {}."""
        t_start = time.time()

        print(f"[SEQ] Step {self._pointer}: {row.label} "
              f"({row.primitive} x{row.parallel_count})")

        # NOOP: just advance
        if row.primitive == "NOOP":
            self._pointer += 1
            return {}

        # Resolve variable values — may reference previous results
        resolved = self._resolve_variables(row.variables)

        # Acquire slots
        slots = self._acquire_slots(row.primitive, row.parallel_count)
        if not slots:
            print(f"[SEQ]   No slots available for {row.primitive}")
            self._pointer += 1
            return {}

        # Execute all parallel instances
        results = []
        for i, slot in enumerate(slots):
            # Get this instance's variables
            instance_vars = self._instance_variables(resolved, i,
                                                      row.parallel_count)
            result_val = self._run_slot(slot, instance_vars,
                                        row.completion_cycles,
                                        trace=trace)
            results.append(result_val)

        # Release slots
        for slot in slots:
            slot.in_use = False

        # Capture result — for parallel runs, take the first result
        # (future: could aggregate, e.g. sum or collect into list)
        step_result = {}
        if row.result_name is not None and results:
            value = results[0]   # primary result
            if value is not None:
                self._named_results[row.result_name] = value
                step_result[row.result_name] = value
                print(f"[SEQ]   Result '{row.result_name}' = {value}")

        # Log trace entry
        if trace:
            self._trace.append({
                "step":         self._pointer,
                "label":        row.label,
                "primitive":    row.primitive,
                "parallel":     row.parallel_count,
                "variables":    resolved,
                "results":      results,
                "elapsed_ms":   round((time.time() - t_start) * 1000, 2),
            })

        self._pointer += 1
        return step_result

    def _run_slot(self, slot: PrimitiveSlot,
                  variables: dict,
                  completion_cycles: int,
                  trace: bool = False) -> Optional[int]:
        """
        Load variables into a slot and run it to completion.

        Uses lock/load/run (freeze → write → thaw).
        Waits for completion_cycles ticks, or AUTO: waits for output.
        """
        if slot.region_id == "__noop__":
            return None

        ctrl = self.ctrl

        # Lock
        ctrl.freeze(region_id=slot.region_id)

        # Flush stale data from compute cells
        for phys_addr in slot.cell_addresses:
            cell = ctrl.array.cells.get(phys_addr)
            if cell is not None and not cell.storage_mode:
                cell.data = None

        # Write variable values directly to storage cells
        for param_name, value in variables.items():
            bus_addr = slot.input_addresses.get(param_name)
            if bus_addr is not None:
                # For gate primitives: write directly to bus for next tick
                ctrl.array.bus[bus_addr] = (value & 1, 0)

        # Arm
        ctrl.thaw(region_id=slot.region_id)

        # Wait for completion
        captured = None

        if completion_cycles == AUTO:
            # Wait until output address appears on bus
            for _ in range(10_000):
                ctrl.array.tick()
                entry = ctrl.array.bus.get(slot.output_address)
                if entry is not None:
                    captured = entry[0] if isinstance(entry, tuple) else entry
                    break
        else:
            # Wait fixed number of ticks
            for _ in range(max(1, completion_cycles)):
                ctrl.array.tick()
            entry = ctrl.array.bus.get(slot.output_address)
            if entry is not None:
                captured = entry[0] if isinstance(entry, tuple) else entry

        # Freeze after completion — slot ready for next use
        ctrl.freeze(region_id=slot.region_id)
        ctrl.array.bus.clear()

        return captured

    # ── Variable resolution ───────────────────────────────────────────────────

    def _resolve_variables(self, variables: dict) -> dict:
        """
        Resolve variable values, substituting named results for references.

        A variable value of "@name" references the result named "name"
        from a previous step. Literal integers are used as-is.
        """
        resolved = {}
        for k, v in variables.items():
            if isinstance(v, str) and v.startswith("@"):
                ref = v[1:]
                if ref in self._named_results:
                    resolved[k] = self._named_results[ref]
                else:
                    print(f"[SEQ]   WARNING: reference @{ref} not found")
                    resolved[k] = 0
            else:
                resolved[k] = v
        return resolved

    def _instance_variables(self, resolved: dict,
                             instance_idx: int,
                             parallel_count: int) -> dict:
        """
        Extract variables for one parallel instance.

        If a variable value is a list, each instance gets the element
        at its index. If scalar, all instances share the same value.
        """
        instance_vars = {}
        for k, v in resolved.items():
            if isinstance(v, list) and parallel_count > 1:
                instance_vars[k] = v[instance_idx] if instance_idx < len(v) else 0
            else:
                instance_vars[k] = v
        return instance_vars

    def _acquire_slots(self, primitive: str,
                        count: int) -> list[PrimitiveSlot]:
        """Acquire up to count free slots for this primitive."""
        available = [s for s in self._slots.get(primitive, [])
                     if not s.in_use]
        chosen = available[:count]
        for slot in chosen:
            slot.in_use = True
        if len(chosen) < count:
            print(f"[SEQ]   WARNING: needed {count} slots for {primitive}, "
                  f"only {len(chosen)} available")
        return chosen

    # ── Inspection ────────────────────────────────────────────────────────────

    @property
    def pointer(self) -> int:
        """Current step index."""
        return self._pointer

    @property
    def results(self) -> dict[str, int]:
        """All named results captured so far."""
        return dict(self._named_results)

    @property
    def trace(self) -> list[dict]:
        """Execution trace (populated when trace=True in run/step)."""
        return list(self._trace)

    def reset(self) -> None:
        """Reset pointer and results for a fresh run."""
        self._pointer       = 0
        self._named_results = {}
        self._trace         = []
        # Re-freeze all slots
        for slots in self._slots.values():
            for slot in slots:
                slot.in_use = False
                if slot.region_id != "__noop__":
                    self.ctrl.freeze(region_id=slot.region_id)

    def status(self) -> dict:
        return {
            "loaded":        self._loaded,
            "pointer":       self._pointer,
            "total_steps":   len(self._commands),
            "results_so_far": len(self._named_results),
            "slots": {
                prim: {
                    "count":    len(slots),
                    "in_use":   sum(1 for s in slots if s.in_use),
                }
                for prim, slots in self._slots.items()
            }
        }

    def __repr__(self) -> str:
        return (f"ProgramSequencer("
                f"step={self._pointer}/{len(self._commands)} "
                f"results={len(self._named_results)})")
