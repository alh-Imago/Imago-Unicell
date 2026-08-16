"""
generic_field_codec_v1.py — a field pack/unpack engine driven ENTIRELY
by `root_definition.json` (`points.md #355`), not by any hand-typed
Python dict. This is `points.md #216` items 2 and 4 together, which
turn out to be the same real undertaking rather than two separate
ones: "grid construction... matching the real hardware topology" (item
2) needs a cell-design-aware engine to build cells FROM (item 4:
"genuinely parameterized against whatever root definition got loaded,
not hardcoded to today's specific cell revision"). This file is that
engine's field-level foundation.

WHY THIS MATTERS, stated concretely rather than abstractly: `icm_v3.py`
's own `CORE_FIELD_TABLES` are a human-maintained Python dict -- built
this session by reading RTL comments and typing the bit positions in by
hand. If the RTL ever moves a field, `icm_v3.py` silently keeps using
the OLD positions until a human notices and updates it -- exactly the
"77+ file Python ecosystem falls further behind every time the RTL
moves" problem `#215`/`#216` both named directly. This module reads
`root_definition.json` (itself mechanically regenerable from the RTL's
own comments via `regenerate_root_definition_v1.py`) and derives the
SAME packing behavior from it directly -- so a moved field only ever
needs the root definition regenerated, not this file edited by hand.

PROVEN EQUIVALENT TO `icm_v3.py`'s OWN HAND-TYPED CODEC, not just
assumed to produce the same thing because the source data matches --
`tests/vm/test_generic_field_codec_v1.py` runs a real, systematic
equivalence check across all 6 cores and many values, comparing this
module's output bit-for-bit against `icm_v3.py`'s own already-proven
(RTL-simulation-verified, `#336`) `pack_core_config()`/
`unpack_core_config()`.

HONEST SCOPE, carried forward from `#355`'s own stated gap: this covers
`core_select`/`core_config` only. `addon_config` isn't in
`root_definition.json` at all (it's wired via direct module port
connections in the RTL, not the same field-map comment convention), so
it isn't -- and can't yet be -- driven generically here. A full
`encode_super_latch()` equivalent still needs `addon_config` supplied
by the caller as a raw already-packed integer, or built via `icm_v3.py`
's own hand-typed `pack_addon_config()` -- not a silent gap, a stated
one.

WHAT THIS DELIBERATELY DOESN'T DO: the higher-level convenience of
accepting a direction NAME or a LIST of directions (`icm_v3.py`'s own
`pack_dirmask()`/`unpack_dirmask()`) is a separate, core-independent
concern from field-position lookup, and isn't re-derived here --
`icm_v3.py`'s own dirmask helpers remain the right tool for that layer,
reusable as-is on top of this module's raw integer fields.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Tuple

DEFAULT_ROOT_DEFINITION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "root_definition.json")

# Maps icm_v3.py's own core_select integer values onto root_definition.json's
# own keys -- the ONE place this file has any hardcoded core-name
# knowledge at all (a name mapping, not a bit-position one).
CORE_SELECT_TO_ROOT_KEY = {
    0: "nano_within_super",   # NOT "nano" -- that's the standalone cmd_latch
                               # layout, a different field map entirely (#355)
    1: "ram",
    2: "adder",
    3: "accumulator",
    4: "comparator",
    5: "latch",
}


def load_root_definition(path: str = DEFAULT_ROOT_DEFINITION_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


def field_table(root_def: dict, core_select: int) -> Dict[str, Tuple[int, int]]:
    """`{field_name: (lo, hi)}` for a given `core_select`, derived
    entirely from the loaded root definition -- no hand-typed table
    consulted at all. `"reserved"` entries are dropped (they're real
    RTL bit ranges, but not addressable fields a caller would ever set)."""
    if core_select not in CORE_SELECT_TO_ROOT_KEY:
        raise ValueError(f"core_select {core_select} has no root-definition entry "
                          f"(only 0-5 are covered -- 6-31 remain genuine future "
                          f"headroom per #317, same as icm_v3.py's own table)")
    key = CORE_SELECT_TO_ROOT_KEY[core_select]
    table: Dict[str, Tuple[int, int]] = {}
    for entry in root_def[key]["fields"]:
        name = entry["name"].split("[")[0]   # strip a "[31:0]"-style width suffix
        if name == "reserved":
            continue
        table[name] = (entry["lo"], entry["hi"])
    return table


def pack_field(value: int, lo: int, hi: int) -> int:
    width = hi - lo + 1
    mask = (1 << width) - 1
    if value & ~mask:
        raise ValueError(f"value {value:#x} does not fit in field [{hi}:{lo}] "
                          f"({width} bits, max {mask:#x})")
    return (value & mask) << lo


def pack_core_config(root_def: dict, core_select: int, values: Dict[str, int]) -> int:
    """Packs raw integer field values into a `core_config` word, purely
    from the loaded root definition -- the generic analog of
    `icm_v3.py`'s own hand-typed `pack_core_config()`. Values here are
    already-resolved integers (a caller wanting the direction-name/list
    convenience should resolve that via `icm_v3.pack_dirmask()` first,
    same separation of concerns noted in the module docstring)."""
    table = field_table(root_def, core_select)
    unknown = set(values) - set(table)
    if unknown:
        raise ValueError(f"unknown field(s) {sorted(unknown)} for core_select {core_select} "
                          f"(known fields: {sorted(table)})")
    packed = 0
    for name, (lo, hi) in table.items():
        packed |= pack_field(values.get(name, 0), lo, hi)
    return packed


def unpack_core_config(root_def: dict, core_select: int, packed: int) -> Dict[str, int]:
    table = field_table(root_def, core_select)
    out = {}
    for name, (lo, hi) in table.items():
        width = hi - lo + 1
        out[name] = (packed >> lo) & ((1 << width) - 1)
    return out


def super_latch_layout(root_def: dict) -> Dict[str, Tuple[int, int]]:
    """The top-level `SUPER_LATCH` layout (`core_select`/`core_config`/
    `addon_config`/`reserved`), also derived from the root definition
    rather than `icm_v3.py`'s own hand-typed constants."""
    out = {}
    for entry in root_def["_super_latch"]["fields"]:
        name = entry["name"].split("[")[0]
        out[name] = (entry["lo"], entry["hi"])
    return out


def pack_super_latch_core_portion(root_def: dict, core_select: int,
                                   core_config_values: Dict[str, int]) -> int:
    """Packs `core_select` + `core_config` into their real
    `SUPER_LATCH` positions, generically. Does NOT include
    `addon_config` -- see the module docstring's own stated gap. Callers
    needing a complete 80-bit `SUPER_LATCH` should OR this with a
    separately-packed `addon_config` shifted into its own real position
    (also available from `super_latch_layout()`)."""
    layout = super_latch_layout(root_def)
    sel_lo, sel_hi = layout["core_select"]
    cfg_lo, cfg_hi = layout["core_config"]
    core_config_word = pack_core_config(root_def, core_select, core_config_values)
    latch = pack_field(core_select, sel_lo, sel_hi)
    latch |= pack_field(core_config_word, cfg_lo, cfg_hi)
    return latch
