"""
fixed_structures_v1.py — points.md #807: the BRAM / DSP FIXED STRUCTURES as a model the compiler can
size, place and check -- the dispatch tree, the gather tree, and the sentinel at the head and tail of a
chain -- built from the project's own proven RTL and design entries, not from a paraphrase.

POLICY (points.md #263, Alan): the BRAM/DSP interface (mux / combiner / splitter / bram_controller) is a
FIXED, BOUNDED, deliberately NON-PORTABLE addon unit. M20K blocks and DSP units are physical resources at
fixed positions on the die; the rest of the fabric stays uniform. So these are SET-PIECES with fixed ports
and fixed sites, sized by how many feeds a design needs -- not ordinary cells.

WHAT IS MODELLED, AND ITS GROUND TRUTH
  * DISPATCH TREE (BRAM -> chains). `mem_read_splitter_v1` splits every 40-bit BRAM word into
    {8-bit ROUTING, 32-bit DATA}. DATA follows the ordinary cardinal path; ROUTING steers a tree of
    `mux_cell_v1` nodes. EVERY node has exactly THREE usable faces (one of its four is consumed by the
    RAM-facing connection -- the correction `#258` made before any RTL existed), so reaching more than 3
    feeds needs a real TREE. Depth therefore VARIES WITH THE NUMBER OF FEEDS: at most 3 levels x 3-way
    branching = 27 destinations.
  * ROUTING BYTE (RTL: `mux_cell_v1.v`): [7:6] count = the number of dynamic levels (0-3); [5:4] slot1,
    [3:2] slot2, [1:0] slot3, each a 2-bit face code (00/01/10 = the node's three faces; 11 is invalid).
    A node reads the slot INDEXED BY THE CURRENT COUNT, selects that face, and forwards the byte with
    only `count` decremented (no shifting). The root therefore reads slot L, the next node slot L-1, ...
  * GATHER TREE (chains -> BRAM): the exact mirror (`combiner_cell_v2` + `combiner_relay_v1`). The
    innermost node starts count at 1 and writes its face into slot1; each parent increments count and
    writes its own face into the slot matching the NEW count. The root writes the completed byte to BRAM
    beside the data, so a result is stamped with the destination it came from.
  * SENTINEL (`sentinel_counter_v1`, ported in `sentinel_bram_automaton_v1`): sits at the HEAD of a
    chain (feed_pulse: an arrival) and at its TAIL (collect_pulse: a result leaving); its running
    difference is the number of items in flight, it latches error on underflow / overflow (diff >=
    2 x chain_length), and reports need_data / results_ready / safe_to_intervene to the host.

VERIFIED AGAINST HARDWARE-PROVEN VALUES. The 2-level, 5-destination mux tree of `tb_mux_tree2_v1.v`
(`#271`) produces routing bytes 0x40, 0x50, 0x88, 0x98, 0xA8, and the 2-level combiner tree of
`tb_combiner_tree2_v1.v` (`#272`) stamps 0x40, 0x50, 0x88, 0x98 -- this module reproduces all of them.

REAL, HONEST LIMITS
  * PHYSICAL FACES ARE NOT ASSIGNED HERE. The model works in face CODES (0, 1, 2). In the proven build a
    node with upstream W maps code 0/1/2 to N/S/E (`DEFAULT_SLOT_FACES`); which physical direction each
    code takes is a per-node CONFIG (`face_for_slotN`), which is exactly what a placer that chooses
    cardinality by routing would emit. Grid placement of the trees is NOT built yet.
  * The streaming harness is PROTOCOL-LEVEL (routing, ordering, sentinel accounting, result correctness),
    the same abstraction `sentinel_bram_automaton_v1` states for itself -- not cycle-for-cycle RTL timing.
  * BRAM/DSP are simulated only as far as the existing automata reach; nothing here has been through
    Quartus or hardware.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sentinel_bram_automaton_v1 import Sentinel, SharedBram  # noqa: E402

MAX_LEVELS = 3
FACES_PER_NODE = 3
MAX_FEEDS = FACES_PER_NODE ** MAX_LEVELS                  # 27
#: face code -> direction for a node whose UPSTREAM face is W: the configuration the proven #271/#273
#: builds use (`face_for_slot0 = N, slot1 = S, slot2 = E`). A per-node config in general.
DEFAULT_SLOT_FACES = {0: "n", 1: "s", 2: "e"}
#: which routing-byte bits hold the slot a node reads when the CURRENT count is c
_SLOT_SHIFT = {1: 4, 2: 2, 3: 0}


class TreeError(ValueError):
    """A routing byte or tree request that the hardware could not honour. Loud by design."""


def levels_for(n: int) -> int:
    """Levels of mux/combiner nodes needed to reach `n` feeds: ceil(log3 n), 0 for a single feed (no tree
    at all: count 0 = zero dynamic levels), and an error beyond 27 (3 levels x 3 faces)."""
    if n < 1:
        raise TreeError("a tree needs at least one feed")
    if n == 1:
        return 0
    if n > MAX_FEEDS:
        raise TreeError(f"{n} feeds exceed the {MAX_FEEDS} the 2-bit level count can address "
                        f"({MAX_LEVELS} levels x {FACES_PER_NODE} faces); deeper trees would need a wider count field "
                        f"(the design, points.md #258, deliberately kept it at 2 bits)")
    level, capacity = 1, FACES_PER_NODE
    while capacity < n:
        level += 1
        capacity *= FACES_PER_NODE
    return level


@dataclass
class TreeNode:
    index: int
    level: int                                               # 1 = the root
    parent: Optional[Tuple[int, int]]                        # (parent index, the parent's face code)
    #: per face code 0..2: ("leaf", destination) | ("node", child index) | None (an unused face)
    slots: List[Optional[Tuple[str, int]]] = field(default_factory=lambda: [None, None, None])


@dataclass
class DistributionTree:
    n: int
    nodes: List[TreeNode]
    #: destination -> face codes from the root to that destination
    paths: Dict[int, List[int]]

    @property
    def levels(self) -> int:
        return max((len(p) for p in self.paths.values()), default=0)

    @property
    def node_count(self) -> int:
        return len(self.nodes)


def build_tree(n: int) -> DistributionTree:
    """The shallowest tree with `n` destinations. Start from a root (3 faces); while there are too few faces,
    turn the SHALLOWEST unused face into a child node (which consumes one face and adds three: net +2),
    preferring the highest face code -- so 5 destinations is exactly the proven #271 tree (root: leaf, leaf,
    child; child: leaf, leaf, leaf). Destinations are numbered in depth-first, ascending-code order."""
    levels_for(n)                                            # validates
    if n == 1:
        return DistributionTree(1, [], {0: []})
    nodes = [TreeNode(0, 1, None)]
    capacity = FACES_PER_NODE
    while capacity < n:
        free = sorted(((nd.level, nd.index, -code) for nd in nodes for code in range(3) if nd.slots[code] is None))
        level, idx, negcode = free[0]
        code = -negcode
        child = TreeNode(len(nodes), level + 1, (idx, code))
        nodes.append(child)
        nodes[idx].slots[code] = ("node", child.index)
        capacity += FACES_PER_NODE - 1
    paths: Dict[int, List[int]] = {}
    counter = [0]

    def walk(node: TreeNode, prefix: List[int]) -> None:
        for code in range(3):
            slot = node.slots[code]
            if slot is not None and slot[0] == "node":
                walk(nodes[slot[1]], prefix + [code])
            elif counter[0] < n:
                node.slots[code] = ("leaf", counter[0])
                paths[counter[0]] = prefix + [code]
                counter[0] += 1
    walk(nodes[0], [])
    return DistributionTree(n, nodes, paths)


# ---------------------------------------------------------------------------
# The bus: the design was built around the Arria 10's 40-bit M20K word
# ---------------------------------------------------------------------------

ROUTING_FIELD_BITS = 8                      # as BUILT: 2-bit count + three 2-bit slots (points.md #258)


class BusError(ValueError):
    """The card's BRAM word cannot carry what this design needs. Loud by design."""


@dataclass(frozen=True)
class BusPlan:
    feeds: int
    width: int
    routing_bits: int
    data_bits: int
    beats: int                          # bus words needed per 32-bit value
    store_and_shift: bool               # True when a value must be assembled/disassembled from several words
    notes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class BusSpec:
    """The BRAM word the fixed structures ride on. `width` is the card's port width (the Arria 10 M20K's
    native 40 bits: 8 ROUTING + 32 DATA, points.md #259/#265); other cards differ, so it is a PARAMETER.

    A design with one feed needs NO routing (no tree, count 0), so the whole word is data. With a tree, the
    routing field is `ROUTING_FIELD_BITS` (8) as built; `fixed_routing_field=False` models a proposed RTL
    parameterisation that spends only 2 + 2 x levels bits. When the data bits left are fewer than a 32-bit
    value, the value is carried in several words (`beats`) and needs a STORE-AND-SHIFT stage to assemble it
    (and disassemble it on the way back)."""
    width: int = 40
    word_bits: int = 32
    fixed_routing_field: bool = True

    def routing_bits(self, feeds: int) -> int:
        levels = levels_for(feeds)
        if levels == 0:
            return 0
        return ROUTING_FIELD_BITS if self.fixed_routing_field else 2 + 2 * levels

    def plan(self, feeds: int) -> BusPlan:
        rb = self.routing_bits(feeds)
        data = self.width - rb
        if data < 1:
            raise BusError(f"a {self.width}-bit word leaves no data bits after {rb} routing bits for {feeds} feeds")
        beats = -(-self.word_bits // data)
        notes = []
        if feeds == 1 and rb == 0 and self.width != 40:
            notes.append("one chain needs no routing byte: the RTL as built always splits {8 routing, 32 data}, so "
                         "dropping it is an RTL VARIANT that does not exist yet")
        if beats > 1:
            notes.append(f"a {self.word_bits}-bit value needs {beats} beats of {data} data bits: a store-and-shift "
                         f"assembler on the read side and a disassembler on the write side, ~{beats}x the latency "
                         f"-- a PROPOSED stage, no RTL exists")
        if self.width != 40:
            notes.append("splitter/mux/combiner RTL is written for a 40-bit word; another width needs it "
                         "parameterised -- not built")
        return BusPlan(feeds, self.width, rb, data, beats, beats > 1, tuple(notes))

    def max_feeds(self, min_data_bits: int = 1) -> int:
        """The most feeds this bus can carry while leaving at least `min_data_bits` of data per beat."""
        best = 0
        for n in range(1, MAX_FEEDS + 1):
            try:
                if self.plan(n).data_bits >= min_data_bits:
                    best = n
            except BusError:
                pass
        return best


# ---------------------------------------------------------------------------
# Routing bytes: the exact encode / decode of mux_cell_v1 / combiner_cell_v2
# ---------------------------------------------------------------------------

def dispatch_id(tree: DistributionTree, dest: int) -> int:
    """The routing byte that steers the BRAM word to `dest`: count = the path length, and the root's face
    code goes in slot[count], the next node's in slot[count-1], ... the last node's in slot1."""
    path = tree.paths[dest]
    count = len(path)
    byte = count << 6
    for i, code in enumerate(path):
        byte |= code << _SLOT_SHIFT[count - i]
    return byte


def mux_decode(tree: DistributionTree, byte: int) -> int:
    """Walk the tree exactly as the hardware does (mux_cell_v1.v lines 139-149): at each node read the
    slot INDEXED BY THE CURRENT COUNT, take that face, forward the byte with count decremented. Returns the
    destination; raises `TreeError` for anything the RTL treats as invalid."""
    count = (byte >> 6) & 3
    if not tree.nodes:
        if count != 0:
            raise TreeError("a single-feed 'tree' has no nodes to route through")
        return 0
    node = tree.nodes[0]
    while True:
        if count == 0:
            raise TreeError("count 0 on arrival at a node: routing was already complete (not a valid arrival)")
        code = (byte >> _SLOT_SHIFT[count]) & 3
        if code == 3:
            raise TreeError("slot code 11 is unused/invalid (3 real faces, 4 possible codes)")
        slot = node.slots[code]
        count -= 1
        if slot is None:
            raise TreeError(f"face code {code} of node {node.index} is unused")
        if slot[0] == "leaf":
            if count != 0:
                raise TreeError("routing byte asks for more levels than the path has")
            return slot[1]
        node = tree.nodes[slot[1]]


def gather_stamp(tree: DistributionTree, dest: int) -> int:
    """The byte the GATHER tree stamps on a result from `dest` -- built by the write-side rule, not by
    reusing dispatch_id: the innermost node starts count at 1 and writes its face into slot1; each parent
    increments count and writes its own face into the slot matching the NEW count."""
    path = tree.paths[dest]
    count = 0
    byte = 0
    for code in reversed(path):                              # innermost node first, root last
        count += 1
        byte |= code << _SLOT_SHIFT[count]
    return (count << 6) | byte


# ---------------------------------------------------------------------------
# The set-piece library
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SetPiece:
    kind: str
    rtl_module: str
    #: how many of its four faces the design can USE (the rest are consumed by the fixed connection)
    usable_faces: int
    #: does it sit on a grid position? (the sentinel and address counter are connection logic with no cell)
    grid_cell: bool
    #: the fixed card resource it must sit on, if any
    site_kind: Optional[str]
    source: str


SET_PIECES: Dict[str, SetPiece] = {p.kind: p for p in (
    SetPiece("mux", "mux_cell_v1", 3, True, None, "#258 (3 faces), #266, #271"),
    SetPiece("combiner", "combiner_cell_v2", 3, True, None, "#258, #268, #272 (root; slots 0-2)"),
    SetPiece("combiner_relay", "combiner_relay_v1", 3, True, None, "#272 (a child of the combiner root)"),
    SetPiece("splitter", "mem_read_splitter_v1", 1, True, "bram", "#257/#258, #260: {8 ROUTING, 32 DATA} split"),
    SetPiece("bram_controller", "bram_controller_v1", 1, True, "bram", "#259/#265: 65536 x 40 bit, 128 M20K"),
    SetPiece("sentinel", "sentinel_counter_v1", 0, False, None, "#291-#308, #410-#415: head feed / tail collect"),
    SetPiece("addr_counter", "addr_counter_v1", 0, False, None, "#409-#415: per-chain block-partitioned address"),
    SetPiece("dsp_add", "dsp_add_wrapper", 3, True, "dsp", "dsp_wrapper_automaton_v1 op ADD"),
    SetPiece("dsp_arith", "dsp_arith_wrapper", 3, True, "dsp", "dsp_wrapper_automaton_v1 ops ADD/SUB/MUL"),
    SetPiece("dsp_compare", "dsp_compare_wrapper", 3, True, "dsp", "dsp_wrapper_automaton_v1 ops GE/LE/NEQ"),
)}

#: DAG op (and icmp predicate) -> the DSP wrapper op that implements it. Only these six exist.
DSP_OPS = {("add", None): "ADD", ("sub", None): "SUB", ("mul", None): "MUL",
           ("icmp", "sge"): "GE", ("icmp", "sle"): "LE", ("icmp", "ne"): "NEQ"}


def dsp_op_for(opcode: str, predicate: Optional[str] = None) -> Optional[str]:
    """The DSP wrapper op for a DAG op, or None if the DSP cannot do it (so it stays in logic)."""
    return DSP_OPS.get((opcode, predicate if opcode == "icmp" else None))


@dataclass
class SentinelSpec:
    """A sentinel at the head and tail of ONE chain. `feed_at` are the chain's head ports (arrivals) and
    `collect_at` its tail (a result leaving). `chain_length` sets the overflow bound: diff >= 2 x chain_length."""
    chain_length: int = 1
    feed_at: List[Tuple[int, int]] = field(default_factory=list)
    collect_at: Optional[Tuple[int, int]] = None


def sentinel_for(result, chain_length: int = 1) -> SentinelSpec:
    """Attach the sentinel to a compiled chain: feeds at its injection sites, collect at its result cell."""
    heads = [site for sites in result.arg_injections.values() for site in sites]
    return SentinelSpec(chain_length=chain_length, feed_at=heads, collect_at=result.result_cell)


@dataclass
class StreamPlan:
    """What a BRAM-fed, N-chain deployment of one compiled design needs."""
    chains: int
    levels: int
    dispatch_nodes: int
    gather_nodes: int
    chain_cells: int
    grid_cells: int                     # chains + mux + combiner + splitter + controller
    sentinels: int                      # connection logic, not grid cells
    bram_sites: int                     # the splitter and the controller each sit on a BRAM site
    notes: List[str] = field(default_factory=list)


def plan_stream(result, chains: int) -> StreamPlan:
    tree = build_tree(chains)
    chain_cells = len(result.records)
    grid = chains * chain_cells + 2 * tree.node_count + 2                 # + splitter + bram controller
    return StreamPlan(chains=chains, levels=levels_for(chains), dispatch_nodes=tree.node_count,
                      gather_nodes=tree.node_count, chain_cells=chain_cells, grid_cells=grid,
                      sentinels=chains, bram_sites=2,
                      notes=["cell count only: placing the trees and chains on the grid is not built, so this is a "
                             "LOWER BOUND on the array the toolchain must instantiate"])


# ---------------------------------------------------------------------------
# Protocol-level streaming: BRAM -> dispatch tree -> chain -> gather tree -> BRAM
# ---------------------------------------------------------------------------

@dataclass
class StreamResult:
    outputs: List[Tuple[int, int, int]]          # (destination chain, gather stamp, value), in input order
    sentinels_safe: bool
    sentinel_errors: List[str]
    levels: int
    dispatch_nodes: int
    gather_nodes: int
    bram_out: SharedBram


def run_stream(result, inputs: List[Dict[str, int]], chains: int, *, chain_length: int = 1,
               destinations: Optional[List[int]] = None, run_chain=None) -> StreamResult:
    """Stream `inputs` through `chains` replicas of a compiled design. Each input becomes a BRAM word
    {routing byte, data}; the routing byte is decoded by walking the dispatch tree exactly as the RTL does;
    the chosen chain's sentinel sees a FEED at its head and a COLLECT at its tail; the result is stamped by
    the gather tree's write-side rule, so it can be matched back to the destination it came from. At the end
    every chain's out-wrap is pulsed and each sentinel must report safe_to_intervene with no error latched."""
    if run_chain is None:
        import llvm_dag_frontend_v1 as F
        run_chain = F.run_in_vm
    tree = build_tree(chains)
    dests = destinations or [i % chains for i in range(len(inputs))]
    sentinels = [Sentinel(chain_length=chain_length, out_frozen=False) for _ in range(chains)]
    bram_out = SharedBram()
    outputs: List[Tuple[int, int, int]] = []
    errors: List[str] = []
    for i, (args, want) in enumerate(zip(inputs, dests)):
        byte = dispatch_id(tree, want)
        got = mux_decode(tree, byte)                          # the tree steers it -- verified, not assumed
        if got != want:
            raise TreeError(f"routing byte {byte:#04x} reached chain {got}, expected {want}")
        s = sentinels[got]
        s.step(feed_pulse=True, collect_pulse=False, out_wrap_pulse=False, host_unfreeze_pulse=False)
        value = run_chain(result, args)
        s.step(feed_pulse=False, collect_pulse=True, out_wrap_pulse=False, host_unfreeze_pulse=False)
        stamp = gather_stamp(tree, got)
        if stamp != byte:
            raise TreeError(f"gather stamp {stamp:#04x} != dispatch id {byte:#04x} for chain {got}")
        bram_out.write(i, (stamp << 32) | (value & 0xFFFFFFFF))
        outputs.append((got, stamp, value))
    for k, s in enumerate(sentinels):
        s.step(feed_pulse=False, collect_pulse=False, out_wrap_pulse=True, host_unfreeze_pulse=False)
        if s.err_flag:
            errors.append(f"chain {k}: sentinel error latched (negative={s.err_negative}, overflow={s.err_overflow})")
        if not s.safe_to_intervene:
            errors.append(f"chain {k}: not safe_to_intervene (diff={s.diff})")
    return StreamResult(outputs=outputs, sentinels_safe=not errors, sentinel_errors=errors,
                        levels=levels_for(chains), dispatch_nodes=tree.node_count,
                        gather_nodes=tree.node_count, bram_out=bram_out)
