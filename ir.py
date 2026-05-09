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
from gate_states import OPERATION_TABLE, GS_PASS, GS_NOT, GS_AND_V2, GS_OR_V2, GS_XOR_V2, GS_NAND_V2, GS_XNOR_V2, GS_NOR_V2


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
    """DEPRECATED: delegates to lower_to_cell_map_v2().
    Returns list only (not tuple) for backward compatibility.
    Will be removed in a future cleanup.
    """
    import warnings
    warnings.warn(
        "lower_to_cell_map() is deprecated -- use lower_to_cell_map_v2()",
        DeprecationWarning, stacklevel=2
    )
    records, _stats = lower_to_cell_map_v2(graph)
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
        "AND":   (GS_AND_V2  | GS_SYNC_WAIT, 2),
        "NAND":  (GS_NAND_V2 | GS_SYNC_WAIT, 2),
        "XOR":   (GS_XOR_V2  | GS_SYNC_WAIT, 2),
        "XNOR":  (GS_XNOR_V2 | GS_SYNC_WAIT, 2),
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
                    gate_state=GS_PASS, input_address=src_a, output_address=pad))
                depth_map[pad] = d_a + 1
                src_a = pad; d_a += 1
            while d_b < d_a:
                pad = graph._alloc.alloc()
                records.append(CellRecord_v2(
                    gate_state=GS_PASS, input_address=src_b, output_address=pad))
                depth_map[pad] = d_b + 1
                src_b = pad; d_b += 1

            # Single-cell OR with SYNC_WAIT -- fires once when both arrive
            records.append(CellRecord_v2(
                gate_state      = GS_OR_V2 | GS_SYNC_WAIT,
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
                gate_state      = gs,
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
                gate_state      = gs,
                input_address   = src_a,
                input_b_address = src_b,
                output_address  = node.output_addr,
            ))
            depth_map[node.output_addr] = d
            stats['cells'] += 1
            stats['two_input'] += 1

    return records, stats
