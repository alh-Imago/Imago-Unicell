"""
vix_n_way_reduction_v1.py — points.md #765: the real, general N-way
reduction compiler, generalizing the hand-built N=4 example (`#759`-
`#763`) to arbitrary N (a power of 2, for this first, bounded version)
-- built directly per Alan's own direct request: fold the composed-
piece timing model in, then add this to the compiler side, giving a
known, working starting point for the N-space generalization.

REAL, DELIBERATE SCOPE, stated precisely, not overclaimed: covers a
balanced binary tree of `priority`-arbitrated pairwise adds over N
compile-time CONSTANT leaves, N a power of 2. Uses the already-proven
rats-nest pipeline exactly as built and tested (`#760`-`#763`): a
loose, generously-spaced initial build (no attempt at compactness),
then real, automatic tightening -- leaf-to-nexus connections via the
fast, structural-only method (`#762`, safe because `priority` absorbs
timing by design), and nexus-to-nexus connections via the rigid-block
method (`#763`). Because every real convergence point here uses
`priority`, the symbolic timing model (`#764`/`#765`) is not needed
for correctness in THIS specific reduction shape -- it remains real,
necessary, separate work for a relay-padded (non-priority) N-way
reduction, not attempted here.

Real, honest, NOT yet covered: N that isn't a power of 2 (an unbalanced
tree); dynamic (non-constant) leaves; mixing `priority` and relay-
padded convergence within one design; 3-or-more-way convergence at a
single nexus (real, separate work -- `priority`'s own arbitration
already supports it per `#751`'s own direct test, but the tightening
machinery here has only ever moved two-source combine units).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import vix_tile_library_v1 as vtl
import icm_vix_v1 as vix
from rats_nest_tighten_v1 import tighten_leaf_connection_fast, tighten_nexus_to_nexus


def _combine_unit(row: int, col: int, uid: str, out_dir: str = "e") -> List[vix.HierCell]:
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1,
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                     cell_id=f"pri_{uid}", rel_row=row, rel_col=col)
    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "w", "out": out_dir},
                     cell_id=f"add_{uid}", rel_row=row, rel_col=col + 1)
    return [pri, add]


def compile_n_way_reduction(leaves: List[int]) -> Tuple[vix.IcmVixFile, Tuple[int, int]]:
    """The real, general reduction compiler. `leaves` is a list of N
    (a power of 2) compile-time constant values to sum. Returns a real,
    tightened `IcmVixFile` and the `(row, col)` of the final adder whose
    own `adder_out_buffer` holds the real, correct sum once run.

    Real, deliberate structure, matching `#759`'s own proven shape
    exactly, generalized: level 0 is the leaves, loosely spaced (10
    rows apart, matching `#760`'s own real "generous slack" principle);
    each subsequent level pairs up the previous level's own real
    results into new combine units, loosely placed further east; the
    whole thing is then tightened level by level, leaves first (`#762`'s
    fast, structural-only method), then each nexus level up via the
    rigid-block method (`#763`)."""
    n = len(leaves)
    if n < 2 or (n & (n - 1)) != 0:
        raise ValueError(f"compile_n_way_reduction: N must be a power of 2 >= 2, got {n}")

    occ: Dict[Tuple[int, int], str] = {}
    final_cells: List[vix.HierCell] = []

    # Level 0: leaves, loosely spaced -- generous, not tuned for
    # compactness at all, per the rat's-nest approach's own real
    # starting discipline.
    leaf_positions = [(i * 10, 0) for i in range(n)]

    # Build every level's own loose combine units first, recording each
    # one's own two real source positions for the tightening pass that
    # follows. Real cells are placed into `occ` for collision tracking
    # only here -- the REAL, final cells collected into `final_cells`
    # come from each tightening call's own real return value below.
    levels: List[List[Tuple[int, int, str, Tuple[int, int], Tuple[int, int]]]] = []
    current_positions = leaf_positions
    level = 1
    col_base = 20
    while len(current_positions) > 1:
        this_level: List[Tuple[int, int, str, Tuple[int, int], Tuple[int, int]]] = []
        next_positions: List[Tuple[int, int]] = []
        for i in range(0, len(current_positions), 2):
            src_a, src_b = current_positions[i], current_positions[i + 1]
            row_mid = (src_a[0] + src_b[0]) // 2 + 1
            uid = f"L{level}_{i // 2}"
            this_level.append((row_mid, col_base, uid, src_a, src_b))
            next_positions.append((row_mid, col_base))
        for row_mid, col, uid, _src_a, _src_b in this_level:
            cells = _combine_unit(row_mid, col, uid, out_dir="e")
            for c in cells:
                occ[(c.rel_row, c.rel_col)] = c.cell_id
        levels.append(this_level)
        current_positions = next_positions
        level += 1
        col_base += 30

    # Tighten level 1: leaf-to-nexus connections, the fast, structural-
    # only method (safe here -- priority absorbs timing by design).
    for row_mid, col, uid, src_a, src_b in levels[0]:
        pri_pos = (row_mid, col)
        idx_a = leaf_positions.index(src_a)
        idx_b = leaf_positions.index(src_b)
        _, chain_a = tighten_leaf_connection_fast(
            leaves[idx_a], src_a, (pri_pos[0] - 1, pri_pos[1]), "s", occ, f"{uid}_a")
        _, chain_b = tighten_leaf_connection_fast(
            leaves[idx_b], src_b, (pri_pos[0] + 1, pri_pos[1]), "n", occ, f"{uid}_b")
        final_cells += chain_a + chain_b

    # Tighten every subsequent level: nexus-to-nexus, the rigid-block
    # method -- each combine unit moves as one piece, re-routing both
    # of its own upstream connections at every candidate step. Each
    # level's own combine unit is placed AT LOOSE POSITION first (its
    # loose priority+adder cells), then immediately re-homed by
    # tighten_nexus_to_nexus() -- so only the REAL, final result of
    # that call is kept, never the loose placeholder.
    unit_final_pos: Dict[str, Tuple[int, int]] = {}
    for lvl_idx, lvl in enumerate(levels):
        for row_mid, col, uid, src_a, src_b in lvl:
            if lvl_idx == 0:
                unit_final_pos[uid] = (row_mid, col)
                final_cells += _combine_unit(row_mid, col, uid, out_dir="e")
                continue
            src_a_uid = _find_owning_unit(levels[lvl_idx - 1], src_a)
            src_b_uid = _find_owning_unit(levels[lvl_idx - 1], src_b)
            real_src_a = unit_final_pos[src_a_uid]
            real_src_b = unit_final_pos[src_b_uid]
            add_pos_a = (real_src_a[0], real_src_a[1] + 1)
            add_pos_b = (real_src_b[0], real_src_b[1] + 1)
            final_pos, unit_cells = tighten_nexus_to_nexus(
                f"pri_{uid}", f"add_{uid}", "e", (row_mid, col),
                add_pos_a, add_pos_b, row_bias=(real_src_a[0] + real_src_b[0]) // 2 + 1,
                occupied=occ, uid_prefix=uid)
            unit_final_pos[uid] = final_pos
            final_cells += unit_cells

    final_uid = levels[-1][0][2]
    final_pri_pos = unit_final_pos[final_uid]
    final_add_pos = (final_pri_pos[0], final_pri_pos[1] + 1)

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=final_cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name=f"reduce{n}")
    return icm, final_add_pos


def _find_owning_unit(level: List[Tuple[int, int, str, Tuple[int, int], Tuple[int, int]]],
                       pos: Tuple[int, int]) -> str:
    for row, col, uid, _a, _b in level:
        if (row, col) == pos:
            return uid
    raise ValueError(f"no combine unit found at {pos}")
