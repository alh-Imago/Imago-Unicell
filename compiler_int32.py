"""
compiler_int32.py — 32-bit integer type extension for the Imago compiler.

Adds first-class int32 support to ImagoCompiler:

  - int32 variables are represented as 32 bus addresses (one per bit, LSB-first)
  - Arithmetic operators (+, -, ==, !=, <) on int32 variables route directly
    to the tile library (INT32_ADD_CLA, INT32_SUB, INT32_EQ, INT32_LT_U)
  - The Python source subset is extended:
      def add(a: int32, b: int32) -> int32:
          return a + b
  - Single-bit path (existing ImagoCompiler) is completely unchanged

Design:
  Int32Value  — typed wrapper for a 32-element list of bus addresses
  Int32Compiler — subclass of ImagoCompiler; overrides _compile_expr and
                  _compile_binop to detect int32 operands and tile-route them

The compiler-to-tile-library contract:
  For each int32 binary op, _place_int32_tile():
    1. Fetches the tile from the library (cache hit path)
    2. Creates a fresh TilePlacer, feeds the operand bit-addresses as
       a_values / b_values, so tile internal wiring connects directly
       to the caller's signals — zero extra PASS cells needed
    3. Returns an Int32Value over the tile's placed output addresses

LLVM IR hook (M9 preparation):
  compile_int32_function() accepts either Python source or an IR dict
  of the form {"op": "+", "a": <Int32Value>, "b": <Int32Value>}.
  This is the seam the LLVM front-end will target.
"""

import ast
from dataclasses import dataclass, field
from typing import Optional, Union

from compiler import ImagoCompiler
from fp_tiles import TileLibrary, TilePlacer
from unicell import VAR_FALSE   # 0-valued bus constant


# ── Int32Value ────────────────────────────────────────────────────────────────

@dataclass
class Int32Value:
    """
    A 32-bit integer represented as 32 bus addresses, one per bit (LSB-first).

    bit_addrs[0]  = LSB (bit 0)
    bit_addrs[31] = MSB (bit 31, sign bit for signed interpretation)

    depth: pipeline depth at which all 32 bits are available on the bus.
      Source inputs start at depth 0. Each tile output has depth equal to
      the tile's pipeline_depth. When chaining tiles, the shallower operand
      must be padded with PASS delay chains to match the deeper one before
      the downstream tile sees both inputs simultaneously.
    """
    bit_addrs: list[int]
    depth: int = 0

    def __post_init__(self):
        if len(self.bit_addrs) != 32:
            raise ValueError(
                f"Int32Value requires exactly 32 addresses, got {len(self.bit_addrs)}"
            )

    def __repr__(self):
        return f"Int32Value(depth={self.depth}, bits=0x{self.bit_addrs[0]:X}..0x{self.bit_addrs[31]:X})"


# ── type annotation helpers ───────────────────────────────────────────────────

def _is_int32_annotation(annotation) -> bool:
    """Return True if an AST annotation node refers to 'int32'."""
    if annotation is None:
        return False
    if isinstance(annotation, ast.Name):
        return annotation.id == "int32"
    return False


def _returns_int32(fn: ast.FunctionDef) -> bool:
    """Return True if the function's return annotation is int32."""
    return _is_int32_annotation(fn.returns)


# ── Int32Compiler ─────────────────────────────────────────────────────────────

# Arithmetic ops that map to tiles when both operands are Int32Value.
# Maps Python AST binary op class name -> (tile_name, cin_value)
# cin_value: None = no cin port, 0 = cin driven low, 1 = cin driven high
_INT32_BINOP_TILES = {
    "Add":  ("INT32_ADD", 0),        # Kogge-Stone parallel prefix, ~548 cells
    "Sub":  ("INT32_SUB",     1),   # carry-in = 1 (two's complement +1)
}

# Comparison ops that produce a 1-bit result from two int32 operands.
# Lt/Gt/LtE/GtE use INT32_SUB + sign bit extraction.
_INT32_CMP_TILES = {
    "Eq":    "INT32_EQ",
    "NotEq": "INT32_EQ",    # EQ then NOT
    "Lt":    "INT32_SUB",   # sign bit of (a - b): 1 if a < b
    "Gt":    "INT32_SUB",   # sign bit of (b - a): 1 if a > b  (operands swapped)
    "LtE":  "INT32_SUB",    # NOT sign bit of (b - a): 1 if a <= b
    "GtE":  "INT32_SUB",    # NOT sign bit of (a - b): 1 if a >= b
}


class Int32Compiler(ImagoCompiler):
    """
    Extends ImagoCompiler with 32-bit integer support.

    Usage:
        compiler = Int32Compiler(tile_library=TileLibrary())
        records, graph, inputs, outputs = compiler.compile_int32_function(source, "add")

    The returned inputs dict maps parameter names to their 32 bit-addresses:
        {"a": [addr0..addr31], "b": [addr0..addr31]}

    The returned outputs list is the 32 output bit-addresses (or 1 for comparisons).
    """

    def __init__(self, tile_library: Optional[TileLibrary] = None,
                 machine_key: int = 0xDEADC0DEBEEF1234):
        super().__init__(tile_library=tile_library, machine_key=machine_key)
        # Parallel type registry: variable name -> Int32Value | None (=single-bit)
        self._int32_scope: dict[str, Int32Value] = {}
        # Tile placer — shared, advances its base address per placement
        self._int32_placer: Optional[TilePlacer] = None

    # ── public entry point ────────────────────────────────────────────────────

    def compile_int32_function(
        self,
        source: str,
        function_name: str,
    ) -> tuple[list, object, dict[str, list[int]], list[int]]:
        """
        Compile a function whose parameters and/or return value are typed int32.

        Parameters annotated `: int32` create 32 input bus addresses each.
        Parameters with no annotation are treated as single-bit (existing path).

        Returns:
          records         — CellMapRecord list for controller.load_map()
          graph           — IRGraph (for inspection / debugging)
          input_bit_map   — {param_name: [bit_addr0..bit_addr31]}  (int32 params)
                            {param_name: bit_addr}                 (single-bit params)
          output_bit_addrs — [bit_addr0..bit_addr31] for int32 return
                             [bit_addr] for single-bit return
        """
        from ir import IRGraph, lower_to_cell_map_v2

        tree = ast.parse(source)
        self._graph = IRGraph(name=function_name)
        self._scope = {}
        self._int32_scope = {}
        self._functions = {}
        self._inline_depth = 0
        self._int32_placer = TilePlacer(base_address=0x00300000)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._functions[node.name] = node

        if function_name not in self._functions:
            raise ValueError(f"Function '{function_name}' not found in source")

        fn = self._functions[function_name]

        # Build input nodes for each parameter
        input_bit_map: dict[str, Union[list[int], int]] = {}
        for arg in fn.args.args:
            name = arg.arg
            if _is_int32_annotation(arg.annotation):
                # 32-bit parameter: 32 input nodes, one per bit
                bit_addrs = []
                for bit in range(32):
                    node = self._graph.add_input(f"{name}_b{bit}")
                    bit_addrs.append(node.output_addr)
                iv = Int32Value(bit_addrs)
                self._int32_scope[name] = iv
                # Also register a sentinel in _scope so _compile_name
                # doesn't raise NameError; actual value comes from _int32_scope
                self._scope[name] = f"__int32__{name}"
                input_bit_map[name] = bit_addrs
            else:
                # Single-bit parameter (existing path)
                node = self._graph.add_input(name)
                self._scope[name] = node.node_id
                input_bit_map[name] = node.output_addr

        # Compile the body
        result = self._compile_function_body(fn, args={})

        # Collect output addresses
        output_bit_addrs: list[int] = []
        if isinstance(result, Int32Value):
            output_bit_addrs = result.bit_addrs
        elif result is not None:
            output_bit_addrs = [result.output_addr]

        # Lower IR graph to cell records
        from ir import lower_to_cell_map_v2
        records, _stats = lower_to_cell_map_v2(self._graph)

        return records, self._graph, input_bit_map, output_bit_addrs

    # ── expression compilation overrides ─────────────────────────────────────

    def _compile_expr(self, expr) -> Union[object, Int32Value]:
        """
        Override: check for int32 context before delegating to parent.
        Returns either an IRNode (single-bit) or an Int32Value (32-bit).
        """
        if isinstance(expr, ast.BinOp):
            return self._compile_binop_typed(expr)

        if isinstance(expr, ast.Compare):
            return self._compile_compare_typed(expr)

        if isinstance(expr, ast.Name):
            # Check int32 scope first
            if expr.id in self._int32_scope:
                return self._int32_scope[expr.id]

        if isinstance(expr, ast.Constant):
            # Integer constants larger than 1: compile as int32 literal
            if isinstance(expr.value, int) and expr.value not in (0, 1, True, False):
                return self._compile_int32_literal(expr.value)

        # Fall through to single-bit parent path
        return super()._compile_expr(expr)

    def _compile_assign(self, stmt: ast.Assign) -> object:
        """Override: capture int32 results into _int32_scope."""
        value = self._compile_expr(stmt.value)

        for target in stmt.targets:
            if isinstance(target, ast.Name):
                if isinstance(value, Int32Value):
                    self._int32_scope[target.id] = value
                    self._scope[target.id] = f"__int32__{target.id}"
                else:
                    self._scope[target.id] = value.node_id

        return value

    def _compile_binop_typed(self, expr: ast.BinOp) -> Union[object, Int32Value]:
        """Compile binary op, routing to tiles when operands are Int32Value."""
        left  = self._compile_expr(expr.left)
        right = self._compile_expr(expr.right)
        op_name = type(expr.op).__name__

        if isinstance(left, Int32Value) and isinstance(right, Int32Value):
            if op_name in _INT32_BINOP_TILES:
                tile_name, cin_value = _INT32_BINOP_TILES[op_name]
                return self._place_int32_tile(tile_name, left, right, cin_value)
            else:
                raise NotImplementedError(
                    f"Int32 binary op '{op_name}' not supported. "
                    f"Supported: {list(_INT32_BINOP_TILES.keys())}."
                )

        # Single-bit fallback
        from gate_states import BINOP_MAP
        if op_name not in BINOP_MAP:
            raise NotImplementedError(
                f"Binary op '{op_name}' not supported. "
                f"For 32-bit arithmetic, annotate operands as int32."
            )
        ir_op = BINOP_MAP[op_name]
        return self._graph.add_node(
            ir_op, [left.node_id, right.node_id],
            comment=f"{left.node_id} {op_name} {right.node_id}"
        )

    def _compile_compare_typed(self, expr: ast.Compare) -> Union[object, Int32Value]:
        """Compile comparison, routing to tiles when operands are Int32Value."""
        if len(expr.ops) != 1:
            raise NotImplementedError("Chained comparisons not supported.")

        left  = self._compile_expr(expr.left)
        right = self._compile_expr(expr.comparators[0])
        op_name = type(expr.ops[0]).__name__

        if isinstance(left, Int32Value) and isinstance(right, Int32Value):
            if op_name in _INT32_CMP_TILES:
                tile_name = _INT32_CMP_TILES[op_name]

                if op_name == "Eq":
                    return self._place_int32_cmp_tile(tile_name, left, right)

                if op_name == "NotEq":
                    result_bit = self._place_int32_cmp_tile(tile_name, left, right)
                    return self._graph.add_node(
                        "NOT", [result_bit.node_id],
                        comment="int32 != (invert EQ)")

                if op_name in ("Lt", "GtE"):
                    # Lt:  sign bit of (a - b) — 1 if a < b
                    # GtE: NOT sign bit of (a - b) — 1 if a >= b
                    sign_bit = self._place_int32_sign_bit(left, right)
                    if op_name == "GtE":
                        return self._graph.add_node(
                            "NOT", [sign_bit.node_id],
                            comment="int32 >= (invert sign)")
                    return sign_bit

                if op_name in ("Gt", "LtE"):
                    # Gt:  sign bit of (b - a) — 1 if b < a, i.e. a > b
                    # LtE: NOT sign bit of (b - a) — 1 if a <= b
                    sign_bit = self._place_int32_sign_bit(right, left)
                    if op_name == "LtE":
                        return self._graph.add_node(
                            "NOT", [sign_bit.node_id],
                            comment="int32 <= (invert sign)")
                    return sign_bit

            else:
                raise NotImplementedError(
                    f"Int32 comparison '{op_name}' not supported. "
                    f"Supported: {list(_INT32_CMP_TILES.keys())}."
                )

        # Single-bit fallback
        from gate_states import COMPARE_MAP
        if op_name not in COMPARE_MAP:
            raise NotImplementedError(f"Comparison '{op_name}' not supported.")
        ir_op = COMPARE_MAP[op_name]
        return self._graph.add_node(
            ir_op, [left.node_id, right.node_id],
            comment=f"compare {op_name}"
        )

    # ── tile placement helpers ────────────────────────────────────────────────

    def _pad_int32_to_depth(self, iv: Int32Value, target_depth: int) -> Int32Value:
        """
        Insert PASS delay chains so all 32 bits of iv are available at
        target_depth. Returns a new Int32Value with padded addresses.

        Each bit gets (target_depth - iv.depth) PASS cells in series.
        The padded addresses are added to _tile_records as raw CellMapRecord
        entries so they load into the array alongside the tile cells.
        """
        from controller import CellMapRecord
        from gate_states import GS_PASS

        if iv.depth >= target_depth:
            return iv   # already deep enough, no padding needed

        padding_needed = target_depth - iv.depth
        new_addrs = []

        for bit_addr in iv.bit_addrs:
            current = bit_addr
            for _ in range(padding_needed):
                next_addr = self._int32_placer._next
                self._int32_placer._next += 1
                self._tile_records.append(CellMapRecord(GS_PASS, current, next_addr))
                current = next_addr
            new_addrs.append(current)

        return Int32Value(new_addrs, depth=target_depth)

    def _place_int32_tile(
        self,
        tile_name: str,
        left: Int32Value,
        right: Int32Value,
        cin_value: Optional[int] = None,
    ) -> Int32Value:
        """
        Place a 32-bit arithmetic tile, with automatic input depth synchronisation.

        When left and right have different depths (e.g. left is a tile output
        at depth 58, right is a fresh input at depth 0), the shallower operand
        is padded with PASS delay chains to match the deeper one. Without this,
        the tile's first-stage NOT cells see the shallower operand immediately
        while the deeper operand hasn't arrived yet — producing wrong results.

        cin_value: 0 for ADD (no carry), 1 for SUB (two's complement +1).
          The carry-in node is padded to the same target depth as the operands.
        """
        if self._tile_library is None:
            raise RuntimeError(
                f"Tile '{tile_name}' requested but no TileLibrary provided. "
                f"Pass tile_library=TileLibrary() to Int32Compiler()."
            )

        tile = self._tile_library.get(tile_name)

        # Synchronise depths: pad the shallower operand to match the deeper one.
        target_depth = max(left.depth, right.depth)
        left_sync  = self._pad_int32_to_depth(left,  target_depth)
        right_sync = self._pad_int32_to_depth(right, target_depth)

        # Build the full b_values: 32 data bits + padded cin if needed.
        if cin_value is not None and len(tile.in_b) == 33:
            cin_node = self._graph.add_input(f"_cin_{tile_name}_{id(left)}")
            cin_node.comment = f"carry-in: {cin_value}"
            # Pad cin to target_depth
            cin_padded = self._pad_int32_to_depth(
                Int32Value([cin_node.output_addr] * 32, depth=0), target_depth
            )
            b_values_full = right_sync.bit_addrs + [cin_padded.bit_addrs[0]]
        else:
            b_values_full = right_sync.bit_addrs

        records, placed_in_a, placed_in_b, placed_out = self._int32_placer.place(
            tile,
            a_values=left_sync.bit_addrs,
            b_values=b_values_full,
        )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
            self._tile_segment_spans = []
            self._next_segment_id = 1

        # Assign this tile to its own segment so its first-tick NOT cells
        # don't accumulate with those of other tiles in the same array.
        seg_id = self._next_segment_id
        self._next_segment_id += 1
        span_start = len(self._tile_records)
        self._tile_records.extend(records)
        span_end = len(self._tile_records)
        self._tile_segment_spans.append((span_start, span_end, seg_id))

        # Pad each output bit to the tile's full pipeline_depth.
        # Individual output bits complete at different depths (e.g. CLA bit 0
        # at depth 13, bit 31 at depth 58; SUB bit 0 at 15, bit 31 at 201).
        # Without padding, downstream tiles receive early bits before later bits
        # arrive — the bus replaces itself each tick, so unaligned bits are lost.
        tile_depth = tile.metadata.pipeline_depth
        output_depth = target_depth + tile_depth

        from controller import CellMapRecord as _CMR
        from gate_states import GS_PASS as _PASS

        # Compute per-bit output depths by simulating depth propagation through
        # the tile's original (pre-placement) records. This is generic — works
        # for any tile without requiring tile-specific rebuild logic.
        _orig_depth_map = {}
        for addr in tile.in_a + tile.in_b:
            _orig_depth_map[addr] = 0
        for r in tile.records:
            in_d = _orig_depth_map.get(r.input_address, 0)
            cur  = _orig_depth_map.get(r.output_address, 0)
            _orig_depth_map[r.output_address] = max(cur, in_d + 1)
        orig_bit_depths = [_orig_depth_map.get(a, tile_depth) for a in tile.out]

        output_addrs = []
        for i, (out_addr, bit_depth) in enumerate(zip(placed_out, orig_bit_depths)):
            # Pad this bit from its actual depth to the full tile pipeline_depth
            pad_needed = tile_depth - bit_depth
            current = out_addr
            for _ in range(pad_needed):
                next_addr = self._int32_placer._next
                self._int32_placer._next += 1
                self._tile_records.append(_CMR(_PASS, current, next_addr))
                current = next_addr
            node = self._graph.add_input(f"_tile_{tile_name}_out_b{i}")
            node.output_addr = current
            output_addrs.append(current)

        self.tile_cache_hits += 1
        self.time_saved_ms += tile.metadata.pipeline_depth * 0.01

        return Int32Value(output_addrs, depth=output_depth)

    def _place_int32_cmp_tile(
        self,
        tile_name: str,
        left: Int32Value,
        right: Int32Value,
    ) -> object:
        """
        Place a comparison tile (e.g. INT32_EQ) with depth synchronisation.
        Returns a single-bit IRNode.
        """
        if self._tile_library is None:
            raise RuntimeError(
                f"Tile '{tile_name}' requested but no TileLibrary provided."
            )

        tile = self._tile_library.get(tile_name)

        # Synchronise depths
        target_depth = max(left.depth, right.depth)
        left_sync  = self._pad_int32_to_depth(left,  target_depth)
        right_sync = self._pad_int32_to_depth(right, target_depth)

        records, placed_in_a, placed_in_b, placed_out = self._int32_placer.place(
            tile,
            a_values=left_sync.bit_addrs,
            b_values=right_sync.bit_addrs,
        )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
        self._tile_records.extend(records)

        # Single output bit
        out_addr = placed_out[0]
        node = self._graph.add_input(f"_tile_{tile_name}_out")
        node.output_addr = out_addr

        self.tile_cache_hits += 1
        self.time_saved_ms += tile.metadata.pipeline_depth * 0.01

        return node

    def _place_int32_sign_bit(self,
                              left: "Int32Value",
                              right: "Int32Value") -> object:
        """
        Place INT32_SUB tile for (left - right) and return the sign bit
        (output bit 31) as an IRNode.

        The sign bit is 1 when the result is negative, i.e. when left < right.
        Used to implement Lt, Gt, LtE, GtE comparisons.
        """
        if self._tile_library is None:
            raise RuntimeError("Tile library required for sign-bit comparison")

        tile = self._tile_library.get("INT32_SUB")

        target_depth = max(left.depth, right.depth)
        left_sync  = self._pad_int32_to_depth(left,  target_depth)
        right_sync = self._pad_int32_to_depth(right, target_depth)

        records, placed_in_a, placed_in_b, placed_out = self._int32_placer.place(
            tile,
            a_values=left_sync.bit_addrs,
            b_values=right_sync.bit_addrs,
        )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
        self._tile_records.extend(records)

        # Inject carry-in = 1 for two's complement subtraction
        # placed_in_b has 33 entries: bits 0-31 = operand b, bit 32 = carry-in
        if len(placed_in_b) > 32:
            cin_addr = placed_in_b[32]
            from controller import CellMapRecord
            from gate_states import GS_PASS
            # carry-in cell: always-1 source → cin address
            # We create a synthetic INPUT node pre-loaded with 1
            cin_node = self._graph.add_input("_sub_cin")
            cin_node.comment = "SUB carry-in = 1"
            # Wire it: a PASS cell routes cin_node output to placed_in_b[32]
            self._tile_records.append(
                CellMapRecord(GS_PASS, cin_node.output_addr, cin_addr))

        # Bit 31 of the 32-bit output is the sign bit
        # placed_out has 32 entries for the result bits (non-contiguous in CLA,
        # but INT32_SUB uses ripple-carry so they're sequential)
        sign_bit_addr = placed_out[31]
        node = self._graph.add_input("_sub_sign_bit")
        node.output_addr = sign_bit_addr

        self.time_saved_ms += tile.metadata.pipeline_depth * 0.01

        return node

    def _compile_int32_literal(self, value: int) -> Int32Value:
        """
        Compile an integer constant into 32 INPUT nodes pre-loaded with
        the constant's bit values (each node holds 0 or 1).
        The controller must inject these values before run().
        Returns an Int32Value for use as an operand.
        """
        u = value & 0xFFFFFFFF
        bit_addrs = []
        for i in range(32):
            bit = (u >> i) & 1
            node = self._graph.add_input(f"_const_{value & 0xFFFFFFFF}_b{i}")
            node.comment = f"int32 literal {value}, bit {i} = {bit}"
            bit_addrs.append(node.output_addr)
        return Int32Value(bit_addrs)

    # ── compile_int32_function with tile record merge ─────────────────────────

    def compile_int32_function(
        self,
        source: str,
        function_name: str,
    ) -> tuple[list, object, dict, list, list]:
        """
        Compile a 32-bit integer function.

        Returns:
          records         -- CellMapRecord list for controller.load_map()
          graph           -- IRGraph
          input_bit_map   -- {param: [bit_addrs]} for int32, {param: addr} for 1-bit
          output_bit_addrs -- output bus addresses (32 for int32, 1 for bool)
          segment_spans   -- [(start_idx, end_idx, seg_id), ...] for load-time
                             segment assignment. Each tile gets its own segment
                             so simultaneous first-tick emissions don't stack.
        """
        from ir import IRGraph, lower_to_cell_map_v2

        # Reset compilation state
        self._tile_records = []
        self._tile_segment_spans = []   # (start_record_idx, end_record_idx, seg_id)
        self._next_segment_id = 1       # segment 0 = default IR ops

        tree = ast.parse(source)
        self._graph = IRGraph(name=function_name)
        self._scope = {}
        self._int32_scope = {}
        self._functions = {}
        self._inline_depth = 0
        self._int32_placer = TilePlacer(base_address=0x00300000)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._functions[node.name] = node

        if function_name not in self._functions:
            raise ValueError(f"Function '{function_name}' not found in source")

        fn = self._functions[function_name]

        # Build input nodes per parameter type annotation
        input_bit_map = {}
        for arg in fn.args.args:
            name = arg.arg
            if _is_int32_annotation(arg.annotation):
                bit_addrs = []
                for bit in range(32):
                    node = self._graph.add_input(f"{name}_b{bit}")
                    bit_addrs.append(node.output_addr)
                iv = Int32Value(bit_addrs, depth=0)
                self._int32_scope[name] = iv
                self._scope[name] = f"__int32__{name}"
                input_bit_map[name] = bit_addrs
            else:
                node = self._graph.add_input(name)
                self._scope[name] = node.node_id
                input_bit_map[name] = node.output_addr

        # Compile the function body
        result = self._compile_function_body(fn, args={})

        # Collect output addresses
        output_bit_addrs = []
        if isinstance(result, Int32Value):
            output_bit_addrs = result.bit_addrs
        elif result is not None:
            output_bit_addrs = [result.output_addr]

        # Lower IR graph to records (single-bit ops, segment 0)
        ir_records, _stats = lower_to_cell_map_v2(self._graph)

        # Tile records precede IR records in the flat list
        all_records = self._tile_records + ir_records

        return (all_records, self._graph, input_bit_map,
                output_bit_addrs, self._tile_segment_spans)


# ── convenience run helper ────────────────────────────────────────────────────

def run_int32_function(
    source: str,
    function_name: str,
    operands: dict[str, int],
    tile_library: Optional[TileLibrary] = None,
) -> Union[int, list[int]]:
    """
    Compile and run a 32-bit integer function end-to-end.

    operands: {param_name: integer_value}
    Returns signed 32-bit integer result, or list of bit values for
    single-bit returns.

    Example:
        result = run_int32_function(
            "def add(a: int32, b: int32) -> int32: return a + b",
            "add",
            {"a": 100, "b": 200},
            tile_library=TileLibrary(),
        )
        assert result == 300
    """
    from controller import ImagoController

    lib = tile_library or TileLibrary()
    compiler = Int32Compiler(tile_library=lib)
    records, graph, input_bit_map, output_addrs, segment_spans = (
        compiler.compile_int32_function(source, function_name)
    )

    # Provision bus segments — one per tile placement.
    # This keeps each tile's first-tick NOT cells isolated so their
    # simultaneous emissions don't stack above the 256-lane limit.
    max_seg = max((s for _,_,s in segment_spans), default=0)
    segments = [{"segment_id": sid, "lane_count": 256}
                for sid in range(1, max_seg + 1)]

    ctrl = ImagoController(cell_count=len(records) + 500, segments=segments)
    rid  = ctrl.load_map(records, function_name,
                         known_values=getattr(compiler, 'known_values', None))

    # Assign cells to their segments (records are ordered: tile0, tile1, ..., ir)
    region = ctrl._regions[rid]
    for start_idx, end_idx, seg_id in segment_spans:
        for cell_addr in region.cell_addresses[start_idx:end_idx]:
            ctrl.array.assign_segment(cell_addr, seg_id)

    # Inject inputs
    inputs: dict[int, int] = {}
    for param, value in operands.items():
        bit_addrs = input_bit_map.get(param)
        if isinstance(bit_addrs, list):
            u = value & 0xFFFFFFFF
            for i, addr in enumerate(bit_addrs):
                inputs[addr] = (u >> i) & 1
        else:
            inputs[bit_addrs] = value & 1

    # Inject carry-in nodes at their declared value (0 for ADD, 1 for SUB)
    # and any constant literal nodes.
    for node in graph.nodes:
        if node.operation == "INPUT" and node.node_id.startswith("_cin_"):
            try:
                cin_val = int(node.comment.split(": ")[-1])
            except (ValueError, IndexError):
                cin_val = 0
            inputs[node.output_addr] = cin_val
        elif node.operation == "INPUT" and node.node_id.startswith("_const_"):
            try:
                bit_val = int(node.comment.split("= ")[-1])
                inputs[node.output_addr] = bit_val
            except (ValueError, IndexError):
                pass

    result = ctrl.run(rid, inputs=inputs, capture_addresses=output_addrs)

    if result is None:
        raise RuntimeError(f"Function '{function_name}' failed to produce output")

    if len(output_addrs) == 32:
        # Reconstruct signed 32-bit integer from bit addresses
        bits = [result.get(addr, 0) for addr in output_addrs]
        unsigned = sum(b << i for i, b in enumerate(bits))
        return unsigned if unsigned < 2**31 else unsigned - 2**32
    else:
        return result.get(output_addrs[0], 0)
