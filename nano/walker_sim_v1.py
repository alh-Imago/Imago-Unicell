"""walker_sim_v1.py — points.md #602: the real simulated Walker, per
`#598`'s own queued idea and `#501`'s already-converged real hardware
protocol design. Runs the EXACT SAME real discovery algorithm `#501`
designed for real silicon over JTAG -- ping a cell (self-or-cardinal),
self answers with its own real identity, a cardinal ping relays
unchanged one hop to whatever's really, physically connected there,
all walk intelligence stays host-side -- just against a VM-mirrored
grid (`vm_mirror_v1.py`, `#601`) instead of a real card. This is the
prerequisite Alan asked for made concrete: `walk()` refuses to fabricate
a map from nothing, per the honest, direct point that a Walker with no
real target discovers nothing.

REAL, DELIBERATE DISCIPLINE, matching `#501`'s own "all walk
intelligence is host-side, cells are purely reactive" design exactly:
`walk()` NEVER reads `session.grid.cells` directly to build its map --
every fact it learns comes through `ping()`, one real hop at a time,
starting from a single known origin. This is what makes it an honest
SIMULATION of the real protocol rather than a shortcut that happens to
produce the same answer -- swapping `ping()`'s own body for a real
JTAG round-trip later should need no change to `walk()` at all.

REAL, HONEST SCOPE: this discovers topology (which cells physically
exist, their real type/ID, and real cardinal adjacency) -- it does NOT
implement `#501`'s own `core_select=31` discovery-mode RTL mechanism
(that's a real, separate, still-unbuilt hardware change) or header
cells for specialist hardware (`#453`/`#474`'s RAM/DSP wrappers have no
`core_select` at all, per `#501`'s own real resolution) -- every cell
in a mirrored VM session is core-shaped today, so that gap doesn't
apply yet. Real, explicit boundary, not silently glossed over.
"""

import datetime
import os
import sys
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unicell_automaton_v1 import N, S, E, W, _OPPOSITE  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import project_assemble_v1 as pa  # noqa: E402

_DIR_NAME = {N: "n", S: "s", E: "e", W: "w"}
_NAME_DIR = {v: k for k, v in _DIR_NAME.items()}


class NoTargetError(Exception):
    """Raised when the Walker's own origin cell doesn't exist in the
    session it was pointed at -- the real, honest failure mode for
    "the VM isn't in place, so there's nothing to discover," rather
    than silently returning an empty, misleading map."""


def ping(session, row: int, col: int, direction: str) -> Optional[Dict[str, Any]]:
    """points.md #602: the real, minimal simulated version of #501's
    own ping protocol. `direction` is "self" or one of "n"/"s"/"e"/"w".

    "self" -> if a cell genuinely exists at (row, col) in this
    session's own real grid, answer directly with its real cell_id and
    type -- exactly what a real hardware cell in discovery mode would
    do for a self-directed ping. No cell there -> None (no response).

    A real cardinal direction -> per #501's own real design, the cell
    at (row, col) does NOT answer -- it relays the ping unchanged out
    that one physical port to whatever's really, physically connected
    there, and THAT neighbor is the one that answers. Simulated here as
    exactly one hop: look up the real neighbor via the grid's own
    `neighbor_pos()` (the same real cardinal-adjacency logic every
    other VM mechanism already uses, not a separate reimplementation),
    then self-ping that neighbor. No neighbor physically there -> None,
    matching a real timeout on an unconnected port."""
    if direction == "self":
        cell = session.grid.cells.get((row, col))
        if cell is None:
            return None
        return {"cell_id": cell.cell_id, "type": cell.core}

    if direction not in _NAME_DIR:
        raise ValueError(f"ping(): direction must be 'self' or one of {sorted(_NAME_DIR)}, got {direction!r}")

    neighbor = session.grid.neighbor_pos(row, col, _NAME_DIR[direction])
    if neighbor is None:
        return None
    return ping(session, neighbor[0], neighbor[1], "self")


@dataclass
class WalkResult:
    """The real, host-assembled map -- everything `walk()` learned by
    pinging, nothing it assumed."""
    origin: Tuple[int, int]
    #: (row, col) -> {"cell_id":..., "type":...}, exactly what a real
    #: self-ping returned for that position.
    discovered: Dict[Tuple[int, int], Dict[str, Any]] = field(default_factory=dict)
    #: one entry per real physical link found, deduplicated (a link is
    #: only ever recorded once, from the side it was first discovered
    #: from) -- (pos_a, dir_from_a, pos_b, dir_from_b).
    edges: List[Tuple[Tuple[int, int], str, Tuple[int, int], str]] = field(default_factory=list)
    #: real, honest ping count -- how many real ping() calls this walk
    #: actually took, so a caller can see this wasn't a free lookup.
    ping_count: int = 0


def walk(session, start: Tuple[int, int] = (0, 0)) -> WalkResult:
    """points.md #602: the real, host-side discovery algorithm, per
    `#501`'s own "all walk intelligence is host-side, cells are purely
    reactive" design. Starts from ONE known-trusted origin (matching
    real hardware's own real, established daisy-chain-addressing entry
    point, `#501`'s own real starting point) and walks outward hop by
    hop, discovering only what pinging actually reveals.

    Raises `NoTargetError` if `start` itself doesn't answer -- the
    real, honest failure for "this session has no real cell there to
    discover from," rather than returning a silently empty map."""
    result = WalkResult(origin=start)

    origin_answer = ping(session, start[0], start[1], "self")
    result.ping_count += 1
    if origin_answer is None:
        raise NoTargetError(
            f"no cell answered at the origin ({start[0]},{start[1]}) -- "
            f"this session has no real target for the Walker to discover. "
            f"Build one first, e.g. via vm_mirror_v1.VMSession.from_man()."
        )
    result.discovered[start] = origin_answer

    visited: Set[Tuple[int, int]] = set()
    linked: Set[frozenset] = set()
    frontier = deque([start])

    while frontier:
        pos = frontier.popleft()
        if pos in visited:
            continue
        visited.add(pos)
        r, c = pos
        for dname, d in _NAME_DIR.items():
            answer = ping(session, r, c, dname)
            result.ping_count += 1
            if answer is None:
                continue
            neighbor_pos = {N: (r - 1, c), S: (r + 1, c), E: (r, c + 1), W: (r, c - 1)}[d]
            if neighbor_pos not in result.discovered:
                result.discovered[neighbor_pos] = answer
            link_key = frozenset((pos, neighbor_pos))
            if link_key not in linked:
                linked.add(link_key)
                opp = _DIR_NAME[_OPPOSITE[d]]
                result.edges.append((pos, dname, neighbor_pos, opp))
            if neighbor_pos not in visited:
                frontier.append(neighbor_pos)

    return result


def _cell_id_str(cell_id: Optional[str]) -> Optional[str]:
    """points.md #602: real, honest pass-through -- icm_v3.
    IcmV3Record.cell_id is already a real, human-readable string (e.g.
    "r1@0,0", the DSL compiler's own convention), NOT the 16-bit int
    CELL_ID real hardware carries (#501's own confirmed field). A
    first draft of this function assumed the hardware convention and
    tried to hex-format it -- caught immediately by a real end-to-end
    smoke test raising TypeError, fixed before any test was written
    against the wrong assumption. No reformatting needed; this
    function exists only so a future real cell_id type change has one
    place to adapt."""
    return cell_id


def to_shape(result: WalkResult, card_id: str) -> Dict[str, Any]:
    """points.md #602: real, SHAPE-compatible output, sharing the same
    top-level fields (`shape_version`/`card_id`/`generated`/`cells`/
    `edges`) as `shape_extract_v1.py`'s own real, static-RTL-extracted
    SHAPE files -- so a real consumer (Composer, per its own already-
    decided scope) can read either kind without caring which one it
    got. `instance` names reuse `project_assemble_v1.inst_name()`
    directly (the SAME real naming convention an actual Quartus build
    would use), not a separately-invented scheme.

    Real, honest, explicit DIFFERENCE from a static-extracted SHAPE,
    stated in the file itself rather than left for a reader to
    discover the hard way: `source_file`/`top_module`/`git_commit` are
    all `None` (there is no RTL source this came from), and a new
    `discovery_method` field says plainly how this SHAPE was actually
    produced."""
    cells = []
    for (r, c), info in sorted(result.discovered.items()):
        cells.append({
            "instance": pa.inst_name(r, c),
            "module_type": info.get("type"),
            "cell_id": _cell_id_str(info.get("cell_id")),
            "role": "programmable_substrate",
            "row": r, "col": c,
        })
    edges = []
    for (pos_a, dir_a, pos_b, dir_b) in result.edges:
        edges.append({
            "from": {"instance": pa.inst_name(*pos_a), "direction": dir_a.upper()},
            "to": {"instance": pa.inst_name(*pos_b), "direction": dir_b.upper()},
        })
    return {
        "shape_version": "1.0",
        "card_id": card_id,
        "generated": datetime.date.today().isoformat(),
        "source_file": None,
        "top_module": None,
        "git_commit": None,
        "discovery_method": "simulated_walker_ping_protocol",
        "origin": list(result.origin),
        "ping_count": result.ping_count,
        "cells": cells,
        "edges": edges,
    }
