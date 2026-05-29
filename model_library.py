"""
model_library.py — Imago Composed Model Library

A model is a pre-built, pre-verified functional unit assembled from one
or more tiles. Unlike individual tiles (fp_tiles.py), models represent
complete operations with named input/output ports, known total pipeline
depth, and a ready-to-load cell map.

Architecture position:

    fp_tiles.py      — leaf operations (INT32_ADD_CLA, FP32_MUL, etc.)
    model_library.py — composed models  (INT32_ADDER, FP32_MULTIPLIER...)
    compiler.py      — looks up models, wires programs together

The compiler sees `a + b`, looks up INT32_ADDER from the model library,
and gets a ModelSpec with pre-placed records and labelled port addresses.
No recompilation — the model is a frozen, verified blueprint.

Each Pond that requests a model gets its own instance loaded at its own
base address. The library holds the spec; the array holds the instance.

ModelSpec fields
================

  name:            unique identifier — used by the compiler
  description:     human-readable purpose
  version:         semantic version string
  category:        grouping (ARITHMETIC, LOGIC, COMPARISON, IO, CONTROL)
  inputs:          {port_name: bit_width}  named input ports
  outputs:         {port_name: bit_width}  named output ports
  tiles_used:      list of tile names this model is built from
  pipeline_depth:  total ticks from inputs to outputs
  cell_count:      total cells in this model
  compiler_ops:    Python AST op names this model handles (e.g. ['Add'])
  operand_types:   which operand widths apply ('int32', 'fp32', 'bool')

Extending
=========

Register new models at startup — no changes to this file needed:

    from model_library import model_library, ModelSpec
    model_library.register(ModelSpec(
        name        = "INT32_MULTIPLIER",
        description = "32-bit integer multiply via repeated addition",
        category    = "ARITHMETIC",
        inputs      = {"a": 32, "b": 32},
        outputs     = {"result": 32},
        tiles_used  = ["INT32_ADD"],  # Kogge-Stone
        operand_types = ["int32"],
        compiler_ops  = ["Mult"],
    ))

Future shared library
=====================
In a multi-system deployment, the model library lives in a LIBRARY Pond.
Other Ponds request models via COMPANION using a TILE key.
COMPANION issues the cell map blueprint; the requesting Pond loads it
via DMA into its own address space. The model library Pond never changes
at runtime — it is frozen after boot and shared read-only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import CellMapRecord


# ── Model categories ──────────────────────────────────────────────────────────

CAT_ARITHMETIC  = "ARITHMETIC"   # add, subtract, multiply, divide
CAT_LOGIC       = "LOGIC"        # AND, OR, XOR, NOT, shift
CAT_COMPARISON  = "COMPARISON"   # equal, less-than, greater-than
CAT_CONTROL     = "CONTROL"      # mux, select, branch, counter
CAT_IO          = "IO"           # peripheral handlers
CAT_SIGNAL      = "SIGNAL"       # sort, filter, transform
CAT_COMPOUND    = "COMPOUND"     # multi-operation models (PID, etc.)
CAT_SYSTEM      = "SYSTEM"       # core OS Ponds — compiler, tile library, sequencer

CATEGORIES = (CAT_ARITHMETIC, CAT_LOGIC, CAT_COMPARISON,
              CAT_CONTROL, CAT_IO, CAT_SIGNAL, CAT_COMPOUND)


# ── ModelPort ─────────────────────────────────────────────────────────────────

@dataclass
class ModelPort:
    """
    One named input or output port on a model.

    name:       port name as used in compiled code (e.g. 'a', 'result')
    bit_width:  number of bits (1 for boolean, 32 for int32/fp32)
    addresses:  absolute bus addresses for each bit (populated at placement)
    """
    name:      str
    bit_width: int
    addresses: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name":      self.name,
            "bit_width": self.bit_width,
            "addresses": [hex(a) for a in self.addresses[:4]] +
                         (["..."] if len(self.addresses) > 4 else []),
        }


# ── ModelSpec ─────────────────────────────────────────────────────────────────

@dataclass
class ModelSpec:
    """
    Complete specification for one composed model.

    name:           unique model identifier
    description:    human-readable purpose
    version:        semantic version (e.g. "1.0")
    category:       see CAT_* constants
    inputs:         {port_name: bit_width}
    outputs:        {port_name: bit_width}
    tiles_used:     tile names this model is built from
    pipeline_depth: total ticks from any input to any output
    cell_count:     total cells in this model
    compiler_ops:   Python AST BinOp names this handles (e.g. ['Add', 'Sub'])
    operand_types:  which types apply ('int32', 'fp32', 'bool')
    metadata:       arbitrary extra info
    """
    name:           str
    description:    str            = ""
    version:        str            = "1.0"
    category:       str            = CAT_ARITHMETIC
    inputs:         dict           = field(default_factory=dict)
    outputs:        dict           = field(default_factory=dict)
    tiles_used:     list           = field(default_factory=list)
    pipeline_depth: int            = 0
    cell_count:     int            = 0
    compiler_ops:   list           = field(default_factory=list)
    operand_types:  list           = field(default_factory=list)
    metadata:       dict           = field(default_factory=dict)
    carry_in:       int            = 0   # carry-in value for extra port bits (0=ADD, 1=SUB)

    def place(self, base_address: int = 0x00200000) -> "ModelInstance":
        """
        Place this model at a specific base address.

        Returns a ModelInstance with concrete cell records and port
        addresses, ready to load via controller.load_map().

        This is what the compiler calls when it needs to instantiate
        the model inside a specific Pond.
        """
        return ModelInstance.build(self, base_address)

    def to_dict(self) -> dict:
        return {
            "name":           self.name,
            "description":    self.description,
            "version":        self.version,
            "category":       self.category,
            "inputs":         self.inputs,
            "outputs":        self.outputs,
            "tiles_used":     self.tiles_used,
            "pipeline_depth": self.pipeline_depth,
            "cell_count":     self.cell_count,
            "compiler_ops":   self.compiler_ops,
            "operand_types":  self.operand_types,
        }

    def __repr__(self) -> str:
        ports_in  = ", ".join(f"{k}:{v}b" for k, v in self.inputs.items())
        ports_out = ", ".join(f"{k}:{v}b" for k, v in self.outputs.items())
        return (f"ModelSpec('{self.name}' v{self.version} "
                f"[{ports_in}]→[{ports_out}] "
                f"depth={self.pipeline_depth} cells={self.cell_count})")


# ── ModelInstance ─────────────────────────────────────────────────────────────

@dataclass
class ModelInstance:
    """
    A placed ModelSpec — concrete records and port addresses at a
    specific base address.

    spec:        the ModelSpec this was built from
    base_address: where in the array this instance lives
    records:     CellMapRecords ready for controller.load_map()
    input_ports: {port_name: ModelPort} with populated addresses
    output_ports:{port_name: ModelPort} with populated addresses
    segment_id:  bus segment ID for this model's cells (isolation)
    ptt_entries: list of PTT-ready dicts for attach_ptt()
    placed_at:   timestamp
    """
    spec:         ModelSpec
    base_address: int
    records:      list
    input_ports:  dict
    output_ports: dict
    segment_id:   int   = 1
    ptt_entries:  list  = field(default_factory=list)
    placed_at:    float = field(default_factory=time.time)

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def pipeline_depth(self) -> int:
        return self.spec.pipeline_depth

    @property
    def cell_count(self) -> int:
        return len(self.records)

    def input_addresses(self, port: str) -> list[int]:
        """Return bus addresses for input port bits."""
        p = self.input_ports.get(port)
        return p.addresses if p else []

    def output_addresses(self, port: str) -> list[int]:
        """Return bus addresses for output port bits."""
        p = self.output_ports.get(port)
        return p.addresses if p else []

    @classmethod
    def build(cls, spec: ModelSpec, base_address: int) -> "ModelInstance":
        """
        Place a ModelSpec at base_address and return the instance.

        Delegates to each tile's TilePlacer, collects all records,
        and maps named ports to their concrete bus addresses.
        """
        from fp_tiles import TileLibrary, TilePlacer

        lib     = TileLibrary()
        placer  = TilePlacer(base_address=base_address)
        records = []
        input_ports  = {}
        output_ports = {}
        ptt_entries  = []

        for tile_name in spec.tiles_used:
            tile = lib.get(tile_name)
            tile_records, in_a, in_b, out, _preload_map = placer.place(tile)
            records.extend(tile_records)

            # Map ports by position — first tile's inputs are the model inputs
            # For single-tile models this is straightforward
            # For multi-tile models subclasses override this method
            if not input_ports:
                port_names = list(spec.inputs.keys())
                if len(port_names) >= 1:
                    p = ModelPort(port_names[0], spec.inputs[port_names[0]],
                                  list(in_a))
                    input_ports[port_names[0]] = p
                if len(port_names) >= 2:
                    p = ModelPort(port_names[1], spec.inputs[port_names[1]],
                                  list(in_b))
                    input_ports[port_names[1]] = p

            # Last tile's outputs are the model outputs
            out_names = list(spec.outputs.keys())
            if out_names:
                output_ports = {
                    out_names[0]: ModelPort(out_names[0],
                                            spec.outputs[out_names[0]],
                                            list(out))
                }

            # PTT entries for this tile
            ptt_entries.append({
                "label":   f"{spec.name}.{tile_name}",
                "type":    "TILE_IN",
                "address": base_address,
            })

        return cls(
            spec         = spec,
            base_address = base_address,
            records      = records,
            input_ports  = input_ports,
            output_ports = output_ports,
            ptt_entries  = ptt_entries,
        )

    def to_dict(self) -> dict:
        return {
            "name":         self.name,
            "base_address": hex(self.base_address),
            "cell_count":   self.cell_count,
            "depth":        self.pipeline_depth,
            "inputs":       {k: v.to_dict() for k, v in self.input_ports.items()},
            "outputs":      {k: v.to_dict() for k, v in self.output_ports.items()},
        }


# ── ModelLibrary ──────────────────────────────────────────────────────────────

class ModelLibrary:
    """
    Central registry of all known composed models.

    Usage:
        from model_library import model_library

        # Look up a model
        spec = model_library.get('INT32_ADDER')

        # Place it at a base address
        instance = spec.place(base_address=0x00400000)

        # Load into the array
        rid = controller.load_map(instance.records, spec.name,
                                   base_address=instance.base_address)

        # Find models by compiler operation
        spec = model_library.for_op('Add', 'int32')

        # Find all arithmetic models
        arith = model_library.by_category(CAT_ARITHMETIC)

        # Register a new model
        model_library.register(ModelSpec('MY_MODEL', ...))
    """

    def __init__(self):
        self._models: dict[str, ModelSpec] = {}
        # Op lookup: (ast_op_name, operand_type) → model_name
        self._op_index: dict[tuple, str] = {}

    def register(self, spec: ModelSpec) -> None:
        """Register a model. Overwrites if name already exists."""
        self._models[spec.name] = spec
        for op in spec.compiler_ops:
            for otype in spec.operand_types:
                self._op_index[(op, otype)] = spec.name

    def get(self, name: str) -> Optional[ModelSpec]:
        """Return ModelSpec by name, or None."""
        return self._models.get(name)

    def require(self, name: str) -> ModelSpec:
        """Return ModelSpec by name, raising ValueError if not found."""
        spec = self._models.get(name)
        if spec is None:
            raise ValueError(
                f"Unknown model '{name}'. "
                f"Available: {sorted(self._models)}"
            )
        return spec

    def for_op(self, ast_op: str,
               operand_type: str = "int32") -> Optional[ModelSpec]:
        """
        Return the model that handles a given AST operation and type.

        ast_op:       Python AST BinOp name — 'Add', 'Sub', 'Mult', etc.
        operand_type: 'int32', 'fp32', 'bool'

        This is the compiler's primary lookup path:
            node is ast.Add → for_op('Add', 'int32') → INT32_ADDER
        """
        name = self._op_index.get((ast_op, operand_type))
        return self._models.get(name) if name else None

    def by_category(self, category: str) -> list[ModelSpec]:
        """Return all models in a given category."""
        return [s for s in self._models.values()
                if s.category == category]

    def available(self) -> list[str]:
        """Return sorted list of all model names."""
        return sorted(self._models.keys())

    def is_valid(self, name: str) -> bool:
        return name in self._models

    def performance_quote(self, name: str,
                           clock_mhz: float = 1.0) -> dict:
        """
        Quote performance estimates for a model at a given clock speed.

        clock_mhz:  target clock frequency in MHz

        Returns timing estimates for both isolated and wired modes:
          isolated: Python hand-off between each operation
          wired:    direct cell-to-cell, one burst of ticks
        """
        spec = self.require(name)
        ticks          = spec.pipeline_depth
        cells          = spec.cell_count
        cycle_us       = 1.0 / clock_mhz        # microseconds per tick
        silicon_us     = ticks * cycle_us
        # Python sim estimate: ~4ms per tick per 6000 active cells
        python_ms_tick = max(0.001, cells / 6000 * 4.0)
        python_ms      = ticks * python_ms_tick

        return {
            "model":          name,
            "pipeline_depth": ticks,
            "cell_count":     cells,
            "clock_mhz":      clock_mhz,
            "silicon_us":     round(silicon_us, 3),
            "silicon_ms":     round(silicon_us / 1000, 6),
            "python_sim_ms":  round(python_ms, 1),
            "tiles_used":     spec.tiles_used,
            "note": (
                f"{ticks} ticks × {cycle_us:.3f}μs = {silicon_us:.3f}μs on silicon, "
                f"~{python_ms:.0f}ms in Python sim"
            ),
        }

    def dump(self) -> str:
        lines = [f"ModelLibrary ({len(self._models)} models):"]
        for cat in CATEGORIES:
            models = self.by_category(cat)
            if not models:
                continue
            lines.append(f"\n  [{cat}]")
            for spec in sorted(models, key=lambda s: s.name):
                ports_in  = ", ".join(f"{k}:{v}b"
                                      for k, v in spec.inputs.items())
                ports_out = ", ".join(f"{k}:{v}b"
                                      for k, v in spec.outputs.items())
                lines.append(
                    f"    {spec.name:<22s} "
                    f"[{ports_in}]→[{ports_out}]  "
                    f"depth={spec.pipeline_depth:>4}  "
                    f"cells={spec.cell_count:>7}  "
                    f"ops={spec.compiler_ops}"
                )
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._models)

    def __contains__(self, name: str) -> bool:
        return name in self._models


# ── Built-in models ───────────────────────────────────────────────────────────

_BUILTIN_MODELS = [

    # ── v2 model figures ─────────────────────────────────────────────────────
    # All figures verified against TileLibrary 2026-05-11.
    # INT32: Kogge-Stone adder/subtractor, verified.
    # FP32: v2 NORBuilder tiles, verified (1253/3066 cells).
    # IO models unchanged — peripheral interface not affected.

    # ── INT32 Arithmetic ──────────────────────────────────────────────────────

    ModelSpec(
        name           = "INT32_ADDER",
        description    = "32-bit integer addition using Kogge-Stone parallel prefix. "
                         "482 cells, depth 2. Fastest INT32 add available.",
        category       = CAT_ARITHMETIC,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 32},
        tiles_used     = ["INT32_ADD"],       # v2: Kogge-Stone parallel prefix
        pipeline_depth = 2,               # v2 Kogge-Stone actual (was 12 estimate, 58 CLA)
        cell_count     = 482,             # v2 Kogge-Stone actual (was 548 estimate, 6,227 CLA)
        compiler_ops   = ["Add"],
        operand_types  = ["int32"],
    ),

    ModelSpec(
        name           = "INT32_ADDER_RIPPLE",
        description    = "32-bit integer addition using ripple carry. "
                         "Slower but uses fewer cells than CLA. "
                         "Not the default compiler target — request by name.",
        category       = CAT_ARITHMETIC,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 32},
        tiles_used     = ["INT32_ADD"],       # v2: same tile as ADDER (KS)
        pipeline_depth = 2,               # v2 Kogge-Stone actual
        cell_count     = 482,             # v2 Kogge-Stone actual (was 12,931 ripple)
        compiler_ops   = [],          # not the default — use INT32_ADDER
        operand_types  = ["int32"],
        metadata       = {"variant": "ripple_carry"},
    ),

    ModelSpec(
        name           = "INT32_SUBTRACTOR",
        description    = "32-bit integer subtraction (a - b). "
                         "carry_in=1 sets the two's complement borrow bit.",
        category       = CAT_ARITHMETIC,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 32},
        tiles_used     = ["INT32_SUB"],
        pipeline_depth = 12,              # actual: NOT(b) depth 1 + KS adder depth 11
        cell_count     = 517,             # actual: 32 NOT cells + 485 KS adder cells
        compiler_ops   = ["Sub"],
        operand_types  = ["int32"],
        carry_in       = 1,
    ),

    # ── FP32 Arithmetic ───────────────────────────────────────────────────────

    ModelSpec(
        name           = "FP32_ADDER",
        description    = "32-bit IEEE 754 single-precision addition.",
        category       = CAT_ARITHMETIC,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 32},
        tiles_used     = ["FP32_ADD"],
        pipeline_depth = 85,              # actual: barrel shifter + ripple mant add
        cell_count     = 1253,            # actual (v2 NORBuilder, native gates)
        compiler_ops   = ["Add"],
        operand_types  = ["fp32"],
    ),

    ModelSpec(
        name           = "FP32_MULTIPLIER",
        description    = "32-bit IEEE 754 single-precision multiplication.",
        category       = CAT_ARITHMETIC,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 32},
        tiles_used     = ["FP32_MUL"],
        pipeline_depth = 89,              # actual: 24-pass partial product accumulation
        cell_count     = 3066,            # actual (v2 NORBuilder, native gates)
        compiler_ops   = ["Mult"],
        operand_types  = ["fp32"],
    ),

    # ── Comparison ────────────────────────────────────────────────────────────

    ModelSpec(
        name           = "INT32_EQUAL",
        description    = "32-bit integer equality comparison (a == b). "
                         "Returns 1-bit result.",
        category       = CAT_COMPARISON,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 1},
        tiles_used     = ["INT32_EQ"],
        pipeline_depth = 7,               # verified: 95 cells, depth 7
        cell_count     = 95,              # verified (was 63/6 — stale estimate)
        compiler_ops   = ["Eq"],
        operand_types  = ["int32"],
    ),

    ModelSpec(
        name           = "INT32_LT_U",
        description    = "32-bit unsigned less-than (a < b). Returns 1-bit result. "
                         "518 cells, depth 14. Uses borrow from Kogge-Stone subtractor.",
        category       = CAT_COMPARISON,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 1},
        tiles_used     = ["INT32_LT_U"],
        pipeline_depth = 14,
        cell_count     = 518,
        compiler_ops   = ["Lt"],
        operand_types  = ["int32"],
    ),

    ModelSpec(
        name           = "INT32_LT_S",
        description    = "32-bit signed less-than (a < b, two's complement). Returns 1-bit result. "
                         "523 cells, depth 16. Handles all sign combinations without overflow.",
        category       = CAT_COMPARISON,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 1},
        tiles_used     = ["INT32_LT_S"],
        pipeline_depth = 16,
        cell_count     = 523,
        compiler_ops   = ["Lt"],
        operand_types  = ["signed"],
    ),

    ModelSpec(
        name           = "INT32_MIN",
        description    = "32-bit signed minimum: out = min(a, b). "
                         "317 cells, depth 66. Uses sign-bit of ripple subtract.",
        category       = CAT_ARITHMETIC,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 32},
        tiles_used     = ["INT32_MIN"],
        pipeline_depth = 66,
        cell_count     = 317,
        compiler_ops   = [],
        operand_types  = ["int32"],
    ),

    ModelSpec(
        name           = "INT32_MAX",
        description    = "32-bit signed maximum: out = max(a, b). "
                         "317 cells, depth 66. Uses sign-bit of ripple subtract.",
        category       = CAT_ARITHMETIC,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 32},
        tiles_used     = ["INT32_MAX"],
        pipeline_depth = 66,
        cell_count     = 317,
        compiler_ops   = [],
        operand_types  = ["int32"],
    ),

    ModelSpec(
        name           = "INT32_CAS",
        description    = "32-bit unsigned compare-and-swap: out_min = min(a,b), out_max = max(a,b). "
                         "711 cells, depth 17. Primitive for 32-bit sorting networks.",
        category       = CAT_COMPARISON,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"out_min": 32, "out_max": 32},
        tiles_used     = ["INT32_CAS"],
        pipeline_depth = 17,
        cell_count     = 711,
        compiler_ops   = [],
        operand_types  = ["int32"],
    ),

    ModelSpec(
        name           = "FP32_EQUAL",
        description    = "32-bit floating point equality comparison.",
        category       = CAT_COMPARISON,
        inputs         = {"a": 32, "b": 32},
        outputs        = {"result": 1},
        tiles_used     = ["FP32_CMP_EQ"],
        pipeline_depth = 6,               # v2 estimate: was 23
        cell_count     = 63,              # v2 estimate: was 763
        compiler_ops   = ["Eq"],
        operand_types  = ["fp32"],
    ),

    # ── Control ───────────────────────────────────────────────────────────────

    ModelSpec(
        name           = "INT32_MUX",
        description    = "32-bit 2:1 multiplexer. "
                         "sel=0 → out=a, sel=1 → out=b.",
        category       = CAT_CONTROL,
        inputs         = {"a": 32, "b": 32, "sel": 1},
        outputs        = {"result": 32},
        tiles_used     = ["INT32_MUX"],
        pipeline_depth = 3,               # v2: was 7
        cell_count     = 128,             # v2: was 544
        compiler_ops   = [],
        operand_types  = ["int32"],
        metadata       = {"is_mux": True},
    ),

    # ── IO Handlers ───────────────────────────────────────────────────────────

    ModelSpec(
        name           = "KEYBOARD_INPUT",
        description    = "Keyboard event handler. Produces keycode on "
                         "keypress. Depth matches keyboard polling rate.",
        category       = CAT_IO,
        inputs         = {},
        outputs        = {"keycode": 32},
        tiles_used     = ["KEYBOARD_HANDLER"],
        pipeline_depth = 12,              # IO tile (unchanged)
        cell_count     = 840,             # IO tile (unchanged)
        compiler_ops   = [],
        operand_types  = [],
        metadata       = {"peripheral": "keyboard"},
    ),

    ModelSpec(
        name           = "DISPLAY_OUTPUT",
        description    = "Display frame handler. Accepts pixel data and "
                         "timing signals.",
        category       = CAT_IO,
        inputs         = {"pixel": 32, "sync": 1},
        outputs        = {},
        tiles_used     = ["DISPLAY_HANDLER"],
        pipeline_depth = 32,              # IO tile (unchanged)
        cell_count     = 18600,           # IO tile (unchanged)
        compiler_ops   = [],
        operand_types  = [],
        metadata       = {"peripheral": "display"},
    ),

    ModelSpec(
        name           = "SENSOR_INPUT",
        description    = "Generic sensor handler. Reads 32-bit sensor "
                         "value on trigger.",
        category       = CAT_IO,
        inputs         = {"trigger": 1},
        outputs        = {"value": 32},
        tiles_used     = ["SENSOR_HANDLER"],
        pipeline_depth = 18,
        cell_count     = 1240,
        compiler_ops   = [],
        operand_types  = [],
        metadata       = {"peripheral": "sensor"},
    ),

    ModelSpec(
        name           = "NETWORK_IO",
        description    = "Network packet handler. Send/receive 32-bit "
                         "data over the network bridge.",
        category       = CAT_IO,
        inputs         = {"data_out": 32, "send": 1},
        outputs        = {"data_in": 32, "ready": 1},
        tiles_used     = ["NETWORK_HANDLER"],
        pipeline_depth = 28,
        cell_count     = 4200,
        compiler_ops   = [],
        operand_types  = [],
        metadata       = {"peripheral": "network"},
    ),

    ModelSpec(
        name           = "STORAGE_IO",
        description    = "Storage read/write handler. Accepts address "
                         "and data, returns read data.",
        category       = CAT_IO,
        inputs         = {"address": 32, "data_out": 32, "write": 1},
        outputs        = {"data_in": 32},
        tiles_used     = ["STORAGE_HANDLER"],
        pipeline_depth = 22,
        cell_count     = 3100,
        compiler_ops   = [],
        operand_types  = [],
        metadata       = {"peripheral": "storage"},
    ),

    ModelSpec(
        name           = "AUDIO_INPUT",
        description    = "Audio sample capture handler.",
        category       = CAT_IO,
        inputs         = {},
        outputs        = {"sample": 32},
        tiles_used     = ["AUDIO_IN_HANDLER"],
        pipeline_depth = 24,
        cell_count     = 2800,
        compiler_ops   = [],
        operand_types  = [],
        metadata       = {"peripheral": "audio_in"},
    ),

    ModelSpec(
        name           = "AUDIO_OUTPUT",
        description    = "Audio sample playback handler.",
        category       = CAT_IO,
        inputs         = {"sample": 32},
        outputs        = {},
        tiles_used     = ["AUDIO_OUT_HANDLER"],
        pipeline_depth = 24,
        cell_count     = 2800,
        compiler_ops   = [],
        operand_types  = [],
        metadata       = {"peripheral": "audio_out"},
    ),

    # ── Counter models (first-order loop primitives) ───────────────────────────
    ModelSpec(
        name           = "SHIFT_COUNTER_8",
        description    = "Shift-register counter for range(8). No arithmetic. "
                         "Pure PASS chain — 9 cells, depth 9 ticks exactly.",
        category       = "COUNTER",
        inputs         = {"tick": 1},
        outputs        = {"step": 8, "done": 1},
        tiles_used     = ["COUNTER_SHIFT_8"],
        pipeline_depth = 9,
        cell_count     = 9,
        compiler_ops   = [],
        operand_types  = [],
    ),
    ModelSpec(
        name           = "SHIFT_COUNTER_16",
        description    = "Shift-register counter for range(16). No arithmetic. "
                         "17 cells, depth 17 ticks exactly.",
        category       = "COUNTER",
        inputs         = {"tick": 1},
        outputs        = {"step": 16, "done": 1},
        tiles_used     = ["COUNTER_SHIFT_16"],
        pipeline_depth = 17,
        cell_count     = 17,
        compiler_ops   = [],
        operand_types  = [],
    ),
    ModelSpec(
        name           = "RIPPLE_COUNTER_8",
        description    = "8-bit ripple increment counter. TICK to advance, "
                         "LIMIT to compare against. DONE fires when count==limit.",
        category       = "COUNTER",
        inputs         = {"tick": 1, "limit": 8},
        outputs        = {"value": 8, "done": 1, "carry": 1},
        tiles_used     = ["COUNTER_RIPPLE_8"],
        pipeline_depth = 4,               # unchanged
        cell_count     = 145,             # v2 estimate: was 924
        compiler_ops   = [],
        operand_types  = [],
    ),
    ModelSpec(
        name           = "RIPPLE_COUNTER_32",
        description    = "32-bit ripple increment counter for large or variable ranges.",
        category       = "COUNTER",
        inputs         = {"tick": 1, "limit": 32},
        outputs        = {"value": 32, "done": 1, "carry": 1},
        tiles_used     = ["COUNTER_RIPPLE_32"],
        pipeline_depth = 12,              # v2: KS adder depth (was 7)
        cell_count     = 620,             # v2 estimate: was 9,564
        compiler_ops   = [],
        operand_types  = [],
    ),
    ModelSpec(
        name           = "DECREMENT_COUNTER_8",
        description    = "8-bit decrement counter. TICK to decrement. "
                         "DONE fires when count reaches 0.",
        category       = "COUNTER",
        inputs         = {"tick": 1, "value": 8},
        outputs        = {"value": 8, "done": 1},
        tiles_used     = ["COUNTER_DECREMENT_8"],
        pipeline_depth = 4,               # unchanged
        cell_count     = 161,             # v2 estimate: was 510
        compiler_ops   = [],
        operand_types  = [],
    ),
    ModelSpec(
        name           = "DECREMENT_COUNTER_32",
        description    = "32-bit decrement counter for large bounded loops.",
        category       = "COUNTER",
        inputs         = {"tick": 1, "value": 32},
        outputs        = {"value": 32, "done": 1},
        tiles_used     = ["COUNTER_DECREMENT_32"],
        pipeline_depth = 12,              # v2: KS adder depth (was 7)
        cell_count     = 650,             # v2 estimate: was 5,598
        compiler_ops   = [],
        operand_types  = [],
    ),
]

# ── Core Pond models — self-hosting layer ─────────────────────────────────────
# These models describe the Pond wrappers for the compiler, tile library,
# sequencer, and other core OS components. Loaded at boot as part of the
# self-hosted layer. See 09_Standalone_Boot_and_Self_Hosting.md.

_CORE_POND_MODELS = [
    ModelSpec(
        name           = "COMPILER_POND",
        description    = "Spatial compiler — Python AST → CellMapRecord list. "
                         "Persistent LIBRARY Pond, always armed, always ready.",
        version        = "1.1",
        category       = CAT_SYSTEM,
        inputs         = {"source": 0, "function_name": 0, "job_ref": 0},
        outputs        = {"cell_map": 0, "input_map": 0, "output_addrs": 0,
                          "status": 1, "depth": 32, "cell_count": 32},
        tiles_used     = [],
        pipeline_depth = 0,
        cell_count     = 0,
        metadata       = {
            "pond_type": "LIBRARY", "security": "HIDDEN",
            "permanent": True, "always_armed": True,
            "base_address": "0x00600000",
            "vm_module": "compiler.ImagoCompiler",
            "boot_tier": 3, "boot_order": 1,
        },
    ),
    ModelSpec(
        name           = "INT32_COMPILER_POND",
        description    = "32-bit integer specialised compiler. "
                         "Handles Add, Sub with CLA adder tile selection automatically.",
        version        = "1.1",
        category       = CAT_SYSTEM,
        inputs         = {"source": 0, "function_name": 0, "job_ref": 0},
        outputs        = {"cell_map": 0, "input_map": 0, "output_addrs": 0,
                          "status": 1, "depth": 32, "cell_count": 32},
        tiles_used     = [],
        pipeline_depth = 0,
        cell_count     = 0,
        operand_types  = ["int32"],
        metadata       = {
            "pond_type": "LIBRARY", "security": "HIDDEN",
            "permanent": True, "always_armed": True,
            "base_address": "0x00610000",
            "vm_module": "compiler_int32.Int32Compiler",
            "boot_tier": 3, "boot_order": 2,
        },
    ),
    ModelSpec(
        name           = "LLVM_COMPILER_POND",
        description    = "LLVM IR compiler. Optional — requires llvmlite.",
        version        = "1.1",
        category       = CAT_SYSTEM,
        inputs         = {"llvm_ir": 0, "job_ref": 0},
        outputs        = {"cell_map": 0, "status": 1, "depth": 32},
        tiles_used     = [],
        pipeline_depth = 0,
        cell_count     = 0,
        metadata       = {
            "pond_type": "LIBRARY", "security": "HIDDEN",
            "permanent": True, "always_armed": True,
            "base_address": "0x00620000",
            "vm_module": "llvm_ir_mapper.compile_ll",
            "boot_tier": 3, "boot_order": 3,
            "optional": True, "requires": "llvmlite",
        },
    ),
    ModelSpec(
        name           = "SEQUENCER_POND",
        description    = "Command table execution model. "
                         "Handles complex branching without dead cells.",
        version        = "1.1",
        category       = CAT_SYSTEM,
        inputs         = {"manifest": 0, "commands": 0, "job_ref": 0},
        outputs        = {"results": 0, "status": 1},
        tiles_used     = [],
        pipeline_depth = 0,
        cell_count     = 0,
        metadata       = {
            "pond_type": "LIBRARY", "security": "HIDDEN",
            "permanent": True, "always_armed": True,
            "base_address": "0x00630000",
            "vm_module": "sequencer.ProgramSequencer",
            "boot_tier": 3, "boot_order": 4,
        },
    ),
    ModelSpec(
        name           = "TILE_LIBRARY_POND",
        description    = "Core tile library — 40 pre-verified cell networks. "
                         "Read-only after boot. Shared across all compile jobs.",
        version        = "1.1",
        category       = CAT_SYSTEM,
        inputs         = {"tile_name": 0, "key_id": 0},
        outputs        = {"tile_spec": 0, "depth": 32, "cell_count": 32, "status": 1},
        tiles_used     = [],
        pipeline_depth = 0,
        cell_count     = 0,
        metadata       = {
            "pond_type": "LIBRARY", "security": "HIDDEN",
            "permanent": True, "always_armed": True,
            "base_address": "0x00640000",
            "vm_module": "fp_tiles.TileLibrary",
            "boot_tier": 3, "boot_order": 5,
            "tile_count": 40,
        },
    ),
    ModelSpec(
        name           = "MODEL_LIBRARY_POND",
        description    = "Composed model library. User-extendable. Shared read-only after boot.",
        version        = "1.1",
        category       = CAT_SYSTEM,
        inputs         = {"model_name": 0, "key_id": 0},
        outputs        = {"model_spec": 0, "depth": 32, "cell_count": 32, "status": 1},
        tiles_used     = [],
        pipeline_depth = 0,
        cell_count     = 0,
        metadata       = {
            "pond_type": "LIBRARY", "security": "HIDDEN",
            "permanent": True, "always_armed": True,
            "base_address": "0x00650000",
            "vm_module": "model_library.ModelLibrary",
            "boot_tier": 3, "boot_order": 6,
        },
    ),
    ModelSpec(
        name           = "PROGRAM_BUILDER_POND",
        description    = "Multi-file dependency walker and global address map.",
        version        = "1.1",
        category       = CAT_SYSTEM,
        inputs         = {"source_files": 0, "entry_point": 0, "job_ref": 0},
        outputs        = {"cell_map": 0, "address_map": 0, "status": 1},
        tiles_used     = [],
        pipeline_depth = 0,
        cell_count     = 0,
        metadata       = {
            "pond_type": "LIBRARY", "security": "HIDDEN",
            "permanent": True, "always_armed": True,
            "base_address": "0x00660000",
            "vm_module": "program_builder.ProgramBuilder",
            "boot_tier": 3, "boot_order": 7,
        },
    ),
]


# ── Module-level registry ─────────────────────────────────────────────────────

model_library = ModelLibrary()
for _spec in _BUILTIN_MODELS:
    model_library.register(_spec)
for _spec in _CORE_POND_MODELS:
    model_library.register(_spec)
