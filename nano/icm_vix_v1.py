"""
icm_vix_v1.py — the real, formalized hierarchical ICM format for the
VIX Carrier lineage (points.md #737-#742, formalized #747).

WHY A NEW FORMAT, NOT A SILENT EXTENSION OF ICM v3/v4:
ICM v3 (`icm_v3.py`) and ICM v4 (`icm_v4.py`) are both scoped to the
OLD core lineage's own flat SUPER_LATCH record shape -- a plain list of
placed cells, one record per cell, with no notion of a reusable
STRUCTURE. Real compiled output (loop unrolling, repeated inlined
patterns) genuinely has repeating shapes this flat format can't name
(points.md #737, prompted directly by Alan's own observation about
LLVM IR codegen). Rather than stretching v3/v4's own field list to
cover something structurally different, this is a real, new,
DIFFERENTLY-NAMED format, matching the same honest-naming discipline
`icm_v4.py`'s own docstring already establishes for itself.

REAL, DIRECT DESIGN LINEAGE, not invented fresh here:
- Every real cell shape becomes a named PATTERN, even one used exactly
  once (Alan's own direct rule, #738) -- this removes the need for any
  per-instance-override mechanism on core_config itself, since a
  genuinely different shape is just a different, separate pattern.
- Patterns are placed via a real DESIGN MAP: an explicit `at` anchor
  (row, col) per placement -- direct coordinates, never solver-derived
  (#739's own real clarification).
- Cross-pattern wiring is expressed via precise `(instance, rel_row,
  rel_col, face)` addressing (#739), with `"NC"` as a real, distinct,
  documented "deliberately not connected" marker -- never invented as
  a proxy for an actual pattern reference.
- The connections list is ADVISORY documentation/cross-checking, NOT
  the authoritative wiring mechanism -- which stays exactly what it
  already is today, each flattened cell's own real `core_config` bits
  (#739's own real, load-bearing clarification, directly paralleling
  `tools/project_assemble_v1.py`'s own `discover_instantiated_modules`/
  `check_dependency_compatibility` advisory check, #590).
- A per-instance `overrides` dict on a placement supplies real,
  genuinely per-INSTANCE facts (`io_name`, `preload_value`) that can't
  live in a shared pattern definition, since (unlike core_config) they
  aren't part of a cell's own computational SHAPE (#741).
- The header's own `cores_used`/`cell_count` is always DERIVED from the
  real pattern/placement data, never a hand-maintained field that can
  go stale (matching `minimum_shell_version()`'s own real precedent,
  and the exact lesson `#734` learned the hard way from a stale,
  hand-maintained dependency list).

REAL, TESTED, NOT SPECULATIVE: this format's own real shape was proven
against three genuinely different real examples before being written
down here -- a linear relay chain (#740), a 4-lane parallel reduction
tree (#741), and a real, dynamic, sign-branching CORDIC z-convergence
pipeline with zero repeated patterns (#742). All three are preserved
as real regression fixtures, not just historical notes -- see
`tests/vm/test_icm_vix_v1.py`.

WHAT DOESN'T LIVE HERE, DELIBERATELY, matching the same honest-scoping
discipline `ICM_V3_FORMAT.md` itself uses:
- Nested patterns (a pattern containing other named patterns). None of
  the three real examples above needed more than one level -- real,
  deliberately deferred, not decided against, per `#737`'s own still-
  open question.
- Solving/inferring placement from the connection graph. The design
  map's own `at` coordinates are always direct and explicit; a loader
  that tried to derive them would be solving a real, unneeded
  constraint problem (#739's own real, direct finding).
- Any claim that the advisory connection check is authoritative. It is
  not, and never should become the actual wiring mechanism -- doing so
  would silently duplicate (and risk diverging from) each cell's own
  real, already-authoritative `core_config` bits.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import icm_v3 as v3

FACE_OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
FACE_OFFSET = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}


class IcmVixFormatError(ValueError):
    """Raised for a real, structurally invalid hierarchical ICM
    document -- a missing pattern reference, a malformed connection
    endpoint, or similar. Never raised for an advisory-check mismatch
    (a real, configured-vs-declared wiring disagreement); those are
    real, non-fatal warnings, returned, not raised -- see
    `check_connections()`."""


@dataclass
class HierCell:
    """One cell's own real, local definition, inside a pattern's own
    local (rel_row, rel_col) coordinate space."""
    cell_id: str
    rel_row: int
    rel_col: int
    core: str
    core_config: dict = field(default_factory=dict)
    addon_config: dict = field(default_factory=dict)
    io_name: Optional[str] = None
    preload_value: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "cell_id": self.cell_id, "rel_row": self.rel_row, "rel_col": self.rel_col,
            "core": self.core, "core_config": self.core_config,
        }
        if self.addon_config:
            d["addon_config"] = self.addon_config
        if self.io_name is not None:
            d["io_name"] = self.io_name
        if self.preload_value is not None:
            d["preload_value"] = self.preload_value
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "HierCell":
        return HierCell(
            cell_id=d["cell_id"], rel_row=d["rel_row"], rel_col=d["rel_col"],
            core=d["core"], core_config=dict(d.get("core_config", {})),
            addon_config=dict(d.get("addon_config", {})),
            io_name=d.get("io_name"), preload_value=d.get("preload_value"),
        )


@dataclass
class HierPattern:
    """A named, reusable (or, just as validly, one-shot -- #738) real
    shape: a real list of cells, in local coordinates."""
    cells: List[HierCell] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"cells": [c.to_dict() for c in self.cells]}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "HierPattern":
        return HierPattern(cells=[HierCell.from_dict(c) for c in d.get("cells", [])])


@dataclass
class HierPlacement:
    """One real instance of a named pattern, anchored at a real,
    direct (row, col) -- never solver-derived (#739)."""
    instance: str
    pattern: str
    at: Tuple[int, int]
    overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"instance": self.instance, "pattern": self.pattern, "at": list(self.at)}
        if self.overrides:
            d["overrides"] = self.overrides
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "HierPlacement":
        return HierPlacement(
            instance=d["instance"], pattern=d["pattern"], at=tuple(d["at"]),
            overrides=dict(d.get("overrides", {})),
        )


# A connection endpoint is (instance, rel_row, rel_col, face); the
# real, distinct "deliberately not connected" case (#739) is the
# literal string "NC", never a fabricated endpoint tuple.
ConnEndpoint = Union[Tuple[str, int, int, str], str]


@dataclass
class HierConnection:
    """One real, advisory cross-check -- documentation and a real
    consistency check against each flattened cell's own actual,
    authoritative core_config bits, NEVER the thing that makes cells
    actually connect (#739's own real, load-bearing clarification)."""
    from_: Tuple[str, int, int, str]
    to: ConnEndpoint

    def to_dict(self) -> Dict[str, Any]:
        return {"from": list(self.from_), "to": (self.to if self.to == "NC" else list(self.to))}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "HierConnection":
        to_raw = d["to"]
        to: ConnEndpoint = "NC" if to_raw == "NC" else tuple(to_raw)
        return HierConnection(from_=tuple(d["from"]), to=to)


@dataclass
class IcmVixFile:
    """The real, whole hierarchical document: named patterns, a design
    map (placements + advisory connections), and an optional name/
    description. Deliberately does NOT carry a flat `records` list --
    call `flatten()` for that, always freshly derived, never stored
    stale alongside the real, authoritative pattern/placement data."""
    patterns: Dict[str, HierPattern] = field(default_factory=dict)
    placements: List[HierPlacement] = field(default_factory=list)
    connections: List[HierConnection] = field(default_factory=list)
    name: str = ""
    description: str = ""
    format_version: str = "icm-vix-v1"

    # ---- real, derived header (never hand-maintained, #734's own lesson) ----

    def header(self) -> Dict[str, Any]:
        """A real, freshly-DERIVED summary -- cores actually used and
        total real cell count -- computed from the real pattern/
        placement data every time, exactly the same real discipline
        `minimum_shell_version()` already established for the old
        lineage (scan the real records, don't trust a stored field)."""
        cores_used = sorted({cell.core for pat in self.patterns.values() for cell in pat.cells})
        cell_count = sum(len(self.patterns[p.pattern].cells) for p in self.placements
                          if p.pattern in self.patterns)
        return {"cores_used": cores_used, "cell_count": cell_count}

    # ---- real flattening: patterns + placements -> real IcmV3Record list ----

    def flatten(self) -> Tuple[List["v3.IcmV3Record"], Dict[Tuple[str, int, int], Tuple[int, int]]]:
        """Real, direct flattening -- no solving, no placement
        inference (#739's own real clarification: `at` is always a
        direct, given anchor). Returns (records, instance_index) where
        instance_index maps (instance, rel_row, rel_col) -> real
        (row, col), the same real lookup `check_connections()` needs.
        Raises `IcmVixFormatError` for a real, structural problem (an
        unknown pattern reference) -- never for an advisory mismatch."""
        records: List[v3.IcmV3Record] = []
        instance_index: Dict[Tuple[str, int, int], Tuple[int, int]] = {}
        seen_positions: Dict[Tuple[int, int], str] = {}
        for placement in self.placements:
            pattern = self.patterns.get(placement.pattern)
            if pattern is None:
                raise IcmVixFormatError(
                    f"placement {placement.instance!r} references unknown pattern {placement.pattern!r}")
            anchor_row, anchor_col = placement.at
            for cell in pattern.cells:
                row = anchor_row + cell.rel_row
                col = anchor_col + cell.rel_col
                if (row, col) in seen_positions:
                    raise IcmVixFormatError(
                        f"real position collision at ({row},{col}): "
                        f"{placement.instance}.{cell.cell_id} and {seen_positions[(row, col)]}")
                seen_positions[(row, col)] = f"{placement.instance}.{cell.cell_id}"
                global_id = f"{placement.instance}.{cell.cell_id}"
                instance_index[(placement.instance, cell.rel_row, cell.rel_col)] = (row, col)
                cell_overrides = placement.overrides.get(cell.cell_id, {})
                io_name = cell_overrides.get("io_name", cell.io_name)
                preload_value = cell_overrides.get("preload_value", cell.preload_value)
                records.append(v3.IcmV3Record(
                    cell_id=global_id, row=row, col=col, core=cell.core,
                    core_config=dict(cell.core_config), addon_config=dict(cell.addon_config),
                    io_name=io_name, preload_value=preload_value,
                ))
        return records, instance_index

    # ---- the real, advisory connection check (#739) ----

    def check_connections(self) -> List[str]:
        """Real, advisory cross-check ONLY -- confirms each declared
        connection's own two endpoints are (a) genuinely grid-adjacent
        in the stated direction, and (b) the source cell's own real
        `downstream_mask` (or `upstream_dir`, for a `branch` cell,
        #739's own real fix for that core's own different field shape)
        and the destination's own real upstream agree with the
        declared link. Returns real, human-readable warning strings --
        NEVER raises for a mismatch, matching `#590`'s own established
        advisory-check shape exactly: the real compile/RTL remains
        authoritative either way, this only helps catch a likely
        mistake before it becomes silent, wrong behavior."""
        records, instance_index = self.flatten()
        by_pos = {(r.row, r.col): r for r in records}
        warnings: List[str] = []
        for conn in self.connections:
            f_inst, f_row, f_col, f_face = conn.from_
            f_pos = instance_index.get((f_inst, f_row, f_col))
            if f_pos is None:
                warnings.append(f"connection {conn.to_dict()}: source position not found")
                continue
            f_rec = by_pos.get(f_pos)
            if f_rec is not None:
                dmask = self._upstream_or_downstream(f_rec, "downstream")
                if f_face not in dmask:
                    warnings.append(
                        f"connection {conn.to_dict()}: source cell at {f_pos} declares a link "
                        f"{f_face}, but its own real downstream is {dmask} -- doesn't actually offer that way")

            if conn.to == "NC":
                # A real, documented "deliberately not connected" claim
                # -- check the source's own real config genuinely has
                # nothing configured in that direction, catching a real
                # mismatch (claimed NC, but actually wired) the same
                # way any other advisory check does.
                if f_rec is not None:
                    dmask = self._upstream_or_downstream(f_rec, "downstream")
                    if f_face in dmask:
                        warnings.append(
                            f"connection {conn.to_dict()}: declared NC, but source cell at {f_pos} "
                            f"actually has {f_face} configured in its own real downstream -- "
                            f"NC claim doesn't match the real, configured bits")
                continue

            t_inst, t_row, t_col, t_face = conn.to
            t_pos = instance_index.get((t_inst, t_row, t_col))
            if t_pos is None:
                warnings.append(f"connection {conn.to_dict()}: destination position not found")
                continue
            if FACE_OPPOSITE.get(f_face) != t_face:
                warnings.append(
                    f"connection {conn.to_dict()}: real face mismatch -- {f_face} should pair "
                    f"with {FACE_OPPOSITE.get(f_face)}, not {t_face}")
            dr = t_pos[0] - f_pos[0]
            dc = t_pos[1] - f_pos[1]
            expected = FACE_OFFSET[f_face]
            if (dr, dc) != expected:
                warnings.append(
                    f"connection {conn.to_dict()}: real placement doesn't match the declared "
                    f"face -- {f_pos} to {t_pos} is offset {(dr, dc)}, not the real "
                    f"{f_face}-direction offset {expected}")
            t_rec = by_pos.get(t_pos)
            if t_rec is not None:
                umask = self._upstream_or_downstream(t_rec, "upstream")
                if t_face not in umask:
                    warnings.append(
                        f"connection {conn.to_dict()}: destination cell at {t_pos} declares a "
                        f"link {t_face}, but its own real upstream is {umask} -- doesn't actually "
                        f"listen that way")
        return warnings

    @staticmethod
    def _upstream_or_downstream(rec: "v3.IcmV3Record", which: str) -> List[str]:
        """Real, direct handling of `branch`'s own genuinely different
        field shape (`upstream_dir`, a single direction, not a mask --
        confirmed directly against `_deliver_branch()`, #742's own
        real finding) alongside every other core's own real
        `upstream_mask`/`downstream_mask`."""
        if which == "upstream" and "upstream_dir" in rec.core_config:
            return list(rec.core_config.get("upstream_dir", []))
        key = "downstream_mask" if which == "downstream" else "upstream_mask"
        return list(rec.core_config.get(key, []))

    # ---- real, whole-file serialization ----

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format_version": self.format_version,
            "name": self.name,
            "description": self.description,
            "header": self.header(),
            "patterns": {name: p.to_dict() for name, p in self.patterns.items()},
            "design_map": {
                "placements": [p.to_dict() for p in self.placements],
                "connections": [c.to_dict() for c in self.connections],
            },
        }

    def record_hash(self) -> str:
        """Same real discipline as `icm_v3.py`'s own `record_hash()` --
        a canonical, reproducible hash over the real, structural
        content (patterns + design map), so a hand-edited or corrupted
        file is caught on load rather than silently trusted."""
        canonical = json.dumps(
            {"patterns": {name: p.to_dict() for name, p in sorted(self.patterns.items())},
             "design_map": {"placements": [p.to_dict() for p in self.placements],
                             "connections": [c.to_dict() for c in self.connections]}},
            sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def save(self, path: str) -> None:
        d = self.to_dict()
        d["record_hash"] = self.record_hash()
        with open(path, "w") as f:
            json.dump(d, f, indent=2)

    @staticmethod
    def load(path: str) -> "IcmVixFile":
        with open(path) as f:
            d = json.load(f)
        icm = IcmVixFile(
            patterns={name: HierPattern.from_dict(p) for name, p in d.get("patterns", {}).items()},
            placements=[HierPlacement.from_dict(p) for p in d.get("design_map", {}).get("placements", [])],
            connections=[HierConnection.from_dict(c) for c in d.get("design_map", {}).get("connections", [])],
            name=d.get("name", ""), description=d.get("description", ""),
            format_version=d.get("format_version", "icm-vix-v1"),
        )
        stored_hash = d.get("record_hash")
        if stored_hash is not None and stored_hash != icm.record_hash():
            raise ValueError(
                f"record_hash mismatch loading {path!r} -- file may be hand-edited or corrupted "
                f"(stored {stored_hash}, recomputed {icm.record_hash()})")
        return icm


# ---- the real, separate save/state mechanism (#737's own design, now with a full round trip) ----

def snapshot_diff(records: List["v3.IcmV3Record"], grid) -> Dict[str, Any]:
    """Real, direct capture of every cell's own CURRENT runtime value,
    keyed by the same real, stable `cell_id` `flatten()` produces
    (#737's own real design: the structure file stays untouched; only
    a real, separate diff, keyed by cell_id, is ever written for a
    running program's own current state). Reads whichever of the real,
    per-core "current value" fields is actually populated -- `ram`'s
    own `ram_data_reg` (when `ram_data_valid`), `adder`'s own
    `adder_out_buffer` (when `adder_data_valid`), `accumulator`'s own
    running total (`acc_total`, always real/live), extending naturally
    as more core types need real snapshotting."""
    diff: Dict[str, Any] = {}
    for rec in records:
        cell = grid.cells.get((rec.row, rec.col))
        if cell is None:
            continue
        if rec.core == "ram" and getattr(cell, "ram_data_valid", False):
            diff[rec.cell_id] = cell.ram_data_reg
        elif rec.core == "adder" and getattr(cell, "adder_data_valid", False):
            diff[rec.cell_id] = cell.adder_out_buffer
        elif rec.core == "accumulator":
            diff[rec.cell_id] = cell.acc_total
    return diff


def save_state(structure_path: str, diff_path: str, records: List["v3.IcmV3Record"], grid) -> None:
    """The real, whole save operation, per #737's own design and #744's
    own restatement: the structure file (already on disk, unchanged)
    plus a real, separate diff file -- never a copy of the structure
    alongside the runtime values, keeping the two real, orthogonal
    concerns (program vs. state) genuinely separate."""
    diff = snapshot_diff(records, grid)
    with open(diff_path, "w") as f:
        json.dump({"structure_path": structure_path, "diff": diff}, f, indent=2)


def load_state(diff_path: str, icm_loader=IcmVixFile.load):
    """The real, full round-trip #744 named as the one remaining,
    un-attempted piece: load the diff file, load the ORIGINAL structure
    it points at (fresh, from disk -- never assumed already in memory),
    flatten it, and return (icm, records, diff) ready for a fresh grid
    to be built and the diff replayed onto it via `apply_diff()`."""
    with open(diff_path) as f:
        saved = json.load(f)
    icm = icm_loader(saved["structure_path"])
    records, _ = icm.flatten()
    return icm, records, saved["diff"]


def apply_diff(records: List["v3.IcmV3Record"], grid, diff: Dict[str, Any]) -> List[str]:
    """Real, direct replay of a loaded diff onto a fresh grid built
    from the same structure. Returns a real list of any cell_ids in the
    diff that no longer resolve to a real cell in `records` (a
    genuinely changed structure file since the diff was saved) --
    applied values for every cell_id that DOES still resolve, not an
    all-or-nothing operation."""
    by_id = {r.cell_id: r for r in records}
    missing: List[str] = []
    for cell_id, value in diff.items():
        rec = by_id.get(cell_id)
        if rec is None:
            missing.append(cell_id)
            continue
        cell = grid.cells.get((rec.row, rec.col))
        if cell is None:
            missing.append(cell_id)
            continue
        if rec.core == "ram":
            cell.ram_data_reg = value
            cell.ram_data_valid = True
        elif rec.core == "adder":
            cell.adder_out_buffer = value
            cell.adder_data_valid = True
        elif rec.core == "accumulator":
            cell.acc_total = value
    return missing
