"""connection_check_v1.py — points.md #606: real, cross-cell cardinal-
connection sanity checking for Composer, per Alan's own real request:
"prompts to give hints/directions of connections before they are
made." A cell can be PHYSICALLY adjacent to a real neighbor and still
have its broadcast silently dropped if that neighbor isn't configured
to listen from the matching direction -- this module finds those real
mismatches before they're committed, not after.

REAL, PER-CORE FIELD MAPPING, verified directly against
`unicell_super_automaton_v1.py`'s own real dispatch and capture logic
before being written here (not assumed from the tile library's naming
alone) -- confirmed every "_dir"-named field (`inc_dir`/`dec_dir`/
`set_dir`/`clear_dir`) is actually a real 4-bit DIRECTION MASK (bit-
tested via `(field >> _DIR_BIT[d]) & 1`), same convention as
`upstream_mask`/`downstream_mask`, with exactly ONE real, documented
exception: `branch`'s own `upstream_dir` is a genuine SINGLE direction
value (`& 0x3`, matched by equality, not a bit test) -- checked
directly, not guessed.

REAL, HONEST SCOPE, stated plainly rather than silently wrong:
- `branch`'s own OUTPUT is data-dependent (`active_route`, chosen at
  runtime by comparing an arrived value against a reference) -- not a
  static config this module can check ahead of time. Excluded from
  the OUTGOING side of this check entirely, not silently mishandled.
- `sequencer` has NO real VM dispatch at all yet (a real, pre-existing
  gap, `#519`) -- can never actually appear in a live session today.
  Handled defensively (skipped, not crashed on) in case that changes.
- `nano` has no real upstream gate at all (`super_tile_library_v1.py`'s
  own documented finding) -- it accepts an arrival from ANY physically
  wired neighbor unconditionally, so it can never be the TARGET of a
  real mismatch, only ever a safe destination.
"""

import os
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unicell_automaton_v1 import N, S, E, W, _OPPOSITE  # noqa: E402
import icm_v3  # noqa: E402

_DIR_NAME = {N: "N", S: "S", E: "E", W: "W"}
_DELTA = {N: (-1, 0), S: (1, 0), E: (0, 1), W: (0, -1)}
_LETTER_TO_DIR = {"n": N, "s": S, "e": E, "w": W}

#: real, verified per-core-type field mapping -- see module docstring.
#: "in_fields": config keys OR'd together to form the real listening
#: mask (empty list = no real gate, always accepts, e.g. nano).
#: "out_field": the single real config key holding the broadcast mask,
#: or None if the core's real output is dynamic/not staticaly checkable.
CORE_DIRECTION_FIELDS: Dict[str, Dict[str, object]] = {
    "ram":         {"in_fields": ["upstream_mask"], "out_field": "downstream_mask"},
    "adder":       {"in_fields": ["upstream_mask"], "out_field": "downstream_mask"},
    "accumulator": {"in_fields": ["inc_dir", "dec_dir"], "out_field": "downstream_mask"},
    "comparator":  {"in_fields": ["upstream_mask"], "out_field": "downstream_mask"},
    "latch":       {"in_fields": ["set_dir", "clear_dir"], "out_field": "downstream_mask"},
    "nano":        {"in_fields": [], "out_field": "routing_mask"},
    "branch":      {"in_fields": None, "out_field": None},   # dynamic -- not statically checkable
    "sequencer":   {"in_fields": None, "out_field": None},   # no real VM dispatch yet, #519
}


def _as_direction_set(val) -> set:
    """Real, robust handling of the two real representations a config
    field can hold at this stage -- a list/tuple/set of direction
    letters (the real, pre-pack ICM v3 form, e.g. `['e']`) or an
    already-packed int bitmask -- via `icm_v3`'s own canonical
    `unpack_dirmask()`/`pack_dirmask()`, not a separate reimplementation
    that could drift from the real encoding."""
    if isinstance(val, (list, tuple, set)):
        letters = [d.lower() for d in val]
    else:
        letters = icm_v3.unpack_dirmask(int(val))
    return {_LETTER_TO_DIR[d] for d in letters if d in _LETTER_TO_DIR}


def _out_directions(core: str, config: dict) -> List[int]:
    spec = CORE_DIRECTION_FIELDS.get(core)
    if spec is None or spec["out_field"] is None:
        return []
    return sorted(_as_direction_set(config.get(spec["out_field"], [])))


def _listens(core: str, config: dict, direction: int) -> Optional[bool]:
    """True/False if this core type has a real, statically-checkable
    listening gate; None if it doesn't (either because it has no gate
    at all -- nano, always listens -- or because it's not statically
    checkable -- branch/sequencer, real unknown, not a real "yes")."""
    spec = CORE_DIRECTION_FIELDS.get(core)
    if spec is None or spec["in_fields"] is None:
        return None
    if not spec["in_fields"]:
        return True  # nano: no real gate, always accepts
    combined: set = set()
    for field_name in spec["in_fields"]:
        combined |= _as_direction_set(config.get(field_name, []))
    return direction in combined


def check_connections(records) -> List[str]:
    """`records` is any iterable of objects with real `.row`/`.col`/
    `.core`/`.core_config`/`.cell_id` attributes (an `IcmV3Record` or
    equivalent). Returns a list of real, human-readable HINT strings
    (never raises, never blocks -- these are prompts, per Alan's own
    framing, not hard rejections like `vm_mirror_v1`'s own real
    topology/shell-compatibility checks)."""
    by_pos: Dict[Tuple[int, int], object] = {(r.row, r.col): r for r in records}
    hints: List[str] = []
    for pos, rec in sorted(by_pos.items()):
        for d in _out_directions(rec.core, rec.core_config):
            neighbor_pos = (pos[0] + _DELTA[d][0], pos[1] + _DELTA[d][1])
            neighbor = by_pos.get(neighbor_pos)
            if neighbor is None:
                continue  # no real physical neighbor there -- nothing to warn about
            listens = _listens(neighbor.core, neighbor.core_config, _OPPOSITE[d])
            if listens is False:
                hints.append(
                    f"{rec.cell_id} at ({pos[0]},{pos[1]}) broadcasts {_DIR_NAME[d]} toward "
                    f"{neighbor.cell_id} at {neighbor_pos}, but {neighbor.cell_id} isn't "
                    f"configured to listen from {_DIR_NAME[_OPPOSITE[d]]} -- this connection "
                    f"would be silently dropped, not an error, just data that never arrives."
                )
    return hints
