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
# int32 is a signed type — use INT32_LT_S for all ordered comparisons.
# Gt/LtE/GtE are derived from Lt with swapped operands and/or NOT.
_INT32_CMP_TILES = {
    "Eq":    "INT32_EQ",
    "NotEq": "INT32_EQ",    # EQ then NOT
    "Lt":    "INT32_LT_S",  # a < b  (signed)
    "Gt":    "INT32_LT_S",  # b < a  (operands swapped)
    "LtE":   "INT32_LT_S",  # NOT (b < a) → NOT Gt
    "GtE":   "INT32_LT_S",  # NOT (a < b) → NOT Lt
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

    tile_config — optional dict mapping tile names to strategy strings.
    Passed through to TileLibrary.get(name, strategy=...) at every tile
    placement.  Blank dict (default) uses each tile's default strategy.

    Examples:
        # All defaults (standard tiles):
        compiler = Int32Compiler(tile_library=lib)

        # Low-latency division and sqrt (e.g. for MathTrix N-body):
        compiler = Int32Compiler(
            tile_library=lib,
            tile_config={
                "MIF_DIV":  "low_latency",
                "MIF_SQRT": "low_latency",
            }
        )

        # Constant divisor (e.g. PageRank degree known at compile time):
        compiler = Int32Compiler(
            tile_library=lib,
            tile_config={"MIF_DIV": "const_divisor"}
        )

    Any tile name not in tile_config uses the library default (strategy="auto").
    Specialist frontends (MathTrix, BioTrix, etc.) pass their own tile_config
    without touching the compiler internals.
    """

    def __init__(self, tile_library: Optional[TileLibrary] = None,
                 machine_key: int = 0xDEADC0DEBEEF1234,
                 tile_config: Optional[dict] = None):
        super().__init__(tile_library=tile_library, machine_key=machine_key)
        # Parallel type registry: variable name -> Int32Value | None (=single-bit)
        self._int32_scope: dict[str, Int32Value] = {}
        # Tile placer — shared, advances its base address per placement
        self._int32_placer: Optional[TilePlacer] = None
        # Accumulated preload maps from tile placements
        self._tile_preloads: dict[int, int] = {}
        # Tile configuration: {tile_name: strategy_string}
        # Empty dict = all defaults.  Passed through to lib.get().
        self._tile_config: dict[str, str] = tile_config or {}

    def _get_tile(self, tile_name: str):
        """
        Fetch a tile from the library, applying tile_config strategy if set.

        This is the single call site for all tile lookups in the compiler.
        Specialist frontends influence tile selection by passing tile_config
        to the constructor — nothing else changes.

        tile_config entry for tile_name → lib.get(name, strategy=that_entry)
        No entry → lib.get(name)  (library default, strategy='auto')
        """
        if self._tile_library is None:
            raise RuntimeError(
                f"Tile '{tile_name}' requested but no TileLibrary provided. "
                f"Pass tile_library=TileLibrary() to Int32Compiler()."
            )
        strategy = self._tile_config.get(tile_name)
        if strategy is not None:
            return self._tile_library.get(tile_name, strategy=strategy)
        return self._tile_library.get(tile_name)

    # ── expression compilation overrides ─────────────────────────────────────

    def _compile_expr_raw(self, expr):
        """
        Like _compile_expr but returns a bare Python int for integer constants
        so that _compile_binop_typed / _compile_compare_typed can broadcast
        them to Int32Value when the other operand is Int32Value.
        Only called from typed binary/compare paths.
        """
        if isinstance(expr, ast.Constant):
            if isinstance(expr.value, int) and not isinstance(expr.value, bool):
                return expr.value   # bare int for broadcast
        return self._compile_expr(expr)

    def _compile_expr(self, expr) -> Union[object, Int32Value]:
        """
        Override: check for int32 context before delegating to parent.
        Returns either an IRNode (single-bit) or an Int32Value (32-bit).
        NEVER returns a bare Python int — callers can always use .node_id.
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
            if isinstance(expr.value, int) and not isinstance(expr.value, bool):
                # All integer constants in an int32 function context should
                # return Int32Value, not fall through to the single-bit IR path.
                # Previously 0 and 1 fell through to parent, which returned an
                # IRNode with a string node_id — incompatible with tile-placer
                # addresses when used in _compile_if fallback paths.
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

        tile = self._get_tile("INT32_MUX")

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
        from gate_states import GS_PASS as _PASS, GS_LATCH_IN

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
                self._tile_records.append(_CMR(_PASS | GS_LATCH_IN, current, next_addr))  # single-arrival padding
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
        left  = self._compile_expr_raw(expr.left)
        right = self._compile_expr_raw(expr.right)
        op_name = type(expr.op).__name__

        # int32 + literal: broadcast the constant to Int32Value
        if isinstance(left, Int32Value) and isinstance(right, int):
            right = self._broadcast_constant(right, left.depth)
        elif isinstance(right, Int32Value) and isinstance(left, int):
            left = self._broadcast_constant(left, right.depth)

        if isinstance(left, Int32Value) and isinstance(right, Int32Value):
            if op_name in _INT32_BINOP_TILES:
                tile_name, cin_value = _INT32_BINOP_TILES[op_name]
                return self._place_int32_tile(tile_name, left, right, cin_value)

            # Shift ops — right operand must be a compile-time constant
            if op_name in ('RShift', 'LShift'):
                # The shift amount must be a known constant — check known_values
                shift_bits = right.bit_addrs
                shift_val = 0
                all_known = True
                for k, addr in enumerate(shift_bits):
                    v = self.known_values.get(addr)
                    if v is None:
                        all_known = False
                        break
                    if v:
                        shift_val |= (1 << k)
                if not all_known:
                    raise NotImplementedError(
                        f"Int32 '{op_name}' requires a compile-time constant shift amount.")
                if shift_val == 0:
                    return left  # shift by 0 is identity
                if shift_val > 31:
                    raise ValueError(f"Shift amount {shift_val} out of range (0-31)")
                tile_name = f"INT32_{'SAR' if op_name == 'RShift' else 'SHL'}_{shift_val}"
                return self._place_int32_tile_unary(tile_name, left)

            else:
                raise NotImplementedError(
                    f"Int32 binary op '{op_name}' not supported. "
                    f"Supported: {list(_INT32_BINOP_TILES.keys())} + RShift/LShift (constant only)."
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

    def _broadcast_constant(self, value: int, depth: int) -> Int32Value:
        """
        Convert an integer literal to Int32Value by creating input
        addresses with known_values for each bit of the constant.
        e.g. _broadcast_constant(1, 0) → Int32Value with bit 0 = 1, rest = 0
        """
        from controller import CellMapRecord
        from gate_states import GS_PASS, GS_PASS_B, GS_LATCH_IN
        bit_addrs = []
        for bit in range(32):
            bit_val = (value >> bit) & 1
            addr = self._int32_placer._next
            self._int32_placer._next += 1
            # Store as known_value so the controller seeds it at run time
            self.known_values[addr] = 0xFFFFFFFF if bit_val else 0
            bit_addrs.append(addr)
        return Int32Value(bit_addrs, depth=depth)

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

        left  = self._compile_expr_raw(expr.left)
        right = self._compile_expr_raw(expr.comparators[0])
        op_name = type(expr.ops[0]).__name__

        # Broadcast int literal to Int32Value when compared against Int32Value
        if isinstance(left, Int32Value) and isinstance(right, int):
            right = self._broadcast_constant(right, left.depth)
        elif isinstance(right, Int32Value) and isinstance(left, int):
            left = self._broadcast_constant(left, right.depth)

        if isinstance(left, Int32Value) and isinstance(right, Int32Value):
            # ── Zero-comparison fast path (tile-based) ────────────────────────
            # Detect patterns like x != 0, x > 0, x < 0, x == 0, x >= 0, x <= 0
            # and commuted forms (0 < x, etc.).
            # Route through tile-based comparisons so the result is in tile-space
            # and arrives in the same timing domain as other tile outputs.
            # This avoids the IR-graph AND/NOT chain which fires late and causes
            # the MUX selector to arrive after the data (wrong branch selected).
            def _iv_is_zero_const(iv):
                return all(self.known_values.get(a, -1) == 0 for a in iv.bit_addrs)
            _left_is_zero  = _iv_is_zero_const(left)
            _right_is_zero = _iv_is_zero_const(right)
            _zero_cmp_val  = None   # the Int32Value being compared to zero
            _zero_op       = None   # effective op (with val on left)

            if _right_is_zero and not _left_is_zero:
                _zero_cmp_val = left
                _zero_op = op_name
            elif _left_is_zero and not _right_is_zero:
                _zero_cmp_val = right
                _COMMUTE = {"Lt": "Gt", "Gt": "Lt", "LtE": "GtE", "GtE": "LtE",
                            "Eq": "Eq", "NotEq": "NotEq"}
                _zero_op = _COMMUTE.get(op_name)

            if _zero_cmp_val is not None and _zero_op is not None:
                # Build constant zero and one Int32Values to compare against.
                # All comparisons use tile-based results (tile-space output addresses)
                # so the MUX selector arrives in the same timing domain as data.
                zero_iv = self._broadcast_constant(0, depth=_zero_cmp_val.depth)

                if _zero_op == "Lt":     # x < 0
                    return self._place_int32_lt_s_tile(_zero_cmp_val, zero_iv)

                if _zero_op == "Gt":     # x > 0  ↔  LT_S(0, x)
                    return self._place_int32_lt_s_tile(zero_iv, _zero_cmp_val)

                if _zero_op == "GtE":   # x >= 0  ↔  LT_S(-1, x)  since -1 < x ↔ x > -1 ↔ x >= 0
                    neg1_iv = self._broadcast_constant(-1, depth=_zero_cmp_val.depth)
                    return self._place_int32_lt_s_tile(neg1_iv, _zero_cmp_val)

                if _zero_op == "LtE":   # x <= 0  ↔  LT_S(x, 1)  since x < 1 ↔ x <= 0
                    one_iv = self._broadcast_constant(1, depth=_zero_cmp_val.depth)
                    return self._place_int32_lt_s_tile(_zero_cmp_val, one_iv)

                if _zero_op == "Eq":    # x == 0
                    return self._place_int32_cmp_tile("INT32_EQ", _zero_cmp_val, zero_iv)

                if _zero_op == "NotEq": # x != 0  ↔  LT_S(x, 0) OR LT_S(0, x)
                    # x != 0 iff x is negative OR x is positive.
                    # Use a tile-space OR cell so forward sim order is correct.
                    # (IR OR node is processed after tile records, giving wrong preload.)
                    lt_neg = self._place_int32_lt_s_tile(_zero_cmp_val, zero_iv)
                    gt_pos = self._place_int32_lt_s_tile(zero_iv, _zero_cmp_val)
                    from controller import CellMapRecord
                    from gate_states import GS_OR
                    or_addr = self._int32_placer._next
                    self._int32_placer._next += 1
                    # GS_OR two-arrival: A=gt_pos (preloaded), B=lt_neg (trigger)
                    self._tile_records.append(
                        CellMapRecord(GS_OR, lt_neg.output_addr, or_addr)
                    )
                    self._tile_preloads[or_addr] = gt_pos.output_addr
                    or_node = self._graph.add_input(f"_neq0_or_{or_addr:08X}")
                    or_node.output_addr = or_addr
                    return or_node
            # ── end zero-comparison fast path ─────────────────────────────────

            if op_name in _INT32_CMP_TILES:
                tile_name = _INT32_CMP_TILES[op_name]

                if op_name == "Eq":
                    return self._place_int32_cmp_tile(tile_name, left, right)

                if op_name == "NotEq":
                    # a != b  ≡  NOT(EQ(a,b))
                    # Use tile-space NOT cell so result is available in forward sim.
                    eq_bit = self._place_int32_cmp_tile(tile_name, left, right)
                    return self._tile_space_not(eq_bit, "int32 != (invert EQ)")

                if op_name == "Lt":
                    # a < b  (signed)
                    return self._place_int32_lt_s_tile(left, right)

                if op_name == "Gt":
                    # a > b  ≡  b < a  (signed)
                    return self._place_int32_lt_s_tile(right, left)

                if op_name == "GtE":
                    # a >= b  ≡  NOT(a < b)
                    # Use tile-space NOT cell so result is available in forward sim.
                    lt_bit = self._place_int32_lt_s_tile(left, right)
                    return self._tile_space_not(lt_bit, "int32 >= (invert Lt_S)")

                if op_name == "LtE":
                    # a <= b  ≡  NOT(b < a)
                    gt_bit = self._place_int32_lt_s_tile(right, left)
                    return self._tile_space_not(gt_bit, "int32 <= (invert Gt_S)")

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

    # ── if/else override — handles Int32Value branches ───────────────────────

    def _compile_if(self, stmt: ast.If) -> object:
        """
        Override base _compile_if to handle branches that return Int32Value.

        When both branches return Int32Value (int32 arithmetic results),
        use an INT32_MUX tile to select between them based on the condition.
        Falls back to the base bool MUX when branches return graph nodes.
        """
        cond_node = self._compile_expr(stmt.test)

        # If condition is an Int32Value (e.g. an int32 arg used as bool),
        # collapse to single bit: bit 0 carries the same value as all bits
        # for bool results (0x00000000 or 0xFFFFFFFF), so bit 0 suffices.
        if isinstance(cond_node, Int32Value):
            # Add an INPUT node to represent bit 0 of the Int32Value in the graph
            bit0_addr = cond_node.bit_addrs[0]
            bit0_node = self._graph.add_input(f"cond_bit0_{bit0_addr:08X}")
            bit0_node.output_addr = bit0_addr
            cond_node = self._graph.add_node(
                "PASS", [bit0_node.node_id],
                comment="int32→bool collapse (bit 0)"
            )

        # ── Force IR-space conditions to tile-space ───────────────────────────
        # If cond_node.output_addr is in IR address space (< TILE_SPACE_BASE),
        # it was produced by the IR fast path (e.g. x > 0 zero-comparison).
        # IR nodes fire AFTER tile cells in the bus simulation, so the MUX
        # tile would be fed a stale sel=0 value. Fix: wrap the IR result in
        # a tile-placed PASS relay registered in tile-space, so it arrives
        # in the same timing domain as the data operands.
        # This is done by emitting a GS_PASS_B|GS_LATCH_IN relay from the
        # IR output address to a fresh tile-placer address, then using that
        # tile-space address as the condition for the MUX.
        TILE_SPACE_BASE_IF = 0x00200000
        cond_addr = getattr(cond_node, 'output_addr', None)
        if cond_addr is not None and cond_addr < TILE_SPACE_BASE_IF:
            # Materialise the IR condition into tile-placer space
            from controller import CellMapRecord
            from gate_states import GS_PASS_B, GS_LATCH_IN as _LI
            tile_cond_addr = self._int32_placer._next
            self._int32_placer._next += 1
            self._tile_records.append(
                CellMapRecord(GS_PASS_B | _LI, cond_addr, tile_cond_addr)
            )
            # Create a wrapper node with the tile-space address
            wrapped = self._graph.add_input(f"_cond_tile_{tile_cond_addr:08X}")
            wrapped.output_addr = tile_cond_addr
            # Depth of cond in tile-space: estimate based on IR chain length
            # The IR OR-reduce is 5 levels + AND = 6, plus relay = 7 total
            # Record the depth on the node for use in _place_int32_mux
            wrapped.depth = 7
            cond_node = wrapped

        # Save scope, compile true branch
        scope_before = dict(self._scope)
        int32_before = dict(self._int32_scope)

        true_result  = None
        for s in stmt.body:
            true_result = self._compile_stmt(s)
        scope_after_true  = dict(self._scope)
        int32_after_true  = dict(self._int32_scope)

        # Restore scope, compile false branch
        self._scope       = dict(scope_before)
        self._int32_scope = dict(int32_before)

        false_result = None
        if stmt.orelse:
            for s in stmt.orelse:
                false_result = self._compile_stmt(s)
        scope_after_false = dict(self._scope)

        if true_result is None or false_result is None:
            return None

        # Promote Python int literals from branches to Int32Value
        # e.g. "return 1" or "return 0" in an int32 function
        if isinstance(true_result, int) and isinstance(false_result, (Int32Value, int)):
            true_result = self._broadcast_constant(true_result, depth=0)
        if isinstance(false_result, int) and isinstance(true_result, (Int32Value, int)):
            false_result = self._broadcast_constant(false_result, depth=0)

        # Handle IR nodes with output_addr=None — these arise when "return 0"
        # or "return 1" falls through to the parent single-bit IR path.
        # _compile_expr for constants 0/1 returns an IRNode (not a bare int),
        # but that IRNode has no physical address (output_addr=None) so it
        # cannot be passed to _place_int32_mux.
        # Fix: extract the constant value from the branch AST directly.
        def _recover_constant_from_branch(result, branch_stmts):
            """If result is an unaddressed IRNode from a constant return,
            recover the literal value and broadcast it as Int32Value."""
            if (result is not None and
                    not isinstance(result, (Int32Value, int)) and
                    getattr(result, 'output_addr', -1) is None):
                # Try to find a constant value in the branch AST
                for s in branch_stmts:
                    if (isinstance(s, ast.Return) and
                            isinstance(s.value, ast.Constant) and
                            isinstance(s.value.value, int)):
                        return self._broadcast_constant(s.value.value, depth=0)
                # Fallback: can't recover, return as-is (will likely error later)
            return result

        true_result  = _recover_constant_from_branch(true_result,  stmt.body)
        false_result = _recover_constant_from_branch(false_result,
                                                      stmt.orelse if stmt.orelse else [])

        # Both branches return Int32Value → use MUX tile
        if isinstance(true_result, Int32Value) and isinstance(false_result, Int32Value):
            return self._place_int32_mux(
                cond_node, true_result, false_result
            )

        # Mixed or single-bit branches — fall back to base bool MUX
        # Convert any Int32Value to a single representative bit for fallback
        def to_node(r):
            if isinstance(r, Int32Value):
                # Collapse to first bit — limited, but handles simple cases
                tmp = self._graph.add_node(
                    "PASS", [r.bit_addrs[0]],
                    comment="int32→bool collapse"
                )
                return tmp
            return r

        true_node  = to_node(true_result)
        false_node = to_node(false_result)

        not_cond  = self._graph.add_node("NOT", [cond_node.node_id])
        true_arm  = self._graph.add_node("AND", [true_node.node_id, cond_node.node_id])
        false_arm = self._graph.add_node("AND", [false_node.node_id, not_cond.node_id])
        mux_out   = self._graph.add_node("OR",  [true_arm.node_id, false_arm.node_id])

        # Update scope
        self._scope = dict(scope_before)
        return mux_out

    def _place_int32_mux(
        self,
        sel_node,
        a_val: Int32Value,
        b_val: Int32Value,
    ) -> Int32Value:
        """
        Place an INT32_MUX tile: if sel then a_val else b_val.
        sel_node is a single-bit graph node (condition bit).
        MUX tile layout: in_a[0..31] = A bits, in_a[32] = sel, in_b[0..31] = B bits.
        Returns Int32Value over the MUX output addresses.

        Bug fix (2026-06-07): sel_node.output_addr must be a tile-placer bus address,
        not an IR-space address. If sel_node.output_addr is already set (from a
        comparison tile), use it directly. If it is None (from the IR fast path,
        e.g. x > 0 zero-comparison), materialise it via lower_to_cell_map_v2 first
        and patch the address back into the tile placer space.
        """
        if self._tile_library is None:
            raise RuntimeError("INT32_MUX tile requested but no TileLibrary provided.")

        tile = self._get_tile("INT32_MUX")
        if tile is None:
            raise RuntimeError("INT32_MUX not found in tile library.")

        from controller import CellMapRecord
        from gate_states import GS_PASS, GS_PASS_B, GS_LATCH_IN

        # ── Resolve condition to a tile-placer-space bus address ─────────────
        # sel_node.output_addr may be:
        #   (a) A tile-placer address (>= 0x00300000): condition came from a
        #       tile-placed comparison like _place_int32_lt_s_tile — already
        #       in the right address space, use directly.
        #   (b) An IR-space address (small integer, < 0x00100000): condition
        #       came from the IR fast path (e.g. x > 0 zero-comparison) or
        #       an IR INPUT node. This address is NOT in the tile placer's
        #       address space — the MUX tile would read the wrong cell.
        #       Fix: allocate a tile-space address and emit a PASS relay.
        #   (c) None: condition is a pure IR computed node not yet lowered.
        #       Fix: emit placeholder PASS, patch after lower_to_cell_map_v2.

        TILE_SPACE_BASE = 0x00200000   # tile placer addresses start here

        raw_addr = getattr(sel_node, 'output_addr', None)

        if raw_addr is not None and raw_addr >= TILE_SPACE_BASE:
            # Case (a): already in tile-placer space — use directly
            sel_phys_addr = raw_addr
        else:
            # Cases (b) and (c): bridge to tile-placer space via PASS relay
            sel_phys_addr = self._int32_placer._next
            self._int32_placer._next += 1

            if raw_addr is not None:
                # Case (b): IR-space address known now — emit PASS_B relay.
                # GS_PASS_B|GS_LATCH_IN: single-arrival, outputs the arriving
                # bus value (B side). GS_PASS alone would output the preloaded
                # A value (zero), which is wrong for a runtime-computed condition.
                from gate_states import GS_PASS_B
                self._tile_records.append(
                    CellMapRecord(GS_PASS_B | GS_LATCH_IN, raw_addr, sel_phys_addr)
                )
            else:
                # Case (c): address not yet known — emit placeholder, patch later
                if not hasattr(self, '_mux_sel_fixups'):
                    self._mux_sel_fixups = []
                fixup_record_idx = len(self._tile_records)
                from gate_states import GS_PASS_B
                # Placeholder: self-loop with GS_PASS_B, will be patched after lowering
                self._tile_records.append(
                    CellMapRecord(GS_PASS_B | GS_LATCH_IN, sel_phys_addr, sel_phys_addr)
                )
                self._mux_sel_fixups.append((fixup_record_idx, sel_node))

        # ── Depth synchronisation ─────────────────────────────────────────────
        # sel_phys must arrive BEFORE the MUX data bits fire.
        # Compute sel_depth: how deep is the sel signal?
        #   - Tile-space sel (raw_addr >= TILE_SPACE_BASE): use sel_node depth
        #     if available, else 0.
        #   - IR-space sel (relay emitted): sel_phys arrives 1 tick after the
        #     IR condition node fires. The IR condition depth is not directly
        #     tracked here, but we can be conservative and use a_val/b_val
        #     depths as a lower bound, then add the relay overhead.
        #     For IR-space conditions, the safe approach is to pad data to
        #     ensure sel arrives first. We use a generous estimate.
        if raw_addr is not None and raw_addr < TILE_SPACE_BASE:
            # IR-space condition that was NOT wrapped (fallback): very conservative estimate
            sel_depth = max(a_val.depth, b_val.depth) + 8
        else:
            # Tile-space sel — use node's depth attribute if set (by _compile_if wrapper)
            node_depth = getattr(sel_node, 'depth', None)
            sel_depth = node_depth if node_depth is not None else 0

        # target_depth: data must wait until AFTER sel arrives
        target_depth = max(a_val.depth, b_val.depth, sel_depth)

        # Pad both values to same depth
        a_sync = self._pad_int32_to_depth(a_val, target_depth)
        b_sync = self._pad_int32_to_depth(b_val, target_depth)

        # MUX tile: in_a = [sel (0), A bits (1..32)], in_b = [B bits (0..31)]
        a_with_sel = [sel_phys_addr] + a_sync.bit_addrs

        records, placed_in_a, placed_in_b, placed_out, placed_preload = \
            self._int32_placer.place(
                tile,
                a_values=a_with_sel,
                b_values=b_sync.bit_addrs,
            )

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
        if not hasattr(self, '_tile_preloads'):
            self._tile_preloads = {}

        seg_id = self._next_segment_id
        self._next_segment_id += 1
        span_start = len(self._tile_records)
        self._tile_records.extend(records)
        span_end = len(self._tile_records)
        self._tile_segment_spans.append((span_start, span_end, seg_id))
        self._tile_preloads.update(placed_preload)

        return Int32Value(placed_out, depth=target_depth + 2)

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
        from gate_states import GS_PASS, GS_PASS_B, GS_LATCH_IN

        if iv.depth >= target_depth:
            return iv   # already deep enough, no padding needed

        padding_needed = target_depth - iv.depth
        new_addrs = []

        for bit_addr in iv.bit_addrs:
            current = bit_addr
            for _ in range(padding_needed):
                next_addr = self._int32_placer._next
                self._int32_placer._next += 1
                # GS_PASS_B|GS_LATCH_IN: single-arrival relay.
                # Controller pre-arms (a_arrived=True). When B (upstream value)
                # arrives, fires output=B — correctly relays runtime values.
                # GS_PASS (old) output A (preloaded=0), breaking the chain.
                self._tile_records.append(CellMapRecord(GS_PASS_B | GS_LATCH_IN, current, next_addr))
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

        tile = self._get_tile(tile_name)

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
        from gate_states import GS_PASS as _PASS, GS_LATCH_IN

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
                self._tile_records.append(_CMR(_PASS | GS_LATCH_IN, current, next_addr))  # single-arrival padding
                current = next_addr
            node = self._graph.add_input(f"_tile_{tile_name}_out_b{i}")
            node.output_addr = current
            output_addrs.append(current)

        self.tile_cache_hits += 1
        self.time_saved_ms += tile.metadata.pipeline_depth * 0.01

        return Int32Value(output_addrs, depth=output_depth)

    def _place_int32_tile_unary(
        self,
        tile_name: str,
        operand: "Int32Value",
    ) -> "Int32Value":
        """
        Place a single-operand int32 tile (SHR, SHL, NOT).
        Simpler than _place_int32_tile — no depth synchronisation needed.
        """
        if self._tile_library is None:
            raise RuntimeError(
                f"Tile '{tile_name}' requested but no TileLibrary provided.")

        tile = self._get_tile(tile_name)

        if not hasattr(self, '_tile_records'):
            self._tile_records = []
            self._tile_segment_spans = []
            self._next_segment_id = 1
        if not hasattr(self, '_tile_preloads'):
            self._tile_preloads = {}

        records, placed_in_a, placed_in_b, placed_out, placed_preload = \
            self._int32_placer.place(tile, a_values=operand.bit_addrs, b_values=[])

        seg_id = self._next_segment_id
        self._next_segment_id += 1
        span_start = len(self._tile_records)
        self._tile_records.extend(records)
        span_end = len(self._tile_records)
        self._tile_segment_spans.append((span_start, span_end, seg_id))

        if placed_preload:
            self._tile_preloads.update(placed_preload)

        tile_depth = tile.metadata.pipeline_depth
        output_depth = operand.depth + tile_depth

        output_addrs = []
        for i, out_addr in enumerate(placed_out):
            node = self._graph.add_input(f"_{tile_name}_out_b{i}")
            node.output_addr = out_addr
            output_addrs.append(out_addr)

        return Int32Value(output_addrs, depth=output_depth)

    def _place_int32_or_reduce(self, val: "Int32Value") -> object:
        """
        Build a balanced OR-reduction tree over all 32 bits of val.
        Returns a single-bit IRNode (1 if any bit is set, else 0).
        Uses log2(32) = 5 OR-gate levels → 31 OR nodes total.
        """
        # Seed with one input node per bit
        nodes = []
        for i, addr in enumerate(val.bit_addrs):
            n = self._graph.add_input(f"_or_reduce_b{i}_{addr:08X}")
            n.output_addr = addr
            nodes.append(n)

        # Pair-reduce until one node remains
        level = 0
        while len(nodes) > 1:
            next_nodes = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    merged = self._graph.add_node(
                        "OR", [nodes[i].node_id, nodes[i+1].node_id],
                        comment=f"or_reduce L{level} pair {i//2}")
                    next_nodes.append(merged)
                else:
                    next_nodes.append(nodes[i])   # odd one out, carry forward
            nodes = next_nodes
            level += 1

        return nodes[0]

    def _tile_space_not(self, source_node, comment: str = "NOT"):
        """
        Emit a tile-space NOT cell for a 1-bit LTS/EQ result.

        IR NOT nodes (graph.add_node("NOT", ...)) are processed after tile
        records in the forward simulation, so the MUX preload gets 0.
        This method instead emits a GS_NOT_B tile record directly, so the
        result is available in tile-record order during forward simulation.

        source_node must have .output_addr set (tile-space address).
        Returns a new IR INPUT node whose output_addr is the NOT cell's output.
        """
        from controller import CellMapRecord
        from gate_states import GS_NOT_B
        not_addr = self._int32_placer._next
        self._int32_placer._next += 1
        # GS_NOT_B: outputs NOT(B) = NOT(incoming bus value). Single-arrival
        # since source fires once and writes to source_node.output_addr.
        # We need two-arrival semantics here: first arrival sets a_data,
        # second fires. But with latch_in the cell fires on every arrival.
        # Source writes once → use standard two-arrival (no latch_in needed
        # since the upstream tile fires exactly once per run).
        from gate_states import GS_LATCH_IN
        self._tile_records.append(
            CellMapRecord(GS_NOT_B | GS_LATCH_IN, source_node.output_addr, not_addr)
        )
        # Pre-arm: controller sets a_arrived=True so single arrival fires.
        # (Same mechanism as GS_PASS_B|GS_LATCH_IN padding cells.)
        # Register in preload map so forward sim can compute value.
        self._tile_preloads[not_addr] = source_node.output_addr
        not_node = self._graph.add_input(f"_tile_not_{not_addr:08X}")
        not_node.output_addr = not_addr
        return not_node

    def _place_int32_cmp_tile(
        self,
        tile_name: str,
        left: Int32Value,
        right: Int32Value,
        invert: bool = False,
    ) -> object:
        """
        Place a comparison tile (e.g. INT32_EQ) with depth synchronisation.
        Returns a single-bit IRNode with a tile-space output address.

        invert=True: add a tile-space NOT relay after the output so the
        result stays in tile-space (not in IR-space via an IR NOT node).
        """
        if self._tile_library is None:
            raise RuntimeError(
                f"Tile '{tile_name}' requested but no TileLibrary provided."
            )

        tile = self._get_tile(tile_name)

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

        if invert:
            from controller import CellMapRecord
            from gate_states import GS_PASS_B, GS_LATCH_IN as _LI, GS_INVERT_OUT_BIT
            inv_addr = self._int32_placer._next
            self._int32_placer._next += 1
            self._tile_records.append(
                CellMapRecord(GS_PASS_B | _LI | GS_INVERT_OUT_BIT, out_addr, inv_addr)
            )
            out_addr = inv_addr

        node = self._graph.add_input(f"_tile_{tile_name}_{'not_' if invert else ''}out")
        node.output_addr = out_addr

        self.tile_cache_hits += 1
        self.time_saved_ms += tile.metadata.pipeline_depth * 0.01

        return node
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

        tile = self._get_tile("INT32_LT_U")

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
                                right: "Int32Value",
                                invert: bool = False) -> object:
        """
        Place INT32_LT_S tile for signed (left < right) and return the 1-bit result.
        invert=True: add a tile-space NOT so result stays in tile-space.
        """
        if self._tile_library is None:
            raise RuntimeError("Tile library required for INT32_LT_S")

        tile = self._get_tile("INT32_LT_S")

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

        if invert:
            # Emit tile-space NOT relay: GS_PASS_B|GS_LATCH_IN|GS_INVERT_OUT_BIT
            # - GS_PASS_B: output = B (the arriving value)
            # - GS_INVERT_OUT_BIT: invert the output at drain time → NOT(B)
            # - GS_LATCH_IN: single-arrival mode
            # - Controller pre-arms GS_PASS_B cells (a_arrived=True, a_data=0)
            # Result: fires on single arrival, outputs NOT(B) = NOT(input)
            from controller import CellMapRecord
            from gate_states import GS_PASS_B, GS_LATCH_IN as _LI, GS_INVERT_OUT_BIT
            inv_addr = self._int32_placer._next
            self._int32_placer._next += 1
            self._tile_records.append(
                CellMapRecord(GS_PASS_B | _LI | GS_INVERT_OUT_BIT, out_addr, inv_addr)
            )
            out_addr = inv_addr

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

        tile = self._get_tile(tile_name)

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
        from gate_states import GS_PASS as _PASS, GS_LATCH_IN

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
                self._tile_records.append(_CMR(_PASS | GS_LATCH_IN, current, next_addr))  # single-arrival padding
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

        tile = self._get_tile("INT32_SUB")

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
        self.known_values = {}          # {addr: value} for preloaded constants

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

        # Seed module-level integer constants into _int32_scope so
        # sentinel/ward functions can reference PTT_*, STATE_* etc.
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Name) and
                            isinstance(node.value, ast.Constant) and
                            isinstance(node.value.value, int)):
                        const_iv = self._broadcast_constant(
                            node.value.value, depth=0)
                        self._int32_scope[target.id] = const_iv
                        self._scope[target.id] = f"__int32__{target.id}"

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
        # Save IR preload_map for forward sim
        self._ir_preload_map = {**getattr(self, '_ir_preload_map', {}), **_stats.get("preload_map", {})}

        # ── Apply deferred MUX sel fixups ─────────────────────────────────────
        # _place_int32_mux may have emitted placeholder PASS records when the
        # condition came from an IR fast-path node (output_addr=None at tile
        # placement time). Now that lower_to_cell_map_v2 has run, those nodes
        # have real output_addr values. Patch the placeholder records.
        for fixup_idx, sel_node in getattr(self, '_mux_sel_fixups', []):
            real_addr = getattr(sel_node, 'output_addr', None)
            if real_addr is not None:
                rec = self._tile_records[fixup_idx]
                from controller import CellMapRecord
                from gate_states import GS_PASS_B, GS_LATCH_IN
                self._tile_records[fixup_idx] = CellMapRecord(
                    GS_PASS_B | GS_LATCH_IN,
                    real_addr,
                    rec.output_address
                )
        self._mux_sel_fixups = []

        # Tile records precede IR records in the flat list
        all_records = self._tile_records + ir_records

        # Security gate requires at least one record (len == 0 → rejected).
        # Passthrough functions (e.g. return a) produce zero tile and zero IR
        # records — no computation needed, outputs ARE inputs. Fix: emit a
        # GS_PASS_B|GS_LATCH_IN relay for each output bit so the record list
        # is non-empty and the security gate passes.
        if len(all_records) == 0 and len(output_bit_addrs) > 0:
            from controller import CellMapRecord
            from gate_states import GS_PASS_B, GS_LATCH_IN
            passthrough_records = []
            for addr in output_bit_addrs:
                # Self-relay: input == output (identity, value passes through)
                passthrough_records.append(
                    CellMapRecord(GS_PASS_B | GS_LATCH_IN, addr, addr)
                )
            all_records = passthrough_records

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
    from gate_states import GS_AND, GS_OR, GS_XOR, GS_NOT, GS_NOT_B, GS_XNOR, GS_NAND, GS_NOR, GS_PASS, GS_PASS_B, TOPO_MASK

    def _eval(gs, a, b):
        topo = gs & TOPO_MASK
        if topo == (GS_AND  & TOPO_MASK):  return a & b
        if topo == (GS_OR   & TOPO_MASK):  return a | b
        if topo == (GS_XOR  & TOPO_MASK):  return a ^ b
        if topo == (GS_XNOR & TOPO_MASK):  return (~(a ^ b)) & 0xFFFFFFFF
        if topo == (GS_NAND & TOPO_MASK):  return (~(a & b)) & 0xFFFFFFFF
        if topo == (GS_NOR  & TOPO_MASK):  return (~(a | b)) & 0xFFFFFFFF
        if topo == (GS_NOT_B & TOPO_MASK):  return (~b) & 0xFFFFFFFF  # NOT(B) standalone-safe
        if topo == (GS_NOT  & TOPO_MASK):  return (~a) & 0xFFFFFFFF  # NOT(A) legacy
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
    tile_config: Optional[dict] = None,
) -> Union[int, list[int]]:
    """
    Compile and run a 32-bit integer function end-to-end.

    operands: {param_name: integer_value}
    Returns signed 32-bit integer result, or list of bit values for
    single-bit returns.

    tile_config — optional dict mapping tile names to strategy strings.
    Passed through to the compiler's _get_tile() at every placement.
    Default (None or {}) uses each tile's standard strategy.

    Examples:
        # Standard tiles (default):
        result = run_int32_function(src, "add", {"a": 1, "b": 2}, lib)

        # Low-latency division (e.g. MathTrix N-body):
        result = run_int32_function(
            src, "compute", operands, lib,
            tile_config={"MIF_DIV": "low_latency", "MIF_SQRT": "low_latency"}
        )

        # Constant divisor (e.g. MathTrix PageRank):
        result = run_int32_function(
            src, "rank_step", operands, lib,
            tile_config={"MIF_DIV": "const_divisor"}
        )
    """
    from controller import ImagoController

    lib = tile_library or TileLibrary()
    compiler = Int32Compiler(tile_library=lib, tile_config=tile_config)
    records, graph, input_bit_map, output_addrs, segment_spans = (
        compiler.compile_int32_function(source, function_name)
    )

    # Provision bus segments — one per tile placement.
    # This keeps each tile's first-tick NOT cells isolated so their
    # simultaneous emissions don't stack above the 256-lane limit.
    max_seg = max((s for _,_,s in segment_spans), default=0)
    segments = [{"segment_id": sid, "lane_count": 256}
                for sid in range(1, max_seg + 1)]

    # ── Pure-constant function: result baked into known_values ────────────────
    # Functions like collision_flag() that always return a fixed literal have
    # zero cell records — the output bit values are in compiler.known_values
    # at the output addresses.  No controller run needed.
    # Also handles identity functions (return a) where output_addrs == input addrs.
    if not records:
        kv = compiler.known_values or {}
        # Build a combined value map: known_values + direct input bit values
        # (identity/pass-through case where output addresses ARE input addresses)
        all_bit_vals: dict[int, int] = dict(kv)
        for param, value in operands.items():
            bit_addrs = input_bit_map.get(param)
            u = value & 0xFFFFFFFF
            if isinstance(bit_addrs, list):
                for i, addr in enumerate(bit_addrs):
                    all_bit_vals[addr] = (u >> i) & 1
            elif bit_addrs is not None:
                all_bit_vals[bit_addrs] = u & 1
        bits = [all_bit_vals.get(a, 0) for a in output_addrs]
        if len(bits) == 32:
            value = 0
            for i, b in enumerate(bits):
                value |= (b << i)
            # Sign-extend to signed 32-bit
            if value & 0x80000000:
                value -= 0x100000000
            return value
        return bits

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
        elif node.operation == "INPUT" and (node.comment or "").startswith("constant:"):
            # Single-bit constants from _compile_constant (ternary, if/else)
            # comment: "constant: 1" or "constant: 0"
            try:
                bit_val = int(node.comment.split("constant:")[-1].strip())
                b_vals[node.output_addr] = bit_val
            except (ValueError, IndexError):
                pass

    # Broadcast constants (from _broadcast_constant): these are pre-seeded in
    # known_values but also need to arrive as live bus triggers so that MUX and
    # other tile cells that listen on those addresses actually fire.
    # Inject them as b_vals triggers (one shot, value matches known_value bit).
    existing_kv = dict(getattr(compiler, 'known_values', None) or {})
    for kv_addr, kv_val in existing_kv.items():
        if kv_addr not in a_vals and kv_addr not in b_vals:
            b_vals[kv_addr] = 1 if kv_val else 0

    # Preloaded-A pattern: evaluate the KS tree in Python to compute a_data
    # for every binary op cell, then write those values into cells before run.
    #
    # sim_vals holds the current value at each address as we walk records.
    # For op cells in preload_map: a_data = sim_vals[in_a_source_addr].
    # For cells NOT in preload_map (PASS/NOT wires): they propagate normally.
    #
    # Gate state evaluators (operate on 32-bit words).
    from gate_states import GS_AND, GS_OR, GS_XOR, GS_NOT, GS_NOT_B, GS_XNOR, GS_NAND, GS_NOR, GS_PASS, GS_PASS_B, TOPO_MASK
    def _eval_gate(gs: int, a: int, b: int) -> int:
        topo = gs & TOPO_MASK
        if topo == (GS_AND  & TOPO_MASK):  return a & b
        if topo == (GS_OR   & TOPO_MASK):  return a | b
        if topo == (GS_XOR  & TOPO_MASK):  return a ^ b
        if topo == (GS_XNOR & TOPO_MASK):  return (~(a ^ b)) & 0xFFFFFFFF
        if topo == (GS_NAND & TOPO_MASK):  return (~(a & b)) & 0xFFFFFFFF
        if topo == (GS_NOR  & TOPO_MASK):  return (~(a | b)) & 0xFFFFFFFF
        if topo == (GS_NOT_B & TOPO_MASK):  return (~b) & 0xFFFFFFFF  # NOT(B) standalone-safe
        if topo == (GS_NOT  & TOPO_MASK):  return (~a) & 0xFFFFFFFF  # NOT(A) legacy
        if topo == (GS_PASS_B & TOPO_MASK): return b
        return b  # GS_PASS and default

    # Collect preload maps accumulated during compilation.
    # _tile_preloads: {placed_out_addr → placed_in_a_src_addr}
    combined_preload: dict[int, int] = {**getattr(compiler, '_tile_preloads', {}), **getattr(compiler, '_ir_preload_map', {})}

    # Forward simulation: walk all records in emit order.
    # Seed sim_vals with 32-bit word values.
    # a_vals already contains 32-bit words (0 or 0xFFFFFFFF per bit).
    # b_vals contains single-bit values (0 or 1) — expand to 32-bit words.
    sim_vals: dict[int, int] = {
        **a_vals,
        **{addr: (0xFFFFFFFF if v else 0) for addr, v in b_vals.items()}
    }
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

    # ── Case 1: no preloads — pure wiring tile (SHR, SHL, NOT, PASS chains) ──
    if not known_preloads and not combined_preload:
        existing_kv = dict(getattr(compiler, 'known_values', None) or {})
        ctrl0 = ImagoController(cell_count=len(records) + 200)
        rid0  = ctrl0.load_map(records, function_name, known_values=existing_kv)
        inputs = {addr: (0xFFFFFFFF if v else 0) for addr, v in {**a_vals, **b_vals}.items()}
        result = ctrl0.run(rid0, inputs=inputs, capture_addresses=output_addrs)

    # ── Case 2 detection ─────────────────────────────────────────────────────
    # If ALL preloaded cells have A-source = a direct input bit (not a computed
    # intermediate), use ordered injection instead of the Python forward sim.
    elif all(
        v in a_vals for v in (compiler._ir_preload_map or {}).values()
    ) if getattr(compiler, '_ir_preload_map', None) else False:
        # Case 2: A-values are direct input bits — build preloaded_a directly
        ir_pm  = getattr(compiler, '_ir_preload_map', {}) or {}
        a_bus  = {addr: (0xFFFFFFFF if v else 0) for addr, v in a_vals.items()}
        b_bus  = {addr: (0xFFFFFFFF if v else 0) for addr, v in b_vals.items()}
        direct_preloads = {
            out_addr: a_bus.get(a_src_addr, 0)
            for out_addr, a_src_addr in ir_pm.items()
        } if ir_pm else known_preloads

        existing_kv = dict(getattr(compiler, 'known_values', None) or {})
        ctrl2 = ImagoController(cell_count=len(records) + 200)
        rid2  = ctrl2.load_map(records, function_name,
                               known_values=existing_kv,
                               preloaded_a={int(k): int(v) & 0xFFFFFFFF
                                            for k, v in direct_preloads.items()} or None)
        inputs = {**a_bus, **b_bus}
        result = ctrl2.run(rid2, inputs=inputs, capture_addresses=output_addrs,
                           max_cycles=50)

    else:
        # Case 3: Python forward sim (KS adder, SUB, EQ, MUX, comparisons)
        existing_kv = dict(getattr(compiler, 'known_values', None) or {})

        ctrl2 = ImagoController(cell_count=len(records) + 500, segments=segments)
        rid2  = ctrl2.load_map(records, function_name, known_values=existing_kv)
        region2 = ctrl2._regions[rid2]
        for start_idx, end_idx, seg_id in segment_spans:
            for cell_addr in region2.cell_addresses[start_idx:end_idx]:
                ctrl2.array.assign_segment(cell_addr, seg_id)

        region2.preloaded_a = {int(k): int(v) & 0xFFFFFFFF
                               for k, v in known_preloads.items()}
        region2._relay_targets.update(a_vals.keys())

        inputs = {**a_vals, **b_vals}
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
    A compiled INT32 function with A-side fixed and ready to accept varying B.

    Created by load_int32_function(). Call run(B_operands) repeatedly
    with different B values without recompiling.

    Architecture:
        load(A) — compile once, fix A-side values.
        run(B)  — re-run forward sim with actual A+B to compute preloads,
                  then inject B trigger wave and return result.

    The forward sim is lightweight (pure Python, no cell array) so re-running
    it per call is fast. The cell array is reused across calls — only the
    preloaded_a values change between runs.

    Note: For purely bitwise ops (AND/OR/XOR/NOT) where preloads don't depend
    on B, the forward sim produces identical results each call but still runs
    correctly. For arithmetic (ADD/SUB) and comparisons the preloads are
    A+B dependent and must be recomputed each call.
    """

    def __init__(self,
                 ctrl: "ImagoController",
                 region_id: str,
                 output_addrs: list,
                 a_vals: dict,            # {addr: bit_value} for A-side inputs
                 b_input_map: dict,       # {param_name: [bit_addrs]} for B params
                 b_const_map: dict,       # {addr: value} for carry-in / constants
                 records: list,           # CellMapRecord list (for forward sim)
                 combined_preload: dict,  # {out_addr: a_src_addr} preload map
                 segment_spans: list,     # for segment assignment
                 function_name: str):
        self._ctrl             = ctrl
        self._region_id        = region_id
        self._output_addrs     = output_addrs
        self._a_vals           = a_vals
        self._b_input_map      = b_input_map
        self._b_const_map      = b_const_map
        self._records          = records
        self._combined_preload = combined_preload
        self._segment_spans    = segment_spans
        self._function_name    = function_name
        self._run_count        = 0

    def run(self, b_operands: dict) -> "Union[int, list[int]]":
        """
        Run with given B operands and return the result.

        b_operands: {param_name: integer_value} for the B-side inputs.
        For ADD: b_operands = {'b': 42}  (a was fixed at load time).
        """
        from typing import Union
        from gate_states import (GS_AND, GS_OR, GS_XOR, GS_NOT, GS_NOT_B,
                                 GS_XNOR, GS_NAND, GS_NOR, GS_PASS, GS_PASS_B,
                                 TOPO_MASK)

        # Build b_vals from B operands
        b_vals: dict[int, int] = {}
        for param, value in b_operands.items():
            bit_addrs = self._b_input_map.get(param)
            u = int(value) & 0xFFFFFFFF
            if isinstance(bit_addrs, list):
                for i, addr in enumerate(bit_addrs):
                    b_vals[addr] = (u >> i) & 1
            elif bit_addrs is not None:
                b_vals[bit_addrs] = u & 1
        b_vals.update(self._b_const_map)

        # Re-run forward sim with actual A+B to compute correct preloads.
        # KS tree preloads are A+B dependent — must recompute each call.
        def _eval(gs, a, b):
            t = gs & TOPO_MASK
            if t == (GS_AND  & TOPO_MASK): return a & b
            if t == (GS_OR   & TOPO_MASK): return a | b
            if t == (GS_XOR  & TOPO_MASK): return a ^ b
            if t == (GS_XNOR & TOPO_MASK): return (~(a ^ b)) & 0xFFFFFFFF
            if t == (GS_NAND & TOPO_MASK): return (~(a & b)) & 0xFFFFFFFF
            if t == (GS_NOR  & TOPO_MASK): return (~(a | b)) & 0xFFFFFFFF
            if t == (GS_NOT_B & TOPO_MASK): return (~b) & 0xFFFFFFFF
            if t == (GS_NOT  & TOPO_MASK):  return (~a) & 0xFFFFFFFF
            if t == (GS_PASS_B & TOPO_MASK): return b
            return b

        sim_vals: dict[int, int] = {
            **self._a_vals,
            **{addr: (0xFFFFFFFF if v else 0) for addr, v in b_vals.items()}
        }
        known_preloads: dict[int, int] = {}

        for rec in self._records:
            in_addr  = rec.input_address
            out_addr = rec.output_address
            gs       = rec.gate_state
            in_val   = sim_vals.get(in_addr, 0)
            if out_addr in self._combined_preload:
                a_src = self._combined_preload[out_addr]
                a_val = sim_vals.get(a_src, 0)
                known_preloads[out_addr] = a_val
                sim_vals[out_addr] = _eval(gs, a_val, in_val)
            else:
                sim_vals[out_addr] = _eval(gs, sim_vals.get(in_addr, 0), in_val)

        # Update region preloads and run
        region = self._ctrl._regions[self._region_id]
        region.preloaded_a = {int(k): int(v) & 0xFFFFFFFF
                              for k, v in known_preloads.items()}

        inputs = {**self._a_vals, **{addr: (0xFFFFFFFF if v else 0)
                                     for addr, v in b_vals.items()}}

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
    tile_config: "Optional[dict]" = None,
) -> "LoadedInt32Function":
    """
    Compile a 32-bit integer function and preload the A-side operands.

    Returns a LoadedInt32Function ready to accept B-side inputs via run().
    The forward simulation is run once with the given A values. Subsequent
    run(b_operands) calls inject B and return results without recompiling.

    tile_config — optional dict mapping tile names to strategy strings.
    Same as run_int32_function. Default (None) uses standard strategies.

    Use this when A is fixed (e.g. a lookup table key, a constant comparand)
    and B varies across many calls.

    Example:
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
    from gate_states import GS_AND, GS_OR, GS_XOR, GS_NOT, GS_NOT_B, GS_XNOR, GS_NAND, GS_NOR, GS_PASS, GS_PASS_B, TOPO_MASK

    lib = tile_library or TileLibrary()
    compiler = Int32Compiler(tile_library=lib, tile_config=tile_config)
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
        elif node.operation == "INPUT" and (node.comment or "").startswith("constant:"):
            # Single-bit constants from _compile_constant (ternary, if/else)
            try:
                b_const_map[node.output_addr] = int(node.comment.split("constant:")[-1].strip())
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
        if topo == (GS_NOT_B & TOPO_MASK):  return (~b) & 0xFFFFFFFF  # NOT(B) standalone-safe
        if topo == (GS_NOT  & TOPO_MASK):  return (~a) & 0xFFFFFFFF  # NOT(A) legacy
        if topo == (GS_PASS_B & TOPO_MASK): return b
        return b

    combined_preload = {**getattr(compiler, '_tile_preloads', {}), **getattr(compiler, '_ir_preload_map', {})}
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
        ctrl             = ctrl,
        region_id        = rid,
        output_addrs     = output_addrs,
        a_vals           = {addr: (0xFFFFFFFF if v else 0) for addr, v in a_vals.items()},
        b_input_map      = b_input_map,
        b_const_map      = b_const_map,
        records          = records,
        combined_preload = combined_preload,
        segment_spans    = segment_spans,
        function_name    = function_name,
    )
