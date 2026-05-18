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
from gate_states import OPERATION_TABLE, GS_PASS, GS_PASS_B, GS_NOT, GS_AND_V2, GS_OR_V2, GS_XOR_V2, GS_NAND_V2, GS_XNOR_V2, GS_NOR_V2, GS_LATCH_IN


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
    Lower an IRGraph to a list of CellMapRecord instances.

    Two-arrival model (silicon-confirmed 2026-05-17):
      ALL binary ops (AND, OR, XOR, XNOR, NOR, NAND) are single cells.
      A arrives first at input_address (stored in a_data).
      B arrives second at the SAME input_address (triggers fire).
      The compiler emits Y-formation routing so both arrive correctly.

      No pad cells needed. No GS_SYNC_WAIT. No input_b_address.
      No GS_OUT_POSEDGE. Depth alignment is not required because
      both inputs arrive sequentially at the same address.

    Operation table maps to topology bits (gate_states.py constants).
    Single-input ops send A twice (NOT: NOR(A,A) = NOT(A)).
    """
    from controller import CellMapRecord
    from gate_states import (
        GS_PASS, GS_PASS_B, GS_NOT,
        GS_AND_V2  as GS_AND,
        GS_OR_V2   as GS_OR,
        GS_NOR_V2  as GS_NOR,
        GS_NAND_V2 as GS_NAND,
        GS_XOR_V2  as GS_XOR,
        GS_XNOR_V2 as GS_XNOR,
        GS_ZERO_V2 as GS_ZERO,
        GS_ONE_V2  as GS_ONE,
        GS_LATCH_IN,
    )

    # Operation table: op -> (gate_state, num_inputs)
    # Two-arrival model: cell holds A in a_data and waits for B.
    # No relay cells, no delay cells, no depth alignment needed.
    # Single-input ops: controller injects value twice (A=B=value).
    # Binary ops: controller injects A first, then B at same address.
    OPS = {
        "PASS":  (GS_PASS_B | GS_LATCH_IN, 1),  # relay-style: fires on single arrival
        "NOT":   (GS_NOT,   1),
        "NOR":   (GS_NOR,   2),
        "OR":    (GS_OR,    2),
        "AND":   (GS_AND,   2),
        "NAND":  (GS_NAND,  2),
        "XOR":   (GS_XOR,   2),
        "XNOR":  (GS_XNOR,  2),
        "ZERO":  (GS_ZERO,  1),
        "ONE":   (GS_ONE,   1),
    }

    records = []
    depth_map: dict[int, int] = {}
    stats = {"cells": 0, "two_input": 0}

    for node in graph.nodes:
        if node.operation == "INPUT":
            depth_map[node.output_addr] = 0
            continue

        if node.operation.startswith("MODEL:"):
            continue

        if node.operation not in OPS:
            raise ValueError(
                f"Unknown operation '{node.operation}' in node '{node.node_id}'. "
                f"Supported: {sorted(OPS)}"
            )

        gs, num_inputs = OPS[node.operation]
        input_nodes = [graph.get(iid) for iid in node.input_ids]

        # Cell listens on src_a (A's address). Two-arrival: A first, B second.
        # For binary ops: emit a PASS_B|latch_in relay from src_b → src_a.
        # Relay pre-armed (a_arrived=True in load_map) fires on single arrival from B,
        # delivering B to src_a as the second arrival. No controller re-injection needed
        # at src_a — relay handles it. Controller only re-injects single-input sources.
        src_a = input_nodes[0].output_addr if input_nodes else graph._alloc.alloc()
        d_a = depth_map.get(src_a, 0)

        if num_inputs == 2 and len(input_nodes) >= 2:
            src_b = input_nodes[1].output_addr
            records.append(CellMapRecord(
                gate_state    = GS_PASS_B | GS_LATCH_IN,
                input_address = src_b,
                output_address= src_a,
            ))
            stats["cells"] += 1

        records.append(CellMapRecord(
            gate_state    = gs,
            input_address = src_a,
            output_address= node.output_addr,
        ))
        depth_map[node.output_addr] = d_a + 1
        stats["cells"] += 1
        if num_inputs == 2:
            stats["two_input"] += 1

    return records, stats
