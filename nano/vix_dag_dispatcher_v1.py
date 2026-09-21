"""
vix_dag_dispatcher_v1.py — points.md #779/#780: the real dispatcher
system, per Alan's own direct instruction: "go ahead and write
dispatcher system, start there." Rebuilt on Alan's own direct,
architectural correction after the first attempt hit real, repeated
routing collisions: "place the first shape, you know where it ends,
and know what it connects to, add a few padding cells, then add the
next shape, this now becomes your first combined shape... if there is
a divergence, then do one path and then revisit the second, this now
becomes your primary shape."

REAL, CENTRAL DESIGN, per that correction: never pre-compute an
instruction's own absolute position independently and then route
blindly across a shared, arbitrary grid afterward (the first attempt's
real, root mistake -- independently-built, long-distance paths can and
did coincidentally cross). Instead, grow the whole design as ONE
CONNECTED, INCREMENTAL structure: each new instruction is placed
immediately adjacent (via a few real padding cells) to the KNOWN,
CURRENT "frontier" (position + facing direction) of whatever it
depends on -- so there is never a long, independently-computed route
that could cross anything else. Genuine divergence (fan-out) grows one
consumer's ENTIRE branch first, then revisits the SAME original
frontier and grows the next consumer in a genuinely different
direction -- the two branches physically cannot cross, since each only
ever grows in its own claimed direction from a shared, known point.
Genuine convergence brings two already-known, already-grown frontiers
together with a short, local connection, using `#777`'s shape catalog
and `#778`'s orientation helper -- never a blind, long-distance route.

REAL, DELIBERATE SCOPE for this working version: operates on a real,
minimal DAG description (`DagInstr`/`DagOperand`) -- named,
topologically-ordered instructions with real operand references --
NOT full LLVM IR text parsing (a real, separate, already-solved
problem in `llvm_ir_frontend_v1.py`). Supports `add` (commutative) and
`sub` (non-commutative) with exactly 2 real operands each. A genuinely
dynamic operand is `DagOperand(kind="dynamic")` -- the compiled result
exposes where to `grid.inject()` it at runtime, per `#774`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import vix_tile_library_v1 as vtl
import icm_vix_v1 as vix
from rats_nest_router_v1 import manhattan_route, _DIR_STEP, _OPP
from vix_convergence_shapes_v1 import ConvergenceShape, choose_convergence_shape
from vix_shape_orientation_v1 import choose_two_way_orientation
from vix_opcode_library_v1 import lookup as library_lookup

Position = Tuple[int, int]
PAD = 3               # real, deliberate padding hop count between shapes
_ROTATION = ("e", "s", "n", "w")  # real, fixed, distinct growth directions for divergent branches


@dataclass
class DagOperand:
    kind: str  # "const", "ref", "dynamic"
    value: Optional[int] = None
    ref_name: Optional[str] = None


@dataclass
class DagInstr:
    name: str
    opcode: str
    operands: List[DagOperand] = field(default_factory=list)


@dataclass
class Frontier:
    """The real, known, current edge of one growing branch: where its
    own output sits right now, and which real direction it currently
    offers from."""
    pos: Position
    out_dir: str


@dataclass
class _TapPoint:
    """A real producer's own original frontier, preserved for genuine
    fan-out: each new real consumer grows its own, separate branch
    from this SAME real point, claiming its own, distinct real
    direction (never reusing one already claimed). Holds the actual
    real producer `HierCell` so each newly-claimed direction can be
    genuinely added to its own real `downstream_mask` -- a real,
    necessary fix: tracking the claim logically without mutating the
    real cell meant the second real consumer's own connection pointed
    at a face the producer never actually, physically offered."""
    pos: Position
    cell: "vix.HierCell"
    claimed_dirs: List[str] = field(default_factory=list)


def ingestion_path(opcode: str, operand_kinds: List[str]) -> str:
    """points.md #796: the ONE place that decides how an instruction's
    operands are ingested -- `"plain_chain"` (at most one real operand,
    order cannot matter) or `"convergence"` (two real operands, OR an
    ORDER-SENSITIVE op with one real + one constant operand).

    Operand order only matters for a non-commutative op, and only when
    the two values reach the cell by different physical routes. The old
    rule (`n_real <= 1` -> plain chain) gave a non-commutative real+
    constant pair NO ordering guarantee: whichever arrived first became
    the minuend (`#770`'s hazard, found by the first real frontend,
    `#795`). Routing that case through the convergence path gets
    `#774`'s SEQUENCER for free -- it waits for the operand that is due
    first and ignores the other however early it shows up -- so the
    result no longer depends on arrival timing. Commutative ops keep
    the cheaper plain chain: ordering is not needed there.

    Public so a frontend's scan pass can record the SAME decision the
    dispatcher will make, rather than re-deriving (and drifting from) it.
    """
    n_real = sum(1 for k in operand_kinds if k != "const")
    if n_real >= 2:
        return "convergence"
    entry = library_lookup(opcode)
    if entry is not None and not entry.is_commutative and len(operand_kinds) == 2 and n_real == 1:
        return "convergence"
    return "plain_chain"


def compile_dag(instructions: List[DagInstr]
                 ) -> Tuple[vix.IcmVixFile, Dict[str, Position], List[Tuple[str, int, int]], Dict[str, Tuple[int, int]]]:
    """The real dispatcher, rebuilt around incremental, frontier-based
    growth. Returns a real `IcmVixFile`, a dict of each instruction's
    own real final-cell position, a list of `(label, row, col)`
    dynamic-injection points (`#774`), and a real `seq_orders` dict
    (instr name -> `(dir_a, dir_b)` as real `N`/`S`/`E`/`W` constants)
    for any instruction using the SEQUENCER shape.

    Real, honest, named limitation: `pri_seq_order` is a real, runtime-
    only `SuperCell` field (`#772`'s own proven VM prototype) -- it has
    no real, schema-validated `core_config` field yet, so it cannot be
    set at real compile time through the `IcmVixFile` alone. The
    caller MUST apply `seq_orders[name]` to the corresponding real
    `SuperCell`'s own `pri_seq_order` attribute after `SuperGrid()`
    construction, matching the exact pattern `#772`/`#774`/`#775`'s
    own tests already established, or any SEQUENCER-shaped
    convergence in the compiled design will never capture anything at
    all (confirmed directly -- this was caught as a real, genuine bug
    while building this dispatcher, not a hypothetical)."""
    ref_count: Dict[str, int] = {}
    for instr in instructions:
        for op in instr.operands:
            if op.kind == "ref":
                ref_count[op.ref_name] = ref_count.get(op.ref_name, 0) + 1

    occ: Dict[Position, str] = {}
    frontiers: Dict[str, Frontier] = {}
    taps: Dict[str, _TapPoint] = {}
    positions: Dict[str, Position] = {}
    dynamic_positions: List[Tuple[str, int, int]] = []
    seq_orders: Dict[str, Tuple[int, int]] = {}
    all_cells: List = []
    leaf_counter = [0]  # real, growing offset so independent leaf instructions never collide

    for instr in instructions:
        resolved = [_resolve_operand(op) for op in instr.operands]
        if ingestion_path(instr.opcode, [r["kind"] for r in resolved]) == "plain_chain":
            cells, out_frontier = _grow_plain_chain(instr, resolved, occ, dynamic_positions, frontiers, taps,
                                                      leaf_counter)
        else:
            shape = choose_convergence_shape(
                has_real_convergence=True,
                is_commutative=library_lookup(instr.opcode).is_commutative,
                # Real, honest scope: this dispatcher does NOT yet
                # compute real, precise arrival-tick formulas (#773's
                # own symbolic_arrival_tick()) to guarantee the
                # STAGGER shape's own correctness when two branches'
                # own natural path lengths differ (the common case in
                # this incremental-growth architecture) -- confirmed
                # directly to produce a wrong result when assumed
                # otherwise. Until that real timing math is built,
                # honestly treat ticks as NOT reliably knowable here,
                # so SEQUENCER (#774's own proven, timing-independent
                # shape) is chosen for every non-commutative case.
                all_arrival_ticks_knowable=False,
            )
            cells, out_frontier, seq_order = _grow_convergence(instr, resolved, shape, occ, dynamic_positions,
                                                                 frontiers, taps, leaf_counter)
            if seq_order is not None:
                seq_orders[instr.name] = seq_order

        for c in cells:
            occ[(c.rel_row, c.rel_col)] = c.cell_id
        all_cells += cells
        instr_cell = _find_instr_cell(cells, instr.name)
        positions[instr.name] = (instr_cell.rel_row, instr_cell.rel_col)
        frontiers[instr.name] = out_frontier
        if ref_count.get(instr.name, 0) > 1:
            taps[instr.name] = _TapPoint(pos=out_frontier.pos, cell=instr_cell, claimed_dirs=[])

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=all_cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="dag_dispatch")
    return icm, positions, dynamic_positions, seq_orders


def _find_instr_cell(cells: List, name: str) -> "vix.HierCell":
    for c in cells:
        if c.cell_id == name:
            return c
    raise ValueError(f"instruction cell {name!r} not found among its own placed cells")


def _resolve_operand(op: DagOperand) -> dict:
    if op.kind == "const":
        return {"kind": "const", "value": op.value}
    if op.kind == "ref":
        return {"kind": "ref", "ref_name": op.ref_name}
    return {"kind": "dynamic"}


# Points.md #793: opcode selection now lives in a real, named,
# separate library (`vix_opcode_library_v1.py`) -- this dispatcher
# stays entirely PLACEMENT-focused, asking the library for the real
# facts (tile, port style, commutativity) it needs, never hardcoding
# an opcode-specific branch of its own. A future opcode needs a new
# `register()` call in the library module ONLY -- never a change here.
def _place_for_opcode(opcode: str, cell_id: str, row: int, col: int,
                       in_a_dir: str, in_b_dir: str, out_dir: str):
    """Real, single place this dispatcher decides HOW an opcode's own
    tile gets its real ports configured -- named (`adder`-style) or
    unconditional (`nano_gate`-style), per the real library entry's
    own `port_style`. Every placement function above calls this
    instead of `vtl.place()` directly."""
    entry = library_lookup(opcode)
    if entry is None:
        raise ValueError(f"no real library entry for opcode {opcode!r} -- #752's own escalation "
                          f"ladder applies: check the shared library, then AI research, then Composer")
    if entry.port_style == "unconditional":
        # nano_gate has no real, named "in" port at all (#718/#781's
        # own confirmed finding) -- only "out" is real and named;
        # whatever is physically wired to its other real faces is
        # accepted unconditionally, no upstream_mask to configure.
        return vtl.place(entry.tile, {"out": out_dir}, params=dict(entry.extra_params),
                          cell_id=cell_id, rel_row=row, rel_col=col)
    return vtl.place(entry.tile, {"in_a": in_a_dir, "in_b": in_b_dir, "out": out_dir},
                      cell_id=cell_id, rel_row=row, rel_col=col)


def _claim_branch_start(ref_name: str, frontiers: Dict[str, Frontier],
                         taps: Dict[str, _TapPoint]) -> Frontier:
    """Real, central fan-out logic: if this producer's own frontier has
    already been consumed once (genuine divergence), grow the NEW
    branch from the SAME original tap point, claiming a genuinely
    different real direction -- and genuinely adding it to the real
    producer cell's own `downstream_mask`, so it actually, physically
    offers there (not just logical bookkeeping) -- never reusing the
    first consumer's own direction, so the two branches physically
    cannot cross. Otherwise, the producer's own current frontier is
    used directly (its first, only real consumer)."""
    if ref_name in taps:
        tap = taps[ref_name]
        for d in _ROTATION:
            if d not in tap.claimed_dirs:
                tap.claimed_dirs.append(d)
                tap.cell.core_config["downstream_mask"] = list(tap.claimed_dirs)
                return Frontier(pos=tap.pos, out_dir=d)
        raise ValueError(f"{ref_name!r} has no free real growth direction left (max {len(_ROTATION)} consumers)")
    return frontiers[ref_name]


def _pad(frontier: Frontier, occ: Dict[Position, str], uid: str, hops: int = PAD) -> Tuple[List, Frontier]:
    """Grows `hops` real relay cells straight out from `frontier`, in
    its own real `out_dir` -- the real, literal "add a few padding
    cells" step. Returns the new cells and the new, real frontier."""
    cells: List = []
    dr, dc = _DIR_STEP[frontier.out_dir]
    pos = frontier.pos
    for i in range(hops):
        pos = (pos[0] + dr, pos[1] + dc)
        cell = vix.HierCell(cell_id=f"{uid}_{i}", rel_row=pos[0], rel_col=pos[1], core="ram",
                             core_config={"upstream_mask": [_OPP[frontier.out_dir]], "downstream_mask": [frontier.out_dir]})
        cells.append(cell)
        occ[pos] = cell.cell_id
    return cells, Frontier(pos=pos, out_dir=frontier.out_dir)


def _grow_plain_chain(instr: DagInstr, resolved: List[dict], occ: Dict[Position, str],
                       dynamic_positions: List[Tuple[str, int, int]],
                       frontiers: Dict[str, Frontier], taps: Dict[str, _TapPoint],
                       leaf_counter: List[int]
                       ) -> Tuple[List, Frontier]:
    """The `PLAIN_CHAIN` shape (`#756`): at most one real operand is
    non-constant. Grows directly out of that operand's own real,
    current frontier (or starts fresh at a genuinely new, unique real
    origin -- via `leaf_counter` -- if this instruction has no real,
    non-constant operand at all)."""
    cells: List = []
    real_op = next((r for r in resolved if r["kind"] != "const"), None)
    const_op = next((r for r in resolved if r["kind"] == "const"), None)

    if real_op is not None and real_op["kind"] == "ref":
        start = _claim_branch_start(real_op["ref_name"], frontiers, taps)
        pad_cells, grown = _pad(start, occ, f"pad_{instr.name}")
        cells += pad_cells
        target_pos = (grown.pos[0] + _DIR_STEP[grown.out_dir][0], grown.pos[1] + _DIR_STEP[grown.out_dir][1])
        in_dir = _OPP[grown.out_dir]
    elif real_op is not None and real_op["kind"] == "dynamic":
        origin = leaf_counter[0] * 100
        leaf_counter[0] += 1
        target_pos = (origin, 1)
        in_dir = "w"
        q = vix.HierCell(cell_id=f"dynq_{instr.name}", rel_row=origin, rel_col=0, core="ram",
                          core_config={"upstream_mask": [], "downstream_mask": ["e"]})
        cells.append(q)
        dynamic_positions.append((f"{instr.name}_x", origin, 0))
    else:
        origin = leaf_counter[0] * 100
        leaf_counter[0] += 1
        target_pos, in_dir = (origin, 0), "w"

    diff_row, diff_col = target_pos
    # Real, deliberate perpendicular stagger for the real constant
    # (`#776`'s own arrival-collision fix): fed from a side orthogonal
    # to the real, non-constant operand's own approach.
    const_side = "n" if in_dir in ("e", "w") else "e"
    offer_dir = _OPP[const_side]  # the direction the const cell/chain actually offers, TOWARD the target
    if const_op is not None:
        step_r, step_c = _DIR_STEP[const_side]
        const_start = (diff_row + step_r * (PAD + 1), diff_col + step_c * (PAD + 1))
        const_cell = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": offer_dir}, cell_id=f"const_{instr.name}",
                                rel_row=const_start[0], rel_col=const_start[1], preload_value=const_op["value"])
        cells.append(const_cell)
        cells += manhattan_route(const_start, offer_dir, (diff_row + step_r, diff_col + step_c),
                                  offer_dir, f"constpad_{instr.name}", occ)
        in_b_dir = const_side
    else:
        in_b_dir = "n" if const_side != "n" else "e"

    out_dir = "e" if "e" not in (in_dir, in_b_dir) else "s"
    diff = _place_for_opcode(instr.opcode, instr.name, diff_row, diff_col, in_dir, in_b_dir, out_dir)
    cells.append(diff)
    return cells, Frontier(pos=(diff_row, diff_col), out_dir=out_dir)


def _grow_convergence(instr: DagInstr, resolved: List[dict], shape: ConvergenceShape,
                       occ: Dict[Position, str], dynamic_positions: List[Tuple[str, int, int]],
                       frontiers: Dict[str, Frontier], taps: Dict[str, _TapPoint],
                       leaf_counter: List[int]
                       ) -> Tuple[List, Frontier, Optional[Tuple[int, int]]]:
    """Real convergence: both real operands' own frontiers are already
    KNOWN, real, local points -- brought together with a short, local
    connection, never a blind, long-distance route. Returns the real
    seq_order (as `N`/`S`/`E`/`W` constants) for the caller to apply to
    the real `SuperCell` post-construction if SEQUENCER was chosen,
    else `None`."""
    a, b = resolved[0], resolved[1]
    a_start = _claim_branch_start(a["ref_name"], frontiers, taps) if a["kind"] == "ref" else None
    b_start = _claim_branch_start(b["ref_name"], frontiers, taps) if b["kind"] == "ref" else None

    if a_start:
        a_padded_cells, a_frontier = _pad(a_start, occ, f"pad_{instr.name}_a")
    else:
        origin = leaf_counter[0] * 100
        leaf_counter[0] += 1
        a_padded_cells, a_frontier = [], Frontier((origin, -3), "e")
    if b_start:
        b_padded_cells, b_frontier = _pad(b_start, occ, f"pad_{instr.name}_b")
    else:
        origin = leaf_counter[0] * 100
        leaf_counter[0] += 1
        b_padded_cells, b_frontier = [], Frontier((origin, -3), "e")
    cells: List = list(a_padded_cells) + list(b_padded_cells)

    target = ((a_frontier.pos[0] + b_frontier.pos[0]) // 2 + 4, max(a_frontier.pos[1], b_frontier.pos[1]) + 4)
    orient = choose_two_way_orientation(target, a_frontier.pos, b_frontier.pos)

    scheduling_mode = 2 if shape == ConvergenceShape.SEQUENCER else 0
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": [orient["in_a"], orient["in_b"]], "out": orient["out"]},
                     params={"priority_rank_n": 0, "priority_rank_s": 0, "priority_rank_e": 0,
                             "priority_rank_w": 0, "scheduling_mode": scheduling_mode},
                     cell_id=f"pri_{instr.name}", rel_row=target[0], rel_col=target[1])
    cells.append(pri)

    dr, dc = _DIR_STEP[orient["out"]]
    add_pos = (target[0] + dr, target[1] + dc)
    add = _place_for_opcode(instr.opcode, instr.name, add_pos[0], add_pos[1],
                             _OPP[orient["out"]], _OPP[orient["out"]], "e")
    cells.append(add)

    b_extra = 2 if shape == ConvergenceShape.STAGGER else 0
    cells += _connect_frontier_to(a_frontier, a, target, orient["in_a"], occ, f"{instr.name}_a", extra_hops=0)
    cells += _connect_frontier_to(b_frontier, b, target, orient["in_b"], occ, f"{instr.name}_b", extra_hops=b_extra)

    seq_order = (_dir_const(orient["in_a"]), _dir_const(orient["in_b"])) if shape == ConvergenceShape.SEQUENCER else None
    if a["kind"] == "dynamic":
        dr_a, dc_a = _DIR_STEP[orient["in_a"]]
        dynamic_positions.append((f"{instr.name}_a", target[0] + dr_a, target[1] + dc_a))
    if b["kind"] == "dynamic":
        dr_b, dc_b = _DIR_STEP[orient["in_b"]]
        dynamic_positions.append((f"{instr.name}_b", target[0] + dr_b, target[1] + dc_b))

    return cells, Frontier(pos=add_pos, out_dir="e"), seq_order


def _connect_frontier_to(frontier: Optional[Frontier], op: dict, target: Position, in_dir: str,
                          occ: Dict[Position, str], uid: str, extra_hops: int = 0) -> List:
    dr, dc = _DIR_STEP[in_dir]
    face_pos = (target[0] + dr, target[1] + dc)
    src_out_dir = _OPP[in_dir]

    if op["kind"] == "const":
        src_pos = (face_pos[0] + (extra_hops + 1) * dr, face_pos[1] + (extra_hops + 1) * dc)
        src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": src_out_dir}, cell_id=f"const_{uid}",
                         rel_row=src_pos[0], rel_col=src_pos[1], preload_value=op["value"])
        cells = [src]
        cells += manhattan_route(src_pos, src_out_dir, face_pos, _OPP[in_dir], f"r_{uid}", occ)
        return cells

    if op["kind"] == "dynamic":
        src_pos = (face_pos[0] + (extra_hops + 1) * dr, face_pos[1] + (extra_hops + 1) * dc)
        q = vix.HierCell(cell_id=f"dynq_{uid}", rel_row=src_pos[0], rel_col=src_pos[1], core="ram",
                          core_config={"upstream_mask": [], "downstream_mask": [src_out_dir]})
        cells = [q]
        cells += manhattan_route(src_pos, src_out_dir, face_pos, _OPP[in_dir], f"r_{uid}", occ)
        return cells

    # a real, known frontier -- a short, local, well-understood route.
    if extra_hops > 0:
        mid_pos = (face_pos[0] + extra_hops * dr, face_pos[1] + extra_hops * dc)
        cells = manhattan_route(frontier.pos, frontier.out_dir, mid_pos, src_out_dir, f"r_{uid}a", occ)
        cells += manhattan_route(mid_pos, src_out_dir, face_pos, _OPP[in_dir], f"r_{uid}b", occ)
    else:
        cells = manhattan_route(frontier.pos, frontier.out_dir, face_pos, _OPP[in_dir], f"r_{uid}", occ)
    return cells


def _dir_const(d: str) -> int:
    from unicell_super_automaton_v1 import N, S, E, W
    return {"n": N, "s": S, "e": E, "w": W}[d]
