"""
icm_v4.py — ICM v4: a real, mixed-grid extension of ICM v3 that adds
DSP wrapper cell records (`dsp_arith_wrapper_v1.v`/`dsp_compare_
wrapper_v1.v`, hardware-confirmed `#472`) alongside ICM v3's existing
SUPER_LATCH super-cell records, in one real file.

WHY A NEW FORMAT NUMBER, NOT A SILENT EXTENSION OF ICM V3: DSP wrapper
cells are a real, deliberate, SEPARATE hardware class from
`unicell_super_v1.v` (`dsp_wrapper_automaton_v1.py`'s own docstring,
`#453`/`#474`) -- dedicated, placement-anchored infrastructure, not a
`core_select` option any super carrier cell could become. A file that
can name BOTH kinds of cell is a real, new capability an ICM v3
consumer cannot correctly interpret (it would silently ignore or choke
on a record it has no `SEL_*` for) -- exactly the kind of "looks safe
while not being safe" silent-drop this project's own capability-
manifest discipline (`icm_v3.py`'s own `_pack_fields()` docstring)
already refuses to allow elsewhere. A new `format_version` makes that
real incompatibility explicit and checkable, rather than hoping every
future reader notices an optional field.

REAL, DELIBERATE SCOPE, stated directly (Alan's own framing): this is
ICM-LEVEL construction -- a real model built and saved DIRECTLY via
Python calls against this format, same discipline as `#480`-`#483`'s
own direct-Python DspWrapperCell/mixed-grid work. The DSL/compiler
does NOT yet know DSP wrappers exist at all (`docs/stripped-cell/
design-notes/dsp_wrapper_timing.md`'s own real, still-open item 1:
"teach the tile library/resolver DSP wrappers exist"), so no DSL
program can target this format yet -- that upgrade is real, separate,
not-yet-started work. This file's own `build_grid()` is the honest
current substitute for what a real loader/binder would otherwise do:
it turns a saved ICM v4 file directly into a live, running
`SuperGrid` + `DspWrapperCell` mix, without any DSL/compiler stage in
between.

GROUND TRUTH for the DSP wrapper record fields: `dsp_wrapper_
automaton_v1.py`'s own real `DspWrapperCell` constructor -- `op`
(one of `ALL_OPS`), `a_dir`/`b_dir` (real, distinct cardinal
directions), `downstream_mask`, and an optional `watchdog_threshold`.
These are STATIC CONFIGURATION, the same category as a super cell's
own `core_config` -- not runtime state (that's `mixed_grid_
checkpoint_v1.py`'s own, separate job, per this project's own
established "config file vs. runtime checkpoint" split, e.g.
`icm_v3.IcmV3File` vs. `dsp_wrapper_automaton_v1.save_model`).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Optional

import icm_v3 as v3
from dsp_wrapper_automaton_v1 import ALL_OPS, DspWrapperCell
from unicell_super_automaton_v1 import SuperCell, SuperGrid

# ── One-hot N/S/E/W convention, reused directly from icm_v3.py so a
# DSP wrapper record's a_dir/b_dir/downstream_mask read exactly like a
# super cell record's own downstream_mask/upstream_mask -- one real
# convention, not a second one invented for this file. ──
_DIR_LETTER_TO_INT = {"n": 0, "s": 1, "e": 2, "w": 3}   # matches unicell_automaton_v1.N/S/E/W
_DIR_INT_TO_LETTER = {v: k for k, v in _DIR_LETTER_TO_INT.items()}


def _dir_to_int(d) -> int:
    if isinstance(d, str):
        dl = d.lower()
        if dl not in _DIR_LETTER_TO_INT:
            raise ValueError(f"unknown direction {d!r}, expected n/s/e/w")
        return _DIR_LETTER_TO_INT[dl]
    return int(d)


@dataclass
class DspWrapperRecord:
    """One real DSP wrapper cell's static configuration, plus its GRID
    POSITION -- same shape convention as `icm_v3.IcmV3Record`
    (position + config, no bus address, connectivity lives inside the
    config itself via `downstream_mask`)."""
    cell_id: str
    row: int
    col: int
    op: str                      # "ADD" | "SUB" | "MUL" | "GE" | "LE" | "NEQ"
    a_dir: "int|str"             # real cardinal direction, n/s/e/w or 0-3
    b_dir: "int|str"
    downstream_mask: "int|list" = 0
    watchdog_threshold: Optional[int] = None

    def __post_init__(self) -> None:
        if self.op not in ALL_OPS:
            raise ValueError(f"DspWrapperRecord: unknown op {self.op!r} -- real, confirmed ops are {sorted(ALL_OPS)}")

    def to_dict(self) -> dict:
        dm = self.downstream_mask
        dm_out = v3.pack_dirmask(dm) if isinstance(dm, (list, tuple, set)) else int(dm)
        return {
            "cell_id": self.cell_id, "row": self.row, "col": self.col,
            "op": self.op,
            "a_dir": self.a_dir if isinstance(self.a_dir, str) else _DIR_INT_TO_LETTER[self.a_dir],
            "b_dir": self.b_dir if isinstance(self.b_dir, str) else _DIR_INT_TO_LETTER[self.b_dir],
            "downstream_mask": dm_out,
            "watchdog_threshold": self.watchdog_threshold,
        }

    @staticmethod
    def from_dict(d: dict) -> "DspWrapperRecord":
        return DspWrapperRecord(
            cell_id=d["cell_id"], row=d["row"], col=d["col"], op=d["op"],
            a_dir=d["a_dir"], b_dir=d["b_dir"],
            downstream_mask=d.get("downstream_mask", 0),
            watchdog_threshold=d.get("watchdog_threshold"),
        )

    def build_cell(self) -> DspWrapperCell:
        """Real, direct construction of the live VM object this
        record describes -- no DSL/compiler stage, matching this
        whole file's own stated scope."""
        dm = self.downstream_mask
        dm_int = v3.pack_dirmask(dm) if isinstance(dm, (list, tuple, set)) else int(dm)
        cell = DspWrapperCell(
            row=self.row, col=self.col, op=self.op,
            a_dir=_dir_to_int(self.a_dir), b_dir=_dir_to_int(self.b_dir),
            downstream_mask=dm_int,
        )
        if self.watchdog_threshold is not None:
            cell.configure_watchdog(self.watchdog_threshold)
        return cell


def _canonical_dsp_records_json(records: List[DspWrapperRecord]) -> str:
    canon = [
        {"cell_id": r.cell_id, "row": r.row, "col": r.col, "op": r.op,
         "a_dir": r.a_dir if isinstance(r.a_dir, str) else _DIR_INT_TO_LETTER[r.a_dir],
         "b_dir": r.b_dir if isinstance(r.b_dir, str) else _DIR_INT_TO_LETTER[r.b_dir],
         "downstream_mask": v3.pack_dirmask(r.downstream_mask) if isinstance(r.downstream_mask, (list, tuple, set)) else int(r.downstream_mask),
         "watchdog_threshold": r.watchdog_threshold}
        for r in records
    ]
    return json.dumps(canon, sort_keys=True, separators=(",", ":"))


@dataclass
class IcmV4File:
    """A real, mixed ICM file: `super_records` (ICM v3's own
    `IcmV3Record`, unchanged, reused directly -- not reimplemented)
    plus `dsp_wrapper_records` (this file's own new kind), together in
    one program. Either list may be empty -- a pure-super or
    pure-DSP-wrapper file is still a valid `icm-v4` file, just an
    unmixed one."""
    name: str
    super_records: List["v3.IcmV3Record"] = field(default_factory=list)
    dsp_wrapper_records: List[DspWrapperRecord] = field(default_factory=list)
    format_version: str = "icm-v4"
    description: str = ""

    def record_hash(self) -> str:
        """Real, single hash over BOTH real record kinds together --
        a file where either list is silently tampered with must fail
        the same real corruption check, not just the one an old ICM
        v3 reader would have known to look at. Canonicalizes
        `super_records` itself directly (same field subset/order as
        `icm_v3.py`'s own `_canonical_records_json`) rather than
        reaching into that module's private helper."""
        super_canon = [
            {"cell_id": r.cell_id, "row": r.row, "col": r.col, "core": r.core,
             "core_config": r.core_config, "addon_config": r.addon_config}
            for r in self.super_records
        ]
        canon = {
            "super_records": super_canon,
            "dsp_wrapper_records": json.loads(_canonical_dsp_records_json(self.dsp_wrapper_records)),
        }
        canon_json = json.dumps(canon, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canon_json.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "format_version": self.format_version,
            "cell_type": ["unicell_super_v1", "dsp_arith_wrapper_v1"],
            "name": self.name,
            "description": self.description,
            "super_records": [r.to_dict() for r in self.super_records],
            "dsp_wrapper_records": [r.to_dict() for r in self.dsp_wrapper_records],
            "record_hash": self.record_hash(),
        }

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load(path: str) -> "IcmV4File":
        with open(path) as f:
            d = json.load(f)
        if d.get("format_version") != "icm-v4":
            raise ValueError(f"not an icm-v4 file: format_version={d.get('format_version')!r}")
        super_records = [v3.IcmV3Record.from_dict(r) for r in d.get("super_records", [])]
        dsp_wrapper_records = [DspWrapperRecord.from_dict(r) for r in d.get("dsp_wrapper_records", [])]
        icm = IcmV4File(
            name=d["name"], super_records=super_records, dsp_wrapper_records=dsp_wrapper_records,
            description=d.get("description", ""),
        )
        stored_hash = d.get("record_hash")
        if stored_hash is not None and stored_hash != icm.record_hash():
            raise ValueError(
                f"record_hash mismatch on load: file says {stored_hash}, "
                f"recomputed {icm.record_hash()} -- file may be corrupted or hand-edited"
            )
        return icm

    def build_grid(self) -> SuperGrid:
        """Real, direct loader -- the honest current substitute for a
        real loader/binder stage (unbuilt, per this file's own module
        docstring): turns this saved ICM v4 program directly into a
        live, running `SuperGrid` mixing real `SuperCell`s and real
        `DspWrapperCell`s at their real grid positions, matching
        `mixed_grid_checkpoint_v1.py`'s own established `(row, col)`
        keying. A real, explicit collision check -- two records
        claiming the same cell would otherwise silently let the
        second one win, an unnoticed placement bug. """
        grid = SuperGrid([])
        for rec in self.super_records:
            pos = (rec.row, rec.col)
            if pos in grid.cells:
                raise ValueError(f"icm_v4.build_grid(): position {pos} claimed by more than one record")
            grid.cells[pos] = SuperCell.from_record(rec)
        for rec in self.dsp_wrapper_records:
            pos = (rec.row, rec.col)
            if pos in grid.cells:
                raise ValueError(f"icm_v4.build_grid(): position {pos} claimed by more than one record")
            grid.cells[pos] = rec.build_cell()
        return grid
