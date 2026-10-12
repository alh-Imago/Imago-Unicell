"""flex_save_v1.py -- ledger #1093: the save for the "save / load / retarget" proof. A save is TWO parts, loaded in this order:

  1. the DESIGN MODEL: the hierarchical ICM document (the programming: what every cell is, its wiring, its constants). Embedded in the save, with its hash.
  2. a STATE DIFF: only what has changed from the freshly built design, keyed by the cell's LOGICAL NAME (cell_id, e.g. "lp.fb3"), never by position or by programming
     word: every attribute that differs from a fresh cell, the words in flight between cells (source name, destination name, face, value), the tick count and the caller's step.

Why a diff against a fresh build: the programming comes from the design, so it is never saved; and nothing about a cell has to be listed by hand, so nothing can be forgotten
(checkpoint v2 forgot `_a_face` and `_merge_rr`; this cannot, because it compares everything the cell has). `mixed_grid_checkpoint_v2.py` and `icm_vix_v1.py` are left as they were.
"""
from __future__ import annotations

import hashlib
import json

FORMAT = "unicell-flex-save-v1"


def _canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


def _enc(v):
    if isinstance(v, tuple):
        return {"t": [_enc(x) for x in v]}
    if isinstance(v, list):
        return [_enc(x) for x in v]
    if isinstance(v, (set, frozenset)):
        return {"s": sorted(_enc(x) for x in v)}
    if isinstance(v, dict):
        return {"d": [[_enc(k), _enc(x)] for k, x in v.items()]}
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    raise TypeError(f"flex_save_v1: cannot save a {type(v).__name__} ({v!r}); add support before saving it")


def _dec(v):
    if isinstance(v, list):
        return [_dec(x) for x in v]
    if isinstance(v, dict):
        if "t" in v:
            return tuple(_dec(x) for x in v["t"])
        if "s" in v:
            return set(_dec(x) for x in v["s"])
        return {_dec(k): _dec(x) for k, x in v["d"]}
    return v


def _by_name(grid) -> dict:
    return {c.cell_id: c for c in grid.cells.values()}


def state_diff(grid, fresh) -> dict:
    """{cell_id: {attribute: value}} for every attribute of every cell that differs from the same cell in `fresh` (a grid just built from the same design)."""
    fr, out = _by_name(fresh), {}
    for name, cell in _by_name(grid).items():
        a, b = vars(cell), vars(fr[name])
        d = {k: _enc(a[k]) for k in a if k not in b or a[k] != b[k]}
        d.update({k: "__absent__" for k in b if k not in a})
        if d:
            out[name] = d
    return out


def save(grid, fresh, design_doc: dict, path: str, step: int = 0, note: str = "") -> dict:
    """`design_doc` is the hierarchical ICM document (a dict) the grid was built from; `fresh` a grid built from it and never ticked."""
    names = {pos: c.cell_id for pos, c in grid.cells.items()}
    flight = []
    for dst, items in sorted(grid._pending.items()):
        for src, face, val in items:
            flight.append([None if src is None else names[src], names[dst], face, val])
    body = {"design": design_doc, "state": state_diff(grid, fresh), "flight": flight, "tick": grid.tick_count, "step": step, "width": grid.width}
    payload = {"format": FORMAT, "note": note, "design_hash": hashlib.sha256(_canon(design_doc).encode()).hexdigest(),
               "state_hash": hashlib.sha256(_canon({k: body[k] for k in ("state", "flight", "tick", "step", "width")}).encode()).hexdigest(), **body}
    with open(path, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
    return payload


def read(path: str) -> dict:
    p = json.load(open(path))
    if p.get("format") != FORMAT:
        raise ValueError(f"not a {FORMAT} file: {p.get('format')!r}")
    if hashlib.sha256(_canon(p["design"]).encode()).hexdigest() != p["design_hash"]:
        raise ValueError("design hash mismatch: the design part was changed")
    if hashlib.sha256(_canon({k: p[k] for k in ("state", "flight", "tick", "step", "width")}).encode()).hexdigest() != p["state_hash"]:
        raise ValueError("state hash mismatch: the state part was changed")
    return p


def load_state(grid, payload: dict) -> int:
    """Apply the state part to `grid`, which must be a fresh grid built from payload['design']. Returns the saved step."""
    byname, pos = _by_name(grid), {c.cell_id: p for p, c in grid.cells.items()}
    unknown = set(payload["state"]) - set(byname)
    if unknown:
        raise ValueError(f"the save names cells the grid does not have: {sorted(unknown)[:5]}")
    for name, d in payload["state"].items():
        for k, v in d.items():
            if v == "__absent__":
                delattr(byname[name], k)
            else:
                setattr(byname[name], k, _dec(v))
    grid._pending = {}
    for src, dst, face, val in payload["flight"]:
        grid._pending.setdefault(pos[dst], []).append((None if src is None else pos[src], face, val))
    grid.tick_count = payload["tick"]
    return payload["step"]
