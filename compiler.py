import imago_log
"""
compiler.py — Python subset → ImagoIR → CellMapRecord list.

Supported Python subset (v0.1):
  - Integer literals 0 and 1
  - Variable assignment
  - Unary ops:  not, ~
  - Binary ops: &, |, ^, and, or
  - Comparison: ==, !=
  - If / else   (compiled as mux — both branches evaluated spatially)
  - Function definitions with return (inlined as spatial tiles)
  - Function calls (to functions defined in the same source)

Out of scope for v0.1 (see Implementation Guide milestones M5-M9):
  - Arithmetic (+, -, *, /)
  - While / for loops (requires loop unrolling pass)
  - Classes, generators, exceptions
  - Multi-bit integers (requires bit-vector extension)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIBRARY MODEL — SPATIAL ECONOMY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Imago compiler does not load libraries wholesale. It loads only what
the dependency graph actually references — nothing extraneous.

In conventional systems a library import loads the entire module regardless
of how much the program uses. In Imago the compiler knows exactly what will
be used before it writes a single cell. Every node in the dependency graph
is a real operation that will execute. Every node not in the graph is
definitionally absent — no cells, no addresses, no bus traffic, no power.

SPATIAL TILE LIBRARIES
  Libraries are collections of pre-compiled named cell-map fragments.
  Each tile is a self-contained functional unit with a known cell count,
  known input addresses, and known output addresses. The compiler:
    1. Scans the source file and builds the dependency graph
    2. Identifies which library tiles are actually referenced
    3. Places only those tiles into the array image
    4. Unreferenced tiles contribute zero cells, zero addresses, zero power

TILE REGISTRY
  The compiler maintains a tile_registry — a dict mapping function names
  to their compiled CellMapRecord lists. Frequently used operations are
  compiled once and placed by reference, not recompiled per call site.
  Each call site receives its own address-assigned placement copy (addresses
  must be unique per placement), but compilation work is done once.

BLOCK PACKING INTEGRATION
  Tiles from different libraries pack into the same 65,536-cell block per
  the block packing model in the Architecture specification. A math tile,
  a string tile, and a user function coexist in the same block with no
  wasted space. The compiler's free-cell map tracks available space per
  block and fills before allocating fresh blocks.

ZERO TREESHAKING PASS NEEDED
  Dead code elimination is structural — dead code is never placed, so it
  never needs to be removed. There is no separate treeshaking pass.
  The architecture makes it impossible to load what is not referenced.

SECURITY
  The security gate verifies each tile independently at load time. A
  compromised tile cannot affect co-resident tiles — address ranges
  assigned by the compiler never overlap, and the security gate rejects
  any config write that would violate this invariant.

PER-FILE COMPILATION UNIT
  Each source file is a compilation unit. The compiler scans the file,
  builds the dependency graph for that unit, resolves external references
  against the tile registry, and emits only the cells needed for that
  file's actual usage. This keeps individual images small, fast to load,
  and independently verifiable.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUTURE CONSIDERATION — SPATIAL PERSONALISATION AND FEATURE LICENSING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NOT IMPLEMENTED — recorded here for future development.

The tile-based compilation model enables a software distribution and
licensing approach that has no direct equivalent in conventional systems.

CONCEPT — PUBLISHER-SIDE FEATURE SELECTION
  A publisher compiles their application as a signed spatial tile library.
  Individual features are named, individually-signed tile collections.
  The publisher website presents a feature selector -- the user chooses
  what they need. The publisher generates a feature licence: a signed
  credential listing which tile groups the user may include, bound to
  their Imago identity hash. Stored in the credential vault of their cloud
  identity, encrypted with their biometric-derived key.

COMPILER BEHAVIOUR WITH FEATURE LICENCES
  When compiling against a licensed tile library the compiler reads the
  feature licence from the credential vault. For each tile it considers
  placing, it checks the licence signature against the publisher key.
  Permitted tiles are placed. Unpermitted tiles are absent -- not locked,
  not hidden, simply never written into the image. Enforcement is
  structural and happens once at compile time. No runtime licence check,
  no phone-home, no DRM mechanism is required or possible.

ADDING FEATURES LATER
  The user returns to the publisher site, selects the additional feature,
  and receives an updated licence. On next compilation the new tile group
  is placed alongside existing tiles. The image grows by exactly the cell
  count of the new feature tiles. Nothing else changes.

SECURITY PROPERTIES
  The compiled image is bound to the machine-unique key -- it cannot run
  on any other machine. The feature licence is bound to the user biometric
  identity -- it cannot be transferred. Licence sharing is structurally
  impossible. A stolen image is useless without the machine key. A stolen
  licence cannot produce a valid image on a different machine.

IMPLICATIONS FOR PUBLISHERS
  One tile library ships to all users. No platform variants, no version
  fragmentation. The licence is the product. Feature-granular pricing is
  enforced by the compiler, not by runtime checks. The application binary
  does not exist as a copyable object -- there is nothing to pirate.

IMPLICATIONS FOR USERS
  The personal image contains exactly the features purchased. Unpurchased
  features consume zero cells, zero power, and zero attack surface. The
  image grows incrementally as the licence grows, without reinstall.

IMPLEMENTATION REQUIREMENTS (future milestones)
  - Tile-level signing by publishers (per-tile ECDSA P-256 signatures)
  - Feature licence format and credential vault integration
  - Compiler licence verification pass before each tile placement
  - Publisher-side feature annotation: mapping user-visible features to
    named tile groups in the dependency graph
  - UI bridge between publisher feature selector and dependency resolver
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUTURE CONSIDERATION — CORPORATE TIERED LICENSING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NOT IMPLEMENTED — recorded here for future development.

The feature licensing model extends naturally to corporate deployments.
A site licence becomes a catalogue of feature licence tiers assigned
per employee identity by the IT administrator or publisher portal.

LICENCE TIERS (example: word processor)
  Basic     -- document creation, reading, basic formatting. Most staff.
  Standard  -- adds tables, styles, review tools, mail merge.
  Power     -- full feature set. Finance, legal, executives.
  Admin     -- full set plus tile library management for the organisation.

Each employee's licence credential is stored in their credential vault,
encrypted with their biometric key. Each compiles their own personal image
against the tile library with their own credential. No licence server
mediates execution -- enforcement happened at compile time, once.

REASSIGNMENT
  Employee leaves: credential vault revoked via cloud identity service.
  Image no longer loads. Licence tier freed for reassignment.
  New employee: licence credential issued, image compiled, ready.
  No software reinstall, no licence transfer, no audit complexity.

AUDIT
  Cloud identity service records licence tier per identity hash.
  Compiler records which tiles were placed per compilation.
  Security gate records each load event.
  Compliance queries are database queries, not machine surveys.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUTURE CONSIDERATION — DISTRIBUTED CLUSTER / MULTI-USER SPATIAL SHARING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NOT IMPLEMENTED — recorded here for future development.

The cluster model in the Architecture specification enables a spatial
equivalent of Unix timesharing -- but genuinely parallel rather than
time-sliced. Multiple users occupy separate cell regions simultaneously.
Their programs execute in parallel because they occupy different addresses.
There is no illusion of simultaneous use -- it is simultaneous use.

MULTI-USER SESSION MANAGEMENT
  Each authenticated user loads their personal image into an allocated
  array region. The OS Array Manager tracks regions per identity.
  The Session Manager tracks running regions independently.
  The start flag controller asserts and de-asserts per region.
  One user halting or freeing their region has no effect on any other.

THIN CLIENT / TERMINAL MODEL
  A lightweight client device handles I/O -- biometric authentication,
  display, and input via UniLink Wave or Prism. Compute runs in the
  cluster. The user's personal image spans both: I/O cells on the client
  device, compute cells in the cluster, connected transparently at the
  address level via UniLink Prism. From the user's perspective the
  session is continuous and local. From the hardware's perspective the
  compute is centralised and shared.

SHARED SPATIAL TILES
  In a multi-user cluster, a shared application tile library lives in
  a permanent region of the array. Multiple users' personal images
  address the same shared tile region simultaneously. User A and User B
  both run the same spell-check tile -- not their own copy of it, but
  the same physical cells at the same addresses. This is the shared
  library model implemented correctly: genuinely shared, not copied
  per process. Cell count for shared tiles is paid once regardless of
  how many users reference them.

CORPORATE COST MODEL
  Dense compute cluster replaces per-employee workstations. Cell capacity
  is shared across all active users dynamically. Light workloads use few
  cells. Heavy computations use more. Total capacity shared efficiently
  rather than sitting idle in individual machines. Session migration
  from desk to meeting room leaves compute in the cluster and changes
  only the I/O surface -- transparent to the user.

IMPLEMENTATION REQUIREMENTS (future milestones)
  - Multi-identity session management in the OS (one session per identity)
  - Per-identity region allocation and lifecycle tracking
  - Shared tile region model: one placement, many addressing identities
  - Thin client I/O bridge: Wave/Prism device as I/O surface for cluster
  - Corporate credential management: IT admin licence tier assignment
  - Cluster capacity scheduler: dynamic cell allocation across active users
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import ast
from typing import Optional
from ir import IRGraph, IRNode, lower_to_cell_map_v2
import time as _time
from gate_states import BINOP_MAP, BOOLOP_MAP, UNARYOP_MAP, COMPARE_MAP


# ── compiler ──────────────────────────────────────────────────────────────────

class ImagoCompiler:
    """
    Compiles a Python subset to a CellMapRecord list via ImagoIR.

    Usage:
        compiler = ImagoCompiler()
        records, graph = compiler.compile_source(python_source_code)
        region_id = controller.load_map(records, image_name="my_program")
    """

    # Default mapping from function name to tile operation name.
    # The compiler checks this before synthesising from scratch.
    # Covers the standard tile library operations.
    TILE_FUNCTION_MAP: dict[str, str] = {
        # 32-bit integer operations
        "int32_add":     "INT32_ADD",
        # int32_add_cla removed -- use int32_add (Kogge-Stone, ~548 cells)
        "int32_sub":     "INT32_SUB",
        "int32_eq":      "INT32_EQ",
        "int32_mux":     "INT32_MUX",
        # 32-bit floating point operations
        "fp32_add":     "FP32_ADD",
        "fp32_mul":     "FP32_MUL",
        "fp32_cmp_eq":  "FP32_CMP_EQ",
    }

    def __init__(self, tile_library=None, machine_key: int = 0xDEADC0DEBEEF1234,
                 fpga_target: str = "vm", cell_budget: int = None):
        """
        tile_library: optional TileLibrary instance.
          If provided, compile_function() checks the library for a
          matching tile before synthesising from the AST.
          On cache miss: synthesises, then saves to library.
        machine_key:  used to sign newly compiled tiles saved to the library.
        fpga_target:  "vm", "icebreaker", "icestick", "basys3",
                      "orangecrab", "kintex7", or "custom".
          compile_function() warns if the compiled program exceeds the
          target's cell budget. Stored in .output_map for .icm export.
        cell_budget:  override default budget for the target.
        """
        _FPGA_BUDGETS = {
            "vm": None, "icebreaker": 64, "icestick": 16,
            "basys3": 256, "orangecrab": 256, "kintex7": 1500,
        }
        self.fpga_target = fpga_target
        self.cell_budget = (cell_budget if cell_budget is not None
                            else _FPGA_BUDGETS.get(fpga_target))

        self._graph: Optional[IRGraph] = None
        self._scope: dict[str, str]   = {}
        self._functions: dict[str, ast.FunctionDef] = {}
        self._inline_depth = 0
        self._max_inline_depth = 8

        # Tile library integration
        self._tile_library = tile_library
        self._machine_key  = machine_key

        # Maturation curve statistics
        self.tile_cache_hits:   int   = 0    # compilations served from library
        self.tile_cache_misses: int   = 0    # compilations synthesised fresh
        self.time_saved_ms:     float = 0.0  # estimated ms saved by cache hits
        self._model_segment_spans: list = []  # set by last compile_function call

        # Extra records emitted directly (loops, feedback cells).
        # Merged with lower_to_cell_map_v2() output at compile_source() time.
        self._extra_records: list = []

        # When compiling a loop body, this holds the body-entry IRNode so
        # that _compile_constant can derive constants from the body signal
        # rather than pre-loaded INPUT nodes (which only fire once at start).
        self._loop_body_entry: object = None

    # ── public entry point ────────────────────────────────────────────────────

    def compile_source(
        self,
        source: str,
        function_name: Optional[str] = None
    ) -> tuple[list, IRGraph]:
        """
        Compile Python source to a (CellMapRecord list, IRGraph) pair.

        If function_name is given, compiles only that function.
        Otherwise compiles the module-level statements.

        Returns (records, graph) — records is the list to pass to
        controller.load_map(), graph is the IR for inspection.
        """
        tree = ast.parse(source)
        self._graph = IRGraph(name=function_name or "module")
        self._scope = {}
        self._functions = {}
        self._extra_records = []            # loop feedback cells etc.
        self._extra_storage_addresses = {}  # loop var name -> storage_addr

        # first pass: collect all function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._functions[node.name] = node

        if function_name:
            if function_name not in self._functions:
                raise ValueError(
                    f"Function '{function_name}' not found in source"
                )
            result_node = self._compile_function_body(
                self._functions[function_name],
                args={}
            )
        else:
            # compile module-level statements
            result_node = None
            for stmt in tree.body:
                if not isinstance(stmt, ast.FunctionDef):
                    result_node = self._compile_stmt(stmt)

        # v2: use single-cell binary ops lowering (preloaded-A pattern, no relay cells)
        from ir import lower_to_cell_map_v2
        _v2_records, _v2_stats = lower_to_cell_map_v2(self._graph)
        records = _v2_records + self._extra_records
        self.second_inputs_map = _v2_stats.get("second_inputs_map", {})
        self._ir_preload_map   = _v2_stats.get("preload_map", {})
        return records, self._graph

    def scan_function(self, source: str, function_name: str) -> dict:
        """
        Pre-compilation scan: identify inputs, output name, and loop variables
        without emitting any cells. Used to prompt the user for port names
        before the full compile pass runs.

        Returns:
          {
            "inputs":     ["a", "b"],           # param names in order
            "output":     "result" | None,       # return var name if simple
            "loop_vars":  ["n"],                 # while/for loop variables
            "found":      True,
          }
        """
        import ast as _ast
        try:
            tree = _ast.parse(source)
        except SyntaxError as e:
            return {"found": False, "error": str(e)}

        fn = None
        for node in _ast.walk(tree):
            if isinstance(node, _ast.FunctionDef) and node.name == function_name:
                fn = node
                break

        if fn is None:
            return {"found": False,
                    "error": f"Function '{function_name}' not found in source"}

        # Inputs: function parameters with type annotations
        inputs = []
        input_types = {}
        for arg in fn.args.args:
            inputs.append(arg.arg)
            ann = getattr(arg.annotation, 'id', None) if arg.annotation else None
            input_types[arg.arg] = ann.lower() if ann else "numeric"

        # Return type annotation
        return_type = None
        if fn.returns is not None:
            return_type = getattr(fn.returns, 'id', None)
            if return_type:
                return_type = return_type.lower()

        # Output: return variable name if the last (or only) return is a simple Name
        output = None
        for node in _ast.walk(fn):
            if isinstance(node, _ast.Return) and node.value is not None:
                if isinstance(node.value, _ast.Name):
                    output = node.value.id

        # Loop variables: targets of For/While loops
        loop_vars = []
        for node in _ast.walk(fn):
            if isinstance(node, _ast.For):
                if isinstance(node.target, _ast.Name):
                    loop_vars.append(node.target.id)
            elif isinstance(node, _ast.While):
                # While loop variable is typically an assign inside the body
                for stmt in node.body:
                    if isinstance(stmt, _ast.Assign):
                        for t in stmt.targets:
                            if isinstance(t, _ast.Name) and t.id not in inputs:
                                if t.id not in loop_vars:
                                    loop_vars.append(t.id)

        return {
            "found":       True,
            "inputs":      inputs,
            "input_types": input_types,
            "output":      output,
            "return_type": return_type,
            "loop_vars":   loop_vars,
        }

    def compile_function(
        self,
        source: str,
        function_name: str,
        input_names: list[str],
        port_names: dict = None,
    ) -> tuple[list, "IRGraph", dict, list]:
        """
        Compile a named function, returning:
          - CellMapRecord list
          - IRGraph
          - input_address_map: {param_name: bus_address}
            Also includes loop storage addresses: the caller must inject
            the initial value of each loop variable before calling run().
            e.g. for 'while n: n = n - 1', input_map includes {'n': storage_addr}
          - output_addresses:  [bus_address, ...]

        The caller uses input_address_map to know where to inject
        input values before calling controller.run().
        """
        tree = ast.parse(source)
        self._graph = IRGraph(name=function_name)
        self._scope = {}
        self._functions = {}
        self._extra_records = []            # loop feedback cells etc.
        self._extra_storage_addresses = {}  # loop var name -> storage_addr

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._functions[node.name] = node

        if function_name not in self._functions:
            raise ValueError(f"Function '{function_name}' not found in source")

        fn = self._functions[function_name]

        # ── Type annotations → gate_state type bits + complement cells ────────
        # Supported annotations: signed, datetime, alpha (str), numeric (default)
        # Each typed port gets a primary cell + complement cell (addr, addr+1)
        # forming a 64-bit typed word. The type bits are stored in type_map
        # for use by the workspace, PTT registration, and .icm output.
        import ast as _ast
        from gate_states import (GS_TYPE_NUMERIC, GS_TYPE_SIGNED,
                                 GS_TYPE_ALPHA, GS_TYPE_DATETIME, GS_TYPE_NAMES)

        TYPE_ANNOTATION_MAP = {
            "signed":   GS_TYPE_SIGNED,
            "int64":    GS_TYPE_SIGNED,
            "datetime": GS_TYPE_DATETIME,
            "date":     GS_TYPE_DATETIME,
            "alpha":    GS_TYPE_ALPHA,
            "str":      GS_TYPE_ALPHA,
            "string":   GS_TYPE_ALPHA,
            "numeric":  GS_TYPE_NUMERIC,
            "int32":    GS_TYPE_NUMERIC,   # handled by Int32Compiler, noted here
            "uint32":   GS_TYPE_NUMERIC,
        }

        self._type_map: dict = {}  # {param_name: gs_type_bits}

        # create input nodes for each parameter
        input_map: dict[str, int] = {}
        for arg in fn.args.args:
            name = arg.arg
            node = self._graph.add_input(name)
            self._scope[name] = node.node_id
            input_map[name] = node.output_addr

            # Read type annotation and record
            ann_type = GS_TYPE_NUMERIC
            if arg.annotation is not None and isinstance(arg.annotation, _ast.Name):
                ann_type = TYPE_ANNOTATION_MAP.get(arg.annotation.id.lower(),
                                                   GS_TYPE_NUMERIC)
            self._type_map[name] = ann_type

            # Allocate complement cell for 64-bit types (signed, datetime)
            # Alpha strings use sequential cells but don't need a fixed complement
            if ann_type in (GS_TYPE_SIGNED, GS_TYPE_DATETIME):
                comp_node = self._graph.add_input(f"_{name}_hi")
                input_map[f"_{name}_hi"] = comp_node.output_addr
                self._type_map[f"_{name}_hi"] = ann_type

        # Read return type annotation
        return_type = GS_TYPE_NUMERIC
        if fn.returns is not None and isinstance(fn.returns, _ast.Name):
            return_type = TYPE_ANNOTATION_MAP.get(fn.returns.id.lower(),
                                                  GS_TYPE_NUMERIC)
        self._return_type = return_type

        # compile the function body
        result_node = self._compile_function_body(fn, args={})

        # Merge loop storage addresses into input_map.
        # Constants store (addr, val) tuples -- extract addr for imap, val for injection.
        self.known_values: dict = {}   # {bus_addr: value} -- auto-injected at start()
        for k, v in self._extra_storage_addresses.items():
            if isinstance(v, tuple):
                addr, val = v
                input_map[k] = addr
                self.known_values[addr] = val   # register for auto-injection
            else:
                input_map[k] = v

        output_addresses = []
        output_name = "output"
        if result_node:
            output_addresses = [result_node.output_addr]
            # Try to recover return variable name from the IR node label
            if hasattr(result_node, 'name') and result_node.name:
                output_name = result_node.name

        # Apply port_names overrides: rename inputs and output in the maps.
        # port_names = {"a": "input_a", "output": "sum"} etc.
        # This is how the CLI/workbench lets the user confirm or rename ports
        # before the .icm is written — names become PTT entries.
        if port_names:
            renamed_map = {}
            for orig_name, addr in input_map.items():
                new_name = port_names.get(orig_name, orig_name)
                renamed_map[new_name] = addr
            input_map = renamed_map
            if "output" in port_names:
                output_name = port_names["output"]

        # Build output_map: {name: addr} — single output for now
        output_map = {}
        if output_addresses:
            output_map[output_name] = output_addresses[0]
            # Allocate complement cell for 64-bit return types
            if self._return_type in (GS_TYPE_SIGNED, GS_TYPE_DATETIME):
                # Reserve the next address as the complement output
                comp_addr = output_addresses[0] + 1
                output_map[f"_{output_name}_hi"] = comp_addr
        self.output_map = output_map   # expose for callers

        # Expose type information for callers (workspace, PTT registration, .icm)
        self.type_map    = getattr(self, '_type_map', {})
        self.return_type = getattr(self, '_return_type', GS_TYPE_NUMERIC)
        # input_types: clean dict of {param_name: type_name_str} for .icm
        self.input_types  = {k: GS_TYPE_NAMES.get(v, "numeric")
                             for k, v in self.type_map.items()
                             if not k.startswith('_')}
        self.output_types = {output_name: GS_TYPE_NAMES.get(self.return_type, "numeric")}

        # ── Tile library lookup ──────────────────────────────────────────────
        if self._tile_library is not None:
            tile_name = self.TILE_FUNCTION_MAP.get(function_name.lower())
            if tile_name is not None:
                tile_result = self._try_tile_placement(
                    tile_name, input_map, output_addresses)
                if tile_result is not None:
                    records, input_map, output_addresses = tile_result
                    self.tile_cache_hits += 1
                    return records, self._graph, input_map, output_addresses
            self.tile_cache_misses += 1

        # v2: use single-cell binary ops lowering
        # lower_to_cell_map_v2 returns (records, stats) where records are CellRecord_v2
        # which are backward-compatible with load_map (both have same fields)
        from ir import lower_to_cell_map_v2
        _v2_records, _v2_stats = lower_to_cell_map_v2(self._graph)
        records = _v2_records + self._extra_records
        self.second_inputs_map = _v2_stats.get("second_inputs_map", {})
        self._ir_preload_map   = _v2_stats.get("preload_map", {})

        # ── Model library instantiation ──────────────────────────────────────
        self._model_segment_spans = []
        model_result = self._instantiate_model_ops(
            self._graph, records, input_map, output_addresses)
        if model_result is not None:
            records, input_map, output_addresses, self._model_segment_spans = (
                model_result)

        if self._tile_library is not None:
            tile_name = self.TILE_FUNCTION_MAP.get(function_name.lower())
            if tile_name is not None:
                self._save_to_library(tile_name, records, input_map,
                                      output_addresses)

        # FPGA target budget check — after all records are finalised
        cell_count = len(records)
        if self.cell_budget is not None and cell_count > self.cell_budget:
            import imago_log as _il
            _il.warn(
                f"[COMPILER] ⚠ '{function_name}' compiles to {cell_count} cells "
                f"but target '{self.fpga_target}' budget is {self.cell_budget}. "
                f"Program is VM-only — will not fit on hardware."
            )
        self.compiled_cell_count = cell_count
        self.fits_target = (self.cell_budget is None or cell_count <= self.cell_budget)

        return records, self._graph, input_map, output_addresses

    # ── model library instantiation ─────────────────────────────────────────

    def _instantiate_model_ops(self,
                                graph,
                                records: list,
                                input_map: dict,
                                output_addresses: list) -> Optional[tuple]:
        """
        Scan the IR graph for MODEL:* nodes and instantiate them.

        For each MODEL:* node:
          1. Look up the ModelSpec in the model library
          2. Place the model at a fresh base address
          3. Assign it a dedicated bus segment (isolates simultaneous
             NOT cell emissions — same isolation used by fp_tiles)
          4. Map function parameters → model input port addresses
          5. Wire each output bit through a PASS cell → fresh return addr

        Returns (records, input_map, output_addresses, segment_spans) if any
        models were found, else None.

        segment_spans: [(start_idx, end_idx, seg_id), ...] — caller must
        provision segments and assign cells before running.
        """
        from model_library import model_library
        from gate_states import GS_PASS
        from controller import CellMapRecord

        model_nodes = [n for n in graph.nodes if n.operation.startswith("MODEL:")]
        if not model_nodes:
            return None

        all_records   = list(records)
        new_input_map = dict(input_map)
        new_output_addresses = list(output_addresses)
        segment_spans = []
        next_seg_id   = 1
        model_base    = 0x00400000

        for node in model_nodes:
            model_name = node.operation[len("MODEL:"):]
            spec = model_library.get(model_name)
            if spec is None:
                imago_log.info(f"[COMPILER] Warning: model '{model_name}' not found")
                continue

            span_start = len(all_records)
            instance   = spec.place(base_address=model_base)
            all_records.extend(instance.records)
            model_base += len(instance.records) * 2
            span_end    = len(all_records)
            segment_spans.append((span_start, span_end, next_seg_id))
            next_seg_id += 1

            # Map parameters → input port addresses (positional)
            param_names = [n.node_id for n in graph.input_nodes()]
            for i, port_name in enumerate(spec.inputs.keys()):
                if i < len(param_names):
                    addrs = instance.input_addresses(port_name)
                    if addrs:
                        new_input_map[param_names[i]] = addrs[0]

            # Wire every output bit through an individual PASS cell
            out_port = list(spec.outputs.keys())[0] if spec.outputs else None
            if out_port:
                out_addrs = instance.output_addresses(out_port)
                if out_addrs:
                    return_addresses = []
                    for out_bit_addr in out_addrs:
                        ret_addr = model_base
                        model_base += 1
                        all_records.append(
                            CellMapRecord(GS_PASS, out_bit_addr, ret_addr))
                        return_addresses.append(ret_addr)
                    new_output_addresses = return_addresses

            imago_log.info(f"[COMPILER] Model instantiated: {model_name} "
                  f"@ 0x{instance.base_address:08X} "
                  f"({instance.cell_count} cells, depth {spec.pipeline_depth}, "
                  f"seg {next_seg_id - 1})")

        return all_records, new_input_map, new_output_addresses, segment_spans

    # ── tile library helpers ─────────────────────────────────────────────────

    def _try_tile_placement(self, tile_name: str,
                             input_map: dict,
                             output_addresses: list) -> Optional[tuple]:
        """
        Attempt to place a tile from the library.

        Returns (records, new_input_map, new_output_addresses) on success.
        Returns None if the tile is not in the library or placement fails.

        Q5 — Explicit return path (Compiler System Definition v0.2 §4.4):
        After the tile's OUTBOUND bridge, a PASS cell is emitted:
          input_address  = tile out[0]  (OUTBOUND bridge address)
          output_address = return_addr  (freshly allocated address)
        Code after the call reads from return_addr. The tile pipeline is:
          INBOUND → compute chain → OUTBOUND → PASS → return_addr
        The return pointer is now explicit and visible in the cell map.
        """
        from fp_tiles import TilePlacer
        try:
            tile = self._tile_library.get(tile_name)
        except KeyError:
            return None

        # Tile found — place it at a fresh address region
        placer = TilePlacer(base_address=0x00200000)
        records, in_a, in_b, out, _ = placer.place(tile)

        # Rebuild input_map to use the tile's placed addresses.
        param_names = list(input_map.keys())
        new_input_map = {}
        n_a = len(in_a)
        n_b = len(in_b)

        if len(param_names) >= 1 and n_a > 0:
            new_input_map[param_names[0]] = in_a[0]
        if len(param_names) >= 2 and n_b > 0:
            new_input_map[param_names[1]] = in_b[0]

        # Q5: Explicit PASS return cell from tile OUTBOUND → return_addr.
        if out:
            from gate_states import GS_PASS
            from controller import CellMapRecord
            return_addr = self._graph._alloc.alloc()
            records = list(records) + [CellMapRecord(GS_PASS, out[0], return_addr)]
            new_output_addresses = [return_addr]
        else:
            new_output_addresses = output_addresses

        # Estimated time saved vs synthesis
        self.time_saved_ms += tile.metadata.pipeline_depth * 0.01

        imago_log.info(f"[COMPILER] Tile cache hit: {tile_name} "
              f"({tile.metadata.cell_count} cells, "
              f"depth {tile.metadata.pipeline_depth})")
        return records, new_input_map, new_output_addresses

    def _save_to_library(self, tile_name: str, records: list,
                          input_map: dict, output_addresses: list):
        """
        Save a freshly synthesised function to the tile library.
        Called on cache miss when the function maps to a known tile name.
        The library grows — next compilation of this function is a cache hit.
        """
        from fp_tiles import Tile, TileMetadata, _TILE_TIERS
        from controller import CellMapRecord
        # Build a minimal Tile from the synthesised records
        tile = Tile(
            records  = records,
            in_a     = list(input_map.values())[:1],
            in_b     = list(input_map.values())[1:2],
            out      = output_addresses[:1],
            metadata = TileMetadata(
                operation      = tile_name,
                precision      = 32,
                pipeline_depth = len(records),   # approximation
                cell_count     = len(records),
                notes          = "Auto-saved by compiler on first synthesis.",
            )
        )
        try:
            import tempfile, os
            tier = _TILE_TIERS.get(tile_name, "BASE")
            # Save to library cache (in-memory for simulator)
            self._tile_library._cache[tile_name] = tile
            imago_log.info(f"[COMPILER] Tile saved to library: {tile_name} "
                  f"({len(records)} cells)")
        except Exception as e:
            pass  # Library save failure is non-fatal

    def cache_stats(self) -> dict:
        """Return tile cache statistics (the maturation curve)."""
        total = self.tile_cache_hits + self.tile_cache_misses
        hit_rate = (self.tile_cache_hits / total * 100) if total > 0 else 0.0
        return {
            "cache_hits":    self.tile_cache_hits,
            "cache_misses":  self.tile_cache_misses,
            "hit_rate_pct":  round(hit_rate, 1),
            "time_saved_ms": round(self.time_saved_ms, 2),
        }

    # ── statement compilation ─────────────────────────────────────────────────

    def _compile_stmt(self, stmt) -> Optional[IRNode]:
        """Compile one statement. Returns the result node if any."""
        if isinstance(stmt, ast.Assign):
            return self._compile_assign(stmt)
        elif isinstance(stmt, ast.Return):
            return self._compile_expr(stmt.value)
        elif isinstance(stmt, ast.If):
            return self._compile_if(stmt)
        elif isinstance(stmt, ast.While):
            return self._compile_while(stmt)
        elif isinstance(stmt, ast.For):
            return self._compile_for(stmt)
        elif isinstance(stmt, ast.AugAssign):
            return self._compile_augassign(stmt)
        elif isinstance(stmt, ast.Expr):
            return self._compile_expr(stmt.value)
        elif isinstance(stmt, ast.FunctionDef):
            # already collected — skip at compile time
            return None
        elif isinstance(stmt, ast.Pass):
            return None   # no-op — valid in for/while bodies
        else:
            raise NotImplementedError(
                f"Statement type '{type(stmt).__name__}' not supported. "
                f"Supported: assignment, return, if/else, while, for, expressions."
            )

    def _compile_assign(self, stmt: ast.Assign) -> IRNode:
        """Compile: var = expr"""
        value_node = self._compile_expr(stmt.value)
        # bind each target name to this node
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                self._scope[target.id] = value_node.node_id
            else:
                raise NotImplementedError(
                    f"Assignment target '{type(target).__name__}' not supported. "
                    f"Only simple variable names supported in v0.1."
                )
        return value_node

    def _compile_if(self, stmt: ast.If) -> Optional[IRNode]:
        """
        Compile if/else as a spatial mux.

        Both branches are evaluated (spatially parallel — both regions
        exist in the array simultaneously). The condition selects which
        result is passed forward. This is the architecture's conditional
        model: not a jump, but a routing decision at a mux cell.

        If there is no else branch, the if body result is passed through
        or held at the pre-if value (v0.1 limitation: requires else).
        """
        # compile condition
        cond_node = self._compile_expr(stmt.test)

        # save scope, compile true branch
        scope_before = dict(self._scope)
        true_result = None
        for s in stmt.body:
            true_result = self._compile_stmt(s)
        scope_after_true = dict(self._scope)

        if not stmt.orelse:
            # if without else: variables assigned in the true branch get a
            # mux against their pre-if values. If cond is True, new value
            # is used; if False, the pre-if value is held.
            # Implements: x = (cond AND new_x) OR (NOT cond AND old_x)
            not_cond = self._graph.add_node("NOT", [cond_node.node_id],
                                             comment="NOT cond (if-no-else)")
            true_assigned = {k for k in scope_after_true
                             if scope_after_true.get(k) != scope_before.get(k)}
            self._scope = dict(scope_before)
            for var in true_assigned:
                old_node_id = scope_before.get(var)
                new_node_id = scope_after_true[var]
                if old_node_id is None:
                    # Variable only exists in true branch — keep it if cond
                    self._scope[var] = new_node_id
                    continue
                true_arm  = self._graph.add_node(
                    "AND", [new_node_id, cond_node.node_id],
                    comment=f"{var} * cond")
                false_arm = self._graph.add_node(
                    "AND", [old_node_id, not_cond.node_id],
                    comment=f"{var}_old * NOT cond")
                mux_out   = self._graph.add_node(
                    "OR", [true_arm.node_id, false_arm.node_id],
                    comment=f"mux {var} (if-no-else)")
                self._scope[var] = mux_out.node_id
            return None   # no single result node for if-only

        # restore scope, compile false branch
        self._scope = dict(scope_before)
        false_result = None
        for s in stmt.orelse:
            false_result = self._compile_stmt(s)
        scope_after_false = dict(self._scope)

        if true_result is None or false_result is None:
            return None

        # mux: if cond then true_result else false_result
        # Implemented as: (true AND cond) OR (false AND NOT cond)
        not_cond  = self._graph.add_node("NOT", [cond_node.node_id],
                                          comment="NOT condition for mux")
        true_arm  = self._graph.add_node("AND",
                                          [true_result.node_id,  cond_node.node_id],
                                          comment="true branch * condition")
        false_arm = self._graph.add_node("AND",
                                          [false_result.node_id, not_cond.node_id],
                                          comment="false branch * NOT condition")
        mux_out   = self._graph.add_node("OR",
                                          [true_arm.node_id, false_arm.node_id],
                                          comment="mux output")

        # Update scope: variables assigned in BOTH branches now point to mux_out.
        # Variables assigned in only one branch retain their pre-if value.
        # Variables not assigned in either branch are unchanged.
        self._scope = dict(scope_before)
        true_assigned  = {k for k in scope_after_true  if scope_after_true.get(k)  != scope_before.get(k)}
        false_assigned = {k for k in scope_after_false if scope_after_false.get(k) != scope_before.get(k)}
        both_assigned  = true_assigned & false_assigned
        for var in both_assigned:
            self._scope[var] = mux_out.node_id

        return mux_out

    # ── while loop compilation ───────────────────────────────────────────────

    def _compile_augassign(self, stmt: ast.AugAssign) -> "IRNode":
        """Compile x op= expr  →  x = x op expr. Supports +=,-=,&=,|=,^="""
        import ast as _ast
        if not isinstance(stmt.target, _ast.Name):
            raise NotImplementedError("AugAssign target must be a simple variable.")
        var_name = stmt.target.id
        if var_name not in self._scope:
            raise NameError(f"Variable {var_name!r} used before assignment.")
        synthetic = _ast.BinOp(left=_ast.Name(id=var_name, ctx=_ast.Load()),
            op=stmt.op, right=stmt.value)
        _ast.copy_location(synthetic, stmt); _ast.fix_missing_locations(synthetic)
        result = self._compile_expr(synthetic)
        self._scope[var_name] = result.node_id
        return result

    def _compile_for(self, stmt: ast.For) -> Optional[IRNode]:
        """
        Compile a for loop: for i in range(n).

        Two paths depending on whether n is a compile-time literal or variable:

        SHIFT path (n is a literal <= 32):
          Uses COUNTER_SHIFT_n — a pure PASS chain, no arithmetic.
          One-hot step outputs drive the body once per step.
          If the loop variable is used in the body, a priority encoder
          converts one-hot to binary (i = 0..n-1).
          Body is compiled once; each step output gates it via AND.

        RIPPLE path (n > 32 or n is a variable):
          Uses COUNTER_RIPPLE_8 or COUNTER_RIPPLE_32.
          TICK is fed back each iteration; DONE exits the loop.
          The current VALUE output provides i to the body each iteration.

        In both cases the loop variable name is added to scope so the body
        can reference it. After the loop, the variable holds its last value.

        Only for i in range(n) is supported. Other iterables raise NotImplementedError.
        """
        import ast as _ast
        from controller import CellMapRecord
        from gate_states import GS_PASS

        # ── Validate: must be `for <var> in range(<n>)` ──────────────────
        if not isinstance(stmt.target, _ast.Name):
            raise NotImplementedError(
                "for loop target must be a simple variable name "
                "(e.g. 'for i in range(n)')"
            )
        loop_var = stmt.target.id

        if (not isinstance(stmt.iter, _ast.Call) or
                not isinstance(stmt.iter.func, _ast.Name) or
                stmt.iter.func.id != "range" or
                len(stmt.iter.args) != 1):
            raise NotImplementedError(
                "for loop iterator must be range(n) with a single argument. "
                "Only 'for i in range(n)' is supported."
            )

        range_arg = stmt.iter.args[0]

        # ── Determine n and which counter to use ─────────────────────────
        if isinstance(range_arg, _ast.Constant) and isinstance(range_arg.value, int):
            n = range_arg.value
            if n <= 0:
                return None   # empty range — compile nothing
            use_shift = (n <= 32)
        elif isinstance(range_arg, _ast.Name):
            n = None           # runtime value
            use_shift = False
        else:
            raise NotImplementedError(
                "range() argument must be an integer literal or a variable name"
            )

        # ── SHIFT path: fixed small range ────────────────────────────────
        if use_shift:
            return self._compile_for_shift(stmt, loop_var, n)

        # ── RIPPLE path: variable or large range ─────────────────────────
        return self._compile_for_ripple(stmt, loop_var, range_arg)

    def _compile_for_shift(self, stmt, loop_var: str, n: int) -> Optional[IRNode]:
        """
        Compile for i in range(n) using COUNTER_SHIFT_n.

        The shift counter emits n sequential one-hot pulses, one per tick.
        For each step k, step[k] fires once. We AND each step output with
        the body computation — effectively running the body n times with i=k.

        If the body does not reference the loop variable, we just need
        to run the body n times (all step outputs are equivalent triggers).
        If the body uses i, we build a binary encoder from the step outputs.

        The final result is the last body output (step n-1 drives the last
        body computation).
        """
        from controller import CellMapRecord
        from gate_states import GS_PASS

        # Pick smallest shift counter that fits n
        for size in (4, 8, 16, 32):
            if size >= n:
                tile_name = f"COUNTER_SHIFT_{size}"
                break
        else:
            raise ValueError(f"n={n} exceeds max shift counter size 32")

        # Allocate shift counter tile addresses in IR
        # The counter itself is managed outside the IR graph (raw records)
        counter_base = self._graph._alloc.alloc_block(size + 2)
        tick_addr    = counter_base
        step_addrs   = [counter_base + 1 + k for k in range(size)]
        done_addr    = counter_base + 1 + size

        # Emit raw PASS chain records (the shift counter)
        for k in range(size + 1):
            src_addr = counter_base + k
            dst_addr = counter_base + k + 1
            rec = CellMapRecord(GS_PASS, src_addr, dst_addr)
            self._extra_records.append(rec)

        # Expose tick_addr so caller can inject a 1 to start the counter
        self._extra_storage_addresses[f"_for_{loop_var}_tick"] = tick_addr

        # Build a binary encoder if i is referenced in the body
        # Check by scanning body AST for the loop variable name
        body_uses_i = any(
            isinstance(node, __import__('ast').Name) and node.id == loop_var
            for s in stmt.body
            for node in __import__('ast').walk(s)
        )

        if body_uses_i:
            # Priority encoder: binary i from one-hot step outputs.
            # Built entirely from raw CellMapRecords (no IR nodes) to
            # avoid creating graph nodes with empty input lists.
            # i[bit] = OR of all step[k] where bit `bit` of k is set.
            import math
            from gate_states import GS_NOT, GS_NOR
            nbits = max(1, math.ceil(math.log2(n + 1)))
            enc_bits = []
            for bit in range(nbits):
                contributing = [step_addrs[k] for k in range(n) if (k >> bit) & 1]
                if not contributing:
                    # Bit never set for any step — constant 0 input node
                    zero_node = self._graph.add_input(f"_for_{loop_var}_bit{bit}_zero")
                    enc_bits.append(zero_node.output_addr)
                elif len(contributing) == 1:
                    enc_bits.append(contributing[0])
                else:
                    # OR-reduce: OR(a,b) = NOR(NOT(a), NOT(b))
                    # Use NOR gate: GS_NOR with two inputs
                    cur = contributing[0]
                    for other in contributing[1:]:
                        not_a   = self._graph._alloc.alloc()
                        not_b   = self._graph._alloc.alloc()
                        or_out  = self._graph._alloc.alloc()
                        # NOT(a): NOR(a,a) — GS_NOT fires on input cur
                        self._extra_records.append(
                            CellMapRecord(GS_NOT, cur,   not_a))
                        # NOT(b): NOR(b,b)
                        self._extra_records.append(
                            CellMapRecord(GS_NOT, other, not_b))
                        # NOR(NOT_a, NOT_b) = OR(a,b)
                        # Represent as two-stage: pass not_a, OR with not_b
                        # Simpler: OR(a,b) via NOR(NOT a, NOT b)
                        # We wire it as a NOT of (NOT_a NOR NOT_b)
                        nor_mid = self._graph._alloc.alloc()
                        self._extra_records.append(
                            CellMapRecord(GS_NOT, not_a, nor_mid))
                        # Second NOT to combine: nor_mid OR not_b
                        self._extra_records.append(
                            CellMapRecord(GS_NOT, not_b, or_out))
                        cur = or_out
                    enc_bits.append(cur)

            # IR input node for loop var pointing to bit 0 of encoder output
            i_node = self._graph.add_input(f"_for_{loop_var}")
            i_node.output_addr = enc_bits[0]
            self._scope[loop_var] = i_node.node_id
        else:
            # Body doesn't use i — use step[0] as the loop variable placeholder
            i_node = self._graph.add_input(f"_for_{loop_var}")
            i_node.output_addr = step_addrs[0]
            self._scope[loop_var] = i_node.node_id

        # Compile the body once — it will be gated by each step output
        last_result = None
        for s in stmt.body:
            last_result = self._compile_stmt(s)

        # The "return value" of the for loop is the last body result
        # gated by the DONE signal (so downstream code sees it after loop)
        if last_result is not None:
            done_node = self._graph.add_input(f"_for_{loop_var}_done")
            done_node.output_addr = done_addr
            gated = self._graph.add_node(
                "AND", [last_result.node_id, done_node.node_id],
                comment=f"for {loop_var} body gated by DONE")
            return gated

        # No body result — return done signal itself
        done_node = self._graph.add_input(f"_for_{loop_var}_done")
        done_node.output_addr = done_addr
        return done_node

    def _compile_for_ripple(self, stmt, loop_var: str,
                            range_arg) -> Optional[IRNode]:
        """
        Compile for i in range(n) using COUNTER_RIPPLE_8.

        Architecture:
          - COUNTER_RIPPLE_8 tile placed at a fresh base address
          - in_a[0] = tick input: a PASS cell feeds back from body completion
          - in_b[0-7] = limit bits: injected by caller as constant
          - out[0-7] = value bits: bound to loop variable i
          - out[8] = done signal: when value == limit, loop exits

        Loop mechanics:
          1. Caller injects limit bits (the range argument) before run()
          2. Initial tick is injected to start the first iteration
          3. Body executes with i = current counter value
          4. Body completion triggers next tick via PASS feedback cell
          5. Counter increments, new value available as i
          6. When done fires, loop exits

        The limit is exposed in the input_map as _for_{var}_limit
        so the caller can inject it.
        """
        import ast as _ast
        from controller import CellMapRecord
        # BLOCKED: GS_SELECT and LOOP_MODE are retired from the silicon.
        # While loop compilation needs a new branch design before this works.
        # See sessions/2026-05-17-python-audit.md — branch design pending.
        raise NotImplementedError(
            "_compile_while: GS_SELECT and LOOP_MODE retired. "
            "Branch design needed — see sessions/2026-05-17-python-audit.md"
        )
        # unreachable — original code below preserved for design reference:
        from gate_states import GS_PASS, GS_SELECT, LOOP_MODE  # noqa: F401
        from fp_tiles import TilePlacer

        bits = 8

        # ── Resolve the limit value ───────────────────────────────────────
        # If range_arg is a constant integer we know it at compile time.
        # If it's a variable, we expose limit_addrs in the input_map.
        limit_const = None
        if isinstance(range_arg, _ast.Constant) and isinstance(range_arg.value, int):
            limit_const = range_arg.value & 0xFF

        # ── Place COUNTER_RIPPLE_8 tile ───────────────────────────────────
        if self._tile_library is None:
            raise RuntimeError(
                "for loop ripple requires a tile library. "
                "Pass tile_library=TileLibrary() to ImagoCompiler()."
            )

        tile = self._tile_library.get("COUNTER_RIPPLE_8")
        base = self._graph._alloc.alloc_block(tile.metadata.cell_count * 4)
        placer = TilePlacer(base_address=base)
        records, in_a, in_b, out, _ = placer.place(tile)
        self._extra_records.extend(records)

        tick_addr   = in_a[0]       # pulse here to increment
        limit_addrs = in_b          # 8 bits: when value==limit, done fires
        value_addrs = out[:8]       # 8 bits: current counter value
        done_addr   = out[8]        # 1 bit: high when value == limit

        # ── Inject limit constant if known ───────────────────────────────
        if limit_const is not None:
            for bit, laddr in enumerate(limit_addrs):
                bit_val = (limit_const >> bit) & 1
                # Pre-load each limit bit via a constant INPUT node
                const_node = self._graph.add_input(
                    f"_for_{loop_var}_limit_b{bit}")
                const_node.output_addr = laddr
                self._extra_storage_addresses[
                    f"_for_{loop_var}_limit_b{bit}"] = laddr
        else:
            # Variable limit — expose first bit address for caller injection
            self._extra_storage_addresses[
                f"_for_{loop_var}_limit"] = limit_addrs[0]

        # ── Bind loop variable i to value bits ───────────────────────────
        # Create an IR input node whose output_addr points to value_addrs[0]
        # The compiler resolves references to loop_var through this node
        i_node = self._graph.add_input(f"_for_{loop_var}_val")
        i_node.output_addr = value_addrs[0]
        self._scope[loop_var] = i_node.node_id

        # ── Compile body ──────────────────────────────────────────────────
        # Body executes with loop_var bound to value_addrs[0]
        last_result = None
        for s in stmt.body:
            last_result = self._compile_stmt(s)

        # ── Feedback tick: body completion → counter tick ─────────────────
        # When the body produces a result, a PASS cell pulses tick_addr.
        # This drives the next counter increment.
        if last_result is not None:
            self._extra_records.append(
                CellMapRecord(
                    GS_PASS | LOOP_MODE,
                    last_result.output_addr,
                    tick_addr,
                ))
        else:
            # Body has no explicit result — use initial tick injection only
            # Caller must pulse tick_addr manually to drive iterations
            pass

        # ── Initial tick ─────────────────────────────────────────────────
        # The very first iteration needs a tick to start the counter.
        # Expose tick_addr in input_map so caller injects a 1 to start.
        self._extra_storage_addresses[
            f"_for_{loop_var}_tick"] = tick_addr

        # ── Done signal → loop exit ───────────────────────────────────────
        done_node = self._graph.add_input(f"_for_{loop_var}_done")
        done_node.output_addr = done_addr
        return done_node

    def _compile_while(self, stmt: ast.While) -> Optional[IRNode]:
        """
        Compile a while loop using the pointer model (v0.2 spec Section 4.2).

        Pointer topology:
          storage_cell (loopback) ──► condition chain ──► SELECT (LOOP_MODE)
                  ▲                                             │          │
                  │                                           true       false
                  │                                             │          │
                  └──── PASS feedback (LOOP_MODE) ◄── body  result_cell (LOOP_MODE)
                                                               │
                                                         (holds last value,
                                                          readable after exit)

        The loop variable lives in a storage cell (storage_mode=True).
        It re-emits its value every tick, so the condition and body can
        both read the current value each iteration. When the body computes
        a new value, the PASS feedback writes it back — the storage cell
        updates and re-emits the new value next tick.

        On exit (condition false), the SELECT routes to the result cell.
        The result cell is also storage_mode=True — it holds the final
        value of the loop variable after the loop ends, and keeps it
        available for code that reads after the while block.

        The initial value of the loop variable is injected by the caller
        via controller.start(inputs={storage_addr: initial_value}).
        The compiler returns storage_addr in the input_map so the caller
        knows where to inject it.
        """
        from controller import CellMapRecord
        from gate_states import GS_PASS, GS_SELECT, LOOP_MODE

        # ── Identify the loop variable ────────────────────────────────────
        test_names = [n.id for n in ast.walk(stmt.test)
                      if isinstance(n, ast.Name)]
        if not test_names:
            raise NotImplementedError(
                "while loop condition must reference at least one variable"
            )
        loop_var_name = test_names[0]

        if loop_var_name not in self._scope:
            raise NameError(
                f"while loop variable '{loop_var_name}' used before assignment"
            )

        # ── Allocate storage cell for the loop variable ───────────────────
        # The storage cell holds the current value of the loop variable.
        # It re-emits every tick (storage_mode=True), so:
        #   - the condition chain can read it each iteration
        #   - the body can read it each iteration
        #   - the feedback write updates it for the next iteration
        # Two addresses for the storage cell to avoid wired-OR collision:
        #   storage_in_addr:  where feedback WRITES the updated value (and
        #                     where the initial value is injected)
        #   storage_out_addr: where the storage cell RE-EMITS, readable by
        #                     the condition chain and loop body each tick
        # Keeping them separate means feedback (writing to storage_in_addr)
        # and the storage cell re-emit (writing to storage_out_addr) never
        # collide on the bus. Without this, wired-OR would merge the old
        # re-emitted value with the new feedback value, blocking the update.
        storage_in_addr  = self._graph._alloc.alloc()  # inject & feedback target
        storage_out_addr = self._graph._alloc.alloc()  # condition & body read from here

        # Storage cell: reads from storage_in_addr, writes to storage_out_addr.
        # storage_mode=True means it re-emits storage_out_addr every tick and
        # updates its stored value whenever storage_in_addr carries new data.
        self._extra_records.append(
            CellMapRecord(GS_PASS,
                          storage_in_addr,
                          storage_out_addr,
                          storage_mode=True)
        )

        # Point the loop variable in scope to storage_out_addr (what other
        # cells read from).
        storage_node = self._graph.add_input(
            f"_while_storage_{loop_var_name}_{self._graph._counter}")
        storage_node.output_addr = storage_out_addr
        self._scope[loop_var_name] = storage_node.node_id

        # The caller injects the initial value at storage_in_addr — the
        # storage cell reads it on tick 0 and begins re-emitting storage_out_addr.
        if not hasattr(self, '_extra_storage_addresses'):
            self._extra_storage_addresses = {}
        self._extra_storage_addresses[loop_var_name] = storage_in_addr

        # ── Compile the condition ─────────────────────────────────────────
        # Condition reads from storage_addr each iteration.
        cond_node = self._compile_expr(stmt.test)
        cond_output_addr = cond_node.output_addr

        # ── Allocate SELECT and exit addresses ────────────────────────────
        exit_addr       = self._graph._alloc.alloc()
        body_start_addr = self._graph._alloc.alloc()

        # ── Allocate result storage cell ──────────────────────────────────
        # Holds the loop variable's value when the loop exits.
        # SELECT routes here on false; it stores and re-emits the exit value.
        result_addr = self._graph._alloc.alloc()
        self._extra_records.append(
            CellMapRecord(GS_PASS | LOOP_MODE,
                          exit_addr,
                          result_addr,
                          storage_mode=True)
        )

        # ── Compile the body ──────────────────────────────────────────────
        body_entry_node = self._graph.add_input(
            f"_while_body_entry_{self._graph._counter}")
        body_entry_node.output_addr = body_start_addr

        scope_before = dict(self._scope)
        self._scope[loop_var_name] = body_entry_node.node_id

        saved_entry = self._loop_body_entry
        self._loop_body_entry = body_entry_node

        for s in stmt.body:
            r = self._compile_stmt(s)

        self._loop_body_entry = saved_entry

        # Find where loop_var_name points after body compilation.
        body_loop_var_node_id = self._scope.get(loop_var_name)
        body_loop_var_node    = self._graph.get(body_loop_var_node_id)
        body_output_addr      = (body_loop_var_node.output_addr
                                 if body_loop_var_node else body_start_addr)

        self._scope = scope_before

        # ── Emit SELECT and PASS feedback ─────────────────────────────────
        # Loop SELECT: condition true → body, false → exit
        self._extra_records.append(
            CellMapRecord(GS_SELECT | LOOP_MODE,
                          cond_output_addr,
                          body_start_addr,
                          output_address_alt=exit_addr)
        )

        # PASS feedback: body result → storage_in_addr (updates storage cell).
        # Writes to storage_in_addr (not storage_out_addr) so there's no
        # wired-OR collision with the storage cell's own re-emission.
        self._extra_records.append(
            CellMapRecord(GS_PASS | LOOP_MODE,
                          body_output_addr,
                          storage_in_addr)
        )

        # ── Return node pointing to result storage cell ───────────────────
        # Code after the while block reads the loop variable from result_addr.
        # The result cell holds the final value persistently after exit.
        result_node = self._graph.add_input(
            f"_while_result_{self._graph._counter}")
        result_node.output_addr = result_addr
        self._scope[loop_var_name] = result_node.node_id

        return result_node

    # ── expression compilation ────────────────────────────────────────────────

    def _compile_expr(self, expr) -> IRNode:
        """Compile one expression node to an IRNode."""

        if isinstance(expr, ast.Constant):
            return self._compile_constant(expr)

        elif isinstance(expr, ast.Name):
            return self._compile_name(expr)

        elif isinstance(expr, ast.UnaryOp):
            return self._compile_unaryop(expr)

        elif isinstance(expr, ast.BinOp):
            return self._compile_binop(expr)

        elif isinstance(expr, ast.BoolOp):
            return self._compile_boolop(expr)

        elif isinstance(expr, ast.Compare):
            return self._compile_compare(expr)

        elif isinstance(expr, ast.Call):
            return self._compile_call(expr)

        elif isinstance(expr, ast.IfExp):
            # Ternary: value_if_true if condition else value_if_false
            # Compiled as: (true AND cond) OR (false AND NOT cond)
            cond_node  = self._compile_expr(expr.test)
            true_node  = self._compile_expr(expr.body)
            false_node = self._compile_expr(expr.orelse)
            not_cond   = self._graph.add_node("NOT", [cond_node.node_id],
                                               comment="NOT cond (ternary)")
            true_arm   = self._graph.add_node("AND",
                                               [true_node.node_id, cond_node.node_id],
                                               comment="true * cond")
            false_arm  = self._graph.add_node("AND",
                                               [false_node.node_id, not_cond.node_id],
                                               comment="false * NOT cond")
            return self._graph.add_node("OR",
                                         [true_arm.node_id, false_arm.node_id],
                                         comment="ternary mux")

        else:
            raise NotImplementedError(
                f"Expression type '{type(expr).__name__}' not supported in v0.1 subset."
            )

    def _compile_constant(self, expr: ast.Constant) -> IRNode:
        """Compile an integer literal 0 or 1.

        Outside a loop body: emits an INPUT node pre-loaded before execution.

        Inside a loop body: derives the constant from the body-entry signal.
        The body-entry signal is 1 when the loop condition was true (the SELECT
        cell routed here). Constants derived from a 1-bit trigger:
          const_1 = PASS(entry)       → passes the 1 through unchanged
          const_0 = NOT(entry)        → NOR(entry, entry) = 0 when entry=1
        This ensures constants are re-driven on every loop iteration rather
        than relying on a pre-loaded value that only exists on the first tick.
        """
        if expr.value not in (0, 1, True, False):
            raise ValueError(
                f"Constant '{expr.value}' not supported. "
                f"v0.1 supports only 0 and 1 (single-bit values)."
            )
        val = 1 if expr.value else 0

        if self._loop_body_entry is not None:
            # Inside a loop body: derive from entry signal.
            entry_node = self._loop_body_entry
            name = f"const_{val}_{self._graph._counter + 1}"
            if val == 1:
                # PASS(entry) = 1 when entry=1 (loop body active)
                node = self._graph.add_node("PASS", [entry_node.node_id],
                                             name=name,
                                             comment=f"loop constant 1 from entry")
            else:
                # NOT(entry) = 0 when entry=1 (loop body active)
                node = self._graph.add_node("NOT", [entry_node.node_id],
                                             name=name,
                                             comment=f"loop constant 0 from entry")
            return node

        # Outside a loop body: pre-loaded INPUT node.
        # Add to extra_storage_addresses so it appears in imap and gets injected.
        name = f"const_{val}_{self._graph._counter + 1}"
        node = self._graph.add_input(name)
        node.comment = f"constant: {val}"
        # Register for auto-injection by the caller
        if not hasattr(self, '_extra_storage_addresses'):
            self._extra_storage_addresses = {}
        self._extra_storage_addresses[name] = (node.output_addr, val)
        return node

    def _compile_name(self, expr: ast.Name) -> IRNode:
        """Look up a variable name in the current scope."""
        if expr.id not in self._scope:
            raise NameError(
                f"Variable '{expr.id}' used before assignment. "
                f"Available: {list(self._scope.keys())}"
            )
        node_id = self._scope[expr.id]
        node = self._graph.get(node_id)
        if node is None:
            raise RuntimeError(f"Internal: node '{node_id}' missing from graph")
        return node

    def _compile_unaryop(self, expr: ast.UnaryOp) -> IRNode:
        op_name = type(expr.op).__name__
        if op_name not in UNARYOP_MAP:
            raise NotImplementedError(
                f"Unary op '{op_name}' not supported. "
                f"Supported: {list(UNARYOP_MAP.keys())}"
            )
        operand = self._compile_expr(expr.operand)
        ir_op   = UNARYOP_MAP[op_name]
        return self._graph.add_node(
            ir_op, [operand.node_id],
            comment=f"{op_name}({operand.node_id})"
        )

    def _compile_binop(self, expr: ast.BinOp) -> IRNode:
        op_name = type(expr.op).__name__

        if op_name in BINOP_MAP:
            # Known boolean/bitwise op — compile directly
            left  = self._compile_expr(expr.left)
            right = self._compile_expr(expr.right)
            ir_op = BINOP_MAP[op_name]
            return self._graph.add_node(
                ir_op, [left.node_id, right.node_id],
                comment=f"{left.node_id} {op_name} {right.node_id}"
            )

        # Not a boolean op — check the model library for arithmetic
        from model_library import model_library
        spec = model_library.for_op(op_name, "int32")
        if spec is None:
            spec = model_library.for_op(op_name, "fp32")

        if spec is not None:
            # Arithmetic op handled by a model library entry
            # Emit a special MODEL_OP IR node that the code generator
            # will expand into a model instance load
            left  = self._compile_expr(expr.left)
            right = self._compile_expr(expr.right)
            return self._graph.add_node(
                f"MODEL:{spec.name}",
                [left.node_id, right.node_id],
                comment=f"{spec.name}({left.node_id}, {right.node_id})"
            )

        raise NotImplementedError(
            f"Binary op '{op_name}' not supported. "
            f"Supported bitwise/boolean: {list(BINOP_MAP.keys())}. "
            f"Supported arithmetic via model library: "
            f"{[s.name for s in model_library.by_category('ARITHMETIC')]}."
        )

    def _compile_boolop(self, expr: ast.BoolOp) -> IRNode:
        op_name = type(expr.op).__name__
        if op_name not in BOOLOP_MAP:
            raise NotImplementedError(f"Bool op '{op_name}' not supported.")
        ir_op  = BOOLOP_MAP[op_name]
        # fold left-to-right for multi-value bool ops (a and b and c → (a and b) and c)
        result = self._compile_expr(expr.values[0])
        for val in expr.values[1:]:
            right  = self._compile_expr(val)
            result = self._graph.add_node(
                ir_op, [result.node_id, right.node_id],
                comment=f"{op_name.lower()} fold"
            )
        return result

    def _compile_compare(self, expr: ast.Compare) -> IRNode:
        if len(expr.ops) != 1:
            raise NotImplementedError(
                "Chained comparisons (a < b < c) not supported in v0.1."
            )
        op_name = type(expr.ops[0]).__name__
        if op_name not in COMPARE_MAP:
            raise NotImplementedError(
                f"Comparison '{op_name}' not supported. "
                f"Supported: {list(COMPARE_MAP.keys())} (single-bit equality only)."
            )
        left  = self._compile_expr(expr.left)
        right = self._compile_expr(expr.comparators[0])
        ir_op = COMPARE_MAP[op_name]
        return self._graph.add_node(
            ir_op, [left.node_id, right.node_id],
            comment=f"{left.node_id} {op_name} {right.node_id}"
        )

    def _compile_call(self, expr: ast.Call) -> IRNode:
        """Compile a function call by inlining the callee spatially."""
        if self._inline_depth >= self._max_inline_depth:
            raise RecursionError(
                f"Inline depth limit ({self._max_inline_depth}) reached. "
                f"Recursive functions cannot be compiled in v0.1."
            )

        func_name = expr.func.id if isinstance(expr.func, ast.Name) else None
        if func_name is None or func_name not in self._functions:
            raise NotImplementedError(
                f"Call to '{ast.unparse(expr.func)}' cannot be resolved. "
                f"Only calls to locally-defined functions are supported in v0.1."
            )

        fn = self._functions[func_name]
        if len(expr.args) != len(fn.args.args):
            raise TypeError(
                f"Function '{func_name}' expects {len(fn.args.args)} args, "
                f"got {len(expr.args)}."
            )

        # compile call arguments in the caller's scope
        arg_nodes = [self._compile_expr(a) for a in expr.args]

        # inline: bind parameters to argument nodes
        inline_scope = {
            param.arg: arg_node.node_id
            for param, arg_node in zip(fn.args.args, arg_nodes)
        }

        return self._compile_function_body(fn, args=inline_scope)

    def _compile_function_body(
        self,
        fn: ast.FunctionDef,
        args: dict[str, str]
    ) -> Optional[IRNode]:
        """Compile a function body with a given argument binding."""
        saved_scope = dict(self._scope)
        self._scope.update(args)
        self._inline_depth += 1

        # ── Early-return rewrite ──────────────────────────────────────────────
        # Pattern: if cond: return X  followed by  return Y
        # AST has orelse=[] so _compile_if returns None and the second return
        # fires unconditionally, always returning Y.
        #
        # Rewrite: splice the trailing return into the if's orelse so the
        # if/else mux path fires correctly.
        body = list(fn.body)
        rewritten = []
        i = 0
        while i < len(body):
            stmt = body[i]
            if (isinstance(stmt, ast.If)
                    and not stmt.orelse
                    and len(stmt.body) == 1
                    and isinstance(stmt.body[0], ast.Return)
                    and i + 1 < len(body)
                    and isinstance(body[i + 1], ast.Return)):
                # Rewrite: move the next return into orelse
                import copy
                new_if = copy.copy(stmt)
                new_if.orelse = [body[i + 1]]
                rewritten.append(new_if)
                i += 2   # consume both the if and the trailing return
            else:
                rewritten.append(stmt)
                i += 1

        result_node = None
        for stmt in rewritten:
            r = self._compile_stmt(stmt)
            if isinstance(stmt, ast.Return):
                result_node = r
                break
            if r is not None:
                result_node = r

        self._inline_depth -= 1
        self._scope = saved_scope
        return result_node


# ── run_model_function — end-to-end helper ────────────────────────────────────

def run_compiled_function(
    source: str,
    function_name: str,
    operands: dict,
) -> object:
    """
    Compile and run a simple (non-model) function using ImagoCompiler.

    Uses the preloaded-A pattern: evaluates the cell graph in Python first
    to compute a_data for every binary op cell, then injects B as the
    trigger wave. Handles multi-level chains (MUX, nested AND/OR etc.)
    correctly without carry collision.

    operands: {param_name: integer_value}
    Returns the output value (int), or None on failure.

    MODE 2 hook: this function is the compile+run path for Mode 1 branches.
    Mode 2 (PTT dispatch) will use compile_function + BranchPoint separately.
    """
    from controller import ImagoController, CellMapRecord
    from gate_states import GS_AND, GS_OR, GS_XOR, GS_NOT, GS_PASS, GS_XNOR, TOPO_MASK

    c = ImagoCompiler()
    recs, graph, imap, oaddrs = c.compile_function(source, function_name, None)
    sim_map = getattr(c, 'second_inputs_map', {})  # {src_a → src_b} for leaf ops

    # Build input values keyed by address
    input_vals: dict[int, int] = {}
    for param, value in operands.items():
        addr = imap.get(param)
        if addr is not None:
            # Normalize to 32-bit word: 0 → 0x00000000, non-zero → 0xFFFFFFFF.
            # run_compiled_function operates on single-bit logic where the bus
            # carries 0 (false) or 0xFFFFFFFF (true). Multi-bit values are
            # handled by run_int32_function / tile library.
            raw = int(value) & 0xFFFFFFFF
            input_vals[addr] = 0xFFFFFFFF if raw else 0

    # Python forward simulation — compute a_data for every op cell.
    def _eval(gs, a, b):
        t = gs & TOPO_MASK
        if t == (GS_AND  & TOPO_MASK): return a & b
        if t == (GS_OR   & TOPO_MASK): return a | b
        if t == (GS_XOR  & TOPO_MASK): return a ^ b
        if t == (GS_XNOR & TOPO_MASK): return ~(a ^ b) & 0xFFFFFFFF
        if t == (GS_NOT  & TOPO_MASK): return (~a) & 0xFFFFFFFF
        return b  # PASS / default

    # Preloaded-A forward simulation using IR lowering's preload_map.
    # preload_map: {cell_out_addr → A_source_addr} from lower_to_cell_map_v2.
    # Walk records in order; for each cell compute its output into sim_vals,
    # then set preloaded_a[out] = sim_vals[A_source_addr] at that point.
    ir_preload_map = getattr(c, '_ir_preload_map', {})

    sim_vals: dict[int, int] = dict(input_vals)
    preload_map: dict[int, int] = {}

    for rec in recs:
        in_addr  = rec.input_address
        out_addr = rec.output_address
        gs       = rec.gate_state

        if out_addr in ir_preload_map:
            # Binary op cell: A is from ir_preload_map, B triggers via in_addr.
            a_src = ir_preload_map[out_addr]
            a_val = sim_vals.get(a_src, 0)
            b_val = sim_vals.get(in_addr, 0)
            preload_map[out_addr] = a_val  # concrete a_data for this run
            sim_vals[out_addr] = _eval(gs, a_val, b_val)
        elif rec.initial_value is not None:
            # NOT cell: a_data=0xFFFFFFFF, result = NOT(b)
            b_val = sim_vals.get(in_addr, 0)
            sim_vals[out_addr] = (~b_val) & 0xFFFFFFFF
        else:
            # Single-input PASS/wire cell
            sim_vals[out_addr] = sim_vals.get(in_addr, 0)

    # Load cells and set preloaded_a on region
    ctrl = ImagoController(cell_count=len(recs) * 5 + 50)
    rid  = ctrl.load_map(recs, function_name,
                         known_values=getattr(c, 'known_values', None),
                         preloaded_a=preload_map)
    region = ctrl._regions[rid]
    # one_shot: prevents carry re-triggering in AND/OR reduction trees.
    region.preloaded_one_shot = True

    # Inject all inputs as trigger wave.
    # Preloaded cells (a_arrived=True) fire on first B arrival.
    # A-source addresses are excluded from direct injection — their values
    # are already in a_data; injecting them would cause premature firing.
    a_source_addrs = set(ir_preload_map.values())

    inputs = {addr: val for addr, val in input_vals.items()
              if addr not in a_source_addrs}

    # Cycle 1: deliver B to src_a (second arrival triggers the op)
    result = ctrl.run(rid, inputs=inputs, capture_addresses=oaddrs)
    if result is None:
        return None
    if len(oaddrs) == 1:
        return result.get(oaddrs[0])
    return {addr: result.get(addr) for addr in oaddrs}



def run_model_function(
    source: str,
    function_name: str,
    operands: dict,
    tile_library=None,
) -> list:
    """
    Compile and run a function that uses model library ops (e.g. a+b, a-b).

    operands: {param_name: integer_value}
    Returns list of bit values at output addresses.

    For 32-bit integer results:
        bits = run_model_function(src, 'f', {'a': 15, 'b': 7})
        unsigned = sum(b << i for i, b in enumerate(bits))
        signed = unsigned if unsigned < 2**31 else unsigned - 2**32
    """
    from fp_tiles import TileLibrary
    from controller import ImagoController

    lib      = tile_library or TileLibrary()
    compiler = ImagoCompiler(tile_library=lib)
    records, graph, imap, oa = compiler.compile_function(
        source, function_name, list(operands.keys()))

    seg_spans = compiler._model_segment_spans
    max_seg   = max((s for _, _, s in seg_spans), default=0)
    segments  = [{"segment_id": sid, "lane_count": 256}
                 for sid in range(1, max_seg + 1)]

    ctrl = ImagoController(cell_count=len(records) + 500, segments=segments)
    rid  = ctrl.load_map(records, function_name,
                         known_values=getattr(compiler, 'known_values', None))

    # Assign model cells to their segments
    region = ctrl._regions[rid]
    for start_idx, end_idx, seg_id in seg_spans:
        for cell_addr in region.cell_addresses[start_idx:end_idx]:
            ctrl.array.assign_segment(cell_addr, seg_id)

    # Build inputs dict from operands — imap gives first-bit address per param
    from model_library import model_library
    # Get full input port addresses from the model instance
    from model_library import model_library
    model_nodes = [n for n in graph.nodes if n.operation.startswith("MODEL:")]
    model_instances = {}  # model_name → instance
    base = 0x00400000
    for node in model_nodes:
        mname = node.operation[len("MODEL:"):]
        spec  = model_library.get(mname)
        if spec:
            inst = spec.place(base_address=base)
            model_instances[mname] = inst
            base += len(inst.records) * 2

    inputs: dict = {}
    for param, value in operands.items():
        first_addr = imap.get(param)
        if first_addr is None:
            continue
        u = value & 0xFFFFFFFF
        # Find the full port address list for this param from the model instance
        port_addrs = None
        param_idx  = list(operands.keys()).index(param)
        for inst in model_instances.values():
            port_names = list(inst.spec.inputs.keys())
            if param_idx < len(port_names):
                port_addrs = inst.input_addresses(port_names[param_idx])
                break
        if port_addrs:
            # Inject all bits including carry-in.
            # Extra bits beyond bit 31 use spec.carry_in (0 for ADD, 1 for SUB).
            for inst in model_instances.values():
                port_names = list(inst.spec.inputs.keys())
                if param_idx < len(port_names):
                    cin = inst.spec.carry_in
                    break
            else:
                cin = 0
            for bit, addr in enumerate(port_addrs):
                inputs[addr] = (u >> bit) & 1 if bit < 32 else cin
        else:
            for bit in range(32):
                inputs[first_addr + bit] = (u >> bit) & 1

    result = ctrl.run(rid, inputs=inputs, capture_addresses=oa)
    if result is None:
        raise RuntimeError(f"'{function_name}' failed to produce output")

    return [result.get(addr, 0) or 0 for addr in oa]
