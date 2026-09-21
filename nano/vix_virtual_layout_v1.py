"""
vix_virtual_layout_v1.py — points.md #800: placement as a VIRTUAL-SPACE stage
that is lowered to real cells only at the end, per Alan's design.

THE IDEA (Alan, 2026-09-21): while a design is being created it sits in a
virtual space -- not yet lowered to a card or an ICM -- and THAT is the point
of optimisation. Once cells are built their in/out faces are fixed, which
naturally forces a design to be built as a simple linear chain; so the
optimiser must be able to CHANGE THE CARDINALITY of each route's endpoints
(which face a value leaves and enters by) while the design is still virtual.
The folding and tightening passes then have a place to work; a design headed
for a bounded card has to be FOLDED to fit, which is exactly why the cardinal
outs must be re-chosen as it folds, and then tightened.

WHY THE GROWTH DISPATCHER COULD NOT DO THIS (`vix_dag_dispatcher_v1`, #780):
it fixes every cell's faces the moment the cell is placed, and grows each new
instruction straight out of a known frontier. Two independently-computed values
that must merge are therefore routed straight-then-turn across whatever is in
the way (points.md #798 -- `select` with two computed arms). A router that ran
DURING growth failed for the reason above (later straight padding ran into it).
A router that runs AFTER placement, when every node and obstacle is known and no
face is yet fixed, is sound -- which is what this module is.

STAGES (all on plain Python objects; nothing is a `HierCell` until the last):
  1. graph      -- `DagInstr` list -> nodes (leaf / unary / binary) + edges.
  2. layout     -- layered columns (depth), rows by barycentre, spacing `S`.
                   Optional FOLD: columns wrap into stacked bands in a snake, and
                   a shape's own orientation flips on alternate bands.
  3. route      -- sequential BFS over the whole occupancy map. Multi-source /
                   multi-target: the router CHOOSES the face at each end, so the
                   cardinal ports are a result of routing, not an input to it.
                   (A keep-out ring around nodes was tried to protect pin access
                   and REMOVED: measured on eight programs it changed no success
                   and made layouts equal or larger -- 166 vs 122 cells. What
                   actually fixed routing was the LAYOUT: leaves attach north /
                   south of their consumer, ops sit on a slot pitch of 3.)
  4. tighten    -- try the smallest spacing that routes (search, not a guess).
  5. lower      -- only now build `HierCell`s with the chosen faces.

EVERY two-operand op is ingested through a PRIORITY cell (PRIORITY when
commutative, SEQUENCER when not), never a bare race between two routes. The
growth dispatcher's real+constant "plain chain" leans on its own geometry for
timing; a general router changes route lengths freely, so correctness must not
depend on them. This costs one priority cell per binary op and buys
independence from layout.

SAME RETURN CONTRACT as `compile_dag()` -- `(icm, positions, dynamic_positions,
seq_orders)` -- so a frontend can swap placers.

REAL, HONEST LIMITS: routing a graph on a plane with no crossover cell is only
possible if the graph can be embedded without crossings; a non-planar program
fails LOUDLY (`ValueError`), never with a wrong answer. A producer has 3 output
faces, so at most 3 consumers per value. Routing is a sequential heuristic
(shortest-first, then seeded reorderings, then more spacing), not an optimum --
routing under crossing/planarity constraints is NP-hard (the Composer scope note
already records this as the reason a human fallback exists).
"""
from __future__ import annotations

import os
import random
import re
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import icm_vix_v1 as vix  # noqa: E402
import vix_tile_library_v1 as vtl  # noqa: E402
from rats_nest_router_v1 import _DIR_STEP, _OPP  # noqa: E402
from vix_convergence_shapes_v1 import ConvergenceShape, choose_convergence_shape  # noqa: E402
from vix_opcode_library_v1 import lookup as library_lookup  # noqa: E402
from vix_dag_dispatcher_v1 import (DagInstr, ingestion_path, _place_for_opcode, _out_field,  # noqa: E402
                                   _dir_const)

Pos = Tuple[int, int]
_FACES = ("n", "s", "e", "w")
DEFAULT_SPACINGS = (3, 4, 5, 6, 8, 12)


class RouteFailure(ValueError):
    """Routing could not complete at this layout. Loud by design."""


def _step(p: Pos, face: str) -> Pos:
    dr, dc = _DIR_STEP[face]
    return (p[0] + dr, p[1] + dc)


def _dir_between(a: Pos, b: Pos) -> str:
    for f in _FACES:
        if _step(a, f) == b:
            return f
    raise AssertionError(f"{a} and {b} are not adjacent")


# ---------------------------------------------------------------------------
# 1. Graph
# ---------------------------------------------------------------------------

@dataclass
class _Edge:
    src: "_Node"
    dst: "_Node"
    slot: int
    src_cell: Optional[Pos] = None
    src_face: Optional[str] = None
    dst_cell: Optional[Pos] = None
    dst_face: Optional[str] = None
    path: List[Pos] = field(default_factory=list)
    #: points.md #808: restrict this edge to specific pins. A rigid macro (a BRAM interface with 2n leaf pins)
    #: must connect leaf pin i to destination i, not to whichever pin is nearest.
    src_pins: Optional[List[Tuple[Pos, str]]] = None
    dst_pins: Optional[List[Tuple[Pos, str]]] = None


@dataclass(eq=False)
class _Node:
    name: str
    kind: str                       # leaf_dyn | leaf_const | unary | binary
    instr: Optional[DagInstr] = None
    label: Optional[str] = None     # injection label (leaf_dyn)
    value: Optional[int] = None     # constant (leaf_const)
    depth: int = 0
    slot: int = 0
    pos: Pos = (0, 0)
    rot: str = "e"
    in_edges: List[_Edge] = field(default_factory=list)
    out_edges: List[_Edge] = field(default_factory=list)

    @property
    def entry(self):
        return library_lookup(self.instr.opcode) if self.instr else None

    @property
    def resource(self) -> Optional[str]:
        e = self.entry
        return e.resource if e is not None else None

    # -- footprint and pins (pure functions of pos/rot) --------------------
    def second(self) -> Pos:
        return _step(self.pos, self.rot)

    def cells(self) -> List[Pos]:
        if self.kind in ("leaf_dyn", "leaf_const"):
            return [self.pos]
        if self.kind == "unary" and not self.entry.needs_capture:
            return [self.pos]
        return [self.pos, self.second()]

    def in_pins(self) -> List[Tuple[Pos, str]]:
        if self.kind.startswith("leaf"):
            return []
        if self.kind == "unary" and not self.entry.needs_capture:
            return [(self.pos, f) for f in _FACES]
        return [(self.pos, f) for f in _FACES if f != self.rot]

    def out_pins(self) -> List[Tuple[Pos, str]]:
        if self.kind.startswith("leaf"):
            return [(self.pos, f) for f in _FACES]
        if self.kind == "unary" and not self.entry.needs_capture:
            return [(self.pos, f) for f in _FACES]
        return [(self.second(), f) for f in _FACES if f != _OPP[self.rot]]

    def result_cell(self) -> Pos:
        return self.pos if self.kind == "unary" and not self.entry.needs_capture else (
            self.second() if self.kind in ("unary", "binary") else self.pos)


def _build_graph(instrs: List[DagInstr]) -> List[_Node]:
    nodes: List[_Node] = []
    by_name: Dict[str, _Node] = {}
    for ins in instrs:
        entry = library_lookup(ins.opcode)
        if entry is None:
            raise ValueError(f"no real library entry for opcode {ins.opcode!r}")
        kind = "unary" if entry.arity == 1 else "binary"
        if len(ins.operands) != entry.arity:
            raise ValueError(f"{ins.name!r}: {ins.opcode} takes {entry.arity} operand(s), got {len(ins.operands)}")
        node = _Node(name=ins.name, kind=kind, instr=ins)
        kinds = [o.kind for o in ins.operands]
        if all(k == "const" for k in kinds):
            raise ValueError(f"{ins.name!r}: every operand is a constant (constant-fold it first)")
        plain = ingestion_path(ins.opcode, kinds) == "plain_chain"
        for slot, op in enumerate(ins.operands):
            if op.kind == "ref":
                if op.ref_name not in by_name:
                    raise ValueError(f"{ins.name!r}: reference to unknown or later value {op.ref_name!r}")
                src = by_name[op.ref_name]
            elif op.kind == "dynamic":
                label = f"{ins.name}_x" if plain else (f"{ins.name}_a" if slot == 0 else f"{ins.name}_b")
                src = _Node(name=f"dynq_{label}", kind="leaf_dyn", label=label)
                nodes.append(src)
            else:
                src = _Node(name=f"const_{ins.name}_{slot}", kind="leaf_const", value=op.value)
                nodes.append(src)
            e = _Edge(src=src, dst=node, slot=slot)
            src.out_edges.append(e)
            node.in_edges.append(e)
        nodes.append(node)
        by_name[ins.name] = node
    return nodes


# ---------------------------------------------------------------------------
# 2. Layout (virtual space)
# ---------------------------------------------------------------------------

def _nearest_free(used: Set[int], want: int) -> int:
    if want not in used:
        return want
    k = 1
    while True:
        for cand in (want + k, want - k):
            if cand not in used:
                return cand
        k += 1


def _assign_slots(nodes: List[_Node], rng: Optional[random.Random] = None, jitter: int = 0) -> None:
    """Depth = column. Operation nodes take row slots that are MULTIPLES OF 3
    (barycentre of their predecessors, nearest free, optionally jittered);
    each operation's leaf operands sit directly NORTH (-1) / SOUTH (+1) of it in
    the same column, so a leaf's route is a short vertical stub into a free
    face and never a long wall across the horizontal corridors (found the hard
    way: leaves placed west-and-below cut the design into strips that no amount
    of spacing could reopen)."""
    ops = [n for n in nodes if n.kind in ("unary", "binary")]
    for n in ops:
        preds = [e.src.depth for e in n.in_edges if e.src.kind in ("unary", "binary")]
        n.depth = 1 + max(preds) if preds else 1
    colslots: Dict[int, Set[int]] = defaultdict(set)      # in units of 3 slots
    for n in ops:
        preds = [e.src.slot / 3 for e in n.in_edges if e.src.kind in ("unary", "binary")]
        want = round(sum(preds) / len(preds)) if preds else 0
        if jitter and rng is not None:
            want += rng.randint(-jitter, jitter)
        idx = _nearest_free(colslots[n.depth], want)
        colslots[n.depth].add(idx)
        n.slot = 3 * idx
    for n in ops:
        leaves = [e.src for e in n.in_edges if e.src.kind.startswith("leaf")]
        sides = [-1, 1]
        if rng is not None and jitter and rng.random() < 0.5:
            sides.reverse()
        for leaf, side in zip(leaves, sides):
            leaf.depth = n.depth
            leaf.slot = n.slot + side


def _layout(nodes: List[_Node], spacing: int, fold_width: Optional[int],
            rng: Optional[random.Random] = None, jitter: int = 0) -> None:
    _assign_slots(nodes, rng, jitter)
    lo = min(n.slot for n in nodes)
    hi = max(n.slot for n in nodes)
    band_h = (hi - lo + 2) * spacing + 2 * spacing
    for n in nodes:
        col = n.depth
        if fold_width:
            band, idx = divmod(col, fold_width)
            x = (idx if band % 2 == 0 else fold_width - 1 - idx) * spacing
            n.rot = "e" if band % 2 == 0 else "w"      # the shape's own cardinality flips on a fold
            y = (n.slot - lo) * spacing + band * band_h
        else:
            x = col * spacing
            n.rot = "e"
            y = (n.slot - lo) * spacing
        n.pos = (y, x + 1)   # +1 keeps a west-rotated shape's second cell off column -1


# ---------------------------------------------------------------------------
# 2b. Bounded grid and fixed sites (points.md #804)
# ---------------------------------------------------------------------------

def _all_cells(nodes: List[_Node]) -> List[Pos]:
    return [p for n in nodes for p in n.cells()]


def _fit_positions(nodes: List[_Node], bounds: Optional[Tuple[int, int]],
                   sites: Optional[Dict[str, List[Pos]]]) -> None:
    """Move the finished virtual layout INTO a bounded grid and PIN resource-bound nodes onto their
    fixed sites. Raises `RouteFailure` if it cannot (loud, per attempt).

    Sites are ABSOLUTE positions, so the whole layout is translated: candidates align a bound node
    with a site, and the translation minimising the total distance from every bound node to its
    nearest unused site wins; each bound node is then SNAPPED onto its site (the router connects the
    consequences -- a snapped node's routes are simply longer). Unbound layouts are just shifted to
    the grid origin with a 1-cell margin."""
    cells = _all_cells(nodes)
    dr = 1 - min(p[0] for p in cells)
    dc = 1 - min(p[1] for p in cells)
    bound = [n for n in nodes if n.resource]
    if bound and sites:
        for n in bound:
            if not sites.get(n.resource):
                raise RouteFailure(f"{n.name} needs a {n.resource!r} site but the target has none")
        rows, cols = bounds if bounds else (10 ** 9, 10 ** 9)

        def inside_all(tr: int, tc: int) -> bool:
            return all(0 <= p[0] + tr < rows and 0 <= p[1] + tc < cols for p in cells)

        def assign(tr: int, tc: int):
            taken: Set[Pos] = set()
            out = []
            cost = 0
            for n in bound:
                ref = n.result_cell()                # the op's CORE cell is what sits on the resource
                px, py = ref[0] + tr, ref[1] + tc
                best = min((s for s in sites[n.resource] if s not in taken),
                           key=lambda s: abs(s[0] - px) + abs(s[1] - py), default=None)
                if best is None:
                    return None, None
                taken.add(best)
                cost += abs(best[0] - px) + abs(best[1] - py)
                out.append((n, best))
            return cost, out

        first = bound[0]
        fref = first.result_cell()
        cands = sorted({(s[0] - fref[0], s[1] - fref[1]) for s in sites[first.resource]})
        if len(cands) > 160:
            cands = cands[::max(1, len(cands) // 160)]
        best_cost, best_assign = None, None
        for tr, tc in cands + [(dr, dc)]:
            if bounds and not inside_all(tr, tc):
                continue
            cost, out = assign(tr, tc)
            if out is not None and (best_cost is None or cost < best_cost):
                best_cost, best_assign, dr, dc = cost, out, tr, tc
        if best_assign is None:
            raise RouteFailure("no translation keeps the layout inside the grid and gives every bound node a site")
        offsets = {id(n): (n.result_cell()[0] - n.pos[0], n.result_cell()[1] - n.pos[1]) for n in bound}
        for n in nodes:
            n.pos = (n.pos[0] + dr, n.pos[1] + dc)
        for n, site in best_assign:                  # snap: the core cell lands exactly on the site
            off = offsets[id(n)]
            n.pos = (site[0] - off[0], site[1] - off[1])
    else:
        for n in nodes:
            n.pos = (n.pos[0] + dr, n.pos[1] + dc)
    cells = _all_cells(nodes)
    if len(set(cells)) != len(cells):
        raise RouteFailure("pinning a node onto its site made two nodes overlap")
    if bounds:
        rows, cols = bounds
        if any(not (0 <= p[0] < rows and 0 <= p[1] < cols) for p in cells):
            raise RouteFailure(f"the layout does not fit a {rows}x{cols} grid")


# ---------------------------------------------------------------------------
# 3. Route
# ---------------------------------------------------------------------------

def _route_edge(e: _Edge, occ: Set[Pos], used: Dict[Pos, Set[str]],
                bbox: Tuple[int, int, int, int], ring: Optional[Dict[Pos, Set[int]]] = None) -> None:
    r0, r1, c0, c1 = bbox
    mine = {id(e.src), id(e.dst)}

    def inside(p: Pos) -> bool:
        # Optional keep-out ring (see `_route_all`): a route may only touch a cell next to a
        # node if that node is one of THIS edge's own endpoints, so it cannot starve the pins
        # of a node it does not serve.
        return r0 <= p[0] <= r1 and c0 <= p[1] <= c1 and not (ring and (ring.get(p, set()) - mine))

    sources: Dict[Pos, Tuple[Pos, str]] = {}
    for cp, f in e.src.out_pins():
        if f in used[cp]:
            continue
        fc = _step(cp, f)
        if fc not in occ and inside(fc):
            sources.setdefault(fc, (cp, f))
    targets: Dict[Pos, Tuple[Pos, str]] = {}
    for cp, f in e.dst.in_pins():
        if f in used[cp]:
            continue
        lc = _step(cp, f)
        if lc not in occ and inside(lc):
            targets.setdefault(lc, (cp, f))
    if not sources or not targets:
        raise RouteFailure(f"edge {e.src.name}->{e.dst.name}: no free output or input face")

    prev: Dict[Pos, Optional[Pos]] = {s: None for s in sources}
    q = deque(sources)
    hit: Optional[Pos] = None
    while q:
        cur = q.popleft()
        if cur in targets:
            hit = cur
            break
        for f in ("e", "s", "w", "n"):
            nxt = _step(cur, f)
            if nxt in prev or nxt in occ or not inside(nxt):
                continue
            prev[nxt] = cur
            q.append(nxt)
    if hit is None:
        raise RouteFailure(f"edge {e.src.name}->{e.dst.name}: no free path")
    path: List[Pos] = []
    node: Optional[Pos] = hit
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()
    e.path = path
    e.src_cell, e.src_face = sources[path[0]]
    e.dst_cell, e.dst_face = targets[path[-1]]
    used[e.src_cell].add(e.src_face)
    used[e.dst_cell].add(e.dst_face)
    occ.update(path)


def _route_all(nodes: List[_Node], rng: random.Random, shuffle: bool, margin: int, ring_on: bool = False,
               bounds: Optional[Tuple[int, int]] = None) -> None:
    """`ring_on` is an ALTERNATE search mode, not the default. A keep-out ring was first built
    on a theory, then REMOVED because on simple programs it changed nothing and made layouts
    equal-or-larger (166 vs 122 cells, points.md #800). It is back only as a fallback attempt,
    because on dense graphs (a nested if-conversion) the failures are 'no free output or input
    face' -- pin starvation -- which is exactly what it prevents."""
    occ: Set[Pos] = set()
    for n in nodes:
        occ.update(n.cells())
    ring: Optional[Dict[Pos, Set[int]]] = None
    if ring_on:
        ring = defaultdict(set)
        for n in nodes:
            for cp in n.cells():
                for f in _FACES:
                    nb = _step(cp, f)
                    if nb not in occ:
                        ring[nb].add(id(n))
    used: Dict[Pos, Set[str]] = defaultdict(set)
    rows = [p[0] for n in nodes for p in n.cells()]
    cols = [p[1] for n in nodes for p in n.cells()]
    bbox = (min(rows) - margin, max(rows) + margin, min(cols) - margin, max(cols) + margin)
    if bounds:        # routes may not leave the grid
        bbox = (max(bbox[0], 0), min(bbox[1], bounds[0] - 1), max(bbox[2], 0), min(bbox[3], bounds[1] - 1))
    edges = [e for n in nodes for e in n.in_edges]
    def length(e: _Edge) -> int:
        a, b = e.src.result_cell(), e.dst.pos
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    edges.sort(key=length)
    if shuffle:
        rng.shuffle(edges)
    for e in edges:
        _route_edge(e, occ, used, bbox, ring)


# ---------------------------------------------------------------------------
# 3b. Negotiated-congestion routing (PathFinder) -- points.md #805
# ---------------------------------------------------------------------------

_INF = float("inf")
_PFAC_CAP = 1e6


def _route_all_pathfinder(nodes: List[_Node], margin: int, bounds: Optional[Tuple[int, int]] = None,
                          max_iter: int = 25, window: int = 10, patience: int = 40) -> int:
    """Rip-up-and-reroute by NEGOTIATED CONGESTION. The greedy router commits each edge once, so an
    early edge can wall off a later one and the whole layout fails. Here every edge is routed with
    overlaps ALLOWED at a cost, then every edge that shares a cell is ripped up and re-routed at a
    rising present-congestion penalty, while cells that stay contested accumulate a HISTORY cost, until
    no cell is shared. A planar graph can be drawn with its nodes at any fixed positions given room,
    so what fails a fixed layout is the greedy commit order, which this removes.

    Returns the number of iterations used; raises `RouteFailure` if congestion never resolves. Uses the
    same pin model as `_route_edge` (multi-source / multi-target: the router chooses both faces), and
    the same result fields, so `_lower` is unchanged."""
    import heapq
    node_cells: Set[Pos] = set()
    for n in nodes:
        node_cells.update(n.cells())
    rows = [p[0] for p in node_cells]
    cols = [p[1] for p in node_cells]
    g_r0, g_r1, g_c0, g_c1 = min(rows) - margin, max(rows) + margin, min(cols) - margin, max(cols) + margin
    if bounds:
        g_r0, g_r1, g_c0, g_c1 = max(g_r0, 0), min(g_r1, bounds[0] - 1), max(g_c0, 0), min(g_c1, bounds[1] - 1)
    edges = [e for n in nodes for e in n.in_edges]

    def length(e: _Edge) -> int:
        a, b = e.src.result_cell(), e.dst.pos
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    edges.sort(key=length)

    hist: Dict[Pos, float] = defaultdict(float)
    usage: Dict[Pos, int] = defaultdict(int)
    routed: Dict[int, Tuple[List[Pos], Tuple[Pos, str], Tuple[Pos, str]]] = {}

    def pins(e: _Edge):
        srcs: Dict[Pos, Tuple[Pos, str]] = {}
        for cp, f in (e.src_pins if e.src_pins is not None else e.src.out_pins()):
            fc = _step(cp, f)
            if fc not in node_cells:
                srcs.setdefault(fc, (cp, f))
        tgts: Dict[Pos, Tuple[Pos, str]] = {}
        for cp, f in (e.dst_pins if e.dst_pins is not None else e.dst.in_pins()):
            lc = _step(cp, f)
            if lc not in node_cells:
                tgts.setdefault(lc, (cp, f))
        return srcs, tgts

    def dijkstra(srcs, tgts, pfac, box):
        r0, r1, c0, c1 = box
        dist: Dict[Pos, float] = {}
        prev: Dict[Pos, Optional[Pos]] = {}
        heap: List[Tuple[float, int, Pos]] = []
        tick = 0
        for s in srcs:
            if r0 <= s[0] <= r1 and c0 <= s[1] <= c1:
                d = (1.0 + hist[s]) * (1.0 + pfac * usage[s])
                dist[s] = d
                prev[s] = None
                tick += 1
                heapq.heappush(heap, (d, tick, s))
        while heap:
            d, _, cur = heapq.heappop(heap)
            if d > dist.get(cur, _INF):
                continue
            if cur in tgts:
                return cur, prev
            cr, cc = cur
            for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                nb = (cr + dr, cc + dc)
                if nb in node_cells or not (r0 <= nb[0] <= r1 and c0 <= nb[1] <= c1):
                    continue
                nd = d + (1.0 + hist[nb]) * (1.0 + pfac * usage[nb])
                if nd < dist.get(nb, _INF):
                    dist[nb] = nd
                    prev[nb] = cur
                    tick += 1
                    heapq.heappush(heap, (nd, tick, nb))
        return None, prev

    def route(e: _Edge, pfac: float) -> None:
        old = routed.pop(id(e), None)
        if old:
            for c in old[0]:
                usage[c] -= 1
        srcs, tgts = pins(e)
        if not srcs or not tgts:
            raise RouteFailure(f"edge {e.src.name}->{e.dst.name}: no free output or input face")
        pts = list(srcs) + list(tgts)
        # first a LOCAL window around the endpoints (fast), then the whole grid
        local = (max(g_r0, min(p[0] for p in pts) - window), min(g_r1, max(p[0] for p in pts) + window),
                 max(g_c0, min(p[1] for p in pts) - window), min(g_c1, max(p[1] for p in pts) + window))
        hit, prev = dijkstra(srcs, tgts, pfac, local)
        if hit is None:
            hit, prev = dijkstra(srcs, tgts, pfac, (g_r0, g_r1, g_c0, g_c1))
        if hit is None:
            raise RouteFailure(f"edge {e.src.name}->{e.dst.name}: no path exists even ignoring congestion")
        path: List[Pos] = []
        node: Optional[Pos] = hit
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()
        routed[id(e)] = (path, srcs[path[0]], tgts[path[-1]])
        for c in path:
            usage[c] += 1

    pfac = 0.6
    for e in edges:
        route(e, pfac)
    best_over, last_gain = None, 0
    for it in range(1, max_iter + 1):
        over = {c for c, u in usage.items() if u > 1}
        if over and (best_over is None or len(over) < best_over):
            best_over, last_gain = len(over), it
        elif over and it - last_gain >= patience:
            # STALL DETECTION: negotiation that has not reduced the number of contested cells for `patience`
            # iterations is not converging (converging cases finish quickly), so stop instead of burning the budget.
            raise RouteFailure(f"negotiated congestion did not resolve: stalled at {best_over} contested cells "
                               f"for {patience} iterations ({sum(1 for u in usage.values() if u > 1)} cells still shared)")
        if not over:
            for e in edges:
                path, (sc, sf), (dc_, df) = routed[id(e)]
                e.path, e.src_cell, e.src_face, e.dst_cell, e.dst_face = path, sc, sf, dc_, df
            return it
        for c in over:
            hist[c] += 1.0
        pfac = min(pfac * 1.5, _PFAC_CAP)      # capped: an unbounded factor overflowed the old 1e18 'infinity' after ~120 iterations
        for e in edges:
            if any(c in over for c in routed[id(e)][0]):
                route(e, pfac)
    raise RouteFailure(f"negotiated congestion did not resolve in {max_iter} iterations "
                       f"({sum(1 for u in usage.values() if u > 1)} cells still shared)")


# ---------------------------------------------------------------------------
# 5. Lower: only now do real cells exist.
# ---------------------------------------------------------------------------

def _lower(nodes: List[_Node]):
    cells: List = []
    positions: Dict[str, Pos] = {}
    dynamic_positions: List[Tuple[str, int, int]] = []
    seq_orders: Dict[str, Tuple[int, int]] = {}

    for n in nodes:
        out_faces = [e.src_face for e in n.out_edges]
        if n.kind == "leaf_dyn":
            cells.append(vix.HierCell(cell_id=n.name, rel_row=n.pos[0], rel_col=n.pos[1], core="ram",
                                       core_config={"upstream_mask": [], "downstream_mask": out_faces}))
            dynamic_positions.append((n.label, n.pos[0], n.pos[1]))
        elif n.kind == "leaf_const":
            c = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": out_faces[0]}, cell_id=n.name,
                          rel_row=n.pos[0], rel_col=n.pos[1], preload_value=n.value)
            cells.append(c)
        elif n.kind == "unary":
            entry = n.entry
            in_face = n.in_edges[0].dst_face
            params = entry.param_builder(n.instr.params) if entry.param_builder else None
            addon = entry.addon_builder(n.instr.params) if entry.addon_builder else None
            if entry.needs_capture:
                cells.append(vtl.place(entry.tile, {"in": in_face, "out": n.rot}, params=params,
                                        cell_id=f"{n.name}_op", rel_row=n.pos[0], rel_col=n.pos[1],
                                        addon_config=addon))
                cp = n.second()
                cap = vtl.place(vtl.TILE_RAM_FLOWING, {"in": _OPP[n.rot], "out": n.rot}, cell_id=n.name,
                                rel_row=cp[0], rel_col=cp[1])
                cap.core_config["downstream_mask"] = list(out_faces)
                cells.append(cap)
            else:
                c = vtl.place(entry.tile, {"in": in_face, "out": (out_faces[0] if out_faces else _OPP[in_face])},
                              params=params, cell_id=n.name, rel_row=n.pos[0], rel_col=n.pos[1], addon_config=addon)
                c.core_config[_out_field(c.core)] = list(out_faces)
                cells.append(c)
        else:  # binary: priority cell then the op cell, in a fixed pair
            faces = [e.dst_face for e in n.in_edges]
            shape = choose_convergence_shape(has_real_convergence=True, is_commutative=n.entry.is_commutative,
                                             all_arrival_ticks_knowable=False)
            seq = shape == ConvergenceShape.SEQUENCER
            pri = vtl.place(vtl.TILE_PRIORITY, {"in": faces, "out": n.rot},
                            params={"priority_rank_n": 0, "priority_rank_s": 0, "priority_rank_e": 0,
                                    "priority_rank_w": 0, "scheduling_mode": 2 if seq else 0},
                            cell_id=f"pri_{n.name}", rel_row=n.pos[0], rel_col=n.pos[1])
            cells.append(pri)
            cp = n.second()
            core = _place_for_opcode(n.instr.opcode, n.name, cp[0], cp[1], _OPP[n.rot], _OPP[n.rot], n.rot)
            core.core_config[_out_field(core.core)] = list(out_faces)
            cells.append(core)
            if seq:
                seq_orders[n.name] = (_dir_const(faces[0]), _dir_const(faces[1]))
        if n.kind in ("unary", "binary"):
            positions[n.name] = n.result_cell()

    k = 0
    for n in nodes:
        for e in n.in_edges:
            for i, p in enumerate(e.path):
                d_in = _OPP[e.src_face] if i == 0 else _dir_between(p, e.path[i - 1])
                d_out = _dir_between(p, e.path[i + 1]) if i + 1 < len(e.path) else _OPP[e.dst_face]
                cells.append(vtl.place(vtl.TILE_RAM_FLOWING, {"in": d_in, "out": d_out},
                                        cell_id=f"rt{k}_{e.src.name}__{e.dst.name}_{e.slot}_{i}",
                                        rel_row=p[0], rel_col=p[1]))
            k += 1
    return cells, positions, dynamic_positions, seq_orders


# ---------------------------------------------------------------------------
# Audit: nothing may offer toward a nano gate except its designated feeder.
# ---------------------------------------------------------------------------

def audit_gate_feeders(cells) -> List[str]:
    """A `nano` gate has NO input gating: it consumes an arrival from ANY wired neighbour
    that offers toward it (`cardinal_edge` only classifies an arrival as consume/relay, it
    does not filter -- CELL_INTERNALS.md). So a neighbour that does NOT point at it is
    harmless, but one that does is silently corrupting (measured, points.md #802: a stray
    constant pointing at `xor(x,12)` turned 12/9/104 into 255/250/155). The only way that
    can happen is a stale or dangling output face -- most likely after a cell is
    re-oriented during a fold. In this placer every gate is fed by its own priority cell,
    so require EXACTLY ONE offering neighbour and that it is a `pri_` cell. Returns
    problems (empty = clean)."""
    by_pos = {(c.rel_row, c.rel_col): c for c in cells}
    problems: List[str] = []
    for g in cells:
        if g.core != "nano":
            continue
        feeders = []
        for f in _FACES:
            nb = by_pos.get(_step((g.rel_row, g.rel_col), f))
            if nb is None:
                continue
            cc = nb.core_config
            offered = cc.get("routing_mask") if nb.core == "nano" else cc.get("downstream_mask")
            if _OPP[f] in (offered or []):
                feeders.append(nb.cell_id)
        if len(feeders) != 1 or not feeders[0].startswith("pri_"):
            problems.append(f"nano gate {g.cell_id} is fed by {feeders or 'nothing'}, expected exactly its priority cell")
    return problems


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compile_dag_routed(instructions: List[DagInstr], spacing: Optional[int] = None,
                       fold_width: Optional[int] = None, attempts: int = 16, seed: int = 0,
                       margin: int = 16, bounds: Optional[Tuple[int, int]] = None,
                       sites: Optional[Dict[str, List[Pos]]] = None, info: Optional[dict] = None,
                       spacings: Optional[Tuple[int, ...]] = None, pathfinder: bool = True,
                       pf_budget: int = 30):
    """Same return contract as `compile_dag()`. `spacing=None` TIGHTENS by
    searching for the smallest workable spacing; `fold_width=N` folds the layout
    into a snake of bands N columns wide, flipping shape orientation on
    alternate bands. Raises `RouteFailure` (a `ValueError`) if nothing routes."""
    last: Optional[Exception] = None
    pf_fails = [0]
    pf_heavy = [0]
    for si, S in enumerate((spacing,) if spacing else (spacings or DEFAULT_SPACINGS)):
        for attempt in range(attempts):
            # A DIFFERENT seed per spacing (#805): success depends on the node ORDERING a seed produces,
            # not on the room, so re-using seed 0..N at every spacing just re-tried the same orderings.
            rng = random.Random(seed + attempt + 97 * si)
            nodes = _build_graph(instructions)
            _layout(nodes, S, fold_width, rng, jitter=0 if attempt == 0 else 1 + attempt // 8)
            try:
                if bounds or sites:
                    _fit_positions(nodes, bounds, sites)
                try:
                    _route_all(nodes, rng, shuffle=attempt > 0, margin=margin, ring_on=attempt % 2 == 1,
                               bounds=bounds)
                except RouteFailure:
                    # STAGE 2 (#805): the greedy router commits each edge once. On the SAME layout, negotiate:
                    # rip up and re-route contested edges at a rising congestion cost. It converges quickly
                    # or never, so it is capped low and tried on a few layouts per spacing, not many
                    # iterations on one; after `pf_budget` failed negotiations it is switched off (a
                    # genuinely non-planar design would otherwise burn the whole search).
                    if not (pathfinder and pf_fails[0] < pf_budget and pf_heavy[0] < 4):
                        raise
                    for n in nodes:
                        for e in n.in_edges:
                            e.path = []
                    try:
                        _route_all_pathfinder(nodes, margin, bounds)
                    except RouteFailure as pe:
                        pf_fails[0] += 1
                        m = re.search(r"\((\d+) cells still shared", str(pe))
                        if m and int(m.group(1)) >= 6:      # many contested cells: a genuine crossing
                            pf_heavy[0] += 1                # (non-planar) -- stop spending time on it
                        raise
            except RouteFailure as e:
                last = e
                continue
            cells, positions, dyn, seqs = _lower(nodes)
            bad = audit_gate_feeders(cells)
            if bad:
                raise RouteFailure("lowering produced a gate that something else feeds: " + "; ".join(bad))
            icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                                 placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                                 name="dag_routed")
            if info is not None:
                info.update(spacing=S, fold_width=fold_width, attempt=attempt,
                            bindings=[(n.instr.name, n.resource, n.result_cell()) for n in nodes if n.resource])
            return icm, positions, dyn, seqs
    raise RouteFailure(f"no routed layout found (spacings tried {spacing or DEFAULT_SPACINGS}, "
                       f"{attempts} orderings each); last failure: {last}")
