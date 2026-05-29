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
# Lt/Gt/LtE/GtE use INT32_LT_U (dedicated less-than tile, carry-in=1).
# Gt/LtE/GtE are derived from Lt with swapped operands and/or NOT.
_INT32_CMP_TILES = {
    "Eq":    "INT32_EQ",
    "NotEq": "INT32_EQ",    # EQ then NOT
    "Lt":    "INT32_LT_U",  # a < b  (unsigned)
    "Gt":    "INT32_LT_U",  # b < a  (operands swapped)
    "LtE":   "INT32_LT_U",  # NOT (b < a) → NOT Gt
    "GtE":   "INT32_LT_U",  # NOT (a < b) → NOT Lt
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
        # Accumulated preload maps from tile placements
        self._tile_preloads: dict[int, int] = {}

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

        if isinstance(expr, ast.Call):
            result = self._compile_call_typed(expr)
            if result is not None:
                return result

        # Fall through to single-bit parent path
        return super()._compile_expr(expr)

    def _compile_call_typed(self, expr: ast.Call):
        """
        Handle builtin calls that have int32 tile equivalents.
        Returns Int32Value for min/max, or None to fall through to parent.

        min(a, b) → INT32_LT_S(a, b) → MUX(lt, a, b)   signed: a if a<b else b
        max(a, b) → INT32_LT_S(b, a) → MUX(lt, b, a)   signed: a if a>b else b
        """
        if not isinstance(expr.func, ast.Name):
            return None

        func_name = expr.func.id

        if func_name in ("min", "max") and len(expr.args) == 2:
            left  = self._compile_expr(expr.args[0])
            right = self._compile_expr(expr.args[1])

            if isinstance(left, Int32Value) and isinstance(right, Int32Value):
                if func_name == "min":
                    # a < b (signed) → select a, else b
                    lt_bit = self._place_int32_lt_s_tile(left, right)
                    return self._place_int32_mux_tile(lt_bit, left, right)
                else:
                    # a > b (signed) ≡ b < a → select a, else b
                    lt_bit = self._place_int32_lt_s_tile(right, left)
                    return self._place_int32_mux_tile(lt_bit, left, right)

        return None

    def _place_int32_mux_tile(self,
                               sel: object,
                               on_true: "Int32Value",
                               on_false: "Int32Value") -> "Int32Value":
        """
        Place INT32_MUX tile: out[i] = on_true[i] if sel=1 else on_false[i].
        INT32_MUX layout: in_a = [sel_bit, a0..a31], in_b = [b0..b31].
        sel=1 → output A (on_true), sel=0 → output B (on_false).
        """
        if self._tile_library is None:
            raise RuntimeError("Tile library required for INT32_MUX")

        tile = self._tile_library.get("INT32_MUX")

        # Synchronise depths of the two data operands
        target_depth = max(on_true.depth, on_false.depth)
        a_sync = self._pad_int32_to_depth(on_true,  target_depth)
        b_sync = self._pad_int32_to_depth(on_false, target_depth)

        # Pad sel bit to target_depth as well
        sel_iv = Int32Value([sel.output_addr] * 32, depth=0)
        sel_padded = self._pad_int32_to_depth(sel_iv, target_depth)

        # in_a = [sel, a0..a31]; in_b = [b0..b31]
        a_values_full = [sel_padded.bit_addrs[0]] + a_sync.bit_addrs
        b_values_full = b_sync.bit_addrs

        records, placed_in_a, placed_in_b, placed_out, placed_preload = self._int32_placer.place(
            tile,
            a_values=a_values_full,
            b_values=b_values_full,
        )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
            self._tile_segment_spans = []
            self._next_segment_id = 1
            self._tile_preloads = {}

        seg_id = self._next_segment_id
        self._next_segment_id += 1
        span_start = len(self._tile_records)
        self._tile_records.extend(records)
        span_end = len(self._tile_records)
        self._tile_segment_spans.append((span_start, span_end, seg_id))
        self._tile_preloads.update(placed_preload)

        tile_depth = tile.metadata.pipeline_depth
        output_depth = target_depth + tile_depth

        from controller import CellMapRecord as _CMR
        from gate_states import GS_PASS as _PASS

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
            pad_needed = tile_depth - bit_depth
            current = out_addr
            for _ in range(pad_needed):
                next_addr = self._int32_placer._next
                self._int32_placer._next += 1
                self._tile_records.append(_CMR(_PASS, current, next_addr))
                current = next_addr
            node = self._graph.add_input(f"_mux_out_b{i}")
            node.output_addr = current
            output_addrs.append(current)

        self.tile_cache_hits += 1
        self.time_saved_ms += tile_depth * 0.01

        return Int32Value(output_addrs, depth=output_depth)

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
            self._tile_segment_spans = []
            self._next_segment_id = 1
            self._tile_preloads = {}

        seg_id = self._next_segment_id
        self._next_segment_id += 1
        span_start = len(self._tile_records)
        self._tile_records.extend(records)
        span_end = len(self._tile_records)
        self._tile_segment_spans.append((span_start, span_end, seg_id))
        self._tile_preloads.update(placed_preload)

        tile_depth = tile.metadata.pipeline_depth
        output_depth = target_depth + tile_depth

        from controller import CellMapRecord as _CMR
        from gate_states import GS_PASS as _PASS

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
            pad_needed = tile_depth - bit_depth
            current = out_addr
            for _ in range(pad_needed):
                next_addr = self._int32_placer._next
                self._int32_placer._next += 1
                self._tile_records.append(_CMR(_PASS, current, next_addr))
                current = next_addr
            node = self._graph.add_input(f"_mux_out_b{i}")
            node.output_addr = current
            output_addrs.append(current)

        self.tile_cache_hits += 1
        self.time_saved_ms += tile_depth * 0.01

        return Int32Value(output_addrs, depth=output_depth)

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

                if op_name == "Lt":
                    # a < b  — direct INT32_LT_U placement
                    return self._place_int32_lt_tile(left, right)

                if op_name == "Gt":
                    # a > b  ≡  b < a  — swap operands
                    return self._place_int32_lt_tile(right, left)

                if op_name == "GtE":
                    # a >= b  ≡  NOT (a < b)
                    lt_bit = self._place_int32_lt_tile(left, right)
                    return self._graph.add_node(
                        "NOT", [lt_bit.node_id],
                        comment="int32 >= (invert Lt)")

                if op_name == "LtE":
                    # a <= b  ≡  NOT (b < a)  ≡  NOT Gt
                    gt_bit = self._place_int32_lt_tile(right, left)
                    return self._graph.add_node(
                        "NOT", [gt_bit.node_id],
                        comment="int32 <= (invert Gt)")

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
        from gate_states import GS_PASS, GS_LATCH_IN

        if iv.depth >= target_depth:
            return iv   # already deep enough, no padding needed

        padding_needed = target_depth - iv.depth
        new_addrs = []

        for bit_addr in iv.bit_addrs:
            current = bit_addr
            for _ in range(padding_needed):
                next_addr = self._int32_placer._next
                self._int32_placer._next += 1
                # GS_LATCH_IN: fire on single arrival (no two-arrival wait).
                # Padding cells carry one value forward — no second arrival comes.
                self._tile_records.append(CellMapRecord(GS_PASS | GS_LATCH_IN, current, next_addr))
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

        records, placed_in_a, placed_in_b, placed_out, placed_preload = self._int32_placer.place(
            tile,
            a_values=left_sync.bit_addrs,
            b_values=b_values_full,
        )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
            self._tile_segment_spans = []
            self._next_segment_id = 1
        if not hasattr(self, '_tile_preloads'):
            self._tile_preloads = {}

        # Assign this tile to its own segment so its first-tick NOT cells
        # don't accumulate with those of other tiles in the same array.
        seg_id = self._next_segment_id
        self._next_segment_id += 1
        span_start = len(self._tile_records)
        self._tile_records.extend(records)
        span_end = len(self._tile_records)
        self._tile_segment_spans.append((span_start, span_end, seg_id))
        self._tile_preloads.update(placed_preload)

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

        records, placed_in_a, placed_in_b, placed_out, placed_preload = self._int32_placer.place(
            tile,
            a_values=left_sync.bit_addrs,
            b_values=right_sync.bit_addrs,
        )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
        if not hasattr(self, '_tile_preloads'):
            self._tile_preloads = {}
        self._tile_records.extend(records)
        self._tile_preloads.update(placed_preload)

        # Single output bit
        out_addr = placed_out[0]
        node = self._graph.add_input(f"_tile_{tile_name}_out")
        node.output_addr = out_addr

        self.tile_cache_hits += 1
        self.time_saved_ms += tile.metadata.pipeline_depth * 0.01

        return node

    def _place_int32_lt_tile(self,
                             left: "Int32Value",
                             right: "Int32Value") -> object:
        """
        Place INT32_LT_U tile for (left < right) and return the single-bit result
        as an IRNode. carry-in (in_b[32]) is pre-loaded to 1.

        Returns an IRNode whose output_addr is the LT result bit.
        """
        if self._tile_library is None:
            raise RuntimeError("Tile library required for INT32_LT_U")

        tile = self._tile_library.get("INT32_LT_U")

        target_depth = max(left.depth, right.depth)
        left_sync  = self._pad_int32_to_depth(left,  target_depth)
        right_sync = self._pad_int32_to_depth(right, target_depth)

        # INT32_LT_U has in_b[32] = carry-in; must be pre-loaded to 1.
        # Pad a constant-1 carry-in node to target_depth as well.
        cin_node = self._graph.add_input(f"_lt_cin_{id(left)}")
        cin_node.comment = "carry-in: 1"
        cin_padded = self._pad_int32_to_depth(
            Int32Value([cin_node.output_addr] * 32, depth=0), target_depth
        )
        b_values_full = right_sync.bit_addrs + [cin_padded.bit_addrs[0]]

        records, placed_in_a, placed_in_b, placed_out, placed_preload = self._int32_placer.place(
            tile,
            a_values=left_sync.bit_addrs,
            b_values=b_values_full,
        )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
            self._tile_segment_spans = []
            self._next_segment_id = 1
            self._tile_preloads = {}

        seg_id = self._next_segment_id
        self._next_segment_id += 1
        span_start = len(self._tile_records)
        self._tile_records.extend(records)
        span_end = len(self._tile_records)
        self._tile_segment_spans.append((span_start, span_end, seg_id))
        self._tile_preloads.update(placed_preload)

        # Single output bit (the LT result)
        out_addr = placed_out[0]
        node = self._graph.add_input(f"_lt_result_{id(left)}")
        node.output_addr = out_addr

        self.tile_cache_hits += 1
        self.time_saved_ms += tile.metadata.pipeline_depth * 0.01

        return node

    def _place_int32_lt_s_tile(self,
                                left: "Int32Value",
                                right: "Int32Value") -> object:
        """
        Place INT32_LT_S tile for signed (left < right) and return the 1-bit result.
        Handles overflow-safe signed comparison:
            if signs differ: result = left[31]  (negative < positive)
            if signs same:   result = unsigned_lt (safe subtraction)
        carry-in (in_b[32]) must be pre-loaded to 1.
        Returns an IRNode whose output_addr is the LT result bit.
        """
        if self._tile_library is None:
            raise RuntimeError("Tile library required for INT32_LT_S")

        tile = self._tile_library.get("INT32_LT_S")

        target_depth = max(left.depth, right.depth)
        left_sync  = self._pad_int32_to_depth(left,  target_depth)
        right_sync = self._pad_int32_to_depth(right, target_depth)

        cin_node = self._graph.add_input(f"_lts_cin_{id(left)}")
        cin_node.comment = "carry-in: 1"
        cin_padded = self._pad_int32_to_depth(
            Int32Value([cin_node.output_addr] * 32, depth=0), target_depth
        )
        b_values_full = right_sync.bit_addrs + [cin_padded.bit_addrs[0]]

        records, placed_in_a, placed_in_b, placed_out, placed_preload = self._int32_placer.place(
            tile,
            a_values=left_sync.bit_addrs,
            b_values=b_values_full,
        )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
            self._tile_segment_spans = []
            self._next_segment_id = 1
            self._tile_preloads = {}

        seg_id = self._next_segment_id
        self._next_segment_id += 1
        span_start = len(self._tile_records)
        self._tile_records.extend(records)
        span_end = len(self._tile_records)
        self._tile_segment_spans.append((span_start, span_end, seg_id))
        self._tile_preloads.update(placed_preload)

        out_addr = placed_out[0]
        node = self._graph.add_input(f"_lts_result_{id(left)}")
        node.output_addr = out_addr

        self.tile_cache_hits += 1
        self.time_saved_ms += tile.metadata.pipeline_depth * 0.01

        return node

    def _place_int32_minmax_tile(self,
                                 tile_name: str,
                                 left: "Int32Value",
                                 right: "Int32Value") -> "Int32Value":
        """
        Place INT32_MIN or INT32_MAX tile and return a 32-bit Int32Value result.
        The TileLibrary versions of these tiles use signed comparison (sign-bit of
        ripple subtract) with in_a=32, in_b=32, out=32 — no external carry-in port.
        min(a, b) and max(a, b) both use signed semantics, matching int32 annotation.
        """
        if self._tile_library is None:
            raise RuntimeError(f"Tile library required for {tile_name}")

        tile = self._tile_library.get(tile_name)

        target_depth = max(left.depth, right.depth)
        left_sync  = self._pad_int32_to_depth(left,  target_depth)
        right_sync = self._pad_int32_to_depth(right, target_depth)

        # No carry-in: INT32_MIN/MAX tile has in_b=32 only.
        records, placed_in_a, placed_in_b, placed_out, placed_preload = self._int32_placer.place(
            tile,
            a_values=left_sync.bit_addrs,
            b_values=right_sync.bit_addrs,
        )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
            self._tile_segment_spans = []
            self._next_segment_id = 1
            self._tile_preloads = {}

        seg_id = self._next_segment_id
        self._next_segment_id += 1
        span_start = len(self._tile_records)
        self._tile_records.extend(records)
        span_end = len(self._tile_records)
        self._tile_segment_spans.append((span_start, span_end, seg_id))
        self._tile_preloads.update(placed_preload)

        # Pad outputs to uniform tile depth
        tile_depth = tile.metadata.pipeline_depth
        output_depth = target_depth + tile_depth

        from controller import CellMapRecord as _CMR
        from gate_states import GS_PASS as _PASS

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
            pad_needed = tile_depth - bit_depth
            current = out_addr
            for _ in range(pad_needed):
                next_addr = self._int32_placer._next
                self._int32_placer._next += 1
                self._tile_records.append(_CMR(_PASS, current, next_addr))
                current = next_addr
            node = self._graph.add_input(f"_{tile_name.lower()}_out_b{i}")
            node.output_addr = current
            output_addrs.append(current)

        self.tile_cache_hits += 1
        self.time_saved_ms += tile_depth * 0.01

        return Int32Value(output_addrs, depth=output_depth)

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

        records, placed_in_a, placed_in_b, placed_out, placed_preload = self._int32_placer.place(
            tile,
            a_values=left_sync.bit_addrs,
            b_values=right_sync.bit_addrs,
        )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
        if not hasattr(self, '_tile_preloads'):
            self._tile_preloads = {}
        self._tile_records.extend(records)
        self._tile_preloads.update(placed_preload)

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

def compute_tile_preloads(
    tile,
    a_vals: dict,
    b_vals: dict,
) -> dict:
    """
    Forward-simulate a tile's cell records to compute concrete preloaded_a values.

    tile.preload_map is {output_addr: input_a_src_addr} — an address-to-address map
    built at tile construction time. To get actual a_data values we must walk the
    records in emit order with the given input values and read a_src at that point.

    Returns {output_addr: a_data_value} suitable for region.preloaded_a.
    """
    from gate_states import GS_AND, GS_OR, GS_XOR, GS_NOT, GS_XNOR, GS_NAND, GS_NOR, GS_PASS, GS_PASS_B, TOPO_MASK

    def _eval(gs, a, b):
        topo = gs & TOPO_MASK
        if topo == (GS_AND  & TOPO_MASK):  return a & b
        if topo == (GS_OR   & TOPO_MASK):  return a | b
        if topo == (GS_XOR  & TOPO_MASK):  return a ^ b
        if topo == (GS_XNOR & TOPO_MASK):  return (~(a ^ b)) & 0xFFFFFFFF
        if topo == (GS_NAND & TOPO_MASK):  return (~(a & b)) & 0xFFFFFFFF
        if topo == (GS_NOR  & TOPO_MASK):  return (~(a | b)) & 0xFFFFFFFF
        if topo == (GS_NOT  & TOPO_MASK):  return (~a) & 0xFFFFFFFF
        if topo == (GS_PASS_B & TOPO_MASK): return b
        return b

    preload_map = getattr(tile, 'preload_map', None) or {}
    sim_vals = {**a_vals, **b_vals}
    known_preloads = {}

    for rec in tile.records:
        in_addr  = rec.input_address
        out_addr = rec.output_address
        gs       = rec.gate_state
        in_val   = sim_vals.get(in_addr, 0)

        if out_addr in preload_map:
            a_src = preload_map[out_addr]
            a_val = sim_vals.get(a_src, 0)
            known_preloads[out_addr] = a_val
            sim_vals[out_addr] = _eval(gs, a_val, in_val)
        else:
            sim_vals[out_addr] = _eval(gs, sim_vals.get(in_addr, 0), in_val)

    return known_preloads


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

    # Build input bit maps: A bits and B bits keyed by address.
    a_vals: dict[int, int] = {}  # addr → bit value for A operand
    b_vals: dict[int, int] = {}  # addr → bit value for B operand (trigger wave)

    for param, value in operands.items():
        bit_addrs = input_bit_map.get(param)
        u = value & 0xFFFFFFFF
        if isinstance(bit_addrs, list):
            target = a_vals if param == list(operands.keys())[0] else b_vals
            for i, addr in enumerate(bit_addrs):
                target[addr] = (u >> i) & 1
        else:
            a_vals[bit_addrs] = u & 1

    # Carry-in nodes: injected as live triggers on the bus (not preloaded).
    # They appear as triggers for KS tree cells — must arrive as bus values.
    # Constant nodes: similar — injected as triggers.
    for node in graph.nodes:
        if node.operation == "INPUT" and "carry-in:" in (node.comment or ""):
            try:
                cin_val = int(node.comment.split("carry-in:")[-1].strip())
            except (ValueError, IndexError):
                cin_val = 1
            b_vals[node.output_addr] = cin_val  # inject as live trigger
        elif node.operation == "INPUT" and node.node_id.startswith("_const_"):
            try:
                bit_val = int(node.comment.split("= ")[-1])
                b_vals[node.output_addr] = bit_val  # inject as live trigger
            except (ValueError, IndexError):
                pass

    # Preloaded-A pattern: evaluate the KS tree in Python to compute a_data
    # for every binary op cell, then write those values into cells before run.
    #
    # sim_vals holds the current value at each address as we walk records.
    # For op cells in preload_map: a_data = sim_vals[in_a_source_addr].
    # For cells NOT in preload_map (PASS/NOT wires): they propagate normally.
    #
    # Gate state evaluators (operate on 32-bit words).
    from gate_states import GS_AND, GS_OR, GS_XOR, GS_NOT, GS_XNOR, GS_NAND, GS_NOR, GS_PASS, GS_PASS_B, TOPO_MASK
    def _eval_gate(gs: int, a: int, b: int) -> int:
        topo = gs & TOPO_MASK
        if topo == (GS_AND  & TOPO_MASK):  return a & b
        if topo == (GS_OR   & TOPO_MASK):  return a | b
        if topo == (GS_XOR  & TOPO_MASK):  return a ^ b
        if topo == (GS_XNOR & TOPO_MASK):  return (~(a ^ b)) & 0xFFFFFFFF
        if topo == (GS_NAND & TOPO_MASK):  return (~(a & b)) & 0xFFFFFFFF
        if topo == (GS_NOR  & TOPO_MASK):  return (~(a | b)) & 0xFFFFFFFF
        if topo == (GS_NOT  & TOPO_MASK):  return (~a) & 0xFFFFFFFF
        if topo == (GS_PASS_B & TOPO_MASK): return b
        return b  # GS_PASS and default

    # Collect preload maps accumulated during compilation.
    # _tile_preloads: {placed_out_addr → placed_in_a_src_addr}
    combined_preload: dict[int, int] = dict(getattr(compiler, '_tile_preloads', {}))

    # Forward simulation: walk all records in emit order.
    sim_vals: dict[int, int] = {**a_vals, **b_vals}
    known_preloads: dict[int, int] = {}  # cell_output_addr → a_data value

    for rec in records:
        in_addr  = rec.input_address
        out_addr = rec.output_address
        gs       = rec.gate_state
        in_val   = sim_vals.get(in_addr, 0)

        if out_addr in combined_preload:
            # This is a preloaded-A op cell.
            # a_data = value at the A source address at this point in the sim.
            a_src = combined_preload[out_addr]
            a_val = sim_vals.get(a_src, 0)
            known_preloads[out_addr] = a_val
            # Simulate the op result for downstream cells.
            sim_vals[out_addr] = _eval_gate(gs, a_val, in_val)
        else:
            # Wire / NOT / PASS cell — just forward the value.
            sim_vals[out_addr] = _eval_gate(gs, sim_vals.get(in_addr, 0), in_val)

    # Reload: known_values only carries compile-time constants (NOT preloads).
    # Preloads go via region.preloaded_a — written into a_data by start().
    existing_kv = dict(getattr(compiler, 'known_values', None) or {})

    ctrl2 = ImagoController(cell_count=len(records) + 500, segments=segments)
    rid2  = ctrl2.load_map(records, function_name, known_values=existing_kv)
    region2 = ctrl2._regions[rid2]
    for start_idx, end_idx, seg_id in segment_spans:
        for cell_addr in region2.cell_addresses[start_idx:end_idx]:
            ctrl2.array.assign_segment(cell_addr, seg_id)

    # Store preloaded a_data values on the region so start() restores them
    # after its reset pass. region.preloaded_a: {output_addr → a_data_val}.
    region2.preloaded_a = {int(k): int(v) & 0xFFFFFFFF
                           for k, v in known_preloads.items()}
    # a_vals are one-shot triggers — exclude from _pending_inputs re-injection
    # to prevent double-firing of preloaded cells that listen on a-addresses.
    region2._relay_targets.update(a_vals.keys())


    # Inject ALL user inputs as trigger waves (A and B).
    # Preloaded cells (a_arrived=True) fire on first arrival regardless of which side.
    # NOT cells need double-injection (handled by _pending_inputs for b_vals).
    # a_vals addresses are added to relay_targets → one-shot injection (no re-injection).
    # b_vals addresses get re-injected on cycle 1 → double-fires NOT cells. 
    inputs = {**a_vals, **b_vals}

    # Run: B wave propagates, each cell fires on arrival.
    KS_DEPTH = 200
    result = ctrl2.run(rid2, inputs=inputs, capture_addresses=output_addrs,
                       max_cycles=KS_DEPTH, _fixed_cycles=True)

    if result is None:
        raise RuntimeError(f"Function '{function_name}' failed to produce output")

    if len(output_addrs) == 32:
        # Reconstruct signed 32-bit integer.
        # Bus values may be 0xFFFFFFFF (=1) or 0xFFFFFFFE (=0 for NOT(1)) —
        # use bit 0 to extract the single-bit value correctly.
        bits = [(result.get(addr) or 0) & 1 for addr in output_addrs]
        unsigned = sum(b << i for i, b in enumerate(bits))
        return unsigned if unsigned < 2**31 else unsigned - 2**32
    else:
        # Single-bit result: extract bit 0 from bus value.
        return (result.get(output_addrs[0]) or 0) & 1


# ── load(A) / run(B) API ──────────────────────────────────────────────────────

class LoadedInt32Function:
    """
    A compiled INT32 function with A-side preloaded and ready to accept B.

    Created by load_int32_function(). Call run(B_operands) repeatedly
    with different B values without recompiling or re-running the forward sim.

    Architecture:
        load(A) — compile, forward-sim with A, preload a_data into cells.
        run(B)  — inject B trigger wave, read result. Resets region between calls.

    This mirrors the hardware pattern: send_twice(addr, A) once to preload,
    then inject B each computation. The region.preloaded_a mechanism restores
    a_data before each run so the same region is reusable.
    """

    def __init__(self,
                 ctrl: "ImagoController",
                 region_id: str,
                 output_addrs: list,
                 b_input_map: dict,       # {param_name: [bit_addrs]} for B params
                 b_const_map: dict,       # {addr: value} for carry-in / constants
                 function_name: str):
        self._ctrl          = ctrl
        self._region_id     = region_id
        self._output_addrs  = output_addrs
        self._b_input_map   = b_input_map
        self._b_const_map   = b_const_map
        self._function_name = function_name
        self._run_count     = 0

    def run(self, b_operands: dict) -> "Union[int, list[int]]":
        """
        Inject B operands and return the result.

        b_operands: {param_name: integer_value} for the B-side inputs only.
        For ADD: b_operands = {'b': 42}  (a was loaded at load time).
        """
        from typing import Union

        b_vals: dict[int, int] = {}

        for param, value in b_operands.items():
            bit_addrs = self._b_input_map.get(param)
            u = int(value) & 0xFFFFFFFF
            if isinstance(bit_addrs, list):
                for i, addr in enumerate(bit_addrs):
                    b_vals[addr] = (u >> i) & 1
            elif bit_addrs is not None:
                b_vals[bit_addrs] = u & 1

        # Merge in carry-in and constant nodes
        b_vals.update(self._b_const_map)

        inputs = dict(b_vals)

        KS_DEPTH = 200
        result = self._ctrl.run(
            self._region_id,
            inputs=inputs,
            capture_addresses=self._output_addrs,
            max_cycles=KS_DEPTH,
            _fixed_cycles=True,
        )
        self._run_count += 1

        if result is None:
            raise RuntimeError(
                f"LoadedInt32Function '{self._function_name}' run #{self._run_count} "
                f"failed to produce output"
            )

        if len(self._output_addrs) == 32:
            bits = [(result.get(addr) or 0) & 1 for addr in self._output_addrs]
            unsigned = sum(b << i for i, b in enumerate(bits))
            return unsigned if unsigned < 2**31 else unsigned - 2**32
        else:
            return (result.get(self._output_addrs[0]) or 0) & 1

    @property
    def run_count(self) -> int:
        return self._run_count

    def __repr__(self) -> str:
        return (f"LoadedInt32Function('{self._function_name}', "
                f"runs={self._run_count})")


def load_int32_function(
    source: str,
    function_name: str,
    a_operands: dict[str, int],
    tile_library: "Optional[TileLibrary]" = None,
) -> "LoadedInt32Function":
    """
    Compile a 32-bit integer function and preload the A-side operands.

    Returns a LoadedInt32Function ready to accept B-side inputs via run().
    The forward simulation is run once with the given A values. Subsequent
    run(b_operands) calls inject B and return results without recompiling.

    Use this when A is fixed (e.g. a lookup table key, a constant comparand)
    and B varies across many calls.

    Example:
        # Preload a=100, run with different b values
        fn = load_int32_function(
            "def add(a: int32, b: int32) -> int32: return a + b",
            "add",
            a_operands={"a": 100},
            tile_library=TileLibrary(),
        )
        assert fn.run({"b": 1})   == 101
        assert fn.run({"b": 200}) == 300
        assert fn.run({"b": -50}) == 50
    """
    from controller import ImagoController
    from gate_states import GS_AND, GS_OR, GS_XOR, GS_NOT, GS_XNOR, GS_NAND, GS_NOR, GS_PASS, GS_PASS_B, TOPO_MASK

    lib = tile_library or TileLibrary()
    compiler = Int32Compiler(tile_library=lib)
    records, graph, input_bit_map, output_addrs, segment_spans = (
        compiler.compile_int32_function(source, function_name)
    )

    max_seg  = max((s for _, _, s in segment_spans), default=0)
    segments = [{"segment_id": sid, "lane_count": 256}
                for sid in range(1, max_seg + 1)]

    # Split input_bit_map into A-side and B-side based on a_operands.
    # A-side: params in a_operands → preloaded, not injected as B triggers.
    # B-side: remaining params → injected each run.
    a_param_names = set(a_operands.keys())
    b_input_map   = {k: v for k, v in input_bit_map.items()
                     if k not in a_param_names}

    # Build a_vals from a_operands
    a_vals: dict[int, int] = {}
    for param, value in a_operands.items():
        bit_addrs = input_bit_map.get(param)
        u = int(value) & 0xFFFFFFFF
        if isinstance(bit_addrs, list):
            for i, addr in enumerate(bit_addrs):
                a_vals[addr] = (u >> i) & 1
        elif bit_addrs is not None:
            a_vals[bit_addrs] = u & 1

    # Collect carry-in and constant nodes (injected as B triggers each run)
    b_const_map: dict[int, int] = {}
    for node in graph.nodes:
        if node.operation == "INPUT" and "carry-in:" in (node.comment or ""):
            try:
                b_const_map[node.output_addr] = int(node.comment.split("carry-in:")[-1].strip())
            except (ValueError, IndexError):
                b_const_map[node.output_addr] = 1
        elif node.operation == "INPUT" and node.node_id.startswith("_const_"):
            try:
                b_const_map[node.output_addr] = int(node.comment.split("= ")[-1])
            except (ValueError, IndexError):
                pass

    # Forward simulation with a_vals to compute preloaded_a values
    def _eval_gate(gs: int, a: int, b: int) -> int:
        topo = gs & TOPO_MASK
        if topo == (GS_AND  & TOPO_MASK):  return a & b
        if topo == (GS_OR   & TOPO_MASK):  return a | b
        if topo == (GS_XOR  & TOPO_MASK):  return a ^ b
        if topo == (GS_XNOR & TOPO_MASK):  return (~(a ^ b)) & 0xFFFFFFFF
        if topo == (GS_NAND & TOPO_MASK):  return (~(a & b)) & 0xFFFFFFFF
        if topo == (GS_NOR  & TOPO_MASK):  return (~(a | b)) & 0xFFFFFFFF
        if topo == (GS_NOT  & TOPO_MASK):  return (~a) & 0xFFFFFFFF
        if topo == (GS_PASS_B & TOPO_MASK): return b
        return b

    combined_preload = dict(getattr(compiler, '_tile_preloads', {}))
    # Use zero for B-side inputs (they are unknown at load time)
    sim_vals: dict[int, int] = dict(a_vals)
    known_preloads: dict[int, int] = {}

    for rec in records:
        in_addr  = rec.input_address
        out_addr = rec.output_address
        gs       = rec.gate_state
        in_val   = sim_vals.get(in_addr, 0)

        if out_addr in combined_preload:
            a_src = combined_preload[out_addr]
            a_val = sim_vals.get(a_src, 0)
            known_preloads[out_addr] = a_val
            sim_vals[out_addr] = _eval_gate(gs, a_val, in_val)
        else:
            sim_vals[out_addr] = _eval_gate(gs, sim_vals.get(in_addr, 0), in_val)

    existing_kv = dict(getattr(compiler, 'known_values', None) or {})

    ctrl = ImagoController(cell_count=len(records) + 500, segments=segments)
    rid  = ctrl.load_map(records, function_name, known_values=existing_kv)
    region = ctrl._regions[rid]
    for start_idx, end_idx, seg_id in segment_spans:
        for cell_addr in region.cell_addresses[start_idx:end_idx]:
            ctrl.array.assign_segment(cell_addr, seg_id)

    region.preloaded_a = {int(k): int(v) & 0xFFFFFFFF
                          for k, v in known_preloads.items()}
    region._relay_targets.update(a_vals.keys())

    return LoadedInt32Function(
        ctrl          = ctrl,
        region_id     = rid,
        output_addrs  = output_addrs,
        b_input_map   = b_input_map,
        b_const_map   = b_const_map,
        function_name = function_name,
    )
