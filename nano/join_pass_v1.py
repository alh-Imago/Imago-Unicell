"""join_pass_v1.py -- ledger #1105 (VIXeN): set `join_mode` where the design needs it.

The standard capture takes ANY two successive arrivals at a two-operand cell (adder / mul / div). A fixed-mode ram feeding such a cell offers its constant again and again, so the cell
pairs the constant with itself (K+K) and the real operand never gets its turn (measured, #1102). On the VIXeN target `join_mode=1` makes the cell wait for BOTH faces. This pass sets it
on every adder / mul / div that has two or more upstream faces and at least one of them is fed by a fixed-mode ram whose downstream mask points at it. Nothing else is touched: a cell
that already has the key keeps its value, a cell with one upstream face is left alone (a join needs two faces), and a design without a fixed constant is unchanged.

Works on anything with a position, a core and a core_config dict: the compilers' HierCell (rel_row / rel_col) or a flat record (row / col). Returns the ids of the cells it changed.
"""
from typing import Dict, Iterable, List, Tuple

_DELTA = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
_OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
JOIN_CORES = ("adder", "mul", "div")


def _pos(c) -> Tuple[int, int]:
    return (c.rel_row, c.rel_col) if hasattr(c, "rel_row") else (c.row, c.col)


def _faces(v) -> List[str]:
    if isinstance(v, (list, tuple, set)):
        return [str(x).upper() for x in v]
    if isinstance(v, int):
        return [f for f, b in (("N", 0), ("S", 1), ("E", 2), ("W", 3)) if (v >> b) & 1]
    return [str(v).upper()] if v else []


def apply(cells: Iterable) -> List[str]:
    cells = list(cells)
    at: Dict[Tuple[int, int], object] = {_pos(c): c for c in cells}
    changed = []
    for c in cells:
        if c.core not in JOIN_CORES:
            continue
        cfg = c.core_config
        if "join_mode" in cfg:
            continue
        ups = _faces(cfg.get("upstream_mask", []))
        if len(ups) < 2:
            continue
        r, col = _pos(c)
        for f in ups:
            dr, dc = _DELTA[f]
            n = at.get((r + dr, col + dc))
            if n is not None and n.core == "ram" and n.core_config.get("fixed_mode") and _OPP[f] in _faces(n.core_config.get("downstream_mask", [])):
                cfg["join_mode"] = 1
                changed.append(c.cell_id)
                break
    return changed
