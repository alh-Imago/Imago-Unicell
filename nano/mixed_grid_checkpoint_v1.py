"""
mixed_grid_checkpoint_v1.py -- real, full checkpoint save/load for a
MIXED grid: ordinary SuperCells and DspWrapperCells coexisting in the
same real dict, matching how `SuperGrid.cells` already holds them
side by side today (`dsp_wrapper_automaton_v1.py`'s own docstring:
"duck-types the same real interface SuperGrid.tick() already expects
... so it can sit in the same real grid as ordinary SuperCells without
SuperGrid itself needing to change").

REAL, DIRECT CONTEXT: `#480`-`#482` built and proved checkpoint/save/
wipe/reload for DspWrapperCell ALONE. `#482`'s own real, honest scope
note flagged full mixed-grid checkpointing (SuperCell + DspWrapperCell
together) as a real, separate, not-yet-built task -- this is that
task, per Alan's own explicit choice to pick this thread back up.

REAL, DELIBERATE DESIGN: reuses the exact same JSON + SHA-256
hash-verification discipline already established twice in this
codebase (`icm_v3.IcmV3File`, `dsp_wrapper_automaton_v1.save_model`/
`load_model`) -- a per-cell `cell_class` discriminator tag ("super" |
"dsp_wrapper") is the only new mechanism, dispatching each snapshot to
the correct class's own already-proven `checkpoint()`/`restore()`.
Neither class needed to change to support this -- SuperCell's own
`checkpoint()`/`restore()` (`#483`) and DspWrapperCell's (`#480`) are
called exactly as they already are, unmodified.
"""

from __future__ import annotations

import hashlib
import json as _json
from typing import Dict, Tuple, Union

from unicell_super_automaton_v1 import SuperCell
from dsp_wrapper_automaton_v1 import DspWrapperCell

MixedCell = Union[SuperCell, DspWrapperCell]

_FORMAT = "mixed-grid-checkpoint-v1"


def _tag_and_snapshot(cell: MixedCell) -> dict:
    if isinstance(cell, DspWrapperCell):
        return {"cell_class": "dsp_wrapper", "state": cell.checkpoint()}
    if isinstance(cell, SuperCell):
        return {"cell_class": "super", "state": cell.checkpoint()}
    raise TypeError(
        f"mixed_grid_checkpoint_v1: unsupported cell type {type(cell).__name__!r} "
        f"-- real, known cell classes are SuperCell and DspWrapperCell"
    )


def _restore_one(tagged: dict) -> MixedCell:
    cls = tagged.get("cell_class")
    if cls == "dsp_wrapper":
        return DspWrapperCell.restore(tagged["state"])
    if cls == "super":
        return SuperCell.restore(tagged["state"])
    raise ValueError(f"mixed_grid_checkpoint_v1: unknown cell_class {cls!r} in checkpoint file")


def save_mixed_model(cells: Dict[Tuple[int, int], MixedCell], path: str, name: str = "") -> None:
    """Real, full checkpoint save for a whole mixed grid -- a dict of
    `(row, col) -> SuperCell | DspWrapperCell`, exactly `SuperGrid.
    cells`'s own real shape. Same real hash-verification discipline as
    `IcmV3File`/`dsp_wrapper_automaton_v1.save_model`, not a
    different, one-off scheme."""
    snapshots = [_tag_and_snapshot(cell) for cell in cells.values()]
    canon = _json.dumps(snapshots, sort_keys=True, separators=(",", ":"))
    payload = {
        "format": _FORMAT,
        "name": name,
        "cells": snapshots,
        "checkpoint_hash": hashlib.sha256(canon.encode()).hexdigest(),
    }
    with open(path, "w") as f:
        _json.dump(payload, f, indent=2)


def load_mixed_model(path: str) -> Dict[Tuple[int, int], MixedCell]:
    """Real, exact reconstruction from a real mixed-grid checkpoint
    file -- verifies the same real hash `save_mixed_model()` computed,
    matching the already-established corruption/tamper-detection
    discipline. Each cell is dispatched back to its own real class via
    the saved `cell_class` tag, so a reloaded grid contains genuine
    `SuperCell`/`DspWrapperCell` instances again, not a generic dict."""
    with open(path) as f:
        payload = _json.load(f)
    if payload.get("format") != _FORMAT:
        raise ValueError(f"not a real {_FORMAT} file: format={payload.get('format')!r}")

    snapshots = payload["cells"]
    canon = _json.dumps(snapshots, sort_keys=True, separators=(",", ":"))
    real_hash = hashlib.sha256(canon.encode()).hexdigest()
    stored_hash = payload.get("checkpoint_hash")
    if stored_hash is not None and stored_hash != real_hash:
        raise ValueError(
            f"checkpoint_hash mismatch on load: file says {stored_hash}, "
            f"recomputed {real_hash} -- file may be corrupted or hand-edited"
        )

    restored: Dict[Tuple[int, int], MixedCell] = {}
    for tagged in snapshots:
        cell = _restore_one(tagged)
        restored[(cell.row, cell.col)] = cell
    return restored
