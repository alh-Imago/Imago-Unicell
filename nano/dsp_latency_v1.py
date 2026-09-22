"""
dsp_latency_v1.py — points.md #822: DSP-WRAPPER LOWERING, the "#816 bridge tile" item, closed at the smallest safe
scope. `mul_dsp` (and any `resource`-bound op) is already BOUND to a real DSP site (`#804`/`#819`); what was still
missing (`#804`/`#811`/`#816`'s own honest limit) is that it still SIMULATES as an ordinary, instant `mul` core --
its real pipeline latency is not represented as elapsed VM time at all.

GROUNDED, before building anything. `#25` (2026-07-09) named this the `HARD_MUL` boundary tile: "a BRIDGE rather
than an opcode... it crosses a latency domain." Its stated concern was the fabric's TWO-ARRIVAL FIRING model
breaking if a DSP result returns late relative to a fabric-computed sibling, needing "delay cells" (`#5`) to
realign. Checked directly against `unicell_super_automaton_v1.py`'s own real capture logic (`_deliver_mul`) before
assuming any of this still applies: a two-arrival core captures A, THEN WAITS -- however long -- for B, then fires.
There is no same-tick requirement at all. So `#25`'s original synchronisation concern does not bind in the
CURRENT, general SuperGrid model (it predates it); what remains genuinely missing is only that the DSP-bound
cell's result becomes visible with ZERO elapsed delay, when a real DSP block needs several.

THE APPROACH, and why it touches no shared file. `#5`'s own "delay cells" ARE exactly this, in existing project
vocabulary: extra relay hops, since a relay cell already takes a real propagation tick per hop in this event-driven
model (used throughout `#808`-`#821`'s work). So representing a DSP's real latency needs no new core type and no
change to `unicell_super_automaton_v1.py`'s shared, heavily-tested tick loop or to `vix_virtual_layout_v1.py`'s
router: it is a PURE POST-PROCESSING step on an already-compiled, already-routed design's cell list -- extend the
DSP-bound cell's existing output relay chain by `extra_hops` cells, via a free-space detour, never touching any
other record.

THE PARITY CONSTRAINT -- worked out by hand, not assumed. `dsp_pos` and the consumer it feeds are FIXED cell
positions; any simple (non-self-crossing) grid path between two fixed points has a length whose PARITY is fixed
by their Manhattan distance -- every step changes Manhattan-parity by exactly 1, so a path's edge count is always
congruent to that distance mod 2. The design's existing routed path already has the correct parity (it exists);
padding it must therefore add an EVEN number of edges, or no simple path of the padded length can exist at all.
`extra_hops` must be even; an odd value is refused outright, not rounded or silently adjusted.

THE DETOUR ITSELF -- a rectangle, not a search. Pick one edge P_i -> P_{i+1} (direction `dir`) on the existing
chain. For a free perpendicular direction `perp` with room for a 2 x k strip (k = extra_hops // 2): lay k cells
out from P_i (`Q_1..Q_k`), one step across in `dir` (`Q_k` -> `R_k`), then k cells back to P_{i+1} (`R_k..R_1`).
That replaces the one edge with `2k + 1` edges -- `2k` more than before, using `2k` new, mutually distinct cells,
with no pathfinding search needed: the rectangle's own two facing columns are provably disjoint from each other.

Per `#815`, the number itself stays LOOSE -- `latency` is a parameter here, never a default asserted for any card.

REAL, HONEST LIMITS
  * Only pads a SIMPLE relay chain (`core="ram"`, flowing, exactly one predecessor and one successor at every hop)
    immediately downstream of the resource-bound cell -- the shape `#804`'s placer/router actually produces for
    the small, single-consumer examples checked here. A DSP result fanning out to SEVERAL consumers, or routed
    through a priority/mux cell immediately with no relay in between, is refused with the reason, not mishandled.
  * The detour needs a genuinely free 2 x k rectangle beside the FIRST hop of the existing chain in one of the two
    perpendicular directions; it does not search further afield or try other edges along the chain if the first
    one has no room. Refused with the reason, not silently attempted elsewhere.
  * `extra_hops` must be even (see above); this is a fact about simple grid paths between fixed points, not a
    limitation of this implementation specifically.
  * Verified end to end on the real VM for one- and two-op programs; not integrated into `stream_layout_v1`'s
    multi-chain placement or `dsp_chain_placement_v1`'s real Arria 10 sites -- this closes the SIMULATION gap
    (latency is now elapsed VM time, not zero), not the physical placement of a real bridge tile itself.
"""
from __future__ import annotations

import os
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dataclasses

import icm_v3 as v3  # noqa: E402
import vix_tile_library_v1 as vtl  # noqa: E402

Pos = Tuple[int, int]
_STEP = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}
_OPP = {"n": "s", "s": "n", "e": "w", "w": "e"}
_DIRS = ("n", "s", "e", "w")


class DspLatencyError(ValueError):
    """The output shape or the local geometry does not support padding here. Loud by design -- never a silent
    mis-route."""


def _step(p: Pos, face: str) -> Pos:
    d = _STEP[face]
    return (p[0] + d[0], p[1] + d[1])


def _face_between(a: Pos, b: Pos) -> str:
    for f in _DIRS:
        if _step(a, f) == b:
            return f
    raise DspLatencyError(f"{a} and {b} are not adjacent")


def _is_flowing_relay(rec) -> bool:
    return rec.core == "ram" and not rec.core_config.get("fixed_mode", 0)


def find_output_chain(records: List, dsp_pos: Pos) -> Tuple[List[Pos], Pos]:
    """Walk the SIMPLE relay chain leaving `dsp_pos`'s single downstream face. Returns (relay_positions, the first
    non-relay cell reached -- the real consumer). Refuses a fan-out, no downstream face, or a branch partway along."""
    by_pos = {(r.row, r.col): r for r in records}
    dsp = by_pos.get(dsp_pos)
    if dsp is None:
        raise DspLatencyError(f"no record at {dsp_pos}")
    down = dsp.core_config.get("downstream_mask") or []
    if len(down) != 1:
        raise DspLatencyError(f"{dsp_pos} does not have exactly one downstream face (has {down}) -- fan-out from a "
                              f"DSP-bound cell is not supported here")
    chain: List[Pos] = []
    cur = _step(dsp_pos, down[0])
    came_from = _OPP[down[0]]
    while True:
        rec = by_pos.get(cur)
        if rec is None:
            raise DspLatencyError(f"the output path from {dsp_pos} leaves the compiled design at {cur}")
        if not _is_flowing_relay(rec):
            return chain, cur                                # a real consumer: the join point
        up = rec.core_config.get("upstream_mask") or []
        down = rec.core_config.get("downstream_mask") or []
        if up != [came_from] or len(down) != 1:
            raise DspLatencyError(f"relay {cur} is not a plain single-in/single-out hop (up={up}, down={down})")
        chain.append(cur)
        came_from = _OPP[down[0]]
        cur = _step(cur, down[0])


def pad_output_latency(records: List, dsp_pos: Pos, extra_hops: int) -> List:
    """Return a NEW records list: `dsp_pos`'s output relay chain extended by exactly `extra_hops` hops, via one
    rectangular detour, so the value takes `extra_hops` more real VM ticks to reach its consumer. `extra_hops=0`
    returns an equivalent (copied) list. Every other record keeps its original position; only the relay cells
    strictly between `dsp_pos` and its consumer are rebuilt."""
    if extra_hops < 0:
        raise ValueError("extra_hops must be >= 0")
    if extra_hops % 2:
        raise DspLatencyError(f"extra_hops must be even ({extra_hops} given) -- a simple path between two fixed "
                              f"points can only change length by an even number and still connect them")
    chain, dest = find_output_chain(records, dsp_pos)
    if extra_hops == 0:
        return list(records)
    k = extra_hops // 2
    path = [dsp_pos] + chain + [dest]                        # the full sequence of positions, endpoints included
    p_i, p_i1 = path[0], path[1]                             # detour the FIRST edge of the existing chain
    fwd = _face_between(p_i, p_i1)
    occ = set((r.row, r.col) for r in records) - set(chain)  # the chain cells will be rebuilt; everything else is fixed
    perp_candidates = [f for f in _DIRS if f not in (fwd, _OPP[fwd])]
    detour_face = None
    for f in perp_candidates:
        qs = [(p_i[0] + _STEP[f][0] * j, p_i[1] + _STEP[f][1] * j) for j in range(1, k + 1)]
        rs = [(p_i1[0] + _STEP[f][0] * j, p_i1[1] + _STEP[f][1] * j) for j in range(1, k + 1)]
        if all(p not in occ for p in qs + rs):
            detour_face = f
            break
    if detour_face is None:
        raise DspLatencyError(f"no free {k}-cell-deep strip beside {p_i}->{p_i1} in either perpendicular direction "
                              f"to detour {extra_hops} extra hops through")
    qs = [(p_i[0] + _STEP[detour_face][0] * j, p_i[1] + _STEP[detour_face][1] * j) for j in range(1, k + 1)]
    rs = [(p_i1[0] + _STEP[detour_face][0] * j, p_i1[1] + _STEP[detour_face][1] * j) for j in range(1, k + 1)]
    detour_positions = qs + list(reversed(rs))               # dsp -> q1 -> ... -> qk -> rk -> ... -> r1 -> p_i1

    def relay(pos: Pos, in_face: str, out_face: str, tag: str):
        hc = vtl.place(vtl.TILE_RAM_FLOWING, {"in": in_face, "out": out_face},
                       cell_id=f"pad_{tag}_{pos[0]}_{pos[1]}")
        return v3.IcmV3Record(cell_id=hc.cell_id, row=pos[0], col=pos[1], core=hc.core,
                              core_config=hc.core_config, addon_config=hc.addon_config)

    new_cells = []
    full = [p_i] + detour_positions + [p_i1] + chain[1:] + [dest]
    for idx in range(1, len(full) - 1):
        pos = full[idx]
        in_face = _OPP[_face_between(full[idx - 1], pos)]
        out_face = _face_between(pos, full[idx + 1])
        new_cells.append(relay(pos, in_face, out_face, "detour" if pos in detour_positions else "orig"))
    by_pos = {(r.row, r.col): r for r in records}
    dsp_rec = by_pos[dsp_pos]
    new_dsp_rec = dataclasses.replace(dsp_rec, core_config={**dsp_rec.core_config,
                                                            "downstream_mask": [_face_between(dsp_pos, full[1])]})
    remaining = [r for r in records if (r.row, r.col) not in chain and (r.row, r.col) != dsp_pos]
    return remaining + [new_dsp_rec] + new_cells
