"""
stream_layout_v1.py — points.md #808: PLACE the BRAM interface -- controller, splitter, dispatch tree,
combiner tree -- and N replicated copies of a compiled chain on the grid, route every leaf pin to ITS chain,
and check the result, including where it sits on the card and what the card's bus width does to it.

GEOMETRY (a modelling choice, stated -- the RTL fixes the ports, not the floor plan):
    dispatch tree  <- splitter <- BRAM controller -> combiner root -> gather tree
The controller sits at the origin; the splitter one cell NORTH of it and the dispatch tree root one cell
beyond that (its upstream face facing the splitter); the combiner root one cell SOUTH of the controller (its
output face toward the controller) with the gather tree growing away from it. Parent and child are UNIT
NEIGHBOURS because the routing byte rides dedicated wires between adjacent nodes (`tree_embedding_v1`).
Each chain is a rigid copy of a compiled design; a leaf pin connects to its chain by an ordinary data ROUTE
(relay cells), which the negotiated-congestion router finds.

WHAT IS PLACED vs WHAT IS RUN. The mux / combiner / splitter / controller are not VIX cores, so they cannot be
simulated on the SuperGrid; they are recorded as `SetPieceCell`s (position, faces, `face_for_slotN` configs) that
occupy array positions and are what a card build consumes. Everything else -- the chains and every relay on
every route -- is a real ICM and IS simulated: a value is injected where the dispatch tree would offer it, runs
through the route and the chain, and is read where the gather tree would receive it. The trees' own decode is
the routing-byte model verified against hardware-proven bytes (`fixed_structures_v1`).

REAL, HONEST LIMITS
  * The floor plan (controller/splitter/root adjacency and sides) is MY ASSUMPTION. The RTL has the
    connections but not a placement.
  * At most 13 feeds in 2D (`tree_embedding_v1` measured this exhaustively); single-argument chains only.
  * A narrower bus (see `BusSpec`) implies a store-and-shift stage and different splitter/combiner RTL; both
    are PROPOSED and not built -- this module accounts their latency (beats) but does not place a shift register.
  * Protocol-level for the trees and BRAM; nothing has been through Quartus or hardware.
"""
from __future__ import annotations

import copy
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import icm_vix_v1 as vix  # noqa: E402
import vix_tile_library_v1 as vtl  # noqa: E402
import vix_virtual_layout_v1 as V  # noqa: E402
import fixed_structures_v1 as FS  # noqa: E402
import tree_embedding_v1 as T  # noqa: E402
import card_fit_v1 as C  # noqa: E402
from rats_nest_router_v1 import _DIR_STEP, _OPP  # noqa: E402

Pos = Tuple[int, int]


COLUMNS = 1
MARGIN = 40
ITERS = 150            # MEASURED: successful placements needed 42-117 iterations


class StreamError(ValueError):
    """The stream cannot be placed. Loud by design."""


@dataclass
class SetPieceCell:
    kind: str                     # controller | splitter | mux | combiner
    cell_id: str
    pos: Pos
    up: Optional[str] = None      # the face toward its parent / feeder
    #: face code -> physical direction (`face_for_slotN` in the RTL config)
    codes: Dict[int, str] = field(default_factory=dict)


@dataclass
class StreamLayout:
    feeds: int
    bus: FS.BusPlan
    dispatch: T.EmbeddedTree
    gather: T.EmbeddedTree
    icm: object
    records: List[object]
    set_pieces: List[SetPieceCell]
    controller: Pos
    in_routes: List[List[Pos]]              # per destination: relay cells from a dispatch leaf pin to the chain
    out_routes: List[List[Pos]]             # per destination: relay cells from the chain to a gather leaf pin
    chain_cells: int
    gap: int
    fit: Optional[C.FitReport] = None
    bindings: List[Tuple[str, str, Pos]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    #: host-visible tables. Chains are IDENTICAL, so which dispatch destination feeds which chain, and which gather
    #: destination it drains into, is arbitrary -- pairing them by GEOMETRY keeps routes monotone. chain -> ids:
    dispatch_of_chain: List[int] = field(default_factory=list)
    gather_of_chain: List[int] = field(default_factory=list)

    def chain_for_dispatch(self, d: int) -> int:
        return self.dispatch_of_chain.index(d)

    def chain_for_gather(self, g: int) -> int:
        return self.gather_of_chain.index(g)

    def all_positions(self) -> List[Pos]:
        return [(r.row, r.col) for r in self.records] + [sp.pos for sp in self.set_pieces]


class _Macro:
    """A rigid multi-cell block as the router sees it (the same interface as a placer `_Node`)."""

    def __init__(self, name: str, cells: List[Pos], in_pins: List[Tuple[Pos, str]], out_pins: List[Tuple[Pos, str]],
                 result: Pos):
        self.name, self._cells, self._in, self._out, self._result = name, cells, in_pins, out_pins, result
        self.pos = min(cells)
        self.in_edges: List[V._Edge] = []
        self.out_edges: List[V._Edge] = []

    def cells(self):
        return list(self._cells)

    def in_pins(self):
        return list(self._in)

    def out_pins(self):
        return list(self._out)

    def result_cell(self):
        return self._result


def _add(p: Pos, f: str) -> Pos:
    return (p[0] + _DIR_STEP[f][0], p[1] + _DIR_STEP[f][1])


def _shift(p: Pos, d: Pos) -> Pos:
    return (p[0] + d[0], p[1] + d[1])


def _chain_block(result):
    """The compiled chain as a rigid block normalised to (0,0), with its single input cell and result cell."""
    if len(result.arg_injections) != 1 or len(next(iter(result.arg_injections.values()))) != 1:
        raise StreamError("a stream feeds ONE 32-bit word per input, so the chain must take exactly one argument "
                          "(multi-argument chains would need several feed streams)")
    cells = copy.deepcopy(result.icm.patterns["main"].cells)
    minr = min(c.rel_row for c in cells)
    minc = min(c.rel_col for c in cells)
    for c in cells:
        c.rel_row -= minr
        c.rel_col -= minc
    inp = next(iter(result.arg_injections.values()))[0]
    inp = (inp[0] - minr, inp[1] - minc)
    out = (result.result_cell[0] - minr, result.result_cell[1] - minc)
    return cells, inp, out


def _free_faces(cell_pos: Pos, taken: set, blocked_faces=()) -> List[str]:
    return [f for f in ("n", "s", "e", "w") if f not in blocked_faces and _add(cell_pos, f) not in taken]


def place_stream(result, feeds: int, *, bus: Optional[FS.BusSpec] = None, target: Optional[C.CardTarget] = None,
                 gaps: Tuple[int, ...] = (6, 10)) -> StreamLayout:
    """Place `feeds` copies of a compiled chain behind a BRAM interface and route them. With a `target`, the BRAM
    controller (and the splitter beside it) is bound to a BRAM site and the whole layout is checked against the
    card's grid and budget."""
    plan = (bus or FS.BusSpec()).plan(feeds)
    dt = T.embed_tree(feeds, up="s")                # dispatch tree: upstream face toward the splitter (south of it)
    gt = T.embed_tree(feeds, up="n")                # gather tree: output face toward the controller (north of it)
    block, in_local, out_local = _chain_block(result)
    block_pos = {(c.rel_row, c.rel_col) for c in block}
    H = max(p[0] for p in block_pos) + 1
    W = max(p[1] for p in block_pos) + 1
    in_cell_cfg = next(c for c in block if (c.rel_row, c.rel_col) == in_local)
    used_in = set(in_cell_cfg.core_config.get("downstream_mask") or [])
    in_faces = [f for f in _free_faces(in_local, block_pos) if f not in used_in]
    out_faces = _free_faces(out_local, block_pos)
    if not in_faces or not out_faces:
        raise StreamError("the chain's input or result cell has no free face to attach a route to")

    # -- the rigid BRAM macro, controller at the origin ------------------------------------------------------------
    ctrl, split = (0, 0), (-1, 0)
    set_pieces: List[SetPieceCell] = [SetPieceCell("controller", "bram_ctrl", ctrl), SetPieceCell("splitter", "splitter", split, up="s")]
    d_off, g_off = (-2, 0), (1, 0)
    macro_cells: List[Pos] = [ctrl, split]
    d_pins: List[Tuple[Pos, str]] = []
    g_pins: List[Tuple[Pos, str]] = []
    if feeds == 1:
        d_pins = [(split, "n")]                     # one chain hangs straight off the splitter: no mux tree, no routing
        g_pins = [(ctrl, "s")]
    else:
        for nd in dt.nodes:
            p = _shift(nd.pos, d_off)
            macro_cells.append(p)
            set_pieces.append(SetPieceCell("mux", f"mux{nd.index}", p, up=nd.up,
                                           codes={c: f for c, f in enumerate(T.out_faces(nd.up))}))
        for nd in gt.nodes:
            p = _shift(nd.pos, g_off)
            macro_cells.append(p)
            set_pieces.append(SetPieceCell("combiner", f"comb{nd.index}", p, up=nd.up,
                                           codes={c: f for c, f in enumerate(T.out_faces(nd.up))}))
        d_pins = [(_shift(dt.nodes[i].pos, d_off), f) for i, f, _ in (dt.pins[d] for d in range(feeds))]
        g_pins = [(_shift(gt.nodes[i].pos, g_off), f) for i, f, _ in (gt.pins[d] for d in range(feeds))]
    if len(set(macro_cells)) != len(macro_cells):
        raise StreamError("the dispatch and gather trees overlap")

    # Chains are IDENTICAL, so which leaf pin feeds which chain is arbitrary. Two hand-made pairings failed to route
    # (by destination number, and by pin position: several pins share a node cell and a west-facing pin must wrap
    # round the tree), so each chain may use ANY leaf pin and the router negotiates the assignment; distinct
    # pins have distinct first cells, so they are mutually exclusive by construction. The result is read back as
    # the host's mapping table.
    last_err: Optional[Exception] = None
    for gap in gaps:
        cols_n = COLUMNS if COLUMNS else max(1, math.ceil(math.sqrt(feeds)))
        macro_c = [p[1] for p in macro_cells]
        col0 = max(macro_c) + gap + 2
        row0 = min(p[0] for p in macro_cells)
        offsets = [(row0 + (i // cols_n) * (H + gap), col0 + (i % cols_n) * (W + gap)) for i in range(feeds)]
        macro = _Macro("bram", macro_cells, g_pins, d_pins, ctrl)
        chains: List[_Macro] = []
        for i, off in enumerate(offsets):
            cpos = [_shift(p, off) for p in block_pos]
            ch = _Macro(f"chain{i}", cpos, [(_shift(in_local, off), f) for f in in_faces],
                        [(_shift(out_local, off), f) for f in out_faces], _shift(out_local, off))
            chains.append(ch)
            e_in = V._Edge(src=macro, dst=ch, slot=0, src_pins=list(d_pins), dst_pins=ch.in_pins())
            e_out = V._Edge(src=ch, dst=macro, slot=1, src_pins=ch.out_pins(), dst_pins=list(g_pins))
            macro.out_edges.append(e_in)
            ch.in_edges.append(e_in)
            ch.out_edges.append(e_out)
            macro.in_edges.append(e_out)
        try:
            V._route_all_pathfinder([macro] + chains, margin=MARGIN, max_iter=ITERS, patience=ITERS)
        except V.RouteFailure as e:
            last_err = e
            continue
        d_of = [d_pins.index((e.src_cell, e.src_face)) for e in macro.out_edges]
        g_of = [g_pins.index((e.dst_cell, e.dst_face)) for e in macro.in_edges]
        if len(set(d_of)) != feeds or len(set(g_of)) != feeds:
            last_err = StreamError("two chains were routed to the same leaf pin")
            continue
        lay = _lower(result, feeds, plan, dt, gt, block, in_local, out_local, offsets, macro, chains, set_pieces,
                     ctrl, len(block), gap, target)
        lay.dispatch_of_chain = d_of
        lay.gather_of_chain = g_of
        return lay
    raise StreamError(f"could not route {feeds} chains to the BRAM interface at gaps {gaps}: {last_err}")


def _lower(result, feeds, plan, dt, gt, block, in_local, out_local, offsets, macro, chains, set_pieces, ctrl,
           chain_cells, gap, target) -> StreamLayout:
    cells: List[vix.HierCell] = []
    in_routes: List[List[Pos]] = []
    out_routes: List[List[Pos]] = []
    for i, off in enumerate(offsets):
        e_in = macro.out_edges[i]
        e_out = macro.in_edges[i]
        for c in block:
            cc = copy.deepcopy(c)
            cc.cell_id = f"c{i}_{c.cell_id}"
            cc.rel_row += off[0]
            cc.rel_col += off[1]
            here = (c.rel_row, c.rel_col)
            if here == in_local:
                cc.core_config["upstream_mask"] = [e_in.dst_face]        # now fed by a route, not injected
            if here == out_local:
                cc.core_config["downstream_mask"] = [e_out.src_face]     # now drains into a route
            cells.append(cc)
        for tag, e, store in (("in", e_in, in_routes), ("out", e_out, out_routes)):
            for k, p in enumerate(e.path):
                d_in = _OPP[e.src_face] if k == 0 else _dir(p, e.path[k - 1])
                d_out = _dir(p, e.path[k + 1]) if k + 1 < len(e.path) else _OPP[e.dst_face]
                cells.append(vtl.place(vtl.TILE_RAM_FLOWING, {"in": d_in, "out": d_out},
                                       cell_id=f"c{i}_{tag}{k}", rel_row=p[0], rel_col=p[1]))
            store.append(list(e.path))
    # translate: origin margin, or onto a BRAM site if a target asks for it
    shift = _choose_shift(cells, set_pieces, ctrl, target)
    for c in cells:
        c.rel_row += shift[0]
        c.rel_col += shift[1]
    for sp in set_pieces:
        sp.pos = _shift(sp.pos, shift)
    in_routes = [[_shift(p, shift) for p in r] for r in in_routes]
    out_routes = [[_shift(p, shift) for p in r] for r in out_routes]
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                         placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))], name="stream")
    records, _ = icm.flatten()
    lay = StreamLayout(feeds=feeds, bus=plan, dispatch=dt, gather=gt, icm=icm, records=records,
                       set_pieces=set_pieces, controller=_shift(ctrl, shift), in_routes=in_routes,
                       out_routes=out_routes, chain_cells=chain_cells, gap=gap)
    pos = lay.all_positions()
    if len(set(pos)) != len(pos):
        raise StreamError("cells overlap in the placed stream")
    if target is not None:
        lay.fit = _fit(lay, target)
        if "bram" in target.sites:
            lay.bindings = [("bram_ctrl", "bram", lay.controller)]
    return lay


def _dir(a: Pos, b: Pos) -> str:
    for f in ("n", "s", "e", "w"):
        if _add(a, f) == b:
            return f
    raise AssertionError((a, b))


def _choose_shift(cells, set_pieces, ctrl, target) -> Pos:
    pts = [(c.rel_row, c.rel_col) for c in cells] + [sp.pos for sp in set_pieces]
    minr, minc = min(p[0] for p in pts), min(p[1] for p in pts)
    base = (1 - minr, 1 - minc)
    if target is None or not target.sites.get("bram"):
        return base
    rows, cols = target.rows, target.cols
    ranked = sorted(target.sites["bram"], key=lambda s: abs(s[0] - rows // 2) + abs(s[1] - cols // 2))
    for site in ranked[:400]:
        sh = (site[0] - ctrl[0], site[1] - ctrl[1])
        if all(0 <= p[0] + sh[0] < rows and 0 <= p[1] + sh[1] < cols for p in pts):
            return sh
    return base                                     # no site keeps it inside the grid: the fit will say so


class _P:
    def __init__(self, r, c):
        self.row, self.col = r, c


def _fit(lay: StreamLayout, target: C.CardTarget) -> C.FitReport:
    pos = lay.all_positions()
    fake = [_P(r, c) for r, c in pos]
    rep = C.check_fit(fake, target, absolute=True)
    rep.cells = len(pos)
    if "bram" in target.sites and lay.controller not in set(target.sites["bram"]):
        rep.fits = False
        rep.problems.append(f"the BRAM controller at {lay.controller} is not on a BRAM site (none keeps the "
                            f"whole layout inside the {target.rows}x{target.cols} grid)")
    else:
        rep.bindings = [("bram_ctrl", "bram", lay.controller)] if "bram" in target.sites else []
    rep.notes.append(f"bus: {lay.bus.data_bits} data bits/beat, {lay.bus.beats} beat(s) per 32-bit value")
    return rep


# ---------------------------------------------------------------------------
# Checking: structure, and a real VM run through the placed routes and chains
# ---------------------------------------------------------------------------

def verify_layout(lay: StreamLayout) -> List[str]:
    """Structural checks; returns problems (empty = clean)."""
    problems: List[str] = []
    pos = lay.all_positions()
    if len(set(pos)) != len(pos):
        problems.append("two cells share a position")
    by_pos = {(r.row, r.col): r for r in lay.records}
    for d in range(lay.feeds):                                   # d = a CHAIN slot here
        for tag, route in (("dispatch", lay.in_routes[d]), ("gather", lay.out_routes[d])):
            if not route:
                problems.append(f"destination {d}: empty {tag} route")
                continue
            for a, b in zip(route, route[1:]):
                if sum(abs(x - y) for x, y in zip(a, b)) != 1:
                    problems.append(f"destination {d}: {tag} route is not contiguous")
        # the tree steers a routing byte to destination d, and the gather tree's stamp decodes back to d
        if lay.feeds > 1:
            dd, gg = lay.dispatch_of_chain[d], lay.gather_of_chain[d]
            if FS.mux_decode(lay.dispatch.tree, FS.dispatch_id(lay.dispatch.tree, dd)) != dd:
                problems.append(f"chain {d}: the dispatch tree does not steer to destination {dd}")
            if FS.mux_decode(lay.gather.tree, FS.gather_stamp(lay.gather.tree, gg)) != gg:
                problems.append(f"chain {d}: the gather stamp {gg} does not decode back")
    if sorted(lay.dispatch_of_chain) != list(range(lay.feeds)) or sorted(lay.gather_of_chain) != list(range(lay.feeds)):
        problems.append("the host mapping tables are not permutations")
    # every mux/combiner node is adjacent to its parent (the routing byte rides dedicated adjacent wires)
    sp = {p.cell_id: p for p in lay.set_pieces}
    for kind, tree, prefix in (("mux", lay.dispatch, "mux"), ("combiner", lay.gather, "comb")):
        for nd in tree.nodes:
            if nd.parent is not None:
                a, b = sp[f"{prefix}{nd.index}"].pos, sp[f"{prefix}{nd.parent[0]}"].pos
                if sum(abs(x - y) for x, y in zip(a, b)) != 1:
                    problems.append(f"{kind} node {nd.index} is not adjacent to its parent")
    return problems


@dataclass
class PlacedStreamRun:
    outputs: List[Tuple[int, int, int]]        # (destination, gather stamp, value)
    sentinels_safe: bool
    sentinel_errors: List[str]
    isolated: bool                             # no value leaked onto any OTHER destination's output route
    bus_beats: int


def run_placed_stream(lay: StreamLayout, inputs: List[int], *, chain_length: int = 1, ticks: Optional[int] = None):
    """Run values through the PLACED structure on the real VM: each is injected where the dispatch tree would offer
    it (the first relay of the destination's route), travels the route, the replicated chain and the output route,
    and is read where the gather tree would receive it. The tree decode and stamping use the routing-byte model."""
    from unicell_super_automaton_v1 import SuperGrid
    ticks = ticks or max(400, 3 * len(lay.records))
    sentinels = [FS.Sentinel(chain_length=chain_length, out_frozen=False) for _ in range(lay.feeds)]
    outputs: List[Tuple[int, int, int]] = []
    isolated = True
    for i, value in enumerate(inputs):
        dest = i % lay.feeds                                 # the routing byte the host writes names a DISPATCH id
        d = lay.chain_for_dispatch(dest)                     # ... which the tree steers to this chain
        if lay.feeds > 1:
            byte = FS.dispatch_id(lay.dispatch.tree, dest)
            if FS.mux_decode(lay.dispatch.tree, byte) != dest:
                raise FS.TreeError("the dispatch tree does not steer to the intended destination")
        sentinels[d].step(feed_pulse=True, collect_pulse=False, out_wrap_pulse=False, host_unfreeze_pulse=False)
        grid = SuperGrid(lay.records)
        first = lay.in_routes[d][0]
        grid.cells[first].ram_data_reg = value & 0xFFFFFFFF
        grid.cells[first].ram_data_valid = True
        for _ in range(ticks):
            grid.tick()
        last = lay.out_routes[d][-1]
        out = grid.cells[last].ram_data_reg
        for k in range(lay.feeds):
            if k != d and grid.cells[lay.out_routes[k][-1]].ram_data_valid:
                isolated = False
        sentinels[d].step(feed_pulse=False, collect_pulse=True, out_wrap_pulse=False, host_unfreeze_pulse=False)
        stamp = FS.gather_stamp(lay.gather.tree, lay.gather_of_chain[d]) if lay.feeds > 1 else 0
        if lay.feeds > 1 and lay.chain_for_gather(FS.mux_decode(lay.gather.tree, stamp)) != d:
            raise FS.TreeError("the gather stamp does not identify the chain it came from")
        outputs.append((dest, stamp, out))
    errors: List[str] = []
    for k, s in enumerate(sentinels):
        s.step(feed_pulse=False, collect_pulse=False, out_wrap_pulse=True, host_unfreeze_pulse=False)
        if s.err_flag or not s.safe_to_intervene:
            errors.append(f"chain {k}: err={s.err_flag} safe={s.safe_to_intervene} diff={s.diff}")
    return PlacedStreamRun(outputs, not errors, errors, isolated, len(inputs) * lay.bus.beats)
