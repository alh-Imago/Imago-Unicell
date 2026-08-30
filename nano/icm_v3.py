"""
icm_v3.py — ICM v3: the SUPER_LATCH[79:0] encode/decode core, plus the
record/file format built on top of it.

GROUND TRUTH, checked field-by-field against real RTL before anything
below was written (not reconstructed from memory or from
`docs/shared/design-notes/modular_cell_builds_and_capability_aware_icm.md`'s
own earlier speculation, which predates `unicell_super_v1.v` existing at
all):
  fpga/verilog/unicell_super_v1.v        — SUPER_LATCH[79:0] layout itself
  fpga/verilog/unicell_stripped_v1.v     — nano core's own cfg_data fields
  fpga/verilog/ram_cell_v1.v             — RAM core's own cfg_data fields
  fpga/verilog/adder_cell_v1.v           — adder core's own cfg_data fields
  fpga/verilog/accumulator_cell_v1.v     — accumulator core's own cfg_data fields
  fpga/verilog/compare_cell_v1.v         — comparator core's own cfg_data fields
  fpga/verilog/latch_cell_v1.v           — latch core's own cfg_data fields

WHY THIS IS A NEW FORMAT, NOT AN EXTENSION OF `docs/shared/ICM_FORMAT.md`
(v2): v2's `gs`/`in`/`out` record shape is a FULL-cell artifact. `in`/`out`
are addressed-BUS addresses -- meaningful because the FULL cell (and, via
the same convention, everything v2 ever targeted) matches on an address
broadcast over a shared bus. Neither nano nor any of `unicell_super_v1.v`'s
other 5 cores work that way: every one of them wires N/S/E/W to PHYSICAL
cardinal neighbors via its own `downstream_mask`/`upstream_mask` (or, for
nano specifically, `routing_mask`/`cardinal_edge` -- same one-hot N/S/E/W
convention, different name for historical reasons). This matches
`nano/unicell_automaton_v1.py`'s own `CAGrid`: "fixed physical neighbors
only, no addressing/bus." So a v3 record has no bus-address field at all
-- connectivity intent lives INSIDE the selected core's own core_config,
exactly as the real RTL already encodes it. What a v3 record needs instead
is a GRID POSITION (which physical cell this record configures) plus the
core_select/core_config/addon_config triple that becomes that cell's real
SUPER_LATCH.

SCOPE OF THIS FILE: the format itself -- encode a record to a real 80-bit
SUPER_LATCH integer, decode one back, save/load a whole program as JSON,
verify round-trip. Deliberately NOT in scope here (see
`current/START.md`'s own NEXT list, items 2 and 3): VM dispatch logic that
actually RUNS a grid of super cells from a loaded ICM v3 file, and a
higher-level compiler that lowers something friendlier than raw
core_config bits down to this. This file is what both of those will sit
on top of.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional


# ── SUPER_LATCH[79:0] top-level layout (unicell_super_v1.v header + RTL,
# lines 17-43 / 101-104) ─────────────────────────────────────────────────
CORE_SELECT_LO, CORE_SELECT_HI = 0, 4          # [4:0]   5 bits
CORE_CONFIG_LO, CORE_CONFIG_HI = 5, 46         # [46:5]  42 bits
ADDON_CONFIG_LO, ADDON_CONFIG_HI = 47, 66      # [66:47] 20 bits
RESERVED_LO, RESERVED_HI = 67, 79              # [79:67] 13 bits

SUPER_LATCH_WIDTH = 80
CORE_CONFIG_WIDTH = CORE_CONFIG_HI - CORE_CONFIG_LO + 1     # 42
ADDON_CONFIG_WIDTH = ADDON_CONFIG_HI - ADDON_CONFIG_LO + 1  # 20

_MASK32 = 0xFFFFFFFF


def _field_mask(lo: int, hi: int) -> int:
    return (1 << (hi - lo + 1)) - 1


def _get_field(value: int, lo: int, hi: int) -> int:
    return (value >> lo) & _field_mask(lo, hi)


def _set_field(value: int, lo: int, hi: int, field_value: int) -> int:
    mask = _field_mask(lo, hi)
    if field_value & ~mask:
        raise ValueError(
            f"value {field_value:#x} does not fit in field [{hi}:{lo}] "
            f"({hi - lo + 1} bits, max {mask:#x})"
        )
    cleared = value & ~(mask << lo)
    return cleared | ((field_value & mask) << lo)


# ── Core selector, unicell_super_v1.v localparams (line 118) ────────────
SEL_NANO, SEL_RAM, SEL_ADDER, SEL_ACC, SEL_CMP, SEL_LATCH = range(6)

# SEL_SEQ=6 is real RTL (unicell_super_v2.v, sequencer_cell_v1.v) but
# has no VM dispatch yet -- deliberately not added here, out of scope
# for this pass, the one remaining half of the asymmetry #519 first
# named. SEL_BRANCH=7 was originally the OPPOSITE gap (real VM, no RTL
# slot) -- now CLOSED (#542): unicell_super_v3.v gives branch_cell_v1
# .v (#500/#504/#497) its own real, physically-instantiated RTL
# core_select slot, sim-verified (`tb_unicell_super_v3.v`, 12/12).
# The VM dispatch below was already correct (it modeled the core's own
# real logic from the start); only this comment's own framing was
# stale.
SEL_BRANCH = 7

CORE_NAMES = {
    SEL_NANO: "nano",
    SEL_RAM: "ram",
    SEL_ADDER: "adder",
    SEL_ACC: "accumulator",
    SEL_CMP: "comparator",
    SEL_LATCH: "latch",
    SEL_BRANCH: "branch",
}
CORE_IDS = {name: sel for sel, name in CORE_NAMES.items()}


# ── One-hot N/S/E/W convention, confirmed identical across every core
# that uses it: bit0=N, bit1=S, bit2=E, bit3=W (ram_cell_v1.v's own
# comment, line 145-146: "bit order matches downstream_mask/upstream_mask
# throughout this module... same convention unicell_stripped_v1.v uses for
# routing_mask/cardinal_edge/targeted_vec"). ──────────────────────────────
_DIR_BITS = {"n": 0, "s": 1, "e": 2, "w": 3}


def pack_dirmask(dirs) -> int:
    """['n','e'] -> 0b0101. Accepts any iterable of 'n'/'s'/'e'/'w'."""
    m = 0
    for d in dirs:
        d = d.lower()
        if d not in _DIR_BITS:
            raise ValueError(f"unknown direction {d!r}, expected n/s/e/w")
        m |= 1 << _DIR_BITS[d]
    return m


def unpack_dirmask(mask: int) -> list:
    return [d for d, bit in _DIR_BITS.items() if (mask >> bit) & 1]


# ── Per-core config field tables. Each entry: name -> (lo, hi), bit
# positions WITHIN that core's own core_config share (i.e. matching each
# .v file's own "cfg_data[N:0] field map" comment exactly -- NOT yet
# offset into the shared 42-bit core_config or the full 80-bit latch;
# that offset is applied generically below). ─────────────────────────────

# nano: unicell_super_v1.v lines 150-156 -- reconstructs nano's own
# 128-bit cfg_data from these SAME core_config bit positions (confirmed:
# topology<-config[9:0], ready<-config[10], routing_mask<-config[16:11],
# cardinal_edge<-config[22:17]).
#
# hold_in/fb_internal_in/a_reemit_in/a_update_in/a_self_update_in
# (#522): a REAL, HONEST GAP in the mechanical extractor, not a typo --
# these are PORTS on unicell_stripped_v1.v, not part of nano's own
# cfg_data structure, so they're wired as individual `wire nano_hold_in
# = incoming_config[23] && sel_active_nano;`-style lines in unicell_
# super_v1.v/v2.v/v3.v, NOT inside nano's own "cfg_data[...] field map"
# comment block the extractor parses. `root_definition_extractor_v1.py`
# genuinely cannot see these -- confirmed directly, not assumed
# (`nano/root_definition.json`'s own `nano_within_super` entry has only
# the 4 fields above). Bit positions below match unicell_super_v1.v's
# own real wiring exactly, hand-verified against the RTL since the
# mechanical check can't cover this case.
_NANO_FIELDS = {
    "topology": (0, 9),
    "ready": (10, 10),
    "routing_mask": (11, 16),
    "cardinal_edge": (17, 22),
    "hold_in": (23, 23),
    "fb_internal_in": (24, 24),
    "a_reemit_in": (25, 25),
    "a_update_in": (26, 26),
    "a_self_update_in": (27, 27),
}

# RAM: ram_cell_v1.v lines 40-47, full 42-bit core_config used exactly.
_RAM_FIELDS = {
    "downstream_mask": (0, 3),
    "upstream_mask": (4, 7),
    "fixed_mode": (8, 8),
    "load_data_valid": (9, 9),
    "init_data": (10, 41),
}

# Adder: adder_cell_v1.v lines 23-26.
_ADDER_FIELDS = {
    "downstream_mask": (0, 3),
    "upstream_mask": (4, 7),
    "subtract_mode": (8, 8),
}

# Accumulator: accumulator_cell_v1.v lines 87-98 (extended #515/#519 --
# step_amount/pulse_mode/threshold added above the original inc_dir/
# dec_dir/downstream_mask, matching the real RTL bit positions exactly).
_ACC_FIELDS = {
    "inc_dir": (0, 3),
    "dec_dir": (4, 7),
    "downstream_mask": (8, 11),
    "step_amount": (12, 19),
    "pulse_mode": (20, 20),
    "threshold": (21, 36),
}

# Comparator: compare_cell_v1.v lines 34-38.
_CMP_FIELDS = {
    "downstream_mask": (0, 3),
    "upstream_mask": (4, 7),
    "threshold": (8, 39),
}

# Latch: latch_cell_v1.v lines 31-35.
_LATCH_FIELDS = {
    "set_dir": (0, 3),
    "clear_dir": (4, 7),
    "downstream_mask": (8, 11),
    "toggle_dir": (12, 15),
}

# Branch: branch_cell_v1.v lines 53-93 (#500/#504/#497's own real,
# final field table). REAL RTL SLOT since #542: unicell_super_v3.v
# gives this core its own real, physically-instantiated SEL_BRANCH=7
# core_select option, sim-verified (`tb_unicell_super_v3.v`, 12/12
# checks, including a substantive held-reference/per-outcome/
# suppression test through core_select routing). Originally added
# here (#519) as a genuine VM-provisional value ahead of that physical
# wiring existing -- matching the exact reasoning `points.md #358`'s
# own registry was built for -- now simply the real, correct table for
# a real core. Bit positions match the RTL's own real field map
# exactly (42 of 64 bits used within this core's own native cfg_data
# bus, zero bits spare within the 42-bit core_config budget once
# placed in the super shell, confirmed directly before #542 was built).
_BRANCH_FIELDS = {
    "upstream_dir": (0, 1),
    "value_source_low": (2, 2),
    "value_source_equal": (3, 3),
    "value_source_high": (4, 4),
    "fixed_value_low": (5, 11),
    "fixed_value_equal": (12, 18),
    "fixed_value_high": (19, 25),
    "emit_low": (26, 26),
    "emit_equal": (27, 27),
    "emit_high": (28, 28),
    "route_low": (29, 32),
    "route_equal": (33, 36),
    "route_high": (37, 40),
    "rolling_mode": (41, 41),
}

CORE_FIELD_TABLES = {
    SEL_NANO: _NANO_FIELDS,
    SEL_RAM: _RAM_FIELDS,
    SEL_ADDER: _ADDER_FIELDS,
    SEL_ACC: _ACC_FIELDS,
    SEL_CMP: _CMP_FIELDS,
    SEL_LATCH: _LATCH_FIELDS,
    SEL_BRANCH: _BRANCH_FIELDS,
}

# Direction-valued fields per core -- these accept either a raw int or a
# list of 'n'/'s'/'e'/'w' when building a record from friendlier Python,
# and are always returned as a list of direction letters on decode.
_DIR_FIELDS = {
    SEL_NANO: (),  # routing_mask/cardinal_edge are 6-bit (3D-ready), not
                    # plain 4-bit one-hot -- left as raw ints, not dir lists
    SEL_RAM: ("downstream_mask", "upstream_mask"),
    SEL_ADDER: ("downstream_mask", "upstream_mask"),
    SEL_ACC: ("inc_dir", "dec_dir", "downstream_mask"),
    SEL_CMP: ("downstream_mask", "upstream_mask"),
    SEL_LATCH: ("set_dir", "clear_dir", "downstream_mask"),
    # route_low/equal/high are real, one-hot(s) N/S/E/W masks (#497's own
    # multi-direction fan-out) -- the same convention as every other
    # core's downstream_mask. upstream_dir is deliberately NOT here: a
    # single fixed 0=N/1=S/2=E/3=W direction CODE (#494's own real
    # constraint), not a one-hot mask -- left as a raw int.
    SEL_BRANCH: ("route_low", "route_equal", "route_high"),
}

# ── ADDON fields, addon_config[19:0] -- unicell_super_v1.v lines 337-349,
# matching nibble_mask_addon_v1.v / shift_lane_addon_v1.v / invert_addon_v1.v
# port order exactly. ──────────────────────────────────────────────────────
_ADDON_FIELDS = {
    "nibble_mask": (0, 7),
    "mask_en": (8, 8),
    "shift_amt": (9, 13),
    "shift_en": (14, 14),
    "direction": (15, 15),
    "lane_cut": (16, 18),
    "invert_en": (19, 19),
}


def _pack_fields(field_table: dict, values: dict, dir_fields=()) -> int:
    """Generic bit-packer: {field_name: value_or_dirlist} -> int, per a
    field_table of name -> (lo, hi). Unknown keys in `values` are a hard
    error (silently dropping a typo'd field is exactly the kind of
    "looks safe while not being safe" mistake this project's own
    capability-manifest notes warn about)."""
    unknown = set(values) - set(field_table)
    if unknown:
        raise ValueError(f"unknown field(s) {sorted(unknown)}, expected one of {sorted(field_table)}")
    packed = 0
    for name, (lo, hi) in field_table.items():
        v = values.get(name, 0)
        if name in dir_fields and isinstance(v, (list, tuple, set)):
            v = pack_dirmask(v)
        packed = _set_field(packed, lo, hi, v)
    return packed


def _unpack_fields(field_table: dict, packed: int, dir_fields=()) -> dict:
    out = {}
    for name, (lo, hi) in field_table.items():
        v = _get_field(packed, lo, hi)
        out[name] = unpack_dirmask(v) if name in dir_fields else v
    return out


# ── Public: core_config (42-bit) and addon_config (20-bit) ──────────────

def pack_core_config(core: "int|str", values: dict) -> int:
    sel = CORE_IDS[core] if isinstance(core, str) else core
    return _pack_fields(CORE_FIELD_TABLES[sel], values, _DIR_FIELDS[sel])


def unpack_core_config(core: "int|str", packed: int) -> dict:
    sel = CORE_IDS[core] if isinstance(core, str) else core
    return _unpack_fields(CORE_FIELD_TABLES[sel], packed, _DIR_FIELDS[sel])


def pack_addon_config(values: dict) -> int:
    return _pack_fields(_ADDON_FIELDS, values)


def unpack_addon_config(packed: int) -> dict:
    return _unpack_fields(_ADDON_FIELDS, packed)


# ── Public: the full 80-bit SUPER_LATCH ──────────────────────────────────

def encode_super_latch(core: "int|str", core_config: dict, addon_config: Optional[dict] = None) -> int:
    sel = CORE_IDS[core] if isinstance(core, str) else core
    if sel not in CORE_NAMES:
        raise ValueError(f"core_select {sel} has no field table (values 6-31 are reserved, per #317)")
    latch = 0
    latch = _set_field(latch, CORE_SELECT_LO, CORE_SELECT_HI, sel)
    latch = _set_field(latch, CORE_CONFIG_LO, CORE_CONFIG_HI, pack_core_config(sel, core_config))
    latch = _set_field(latch, ADDON_CONFIG_LO, ADDON_CONFIG_HI, pack_addon_config(addon_config or {}))
    return latch


def decode_super_latch(latch: int) -> dict:
    sel = _get_field(latch, CORE_SELECT_LO, CORE_SELECT_HI)
    core_config_raw = _get_field(latch, CORE_CONFIG_LO, CORE_CONFIG_HI)
    addon_config_raw = _get_field(latch, ADDON_CONFIG_LO, ADDON_CONFIG_HI)
    out = {
        "core_select": sel,
        "core": CORE_NAMES.get(sel, f"reserved_{sel}"),
        "addon_config": unpack_addon_config(addon_config_raw),
    }
    if sel in CORE_FIELD_TABLES:
        out["core_config"] = unpack_core_config(sel, core_config_raw)
    else:
        out["core_config"] = {"_raw": core_config_raw}  # unassigned select, #317 headroom
    return out


# ── ICM v3 record / file format ──────────────────────────────────────────

@dataclass
class IcmV3Record:
    """One super_v1 cell's real configuration, plus its GRID POSITION --
    the direct replacement for v2's bus-address `in`/`out` (see module
    docstring). `row`/`col` are the only placement info needed since
    connectivity itself lives inside core_config's own downstream_mask/
    upstream_mask (or nano's routing_mask/cardinal_edge)."""
    cell_id: str
    row: int
    col: int
    core: str
    core_config: dict = field(default_factory=dict)
    addon_config: dict = field(default_factory=dict)

    def super_latch(self) -> int:
        return encode_super_latch(self.core, self.core_config, self.addon_config)

    def to_dict(self) -> dict:
        latch = self.super_latch()
        return {
            "cell_id": self.cell_id,
            "row": self.row,
            "col": self.col,
            "core": self.core,
            "core_config": self.core_config,
            "addon_config": self.addon_config,
            "super_latch_hex": f"0x{latch:020x}",
        }

    @staticmethod
    def from_dict(d: dict) -> "IcmV3Record":
        return IcmV3Record(
            cell_id=d["cell_id"], row=d["row"], col=d["col"], core=d["core"],
            core_config=d.get("core_config", {}), addon_config=d.get("addon_config", {}),
        )


def _canonical_records_json(records) -> str:
    """Canonicalization for record_hash -- same discipline as v2's own
    record_hash (docs/shared/ICM_FORMAT.md's version-history note): a
    fixed field order, no whitespace, so the hash is reproducible across
    languages/implementations, not just this one file's own dict order."""
    canon = [
        {"cell_id": r.cell_id, "row": r.row, "col": r.col, "core": r.core,
         "core_config": r.core_config, "addon_config": r.addon_config}
        for r in records
    ]
    return json.dumps(canon, sort_keys=True, separators=(",", ":"))


# Real, honest fact worth being explicit about: not every core is
# available in every real shell version. v1 has the original 6, v2
# adds the sequencer (#421/#422), v3 adds branch cell (#542). A saved
# ICM file using a core that doesn't exist in v1 would be silently
# wrong if it claimed "unicell_super_v1" as its target regardless --
# checked directly against each shell's own real core_select support
# before writing this, not assumed.
_CORES_REQUIRING_V2 = {"sequencer"}
_CORES_REQUIRING_V3 = {"branch"}


def minimum_shell_version(records) -> str:
    """The real minimum unicell_super_*.v shell version that can run
    every core used across `records` -- v1 unless something here
    needs more."""
    cores = {r.core for r in records}
    if cores & _CORES_REQUIRING_V3:
        return "unicell_super_v3"
    if cores & _CORES_REQUIRING_V2:
        return "unicell_super_v2"
    return "unicell_super_v1"


@dataclass
class IcmV3File:
    name: str
    records: list  # list[IcmV3Record]
    format_version: str = "icm-v3"
    description: str = ""

    def record_hash(self) -> str:
        return hashlib.sha256(_canonical_records_json(self.records).encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "format_version": self.format_version,
            # Real, computed minimum shell version this file actually
            # needs -- NOT hardcoded, since which cores are used
            # determines which real unicell_super_*.v can run it.
            "cell_type": minimum_shell_version(self.records),
            "name": self.name,
            "description": self.description,
            "records": [r.to_dict() for r in self.records],
            "record_hash": self.record_hash(),
        }

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load(path: str) -> "IcmV3File":
        with open(path) as f:
            d = json.load(f)
        if d.get("format_version") != "icm-v3":
            raise ValueError(f"not an icm-v3 file: format_version={d.get('format_version')!r}")
        records = [IcmV3Record.from_dict(r) for r in d["records"]]
        icm = IcmV3File(name=d["name"], records=records, description=d.get("description", ""))
        stored_hash = d.get("record_hash")
        if stored_hash is not None and stored_hash != icm.record_hash():
            raise ValueError(
                f"record_hash mismatch on load: file says {stored_hash}, "
                f"recomputed {icm.record_hash()} -- file may be corrupted or hand-edited"
            )
        return icm
