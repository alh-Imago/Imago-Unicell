"""
program_image.py — Program Image with Named Ranges

Sits between the compiler output and the GPU execution layer.
A ProgramImage is a self-describing executable unit:

  ┌─────────────────────────────────────────────────────┐
  │  MANIFEST HEADER                                    │
  │    program_id, name, version, os_name               │
  │                                                     │
  │  MODELS NEEDED                                      │
  │    list of tile names required (checked at load)    │
  │                                                     │
  │  NAMED RANGES  ← the reference layer               │
  │    name → {vram_offset, width, kind, description}  │
  │    CPU resolves names to addresses                  │
  │    GPU uses offsets into cell array                 │
  │                                                     │
  │  PROGRAM SCRIPTS                                    │
  │    compiled CellMapRecord list (the cell fabric)    │
  │    loop scripts reference ranges by name            │
  └─────────────────────────────────────────────────────┘

Named Range kinds
=================
  INPUT       — caller injects value here before run()
  OUTPUT      — caller reads result here after run()
  ACCUMULATOR — loop variable with storage cell (persists across iterations)
  SCRATCH     — internal working cell (not visible to caller)
  TILE_PORT   — named port of a tile instance
  LOOP_TICK   — counter tick address for for/while loops
  LOOP_LIMIT  — counter limit address

GPU split
=========
  VRAM:  cell array (gate_state, addresses, flags) — GPU owns between ticks
  RAM:   bus buffer {address: value}               — CPU owns, fed to GPU

The named range table is the contract between CPU and GPU:
  - CPU looks up a range by name to know which bus address to write
  - GPU looks up a range by vram_offset to know which cell slice to read
  - No address guessing, no positional indexing

Usage
=====

  from program_image import ProgramImage, NamedRange, RangeKind

  # Build from compiler output
  img = ProgramImage.from_compiler(
      name        = "add_two_numbers",
      records     = records,
      input_map   = imap,
      output_addrs= oa,
      models      = ["INT32_ADD_CLA"],
  )

  # Inspect the manifest
  print(img.manifest())

  # Run via GPU backend
  result = img.run(inputs={"a": 5, "b": 3})
  print(result["output"])   # 8

  # Serialise to dict (for VM image embedding)
  d = img.to_dict()
  img2 = ProgramImage.from_dict(d)
"""

from __future__ import annotations

import imago_log
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Any

from companion import OS_NAME, OS_VERSION
from pond_types import SCOPE_LOCAL, SCOPE_SHORE, SCOPE_EXTENDED


# ── Range kinds ───────────────────────────────────────────────────────────────

class RangeKind:
    INPUT       = "INPUT"        # caller injects before run
    OUTPUT      = "OUTPUT"       # caller reads after run
    ACCUMULATOR = "ACCUMULATOR"  # loop variable — persists across iterations
    SCRATCH     = "SCRATCH"      # internal working register
    TILE_PORT   = "TILE_PORT"    # named port of a tile instance
    LOOP_TICK   = "LOOP_TICK"    # for/while counter tick address
    LOOP_LIMIT  = "LOOP_LIMIT"   # for loop limit bits


# ── NamedRange ────────────────────────────────────────────────────────────────

@dataclass
class NamedRange:
    """
    A named addressable range in the program's cell fabric.

    name:         logical name (matches input_map key or user label)
    bus_address:  absolute bus address (used by CPU to write/read)
    vram_offset:  cell index in GPUArrayBackend (used by GPU kernel)
    width:        number of bits (1 for single-bit, 32 for int32)
    kind:         RangeKind constant
    description:  human-readable purpose
    bit_addresses: list of bus addresses for multi-bit ranges (LSB first)
    """
    name:          str
    bus_address:   int            # primary address (bit 0 for multi-bit)
    vram_offset:   int = 0        # filled in when loaded onto GPU
    width:         int = 1
    kind:          str = RangeKind.SCRATCH
    description:   str = ""
    scope:         str = SCOPE_LOCAL   # object scope: LOCAL / SHORE / EXTENDED
    bit_addresses: list = field(default_factory=list)  # [addr_bit0, addr_bit1, ...]

    def to_dict(self) -> dict:
        return {
            "name":          self.name,
            "bus_address":   self.bus_address,
            "vram_offset":   self.vram_offset,
            "width":         self.width,
            "kind":          self.kind,
            "description":   self.description,
            "scope":         self.scope,
            "bit_addresses": self.bit_addresses,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NamedRange":
        return cls(
            name         = d["name"],
            bus_address  = d["bus_address"],
            vram_offset  = d.get("vram_offset", 0),
            width        = d.get("width", 1),
            kind         = d.get("kind", RangeKind.SCRATCH),
            description  = d.get("description", ""),
            scope        = d.get("scope", SCOPE_LOCAL),
            bit_addresses= d.get("bit_addresses", []),
        )


# ── ProgramImage ──────────────────────────────────────────────────────────────

class ProgramImage:
    """
    Self-describing executable program unit.

    Contains: manifest, models needed, named ranges, compiled cell records.
    The named range table is the CPU/GPU contract — CPU uses bus_address,
    GPU kernel uses vram_offset.
    """

    def __init__(self,
                 name:       str,
                 records:    list,
                 ranges:     list[NamedRange] = None,
                 models:     list[str]        = None,
                 program_id: str              = None):
        self.program_id  = program_id or str(uuid.uuid4())[:8]
        self.name        = name
        self.records     = records          # list of CellMapRecord
        self.ranges:     list[NamedRange] = ranges or []
        self.models:     list[str]        = models or []
        self.created_at  = time.time()
        self.os_name     = OS_NAME
        self.os_version  = OS_VERSION

        # Build lookup tables
        self._by_name:   dict[str, NamedRange] = {r.name: r for r in self.ranges}
        self._by_addr:   dict[int, NamedRange] = {r.bus_address: r for r in self.ranges}
        self._by_kind:   dict[str, list]       = {}
        for r in self.ranges:
            self._by_kind.setdefault(r.kind, []).append(r)

    # ── Factory: from compiler output ─────────────────────────────────────────

    @classmethod
    def from_compiler(cls,
                      name:         str,
                      records:      list,
                      input_map:    dict,
                      output_addrs: list,
                      models:       list[str] = None,
                      arg_names:    list[str] = None) -> "ProgramImage":
        """
        Build a ProgramImage from ImagoCompiler.compile_function() output.

        input_map:    {logical_name: bus_address} from compile_function
        output_addrs: [bus_address, ...] from compile_function
        models:       tile names used (for MODELS NEEDED section)
        arg_names:    original function argument names (for labelling)
        """
        ranges = []

        # Build named ranges from input_map
        for logical_name, bus_addr in input_map.items():
            # Classify by name convention
            if logical_name.startswith("_for_") or logical_name.startswith("_while_"):
                if "_tick" in logical_name:
                    kind = RangeKind.LOOP_TICK
                elif "_limit" in logical_name:
                    kind = RangeKind.LOOP_LIMIT
                else:
                    kind = RangeKind.ACCUMULATOR
            elif arg_names and logical_name in arg_names:
                kind = RangeKind.INPUT
            elif logical_name.startswith("const_"):
                kind = RangeKind.SCRATCH
            else:
                kind = RangeKind.INPUT  # default: assume caller-supplied

            ranges.append(NamedRange(
                name        = logical_name,
                bus_address = bus_addr,
                width       = 1,          # compiler gives single-bit addresses
                kind        = kind,
                description = f"Compiler: {logical_name}",
            ))

        # Build named ranges for outputs
        for i, addr in enumerate(output_addrs):
            ranges.append(NamedRange(
                name        = f"output_b{i}",
                bus_address = addr,
                width       = 1,
                kind        = RangeKind.OUTPUT,
                description = f"Output bit {i}",
            ))

        # Add a synthetic "output" range covering all output bits
        if output_addrs:
            ranges.append(NamedRange(
                name          = "output",
                bus_address   = output_addrs[0],
                width         = len(output_addrs),
                kind          = RangeKind.OUTPUT,
                description   = f"Full output ({len(output_addrs)} bits)",
                bit_addresses = output_addrs,
            ))

        return cls(
            name    = name,
            records = records,
            ranges  = ranges,
            models  = models or [],
        )

    # ── Range access ──────────────────────────────────────────────────────────

    def range(self, name: str) -> Optional[NamedRange]:
        """Look up a named range."""
        return self._by_name.get(name)

    def inputs(self) -> list[NamedRange]:
        """All INPUT ranges — what the caller must supply."""
        return self._by_kind.get(RangeKind.INPUT, [])

    def outputs(self) -> list[NamedRange]:
        """All OUTPUT ranges — what the caller reads back."""
        return self._by_kind.get(RangeKind.OUTPUT, [])

    def accumulators(self) -> list[NamedRange]:
        """All ACCUMULATOR ranges — loop variables with storage."""
        return self._by_kind.get(RangeKind.ACCUMULATOR, [])

    def loop_controls(self) -> list[NamedRange]:
        """LOOP_TICK and LOOP_LIMIT ranges."""
        return (self._by_kind.get(RangeKind.LOOP_TICK, []) +
                self._by_kind.get(RangeKind.LOOP_LIMIT, []))

    def input_address(self, name: str) -> Optional[int]:
        """Bus address for a named input."""
        r = self._by_name.get(name)
        return r.bus_address if r else None

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self,
            inputs: dict[str, Any] = None,
            max_cycles: int = 100_000,
            controller=None) -> dict[str, Any]:
        """
        Execute the program.

        inputs:     {range_name: value}  — resolved via named ranges
        controller: ImagoController (created fresh if None)

        Returns {range_name: value} for all OUTPUT ranges.
        """
        from controller import ImagoController

        ctrl = controller or ImagoController(
            cell_count=len(self.records) + 500)
        rid = ctrl.load_map(self.records, self.name)

        # Resolve named inputs → bus addresses
        raw_inputs = {}
        for name, value in (inputs or {}).items():
            r = self._by_name.get(name)
            if r is None:
                # Try direct address
                raw_inputs[int(name)] = value
                continue
            if r.bit_addresses:
                # Multi-bit: expand to individual bit addresses
                for bit, addr in enumerate(r.bit_addresses):
                    raw_inputs[addr] = (value >> bit) & 1
            else:
                raw_inputs[r.bus_address] = value

        # Auto-inject loop ticks
        for r in self.loop_controls():
            if r.kind == RangeKind.LOOP_TICK:
                raw_inputs.setdefault(r.bus_address, 1)

        # Collect output addresses
        output_addrs = [r.bus_address for r in self.outputs()
                        if r.name != "output"]
        if not output_addrs:
            output_addrs = [r.bus_address for r in self.outputs()]

        raw_result = ctrl.run(rid, inputs=raw_inputs,
                               capture_addresses=output_addrs,
                               max_cycles=max_cycles)

        # Resolve results back to named ranges
        result = {}
        output_range = self._by_name.get("output")
        if output_range and output_range.bit_addresses:
            val = 0
            for bit, addr in enumerate(output_range.bit_addresses):
                v = raw_result.get(addr)
                if v:
                    val |= (1 << bit)
            result["output"] = val

        # Individual bit outputs
        for r in self.outputs():
            if r.name == "output":
                continue
            v = raw_result.get(r.bus_address)
            result[r.name] = v

        return result

    # ── Manifest ──────────────────────────────────────────────────────────────

    def manifest(self) -> dict:
        """
        Full program manifest — human-readable description of the program.
        This is what gets printed when you inspect a program in the workbench.
        """
        return {
            "MANIFEST HEADER": {
                "program_id":  self.program_id,
                "name":        self.name,
                "os":          f"{self.os_name} v{self.os_version}",
                "created_at":  self.created_at,
                "cell_count":  len(self.records),
            },
            "MODELS NEEDED": self.models,
            "NAMED RANGES": {
                r.name: {
                    "kind":        r.kind,
                    "bus_address": hex(r.bus_address),
                    "width":       r.width,
                    "description": r.description,
                }
                for r in self.ranges
            },
            "PROGRAM SCRIPTS": {
                "record_count": len(self.records),
            },
        }

    def describe(self) -> str:
        """Compact one-line description."""
        n_in  = len(self.inputs())
        n_out = len(self.outputs())
        n_acc = len(self.accumulators())
        n_lp  = len(self.loop_controls())
        return (f"ProgramImage '{self.name}' — "
                f"{len(self.records)} cells, "
                f"{n_in} inputs, {n_out} outputs"
                + (f", {n_acc} accumulators" if n_acc else "")
                + (f", {n_lp} loop controls" if n_lp else ""))

    # ── GPU loading ───────────────────────────────────────────────────────────

    def load_to_gpu(self, backend=None):
        """
        Load this program onto a GPU backend.

        Assigns vram_offset to each named range.
        Returns the backend (created if None).
        """
        from gpu_array import GPUArrayBackend
        from gate_states import GS_PASS

        if backend is None:
            backend = GPUArrayBackend(cell_count=len(self.records) + 500)

        # Load cells and assign vram offsets
        for i, rec in enumerate(self.records):
            addr = 0x200000 + i   # stable base for GPU layout
            backend.configure_cell(
                address        = addr,
                gate_state     = getattr(rec, 'gate_state', GS_PASS),
                input_address  = getattr(rec, 'input_address', 0),
                output_address = getattr(rec, 'output_address', 0),
                start_flag     = True,
            )

        # Assign vram offsets to named ranges
        # vram_offset = index of the cell whose bus_address matches
        addr_to_offset = {}
        for i, rec in enumerate(self.records):
            if hasattr(rec, 'input_address'):
                addr_to_offset[rec.input_address] = i

        for r in self.ranges:
            offset = addr_to_offset.get(r.bus_address, 0)
            r.vram_offset = offset
            # Rebuild lookup
            self._by_name[r.name] = r

        imago_log.info(f"[PROGRAM] '{self.name}' loaded to GPU backend: "
              f"{len(self.records)} cells, "
              f"{len(self.ranges)} named ranges")
        return backend

    # ── GPU run ───────────────────────────────────────────────────────────────

    def run_gpu(self,
                inputs:     dict[str, Any] = None,
                max_ticks:  int = 100_000,
                backend=None) -> dict[str, Any]:
        """
        Execute program on GPU backend.

        RAM side:  bus buffer — CPU writes inputs by name, reads outputs by name
        VRAM side: cell array — GPU ticks all armed cells in parallel

        Returns {range_name: value} for all OUTPUT ranges.
        """
        backend = self.load_to_gpu(backend)

        # CPU: write named inputs to RAM bus
        for name, value in (inputs or {}).items():
            r = self._by_name.get(name)
            if r is None:
                continue
            if r.bit_addresses:
                for bit, addr in enumerate(r.bit_addresses):
                    backend._bus[addr] = ((value >> bit) & 1, 0)
            else:
                backend._bus[r.bus_address] = (value, 0)

        # Auto-inject loop ticks
        for r in self.loop_controls():
            if r.kind == RangeKind.LOOP_TICK:
                backend._bus.setdefault(r.bus_address, (1, 0))

        # GPU: tick until quiescent
        output_addrs = set()
        for r in self.outputs():
            if r.bit_addresses:
                output_addrs.update(r.bit_addresses)
            else:
                output_addrs.add(r.bus_address)

        results_seen = {}
        for tick in range(max_ticks):
            fired, updates = backend.tick(bus_in=backend._bus)
            if fired == 0:
                break
            for addr, val in updates.items():
                if addr in output_addrs:
                    results_seen[addr] = val[0] if isinstance(val, tuple) else val

        # CPU: read named outputs from RAM bus
        result = {}
        output_range = self._by_name.get("output")
        if output_range and output_range.bit_addresses:
            val = 0
            for bit, addr in enumerate(output_range.bit_addresses):
                v = results_seen.get(addr, backend._bus.get(addr))
                if v:
                    bit_v = v[0] if isinstance(v, tuple) else v
                    if bit_v:
                        val |= (1 << bit)
            result["output"] = val

        for r in self.outputs():
            if r.name == "output":
                continue
            v = results_seen.get(r.bus_address,
                                  backend._bus.get(r.bus_address))
            if v is not None:
                result[r.name] = v[0] if isinstance(v, tuple) else v

        return result

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise to dict (for embedding in VM image or saving to disk)."""
        # Derive flat inputs/outputs dicts from ranges for easy loading
        inputs  = {r.name: r.bus_address for r in self.ranges
                   if r.kind in ("INPUT",  "ACCUMULATOR")}
        outputs = {r.name: r.bus_address for r in self.ranges
                   if r.kind == "OUTPUT" and not r.name.startswith("output_b")}
        return {
            "program_id":  self.program_id,
            "name":        self.name,
            "os_name":     self.os_name,
            "os_version":  self.os_version,
            "created_at":  self.created_at,
            "inputs":      inputs,
            "outputs":     outputs,
            "models":      self.models,
            "ranges":      [r.to_dict() for r in self.ranges],
            "records": [
                {
                    "gs":   getattr(r, 'gate_state', 0),
                    "in":   getattr(r, 'input_address', 0),
                    "out":  getattr(r, 'output_address', 0),
                    "inB":  getattr(r, 'input_b_address', None),
                    "alt":  getattr(r, 'output_address_alt', None),
                    "stor": getattr(r, 'storage_mode', False),
                    "init": getattr(r, 'initial_value', None),
                }
                for r in self.records
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProgramImage":
        """Restore from serialised dict."""
        from controller import CellMapRecord
        records = [
            CellMapRecord(
                r["gs"], r["in"], r["out"],
                output_address_alt = r.get("alt"),
                storage_mode       = r.get("stor", False),
                initial_value      = r.get("init"),
                input_b_address    = r.get("inB"),
            )
            for r in d.get("records", [])
        ]
        ranges = [NamedRange.from_dict(r) for r in d.get("ranges", [])]
        img = cls(
            name       = d["name"],
            records    = records,
            ranges     = ranges,
            models     = d.get("models", []),
            program_id = d.get("program_id"),
        )
        img.created_at  = d.get("created_at", time.time())
        img.os_name     = d.get("os_name",    OS_NAME)
        img.os_version  = d.get("os_version", OS_VERSION)
        return img

    def __repr__(self) -> str:
        return self.describe()
