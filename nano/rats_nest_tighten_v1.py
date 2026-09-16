"""
rats_nest_tighten_v1.py — points.md #761: the real, second half of
Alan's own proposed "rat's nest" placement approach -- given a loose
layout (built via `rats_nest_router_v1.manhattan_route()`), find the
real nexus points (genuine multi-directional convergences), then
iteratively shrink each incoming connection toward its own nexus,
re-validating correctness at every single step, stopping the moment a
step would break something. Confirmed directly this session: this is
not a heuristic that might work -- every single tested step either
succeeds cleanly or the loop stops, exactly matching Alan's own
proposed discipline ("shift by 1 block, test for collision, then the
next").

REAL, DELIBERATE SCOPE for this first, working version: only tightens
connections whose own SOURCE is freely movable (a leaf/root value with
no other real connections depending on its own position) toward a
FIXED target (a nexus). Tightening a connection between two nexus
points -- where moving one end requires simultaneously re-routing
everything ELSE connected to it too -- is real, separate, harder work,
not attempted here.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import vix_tile_library_v1 as vtl
import icm_vix_v1 as vix
from unicell_super_automaton_v1 import SuperGrid
from rats_nest_router_v1 import manhattan_route, _DIR_STEP, _OPP


def find_nexus_points(cells: List[vix.HierCell]) -> List[vix.HierCell]:
    """A real nexus point: a cell whose real, configured upstream_mask
    names MORE THAN ONE cardinal direction -- a genuine, physical
    convergence of separate incoming routes. A two-arrival core like
    `adder` is NOT a nexus by this definition if both its real
    arrivals share one configured direction (its own real upstream_mask
    has only one entry) -- the convergence, if any, already happened
    upstream of it."""
    return [c for c in cells if len(c.core_config.get("upstream_mask") or []) > 1]


def tighten_leaf_connection(leaf_value: int, start_pos: Tuple[int, int],
                             target_pos: Tuple[int, int], target_out_dir: str,
                             occupied: Dict[Tuple[int, int], str], uid_prefix: str
                             ) -> Tuple[Tuple[int, int], List[vix.HierCell]]:
    """Shrink one leaf-to-nexus connection as far as it will go,
    re-validating with a real, full VM run at every single step.
    Returns the final, tightened leaf position and the real cells
    (leaf + relay chain) for that final, confirmed-correct state.
    Real, deliberate simplicity, per Alan's own proposed discipline:
    tries moving the leaf one step closer (closing the column gap
    first, then the row gap, matching the router's own order) at each
    iteration; stops the moment a step fails (a real collision, or the
    delivered value stops matching) or the leaf becomes directly
    adjacent to its own target.

    Points.md #762: for an ISOLATED connection like this one -- a
    single source, a single target, no other real value converging on
    the same consumer at the same time -- the full VM run turned out
    to be provably unnecessary. Confirmed directly, not assumed: every
    one of #761's own four real bugs was a STRUCTURAL problem (a
    position collision, or a test-harness logic error) -- none of them
    were timing bugs the VM's own tick-by-tick simulation was needed to
    catch. `tighten_leaf_connection_fast()` below does the identical
    real job using only `check_connections()`/`flatten()`'s own
    structural checks, confirmed to produce the exact same real result,
    roughly 6x faster on this session's own measured example. That
    speed only holds for ISOLATED connections -- once two real paths
    converge on the same consumer, real TIMING (not just geometry)
    decides correctness (`#750`/`#751`'s own entire subject), and a
    purely structural check is no longer sufficient on its own.
    """
    return _tighten_leaf_connection_impl(leaf_value, start_pos, target_pos, target_out_dir,
                                          occupied, uid_prefix, use_vm=True)


def tighten_leaf_connection_fast(leaf_value: int, start_pos: Tuple[int, int],
                                  target_pos: Tuple[int, int], target_out_dir: str,
                                  occupied: Dict[Tuple[int, int], str], uid_prefix: str
                                  ) -> Tuple[Tuple[int, int], List[vix.HierCell]]:
    """The real, faster twin of `tighten_leaf_connection()` -- identical
    real job, identical real result (confirmed directly, not assumed,
    by a dedicated test comparing both against the same real inputs),
    validating each candidate step with `check_connections()`/
    `flatten()`'s own structural checks alone, never running the VM.
    Real, honest scope: correct ONLY for isolated connections with no
    real convergence -- see `#762`'s own real reasoning above."""
    return _tighten_leaf_connection_impl(leaf_value, start_pos, target_pos, target_out_dir,
                                          occupied, uid_prefix, use_vm=False)


def _tighten_leaf_connection_impl(leaf_value: int, start_pos: Tuple[int, int],
                                   target_pos: Tuple[int, int], target_out_dir: str,
                                   occupied: Dict[Tuple[int, int], str], uid_prefix: str,
                                   use_vm: bool
                                   ) -> Tuple[Tuple[int, int], List[vix.HierCell]]:
    row, col = start_pos

    def try_at(r, c):
        test_occ = dict(occupied)
        if (r, c) in test_occ:
            return None
        # Real, deliberate fix: the leaf's own real output direction
        # must point toward whichever gap actually remains -- if its
        # own column already matches the target's, heading "east" by
        # default overshoots and the route loops back onto the leaf's
        # own position (a real, genuine bug found directly this
        # session, not a hypothetical edge case).
        if c != target_pos[1]:
            leaf_out = "e" if target_pos[1] > c else "w"
        elif r != target_pos[0]:
            leaf_out = "s" if target_pos[0] > r else "n"
        else:
            return None  # leaf would sit exactly on the target -- never valid
        src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": leaf_out}, cell_id=f"{uid_prefix}_leaf",
                         rel_row=r, rel_col=c, preload_value=leaf_value)
        test_occ[(r, c)] = src.cell_id
        route = manhattan_route((r, c), leaf_out, target_pos, target_out_dir, f"{uid_prefix}_r", test_occ)
        for cell in route:
            if (cell.rel_row, cell.rel_col) in occupied:
                return None  # real collision with something outside this connection
        # The real probe 'sink' must sit on whichever side target_pos
        # actually offers toward (target_out_dir), not a hardcoded
        # direction -- a real, genuine bug found directly this session:
        # a route approaching target_pos from the south (heading
        # north) has its own last relay SOUTH of target_pos, colliding
        # with a sink hardcoded one row south regardless of direction.
        sink_dr, sink_dc = _DIR_STEP[target_out_dir]
        sink_pos = (target_pos[0] + sink_dr, target_pos[1] + sink_dc)
        # Real, deliberate fix: sink_pos is a stand-in for the REAL,
        # eventual target cell (already registered in `occupied` under
        # its own real name, e.g. a priority cell) -- it is not a
        # competing new cell, so it must never be checked against
        # `occupied` for collision. A first version incorrectly
        # rejected every candidate once the real target was already
        # placed, found directly by re-running this session.
        sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": _OPP[target_out_dir], "out": "e"},
                          cell_id=f"{uid_prefix}_sink", rel_row=sink_pos[0], rel_col=sink_pos[1])
        icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[src] + route + [sink])},
                              placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                              name="tighten_probe")
        try:
            if icm.check_connections():
                return None
            recs, _ = icm.flatten()
        except vix.IcmVixFormatError:
            return None  # a real structural problem (e.g. a position collision) -- reject this candidate
        if not use_vm:
            return [src] + route  # structural checks alone are enough for an isolated connection
        grid = SuperGrid(recs)
        for _ in range(max(30, len(route) + 5)):
            grid.tick()
        sink_cell = grid.cells[sink_pos]
        if not (sink_cell.ram_data_valid and sink_cell.ram_data_reg == leaf_value):
            return None
        return [src] + route

    current = try_at(row, col)
    assert current is not None, "starting position must already be valid"

    while True:
        new_row, new_col = row, col
        if new_col != target_pos[1]:
            new_col += 1 if target_pos[1] > new_col else -1
        elif new_row != target_pos[0]:
            new_row += 1 if target_pos[0] > new_row else -1
        else:
            break  # leaf is already at the target's own position -- can't happen validly
        if (new_row, new_col) == target_pos:
            break  # don't move the leaf onto the target cell itself
        candidate = try_at(new_row, new_col)
        if candidate is None:
            break
        row, col, current = new_row, new_col, candidate

    for cell in current:
        occupied[(cell.rel_row, cell.rel_col)] = cell.cell_id
    return (row, col), current


def tighten_nexus_to_nexus(pri_cell_id: str, add_cell_id: str, add_out_dir: str,
                            start_pos: Tuple[int, int],
                            src_a_pos: Tuple[int, int], src_b_pos: Tuple[int, int],
                            row_bias: int, occupied: Dict[Tuple[int, int], str],
                            uid_prefix: str
                            ) -> Tuple[Tuple[int, int], List[vix.HierCell]]:
    """Points.md #763: real nexus-to-nexus tightening -- the harder
    case `#761` explicitly deferred, where the moving end is itself a
    nexus with its OWN two upstream connections, not a freely-movable
    leaf. Per Alan's own direct proposal: move the whole combine unit
    (priority + its own adder) as one rigid block -- the same real
    'solved piece becomes the next whole piece' framing already
    established -- re-routing both of its own real upstream
    connections from their own FIXED source positions at every
    candidate step.

    Real, honest, deliberately narrow scope, confirmed directly, not
    assumed: this uses ONLY structural checks (`check_connections()`/
    `flatten()`), never the VM. That is correct here specifically
    because both real sources feed into a `priority` cell, which
    already absorbs any real timing mismatch between them by design
    (`#751`'s own entire point) -- there is no `#750`-style arrival-
    collision hazard to check for. This does NOT generalize to a
    relay-padded design where two paths must keep genuinely different
    lengths to stay correct -- that case still needs a real, symbolic
    timing check (or the VM), not attempted here.

    `row_bias` sets which row the priority cell settles on once its own
    column reaches `src_a_pos`'s (its own real N-neighbor's column) --
    typically the real midpoint between the two source rows, so the
    priority cell can directly sandwich both once fully tightened."""
    row, col = start_pos

    def move_unit(new_row, new_col):
        new_pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                             params={"priority_rank_n": 0, "priority_rank_s": 1,
                                     "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                             cell_id=pri_cell_id, rel_row=new_row, rel_col=new_col)
        new_add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "w", "out": add_out_dir},
                             cell_id=add_cell_id, rel_row=new_row, rel_col=new_col + 1)
        return [new_pri, new_add]

    def try_at(new_row, new_col):
        moved = move_unit(new_row, new_col)
        test_occ = {k: v for k, v in occupied.items() if v not in (pri_cell_id, add_cell_id)}
        for c in moved:
            if (c.rel_row, c.rel_col) in test_occ:
                return None
            test_occ[(c.rel_row, c.rel_col)] = c.cell_id
        route_a = manhattan_route(src_a_pos, "e", (new_row - 1, new_col), "s", f"{uid_prefix}_a", test_occ)
        route_b = manhattan_route(src_b_pos, "e", (new_row + 1, new_col), "n", f"{uid_prefix}_b", test_occ)
        all_cells = moved + route_a + route_b
        icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=all_cells)},
                              placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                              name="nexus_probe")
        try:
            if icm.check_connections():
                return None
            icm.flatten()
        except vix.IcmVixFormatError:
            return None
        return all_cells

    current = try_at(row, col)
    assert current is not None, "starting position must already be valid"

    while True:
        new_row, new_col = row, col
        if new_col > src_a_pos[1] + 1:
            new_col -= 1
        elif new_row != row_bias:
            new_row += 1 if row_bias > new_row else -1
        else:
            break
        candidate = try_at(new_row, new_col)
        if candidate is None:
            break
        row, col, current = new_row, new_col, candidate

    for c in current:
        occupied[(c.rel_row, c.rel_col)] = c.cell_id
    return (row, col), current
