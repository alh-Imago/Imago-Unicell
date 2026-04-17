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
from gate_states import OPERATION_TABLE, GS_PASS, GS_NOT, GS_AND, GS_OR, GS_XOR


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

    Uses depth-tracking to ensure all paths to any wired-OR combiner
    have equal pipeline depth. PASS cells are inserted to pad shorter
    paths. This guarantees one-fire correctness: every cell sees a
    complete combined value at its input address before firing.

    Node depth: the number of cell pipeline stages from the initial
    bus injection to the node's output address. Input nodes have
    depth 0 (they exist on the initial bus before any tick).
    Each CellMapRecord adds exactly one tick of depth.
    """
    from controller import CellMapRecord

    records = []
    alloc = graph._alloc

    # depth_map: output_address -> pipeline depth
    depth_map: dict[int, int] = {}

    # input nodes have depth 0
    for node in graph.nodes:
        if node.operation == "INPUT":
            depth_map[node.output_addr] = 0

    def emit(gs, in_addr, out_addr):
        """Emit one cell and update depth map."""
        in_depth = depth_map.get(in_addr, 0)
        records.append(CellMapRecord(gs, in_addr, out_addr))
        depth_map[out_addr] = in_depth + 1

    def pad_to_depth(addr: int, target_depth: int) -> int:
        """
        Insert PASS cells to advance addr to target_depth.
        Returns the new address at target_depth.
        """
        current = addr
        current_depth = depth_map.get(current, 0)
        while current_depth < target_depth:
            next_addr = alloc.alloc()
            emit(GS_PASS, current, next_addr)
            current = next_addr
            current_depth += 1
        return current

    def emit_two_input(op: str, src_a: int, src_b: int, out_addr: int):
        """
        Emit cells for a two-input operation with depth equalisation.
        Both inputs are padded to equal depth before the wired-OR combiner.
        """
        d_a = depth_map.get(src_a, 0)
        d_b = depth_map.get(src_b, 0)

        if op == "NOR":
            # NOR(A,B): wired-OR(A,B) then NOT
            # Equalise depths
            target = max(d_a, d_b)
            a_eq = pad_to_depth(src_a, target)
            b_eq = pad_to_depth(src_b, target)
            inter = alloc.alloc()
            emit(GS_PASS, a_eq, inter)
            emit(GS_PASS, b_eq, inter)
            emit(GS_NOT, inter, out_addr)

        elif op == "OR":
            # OR(A,B) = NOT(NOR(A,B))
            target = max(d_a, d_b)
            a_eq = pad_to_depth(src_a, target)
            b_eq = pad_to_depth(src_b, target)
            inter = alloc.alloc()
            nor_out = alloc.alloc()
            emit(GS_PASS, a_eq, inter)
            emit(GS_PASS, b_eq, inter)
            emit(GS_NOT, inter, nor_out)
            emit(GS_NOT, nor_out, out_addr)

        elif op == "AND":
            # AND(A,B) = NOR(NOT_A, NOT_B)
            not_a = alloc.alloc()
            not_b = alloc.alloc()
            emit(GS_NOT, src_a, not_a)
            emit(GS_NOT, src_b, not_b)
            # Equalise after NOT cells
            d_na = depth_map[not_a]
            d_nb = depth_map[not_b]
            target = max(d_na, d_nb)
            na_eq = pad_to_depth(not_a, target)
            nb_eq = pad_to_depth(not_b, target)
            inter = alloc.alloc()
            emit(GS_PASS, na_eq, inter)
            emit(GS_PASS, nb_eq, inter)
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
