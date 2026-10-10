"""
mixed_grid_checkpoint_v2.py -- a checkpoint of a WHOLE grid: every cell AND the grid's own in-flight state (ledger #1036 addendum 60).

WHY v2 EXISTS. `mixed_grid_checkpoint_v1.py` (#483) saves the cells only. `tests/vm/test_unicell_vs_pure_v1.py` (addendum 59) cut a CORDIC run at every tick,
saved the cells with v1, reloaded them into a fresh grid and finished: with the cells alone all 80 restores failed, because the words that are on their way
from one cell to the next sit in the GRID (`SuperGrid._pending`, delivered on the next tick) and not in any cell. v1 is left exactly as it was (working rule: a
proven file is cloned and versioned, never edited); this file adds the missing piece. Cross-reference: addendum 59 (the finding), addendum 60 (this file).

WHAT IS SAVED: each cell (the same snapshot v1 takes, same class tags), plus the grid's `width`, `mask`, `tick_count` and its pending deliveries, plus the grid class name.
WHAT IS NOT SAVED: the wiring. The grid is rebuilt from the same program (records); `restore_into()` puts the saved state into that fresh grid and refuses a grid of a
different class. The file is hash-checked like v1 (the hash covers the cells AND the grid state).
"""
from __future__ import annotations

import hashlib
import json as _json
from typing import Dict, Tuple

from mixed_grid_checkpoint_v1 import _restore_one, _tag_and_snapshot

_FORMAT = "mixed-grid-checkpoint-v2"


def _pending_to_list(pending) -> list:
    out = []
    for (r, c), items in sorted(pending.items()):
        rows = []
        for src, d, val in items:
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise TypeError(f"mixed_grid_checkpoint_v2: pending value {val!r} is not a number; add support before saving it")
            rows.append([None, None, d, val] if src is None else [src[0], src[1], d, val])
        out.append([r, c, rows])
    return out


def _pending_from_list(lst) -> dict:
    return {(r, c): [(None if sr is None else (sr, sc), d, val) for sr, sc, d, val in rows] for r, c, rows in lst}


def _hash(cells: list, grid: dict) -> str:
    return hashlib.sha256(_json.dumps({"cells": cells, "grid": grid}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def save_grid(grid, path: str, name: str = "") -> None:
    """Save every cell of `grid` and the grid's in-flight state to `path`."""
    cells = [_tag_and_snapshot(cell) for cell in grid.cells.values()]
    gstate = {"class": type(grid).__name__, "width": grid.width, "mask": grid.mask, "tick_count": grid.tick_count, "pending": _pending_to_list(grid._pending)}
    payload = {"format": _FORMAT, "name": name, "cells": cells, "grid": gstate, "checkpoint_hash": _hash(cells, gstate)}
    with open(path, "w") as f:
        _json.dump(payload, f, indent=2)


def load_grid(path: str) -> Tuple[Dict[Tuple[int, int], object], dict]:
    """Verify the hash and return (cells by position, grid state with `pending` already converted back to the grid's own shape)."""
    with open(path) as f:
        payload = _json.load(f)
    if payload.get("format") != _FORMAT:
        raise ValueError(f"not a {_FORMAT} file: format={payload.get('format')!r}")
    real = _hash(payload["cells"], payload["grid"])
    if payload.get("checkpoint_hash") != real:
        raise ValueError(f"checkpoint_hash mismatch on load: file says {payload.get('checkpoint_hash')}, recomputed {real} -- file may be corrupted or hand-edited")
    cells = {}
    for tagged in payload["cells"]:
        cell = _restore_one(tagged)
        cells[(cell.row, cell.col)] = cell
    g = dict(payload["grid"])
    g["pending"] = _pending_from_list(g["pending"])
    return cells, g


def restore_into(grid, path: str) -> None:
    """Put a saved state into `grid`, which must be a FRESH grid built from the same program and of the same class. Replaces every cell and sets the grid's in-flight state."""
    cells, g = load_grid(path)
    if g["class"] != type(grid).__name__:
        raise ValueError(f"checkpoint was taken from a {g['class']}, not a {type(grid).__name__}")
    if set(cells) != set(grid.cells):
        raise ValueError("checkpoint cells do not match the grid's cells: the grid was not built from the same program")
    for pos, cell in cells.items():
        cell.width, cell.mask = g["width"], g["mask"]
        if isinstance(getattr(cell, "pri_seq_order", None), list):
            cell.pri_seq_order = tuple(cell.pri_seq_order)      # JSON turns tuples into lists
        grid.cells[pos] = cell
    grid.width, grid.mask, grid.tick_count, grid._pending = g["width"], g["mask"], g["tick_count"], g["pending"]
