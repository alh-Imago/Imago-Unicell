"""
validate_icm_v3_against_rtl_v1.py — the real payoff of `points.md #216`
item 1: cross-checks `icm_v3.py`'s own hand-typed `CORE_FIELD_TABLES`
(built this session by a human reading RTL comments and transcribing
them into Python dicts) against `root_definition_extractor_v1.py`'s
mechanical extraction of the SAME comments -- a genuine independent
check, not two copies of the same information. Run as a script; exits
non-zero and prints every real mismatch found if `icm_v3.py`'s tables
have ever silently drifted from the RTL they're supposed to mirror.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import icm_v3 as v3
from root_definition_extractor_v1 import extract_all


def _normalize_name(name: str) -> str:
    """RTL comments sometimes suffix a field name with its own width,
    e.g. `init_data[31:0]` -- strip that back to the bare field name
    `icm_v3.py`'s own dict keys use."""
    return name.split("[")[0]


def validate(repo_root: str) -> int:
    extracted = extract_all(repo_root)
    mismatches = 0

    # ── The 5 non-nano cores: core_config[N:0] maps onto each one's own
    # real cfg_data[N:0] with zero reshuffling, per unicell_super_v1.v's
    # own comment -- a DIRECT comparison is the right one here. ──────
    core_map = {
        "ram": v3.SEL_RAM, "adder": v3.SEL_ADDER, "accumulator": v3.SEL_ACC,
        "comparator": v3.SEL_CMP, "latch": v3.SEL_LATCH,
    }
    for name, sel in core_map.items():
        rtl_fields = {_normalize_name(f.name): (f.lo, f.hi) for f in extracted[name].fields
                      if _normalize_name(f.name) != "reserved"}
        py_fields = v3.CORE_FIELD_TABLES[sel]
        mismatches += _diff(f"core={name}", rtl_fields, py_fields)

    # ── nano: compare against the "nano_within_super" extraction
    # specifically -- the standalone cmd_latch layout is a DIFFERENT,
    # not-comparable field map (see the extractor's own docstring). ──
    rtl_nano = {_normalize_name(f.name): (f.lo, f.hi) for f in extracted["nano_within_super"].fields}
    py_nano = v3.CORE_FIELD_TABLES[v3.SEL_NANO]
    mismatches += _diff("core=nano (within SUPER_LATCH)", rtl_nano, py_nano)

    # ── SUPER_LATCH's own top-level layout. ──────────────────────────
    rtl_super = {_normalize_name(f.name): (f.lo, f.hi) for f in extracted["_super_latch"].fields
                 if _normalize_name(f.name) != "reserved"}
    py_super = {
        "core_select": (v3.CORE_SELECT_LO, v3.CORE_SELECT_HI),
        "core_config": (v3.CORE_CONFIG_LO, v3.CORE_CONFIG_HI),
        "addon_config": (v3.ADDON_CONFIG_LO, v3.ADDON_CONFIG_HI),
    }
    mismatches += _diff("SUPER_LATCH top-level layout", rtl_super, py_super)

    if mismatches == 0:
        print("PASS: icm_v3.py's field tables match the RTL's own field-map comments exactly, "
              f"across all 5 non-nano cores, nano's within-super subset, and the top-level "
              f"SUPER_LATCH layout ({sum(len(v) for v in [rtl_super]) + len(core_map) + 1} "
              f"real comparisons made).")
    else:
        print(f"FAIL: {mismatches} real mismatch(es) found -- see above.")
    return mismatches


def _diff(label: str, rtl: dict, py: dict) -> int:
    mismatches = 0
    for name, (lo, hi) in rtl.items():
        if name not in py:
            print(f"MISMATCH [{label}]: RTL has field {name!r} at [{hi}:{lo}], "
                  f"but icm_v3.py has no such field at all")
            mismatches += 1
        elif py[name] != (lo, hi):
            print(f"MISMATCH [{label}]: field {name!r} -- RTL says [{hi}:{lo}] "
                  f"(lo={lo},hi={hi}), icm_v3.py says lo={py[name][0]},hi={py[name][1]}")
            mismatches += 1
    for name in py:
        if name not in rtl:
            print(f"MISMATCH [{label}]: icm_v3.py has field {name!r}, "
                  f"but the RTL's own field-map comment has no such field")
            mismatches += 1
    return mismatches


if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    raise SystemExit(1 if validate(repo_root) else 0)
