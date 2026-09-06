"""
vm_autosize_v1.py — points.md #667: builds a minimally-sized VM
directly from an ICM file (the real, standing #651 gap this closes),
and resolves named external data entry/exit points
(`IcmV3Record.io_name`) into a clean, position-independent API.

Real motivation, stated directly: a real design will need genuine
external data -- direct from a person testing it, or later from real
I/O hardware (a sensor, a network bridge, a microSD card). Even the
simplest real entry point -- a RAM cell sitting at a known position --
needs a way to be reached WITHOUT the caller needing to know or care
which raw (row, col) it happens to occupy. `io_name` (an ICM record's
own real, optional field) is that name; this module is what resolves
it, on top of a real, minimally-sized grid rather than whatever
oversized bounding space the design happened to be authored in.

Two real, separate concerns, on purpose:
- Auto-sizing: the ICM's own records may span a much larger conceptual
  coordinate space than the design actually uses (generous authoring
  padding, or extraction from a larger composed design). The real VM
  built here uses only the tight, minimum bounding rectangle the
  design genuinely occupies, not whatever space it happened to be
  drawn in.
- Named I/O: resolving `io_name` into direct grid positions, in the
  REMAPPED (post-auto-sizing) coordinate space, so callers never touch
  raw coordinates at all.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import icm_v3 as v3
from unicell_super_automaton_v1 import SuperGrid, SuperCell


def compute_bounding_box(records: List["v3.IcmV3Record"]) -> Tuple[int, int, int, int]:
    """Returns (min_row, min_col, max_row, max_col) -- the real,
    minimum rectangle containing every real cell in the design. Raises
    on an empty record list rather than returning a meaningless
    default (there is no honest bounding box for zero cells)."""
    if not records:
        raise ValueError("cannot compute a bounding box for an empty record list")
    rows = [r.row for r in records]
    cols = [r.col for r in records]
    return min(rows), min(cols), max(rows), max(cols)


def remap_records_to_origin(records: List["v3.IcmV3Record"]) -> List["v3.IcmV3Record"]:
    """Real, necessary shift so the design uses only the real, tight
    grid footprint it actually occupies, not whatever larger
    coordinate space it happened to be authored in. Always returns a
    fresh list of fresh records (even when already at the origin) --
    callers should never need to reason about whether the result
    aliases the input."""
    min_row, min_col, _, _ = compute_bounding_box(records)
    return [
        v3.IcmV3Record(
            cell_id=r.cell_id, row=r.row - min_row, col=r.col - min_col,
            core=r.core, core_config=dict(r.core_config), addon_config=dict(r.addon_config),
            io_name=r.io_name,
        )
        for r in records
    ]


def collect_io_points(records: List["v3.IcmV3Record"]) -> Dict[str, Tuple[int, int]]:
    """Real, necessary validation: two cells sharing the same real
    `io_name` is an unambiguous real design error (which one would a
    caller actually reach?) -- raised clearly here rather than
    silently keeping whichever one happened to be scanned last."""
    points: Dict[str, Tuple[int, int]] = {}
    for r in records:
        if r.io_name is None:
            continue
        if r.io_name in points:
            raise ValueError(
                f"duplicate io_name {r.io_name!r} -- real cells at "
                f"{points[r.io_name]} and {(r.row, r.col)} both claim it; "
                f"every named entry/exit point must be unique"
            )
        points[r.io_name] = (r.row, r.col)
    return points


# Real, honest, per-core-type "current value" field -- deliberately
# narrow rather than pretending every core type has an equally
# meaningful single output value to read back (comparator/branch emit
# routing decisions, not a value; sequencer cycles between several).
_READABLE_VALUE_FIELD = {
    "nano": None,   # special-cased below -- lives on the inner _nano object, not a flat field
    "adder": "adder_out_buffer",
    "ram": "ram_data_reg",
}


def _read_cell_value(cell: "SuperCell") -> int:
    if cell.core == "nano":
        return cell._nano.out_buffer
    field_name = _READABLE_VALUE_FIELD.get(cell.core)
    if field_name is None:
        raise ValueError(
            f"reading a current value back from a real {cell.core!r} cell isn't "
            f"supported yet -- real, supported core types for read_named(): "
            f"{sorted(n for n in _READABLE_VALUE_FIELD if n != 'nano') + ['nano']}. "
            f"inject_named() (writing data IN) works for any real core type "
            f"regardless, since it's just an ordinary arrival."
        )
    return getattr(cell, field_name)


@dataclass
class AutoSizedVM:
    """Points.md #667: a real, minimally-sized VM built directly from
    an ICM file, with named external data entry/exit points resolved
    into direct grid-position lookups. A caller -- a person testing a
    design in a REPL, or later a real I/O bridge (a sensor, a network
    connection, a microSD card) -- never needs to know or care which
    raw (row, col) a named point actually lives at, only its own
    chosen name."""
    grid: SuperGrid
    io_points: Dict[str, Tuple[int, int]]
    rows: int
    cols: int

    def inject_named(self, name: str, value: int) -> None:
        """Real, direct data-in path -- works for any real core type,
        since it's just an ordinary cardinal arrival at that cell's own
        position, the same real mechanism `SuperGrid.inject()` already
        provides generically."""
        row, col = self._resolve(name)
        self.grid.inject(row, col, value)

    def read_named(self, name: str) -> int:
        """Real, direct data-out path -- reads whichever field actually
        holds that core type's own current value (see
        `_read_cell_value()`'s own real, honest per-core-type scope).
        Does not tick the grid itself -- callers run the grid to
        quiescence first, same real convention as everywhere else in
        this VM."""
        row, col = self._resolve(name)
        return _read_cell_value(self.grid.cells[(row, col)])

    def _resolve(self, name: str) -> Tuple[int, int]:
        if name not in self.io_points:
            raise KeyError(
                f"no real entry/exit point named {name!r} in this design -- "
                f"real, available names: {sorted(self.io_points)}"
            )
        return self.io_points[name]


def build_auto_sized_vm(icm: "v3.IcmV3File") -> AutoSizedVM:
    """Points.md #667: the real, single entry point this module exists
    for -- given an ICM file, builds the minimally-sized real VM it
    actually needs, with every real `io_name` resolved and ready to use
    by name. Closes the standing #651 gap directly: an ICM file already
    carries everything needed to know its own minimum runnable
    footprint; this is the tool that derives it, rather than leaving
    that step to be redone by hand each time."""
    remapped = remap_records_to_origin(icm.records)
    grid = SuperGrid(remapped)
    io_points = collect_io_points(remapped)
    _, _, max_row, max_col = compute_bounding_box(remapped)
    return AutoSizedVM(grid=grid, io_points=io_points, rows=max_row + 1, cols=max_col + 1)
