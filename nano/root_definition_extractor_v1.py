"""
root_definition_extractor_v1.py — mechanically extracts field-map bit
positions DIRECTLY from the RTL's own comments, rather than trusting a
human's hand-transcription of them. Item 1 of `points.md #216`'s VM-core
architecture: "the VM reads, or has generated, a file that reflects the
actual base cell's Verilog exactly... the field map is already
mechanically derivable straight from the RTL's own comments."

CONFIRMED TRACTABLE BEFORE BUILDING, not assumed: every one of the 6
real cores (`ram_cell_v1.v`, `adder_cell_v1.v`, `accumulator_cell_v1.v`,
`compare_cell_v1.v`, `latch_cell_v1.v`, `unicell_stripped_v1.v`) and
`unicell_super_v1.v`'s own `SUPER_LATCH[79:0]` layout share one
consistent comment convention:
```
// cfg_data[N:0] field map:
//   [hi:lo]  field_name   -- description...
//   [bit]    other_field  -- description...
```
grepped directly across all of them before writing a single line of
parser code.

THE REAL VALUE, beyond "a file exists": this is a genuine VALIDATION
tool against `icm_v3.py`'s own `CORE_FIELD_TABLES`, which were built by
a human (this session) reading the same RTL comments and hand-typing
Python dicts from them -- exactly the kind of transcription that could
silently drift from the real source. Running this extractor and
diffing its output against `icm_v3.py`'s own tables is a real
independent check, not just a second copy of the same information.

HONEST SCOPE, not glossed over: `addon_config`'s own field positions
(`nibble_mask`/`shift_amt`/etc.) are NOT wired through this same
"field map" comment convention at all -- they're set via direct module
port connections at `unicell_super_v1.v`'s own `ADDON_NM`/`ADDON_SL`/
`ADDON_INV` instantiations (checked directly, confirmed absent: grepped
the three addon `.v` files themselves for any `addon_config[` field-map
comment and found none). This extractor does NOT cover addon_config --
a real, stated gap, not silently assumed solved.

A SECOND real, honest gap of the SAME general shape, found later
(#522/#543): nano's own `hold_in`/`fb_internal_in`/`a_reemit_in`/
`a_update_in`/`a_self_update_in` are ALSO ports, not cfg_data fields --
wired individually via `core_config` bits in `unicell_super_v1.v`/
`v2.v`/`v3.v`, physically separated from nano's own real field-map
comment block by ~150 lines of other core instantiations. This
extractor cannot see them either. **`nano/root_definition.json`'s own
`nano_within_super` entry has these 5 fields added MANUALLY** (see its
own `_manual_overrides_warning` key) -- running this script WITHOUT
`--check` will silently wipe them. Re-add manually (matching `icm_v3.
py`'s own `_NANO_FIELDS` table) after any future regeneration, until
this extractor is taught to handle scattered, ports-not-cfg_data field
definitions properly -- real, deliberately deferred, not solved here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Dict, List, Optional

# Matches a field-map header line, e.g. "cfg_data[63:0] field map:" or
# "SUPER_LATCH[79:0] layout —":
_HEADER_RE = re.compile(r"field map|\blayout\b", re.IGNORECASE)

# Matches one field entry line inside a field-map comment block, e.g.:
#   "//   [3:0]   downstream_mask  — one-hot(s), N/S/E/W, ..."
#   "//   [13]    ready            — NEW. This cell's own readiness..."
_FIELD_RE = re.compile(
    r"^\s*//\s*\[(?P<hi>\d+)(?::(?P<lo>\d+))?\]\s+(?P<name>\S+)\s*"
    r"(?:—|--)?\s*(?P<desc>.*)$"
)


@dataclass
class FieldDef:
    name: str
    hi: int
    lo: int
    description: str

    @property
    def width(self) -> int:
        return self.hi - self.lo + 1


@dataclass
class RootDefinition:
    """One extracted field map -- which real file it came from, kept
    alongside the fields themselves so a validation diff can always
    point back at real RTL, not just an opaque dict."""
    source_file: str
    fields: List[FieldDef] = dc_field(default_factory=list)

    def as_dict(self) -> Dict[str, tuple]:
        return {f.name: (f.lo, f.hi) for f in self.fields}


def extract_field_map(filepath: str, occurrence: int = 0) -> Optional[RootDefinition]:
    """Finds the `occurrence`-th "field map"/"layout" comment block in
    `filepath` and parses every `[hi:lo] name` line inside it.

    A block continues for as long as consecutive lines stay inside a
    `//` comment -- any comment line that ISN'T a `[hi:lo] name` entry
    (a wrapped header, a wrapped description, a closing remark) is
    treated as a CONTINUATION, not a block-ender, and its text is
    appended to whichever field most recently matched. This was found
    to matter for real, not a hypothetical: several headers in the
    actual RTL wrap onto a second comment line before the first real
    `[hi:lo]` entry even appears (`ram_cell_v1.v`/`adder_cell_v1.v`/
    `unicell_super_v1.v` all do this) -- an earlier version of this
    function that stopped at the first non-matching comment line lost
    EVERY field in exactly those three files, confirmed by actually
    running it before this fix, not assumed. The block ends only at the
    first genuinely non-comment line (blank or code) -- deliberately
    permissive about what counts as "still part of this block," since
    missing a real field silently is a much worse failure mode than an
    overly long description string."""
    with open(filepath) as f:
        lines = f.readlines()

    seen = 0
    i = 0
    while i < len(lines):
        if _HEADER_RE.search(lines[i]) and "//" in lines[i]:
            if seen == occurrence:
                fields: List[FieldDef] = []
                j = i
                while j < len(lines) and lines[j].strip().startswith("//"):
                    m = _FIELD_RE.match(lines[j])
                    if m:
                        hi = int(m.group("hi"))
                        lo = int(m.group("lo")) if m.group("lo") is not None else hi
                        fields.append(FieldDef(
                            name=m.group("name"), hi=hi, lo=lo,
                            description=m.group("desc").strip(),
                        ))
                    elif fields:
                        extra = lines[j].strip().lstrip("/").strip()
                        if extra:
                            fields[-1].description = (fields[-1].description + " " + extra).strip()
                    j += 1
                return RootDefinition(source_file=filepath, fields=fields)
            seen += 1
        i += 1
    return None


# ── The real, canonical extraction for every field map this project's
# RTL actually has, in one place -- run this to regenerate
# `root_definition.json` whenever the RTL's own comments change. ──────

CORE_RTL_FILES = {
    "nano": "fpga/verilog/unicell_stripped_v1.v",
    "ram": "fpga/verilog/ram_cell_v1.v",
    "adder": "fpga/verilog/adder_cell_v1.v",
    "accumulator": "fpga/verilog/accumulator_cell_v1.v",
    "comparator": "fpga/verilog/compare_cell_v1.v",
    "latch": "fpga/verilog/latch_cell_v1.v",
    "sequencer": "fpga/verilog/sequencer_cell_v1.v",
    "branch": "fpga/verilog/branch_cell_v1.v",
}

SUPER_LATCH_RTL_FILE = "fpga/verilog/unicell_super_v1.v"

# Matches the `assign nano_cfg_data[...] = incoming_config[...]; // name`
# pattern `unicell_super_v1.v` uses to reconstruct nano's OWN reduced
# subset from `core_config` -- a genuinely DIFFERENT field map from
# `unicell_stripped_v1.v`'s own standalone `cmd_latch[31:0]` layout
# (checked directly, not assumed the same): the standalone nano cell has
# `ready` at bit 13 of a 128-bit register; embedded in Unicell-S, the
# SAME concept lives at a completely different bit position inside a
# 42-bit `core_config` share. Comparing the wrong one against
# `icm_v3.py`'s own `SEL_NANO` table would produce false "mismatches"
# that aren't real bugs at all -- two legitimately different field maps
# for two different contexts.
_NANO_SUBSET_ASSIGN_RE = re.compile(
    r"assign\s+nano_cfg_data\[\d+(?::\d+)?\]\s*=\s*incoming_config\[(?P<hi>\d+)(?::(?P<lo>\d+))?\]\s*;"
    r"\s*//\s*(?P<name>\S+)"
)


def extract_nano_subset_within_super(filepath: str) -> RootDefinition:
    """The nano-specific field map AS EMBEDDED inside `SUPER_LATCH`'s
    own `core_config` share -- the correct comparison target for
    `icm_v3.py`'s `SEL_NANO` table, NOT `unicell_stripped_v1.v`'s own
    standalone `cmd_latch` layout."""
    with open(filepath) as f:
        text = f.read()
    fields = []
    for m in _NANO_SUBSET_ASSIGN_RE.finditer(text):
        hi = int(m.group("hi"))
        lo = int(m.group("lo")) if m.group("lo") is not None else hi
        fields.append(FieldDef(name=m.group("name"), hi=hi, lo=lo, description=""))
    return RootDefinition(source_file=filepath, fields=fields)


def extract_all(repo_root: str) -> Dict[str, RootDefinition]:
    """Extracts every core's own field map, plus `SUPER_LATCH`'s own
    top-level layout, keyed the same way `icm_v3.py`'s own
    `CORE_FIELD_TABLES` are keyed -- so the two can be diffed directly."""
    import os
    out: Dict[str, RootDefinition] = {}
    for core, relpath in CORE_RTL_FILES.items():
        rd = extract_field_map(os.path.join(repo_root, relpath))
        if rd is None:
            raise ValueError(f"no field-map comment found in {relpath} for core {core!r} -- "
                              f"either the RTL's own comment convention changed, or this "
                              f"extractor's pattern needs updating, not silently skipped")
        out[core] = rd
    super_latch = extract_field_map(os.path.join(repo_root, SUPER_LATCH_RTL_FILE))
    if super_latch is None:
        raise ValueError(f"no SUPER_LATCH field-map comment found in {SUPER_LATCH_RTL_FILE}")
    out["_super_latch"] = super_latch
    out["nano_within_super"] = extract_nano_subset_within_super(
        os.path.join(repo_root, SUPER_LATCH_RTL_FILE))
    return out
