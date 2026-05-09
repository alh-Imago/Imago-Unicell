"""
ir.py — ImagoIR intermediate representation.

ImagoIR is the language-agnostic dependency graph that sits between
source code and the cell map. Every node is one logical operation.
Every edge is a data dependency resolved to a bus address.

The compiler front-end (Python AST → ImagoIR) produces a graph.
The back-end (ImagoIR → CellMapRecord list) assigns addresses and
emits config records.
"""

from dataclasses import dataclass, field
from typing import Optional
from gate_states import OPERATION_TABLE, GS_PASS, GS_NOT, GS_AND, GS_OR, GS_XOR, GS_OUT_POSEDGE


# ── address allocation ────────────────────────────────────────────────────────

class AddressAllocator:
    """Sequential address allocator for IR node outputs."""

    BASE = 0x00001000      # first usable address (0x0 is reserved)

    def __init__(self):
        self._next = self.BASE

    def alloc(self) -> int:
        addr = self._next
        self._next += 1
        return addr

    def alloc_block(self, count: int) -> int:
        """Allocate a contiguous block of `count` addresses. Returns base."""
        base = self._next
        self._next += count
        return base

    def alloc_n(self, n: int) -> list[int]:
        return [self.alloc() for _ in range(n)]


# ── IR node ───────────────────────────────────────────────────────────────────

@dataclass
class IRNode:
    """
    One node in the ImagoIR dependency graph.
    Corresponds to one or more UniCells after address assignment.
    """
    node_id:    str                   # unique name within the graph
    operation:  str                   # operation from OPERATION_TABLE or composite
    input_ids:  list[str]             # node_ids this node reads from
    output_addr: Optional[int] = None # assigned bus address for this node's output
    comment:    str = ""              # human-readable annotation

    def __repr__(self) -> str:
        ins = ", ".join(self.input_ids)
        addr = f"0x{self.output_addr:08X}" if self.output_addr else "unassigned"
        return f"IRNode({self.node_id}: {self.operation}({ins}) → {addr})"


# ── IR graph ──────────────────────────────────────────────────────────────────

class IRGraph:
    """
    A complete ImagoIR dependency graph for one compiled function or program.

    Nodes are ordered — earlier nodes must be evaluated before later ones.
    Input nodes have no input_ids and represent external data injected
    onto the bus before execution.
    Output nodes are the final result addresses the controller reads.
    """

    def __init__(self, name: str = "unnamed"):
        self.name:   str              = name
        self.nodes:  list[IRNode]     = []
        self._index: dict[str, IRNode] = {}
        self._alloc  = AddressAllocator()
        self._counter = 0

    def fresh_id(self, prefix: str = "n") -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"

    def add_input(self, name: str) -> IRNode:
        """Add an external input node (data injected before execution)."""
        node = IRNode(
            node_id   = name,
            operation = "INPUT",
            input_ids = [],
            output_addr = self._alloc.alloc(),
            comment   = f"external input: {name}"
        )
        self.nodes.append(node)
        self._index[name] = node
        return node

    def add_node(
        self,
        operation: str,
        input_ids: list[str],
        name: Optional[str] = None,
        comment: str = ""
    ) -> IRNode:
        """Add a computation node."""
        node_id = name or self.fresh_id(operation.lower())
        node = IRNode(
            node_id   = node_id,
            operation = operation,
            input_ids = input_ids,
            output_addr = self._alloc.alloc(),
            comment   = comment
        )
        self.nodes.append(node)
        self._index[node_id] = node
        return node

    def get(self, node_id: str) -> Optional[IRNode]:
        return self._index.get(node_id)

    def input_nodes(self) -> list[IRNode]:
        return [n for n in self.nodes if n.operation == "INPUT"]

    def output_nodes(self) -> list[IRNode]:
        """Last node(s) — the result(s) the program produces."""
        return [self.nodes[-1]] if self.nodes else []

    def dump(self) -> str:
        lines = [f"IRGraph '{self.name}' — {len(self.nodes)} nodes"]
        for node in self.nodes:
            lines.append(f"  {node}")
        return "\n".join(lines)


# ── IR → CellMapRecord list ───────────────────────────────────────────────────

def lower_to_cell_map(graph: IRGraph) -> list:
    """
    Lower an IRGraph to a flat list of CellMapRecord objects.

    Uses edge separation to resolve bus collisions without PASS pad cells
    wherever possible. When two values target the same address in the same
    clock cycle, the compiler assigns one to the rising edge (default) and
    one to the falling edge (GS_FALL_EDGE), separating them within the cycle
    rather than inserting dummy cells.

    Edge assignment rules (applied automatically, never user-visible):
      - Table/literal injections : falling edge (GS_FALL_EDGE set)
      - Cell outputs             : rising edge (default, no flag needed)
      - Cell-to-cell conflict    : deeper/later cell gets GS_FALL_EDGE;
                                   flagged in compile stats as edge_resolved.

    GS_FALL_EDGE is a hardware timing hint only. The VM parses the bit
    and ignores it — tick-based simulation has no sub-cycle edges.
    GS_LATCH is NOT applied automatically by the compiler; only cells
    explicitly configured for state-holding carry it.

    pad_to_depth is retained for deep trees where depth difference > 1 tick
    (edge separation only buys one half-cycle within a single tick).

    Node depth: the number of cell pipeline stages from the initial
    bus injection to the node's output address. Input nodes have
    depth 0 (they exist on the initial bus before any tick).
    Each CellMapRecord adds exactly one tick of depth.
    """
    from controller import CellMapRecord
    from gate_states import GS_FALL_EDGE

    records = []
    alloc = graph._alloc

    # depth_map: output_address -> pipeline depth
    depth_map: dict[int, int] = {}

    # edge_map: output_address -> 'rising' | 'falling'
    # Tracks which edge each address is already committed to.
    edge_map: dict[int, str] = {}

    # Compile statistics
    stats = {'pad_cells': 0, 'edge_resolved': 0}

    # input nodes have depth 0, rising edge
    for node in graph.nodes:
        if node.operation == "INPUT":
            depth_map[node.output_addr] = 0
            edge_map[node.output_addr] = 'rising'

    def emit(gs, in_addr, out_addr, edge='rising'):
        """Emit one cell and update depth and edge maps.
        
        GS_FALL_EDGE is a hardware timing hint only — applied to gate_state
        so it survives into the image and the Verilog sees it. The VM parses
        the bit but ignores it (tick-based simulation has no sub-cycle edges).
        GS_LATCH is NOT applied here — it is only set on cells explicitly
        configured for state-holding, never on transient combiner cells.
        """
        in_depth = depth_map.get(in_addr, 0)
        if edge == 'falling':
            gs = gs | GS_FALL_EDGE   # hint only — VM ignores, Verilog acts on it
        records.append(CellMapRecord(gs, in_addr, out_addr))
        depth_map[out_addr] = in_depth + 1
        edge_map[out_addr] = edge

    def resolve_edge(addr: int, shared_addr: int) -> str:
        """
        Determine which edge to assign to addr when it shares shared_addr
        with another cell output. Returns 'rising' or 'falling'.
        If the shared address is already committed to rising, assign falling.
        If already falling, must pad (two falling edges still collide).
        """
        existing = edge_map.get(shared_addr)
        if existing == 'rising':
            stats['edge_resolved'] += 1
            return 'falling'
        return 'rising'  # no conflict yet, take rising

    def pad_to_depth(addr: int, target_depth: int) -> int:
        """
        Insert PASS cells to advance addr to target_depth.
        Used when depth difference > 1 tick (edge separation insufficient).
        Returns the new address at target_depth.
        """
        current = addr
        current_depth = depth_map.get(current, 0)
        while current_depth < target_depth:
            next_addr = alloc.alloc()
            stats['pad_cells'] += 1
            emit(GS_PASS, current, next_addr)
            current = next_addr
            current_depth += 1
        return current

    def emit_two_input(op: str, src_a: int, src_b: int, out_addr: int):
        """
        Emit cells for a two-input operation.

        Strategy:
          1. If depths are equal: use edge separation — one cell rising,
             one falling — no pad cells required.
          2. If depths differ by 1: pad the shallower by one PASS cell,
             then use edge separation for the combiner.
          3. If depths differ by > 1: pad_to_depth as before.
        """
        d_a = depth_map.get(src_a, 0)
        d_b = depth_map.get(src_b, 0)
        depth_gap = abs(d_a - d_b)

        if op == "NOR":
            # NOR(A,B): wired-OR(A,B) then NOT
            if depth_gap <= 1:
                # Edge-separate the two inputs at the combiner address
                inter = alloc.alloc()
                if depth_gap == 1:
                    # Pad the shallower by one tick
                    if d_a < d_b:
                        src_a = pad_to_depth(src_a, d_b)
                    else:
                        src_b = pad_to_depth(src_b, d_a)
                edge_b = resolve_edge(src_b, inter)
                emit(GS_PASS, src_a, inter, 'rising')
                emit(GS_PASS, src_b, inter, edge_b)
                emit(GS_NOT, inter, out_addr)
            else:
                target = max(d_a, d_b)
                a_eq = pad_to_depth(src_a, target)
                b_eq = pad_to_depth(src_b, target)
                inter = alloc.alloc()
                emit(GS_PASS, a_eq, inter, 'rising')
                emit(GS_PASS, b_eq, inter, 'falling')
                emit(GS_NOT, inter, out_addr)

        elif op == "OR":
            # OR(A,B) = NOT(NOR(A,B))
            if depth_gap <= 1:
                inter = alloc.alloc()
                nor_out = alloc.alloc()
                if depth_gap == 1:
                    if d_a < d_b:
                        src_a = pad_to_depth(src_a, d_b)
                    else:
                        src_b = pad_to_depth(src_b, d_a)
                edge_b = resolve_edge(src_b, inter)
                emit(GS_PASS, src_a, inter, 'rising')
                emit(GS_PASS, src_b, inter, edge_b)
                emit(GS_NOT, inter, nor_out)
                emit(GS_NOT, nor_out, out_addr)
            else:
                target = max(d_a, d_b)
                a_eq = pad_to_depth(src_a, target)
                b_eq = pad_to_depth(src_b, target)
                inter = alloc.alloc()
                nor_out = alloc.alloc()
                emit(GS_PASS, a_eq, inter, 'rising')
                emit(GS_PASS, b_eq, inter, 'falling')
                emit(GS_NOT, inter, nor_out)
                emit(GS_NOT, nor_out, out_addr)

        elif op == "AND":
            # AND(A,B) = NOR(NOT_A, NOT_B)
            not_a = alloc.alloc()
            not_b = alloc.alloc()
            emit(GS_NOT, src_a, not_a)
            emit(GS_NOT, src_b, not_b)
            d_na = depth_map[not_a]
            d_nb = depth_map[not_b]
            gap = abs(d_na - d_nb)
            if gap <= 1:
                inter = alloc.alloc()
                if gap == 1:
                    if d_na < d_nb:
                        not_a = pad_to_depth(not_a, d_nb)
                    else:
                        not_b = pad_to_depth(not_b, d_na)
                edge_nb = resolve_edge(not_b, inter)
                emit(GS_PASS, not_a, inter, 'rising')
                emit(GS_PASS, not_b, inter, edge_nb)
                emit(GS_NOT, inter, out_addr)
            else:
                target = max(d_na, d_nb)
                na_eq = pad_to_depth(not_a, target)
                nb_eq = pad_to_depth(not_b, target)
                inter = alloc.alloc()
                emit(GS_PASS, na_eq, inter, 'rising')
                emit(GS_PASS, nb_eq, inter, 'falling')
                emit(GS_NOT, inter, out_addr)

        elif op == "NAND":
            # NAND(A,B) = NOT(AND(A,B))
            and_out = alloc.alloc()
            emit_two_input("AND", src_a, src_b, and_out)
            emit(GS_NOT, and_out, out_addr)

        elif op in ("XOR", "XNOR"):
            # XOR(A,B) = OR(AND(A,NOT_B), AND(NOT_A,B))
            # Compute NOT_A and NOT_B
            not_a = alloc.alloc()
            not_b = alloc.alloc()
            emit(GS_NOT, src_a, not_a)
            emit(GS_NOT, src_b, not_b)

            # AND(A, NOT_B) with depth equalisation
            and_ab = alloc.alloc()
            emit_two_input("AND", src_a, not_b, and_ab)

            # AND(NOT_A, B) with depth equalisation
            and_ba = alloc.alloc()
            emit_two_input("AND", not_a, src_b, and_ba)

            # OR(and_ab, and_ba) with depth equalisation
            xor_out = alloc.alloc()
            emit_two_input("OR", and_ab, and_ba, xor_out)

            if op == "XOR":
                emit(GS_PASS, xor_out, out_addr)
            else:  # XNOR = NOT(XOR)
                emit(GS_NOT, xor_out, out_addr)

        else:
            raise ValueError(f"Unhandled two-input op in emit_two_input: {op}")

    for node in graph.nodes:
        if node.operation == "INPUT":
            continue

        # MODEL: nodes are model library references — handled by the
        # compile_function caller, not by single-bit IR lowering.
        # They appear in the graph for dependency tracking only.
        if node.operation.startswith("MODEL:"):
            continue

        if node.operation not in OPERATION_TABLE and node.operation != "INPUT":
            raise ValueError(
                f"Unknown operation '{node.operation}' in node '{node.node_id}'."
            )

        gs, num_inputs = OPERATION_TABLE[node.operation]
        input_nodes = [graph.get(iid) for iid in node.input_ids]

        if num_inputs == 1:
            src = input_nodes[0].output_addr
            emit(gs, src, node.output_addr)

        elif num_inputs == 2:
            src_a = input_nodes[0].output_addr
            src_b = input_nodes[1].output_addr
            emit_two_input(node.operation, src_a, src_b, node.output_addr)

        else:
            raise ValueError(
                f"Unsupported input count {num_inputs} for op '{node.operation}'"
            )

    return records


# ── v2 IR lowering ────────────────────────────────────────────────────────────

def lower_to_cell_map_v2(graph: IRGraph) -> list:
    """
    Lower an IRGraph to CellRecord_v2 instances.

    v2 change: ALL binary logic ops (AND, OR, XOR, XNOR, NOR, NAND)
    are single cells with two input addresses.

    No multi-cell chains. No pad cells for binary ops. No edge resolution
    for binary ops. A arrives on rising edge, B on falling edge -- the
    cell handles the timing internally.

    Only arithmetic (ADD, SUB) still requires multi-cell tiles.

    Returns list of CellRecord_v2.
    """
    # Use CellMapRecord from v1 but with input_b_address field (added in v2 migration)
    # This avoids a cross-directory import dependency.
    from controller import CellMapRecord as CellRecord_v2
    from gate_states import (
        GS_PASS, GS_NOT, GS_SYNC_WAIT, LOOP_MODE,
        GS_AND_V2  as GS_AND,
        GS_OR_V2   as GS_OR,
        GS_OR_V2,
        GS_NOR_V2  as GS_NOR,
        GS_NAND_V2 as GS_NAND,
        GS_XOR_V2  as GS_XOR,
        GS_XNOR_V2 as GS_XNOR,
        GS_ZERO_V2 as GS_ZERO,
        GS_ONE_V2  as GS_ONE,
    )

    # v2 operation table: op -> (gate_state, num_inputs)
    # OR uses wired-OR bus (no SYNC_WAIT): both inputs write to same address,
    # bus naturally OR's them. This preserves v1 loop accumulation semantics.
    # AND/XOR/XNOR use SYNC_WAIT (true two-input, separate addresses).
    # NOR = single-cell NOT of wired-OR (no SYNC_WAIT needed).
    V2_OPS = {
        "PASS":  (GS_PASS,                1),
        "NOT":   (0b000000001,            1),   # NOR(A,A) = NOT(A), B=0 safe
        "NOR":   (GS_NOR,                 1),   # NOT of wired-OR on single address
        "OR":    (GS_PASS,                1),   # wired-OR: both inputs same address
        "AND":   (GS_AND  | GS_SYNC_WAIT, 2),
        "NAND":  (GS_NAND | GS_SYNC_WAIT, 2),
        "XOR":   (GS_XOR  | GS_SYNC_WAIT, 2),
        "XNOR":  (GS_XNOR | GS_SYNC_WAIT, 2),
        "ZERO":  (GS_ZERO,                1),
        "ONE":   (GS_ONE,                 1),
    }

    records = []
    depth_map: dict[int, int] = {}
    stats   = {'cells': 0, 'two_input': 0}

    for node in graph.nodes:
        if node.operation == "INPUT":
            depth_map[node.output_addr] = 0
            continue

        if node.operation.startswith("MODEL:"):
            continue

        if node.operation not in V2_OPS:
            raise ValueError(
                f"Unknown v2 operation '{node.operation}' "
                f"in node '{node.node_id}'. "
                f"Supported: {sorted(V2_OPS)}"
            )

        gs, num_inputs = V2_OPS[node.operation]
        input_nodes = [graph.get(iid) for iid in node.input_ids]

        if node.operation == "OR" and len(input_nodes) == 2:
            # OR(A, B) using single-cell GS_OR with GS_SYNC_WAIT.
            # Depth-align inputs first so both arrive in the same tick.
            # This is the silicon-honest approach -- the cell fires once
            # when both A and B have arrived, not multiple times.
            src_a = input_nodes[0].output_addr
            src_b = input_nodes[1].output_addr
            d_a = depth_map.get(src_a, 0)
            d_b = depth_map.get(src_b, 0)

            # Align depths with PASS pad cells
            while d_a < d_b:
                pad = graph._alloc.alloc()
                records.append(CellRecord_v2(
                    gate_state=GS_PASS | GS_OUT_POSEDGE, input_address=src_a, output_address=pad))
                depth_map[pad] = d_a + 1
                src_a = pad; d_a += 1
            while d_b < d_a:
                pad = graph._alloc.alloc()
                records.append(CellRecord_v2(
                    gate_state=GS_PASS | GS_OUT_POSEDGE, input_address=src_b, output_address=pad))
                depth_map[pad] = d_b + 1
                src_b = pad; d_b += 1

            # Single-cell OR with SYNC_WAIT -- fires once when both arrive
            records.append(CellRecord_v2(
                gate_state      = GS_OR_V2 | GS_SYNC_WAIT | GS_OUT_POSEDGE,
                input_address   = src_a,
                input_b_address = src_b,
                output_address  = node.output_addr,
            ))
            depth_map[node.output_addr] = d_a + 1
            stats['cells'] += 1 + abs(depth_map.get(
                input_nodes[0].output_addr, 0) -
                depth_map.get(input_nodes[1].output_addr, 0))
            stats['two_input'] += 1

        elif num_inputs == 1:
            src_a = input_nodes[0].output_addr
            records.append(CellRecord_v2(
                gate_state      = gs | GS_OUT_POSEDGE,
                input_address   = src_a,
                output_address  = node.output_addr,
            ))
            depth_map[node.output_addr] = depth_map.get(src_a, 0) + 1
            stats['cells'] += 1

        elif num_inputs == 2:
            src_a = input_nodes[0].output_addr
            src_b = input_nodes[1].output_addr
            d = max(depth_map.get(src_a, 0), depth_map.get(src_b, 0)) + 1

            # v2: single cell, A=rising, B=falling
            records.append(CellRecord_v2(
                gate_state      = gs | GS_OUT_POSEDGE,
                input_address   = src_a,
                input_b_address = src_b,
                output_address  = node.output_addr,
            ))
            depth_map[node.output_addr] = d
            stats['cells'] += 1
            stats['two_input'] += 1

    return records, stats
