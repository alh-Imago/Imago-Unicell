"""vm_mirror_v2.py -- ledger #1294: the mirror target built from the CARD'S OWN SHAPE.

vm_mirror_v1 builds the mirror from a MAN file and a cell count (the layout a real build would use). The Walker (tools/walker_card_v2.py, ledgers #1289-#1292) now reads the programmed card's
own wires and writes `card.shape.json`: every cell on the card (type, CELL_ID, grid site), every connection (with direction), and for each whether the card itself saw a word cross it.
This module makes that SHAPE a mirror target: the Workbench grid becomes the card's layout, cell by cell, and a design loaded into it is checked against what the card has and has shown.

Everything of v1 is re-exported unchanged (load_mirror_bounds, MirrorBounds, check_records_fit for a MAN target); `check_records_fit` here dispatches on the kind of bounds.

REAL, HONEST SCOPE. (1) The SHAPE is of a FLEX-family design on the Kintex card, and only connections the card showed (`confirmed_by_card`) count as present; unconfirmed ones are reported as "not shown by the
card yet", not as absent. (2) The card holds a few cells the ICM file does not list (merge cores the generator inserts); a design may use fewer cells than the card has but never a cell the card lacks.
(3) The check compares the design with the SHAPE; it does not run the design on the card. (4) Flat DSL/ICM programs are not checked against a SHAPE in this version (they carry no connection map the
check can use): load a hierarchical design (load_icm_vix)."""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from vm_mirror_v1 import MirrorBounds, MirrorFitError, load_mirror_bounds, check_records_fit as _fit_man  # noqa: E402,F401


@dataclass
class CardShapeBounds(MirrorBounds):
    """MirrorBounds (so everything that reads card_id/cells/rows/cols/valid_positions still works) plus what the card showed."""
    kind: str = "card_shape"
    shape_path: str = ""
    fingerprint: str = ""
    source: str = ""
    sites: Dict[Tuple[int, int], List[str]] = field(default_factory=dict)     # grid site -> the card cells there (several can share a site)
    types: Dict[str, str] = field(default_factory=dict)                       # card cell -> module type
    edges: Set[Tuple[str, str]] = field(default_factory=set)                  # every connection the card hardware has
    confirmed: Set[Tuple[str, str]] = field(default_factory=set)              # those the card itself saw a word cross
    complete: bool = False


def load_card_shape_bounds(shape_path: str) -> CardShapeBounds:
    import walker_card_v2 as wk
    sh = wk.read_card_shape(shape_path)                      # raises ValueError for anything that is not a whole card-witnessed SHAPE
    h = sh["header"]
    cells = sh["cells"]
    sites: Dict[Tuple[int, int], List[str]] = {}
    for inst, c in cells.items():
        sites.setdefault((c["row"], c["col"]), []).append(inst)
    rows = [p[0] for p in sites]; cols = [p[1] for p in sites]
    return CardShapeBounds(card_id=str(h.get("card_id")), man_path=shape_path, cells=len(cells), rows=max(rows) - min(rows) + 1, cols=max(cols) - min(cols) + 1,
                           valid_positions=set(sites), shape_path=shape_path, fingerprint=str(h.get("design_fingerprint")), source=str(h.get("source_file")), sites=sites,
                           types={i: c["module_type"] for i, c in cells.items()},
                           edges={(e["from"]["instance"], e["to"]["instance"]) for e in sh["edges"]}, confirmed=set(sh["confirmed"]), complete=bool(sh["complete"]))


def records_not_on_card(records, bounds: CardShapeBounds) -> List[str]:
    """Design cells the card does not have. For the card's own design these are cells the generator absorbed when it built the hardware (e.g. an entry merge folded into its branch): the VM still runs
    them, the card has no separate cell for them."""
    return sorted(r.cell_id for r in records if r.cell_id not in bounds.types)


def check_records_fit(records, bounds, absorbed_ok: bool = False) -> List[str]:
    """MAN target: v1's rule. Card SHAPE target: every record must be a cell the card has, at the card's site, of the card's type; a site holds no more records than the card has cells there.
    `absorbed_ok` (only when the design is the card's own design, same fingerprint): records the card lacks are the generator's absorbed cells and are not an error."""
    if not isinstance(bounds, CardShapeBounds):
        return _fit_man(records, bounds)
    problems: List[str] = []
    used: Dict[Tuple[int, int], int] = {}
    for r in records:
        pos = (r.row, r.col)
        if r.cell_id not in bounds.types:
            if not absorbed_ok:
                problems.append(f"cell {r.cell_id} at ({r.row},{r.col}) is not a cell the card has (the card SHAPE lists {bounds.cells} cells)")
            continue
        card_pos = next(p for p, ids in bounds.sites.items() if r.cell_id in ids)
        if card_pos != pos:
            problems.append(f"cell {r.cell_id} is at ({r.row},{r.col}) in the design but at {card_pos} on the card")
        if bounds.types[r.cell_id] != r.core:
            problems.append(f"cell {r.cell_id} is a '{r.core}' in the design but a '{bounds.types[r.cell_id]}' on the card")
        used[pos] = used.get(pos, 0) + 1
        if used[pos] > len(bounds.sites.get(pos, [])):
            problems.append(f"more design cells at ({r.row},{r.col}) than the card has there")
    return problems


def check_design_against_card(icm_path: str, bounds: CardShapeBounds) -> Dict:
    """Compare the design's own connection map (the generator's, tools/design_map_v2.py) with the card SHAPE. Returns:
    same_design (fingerprints equal), cells_not_on_card, edges_not_on_card (the card has no such connection: the design cannot run there), edges_not_shown (the card has it but has not yet shown a word crossing)."""
    import design_map_v2 as dm
    try:
        m = dm.build_map(icm_path, rings=True)
    except Exception as e:       # a family or construct the flex generator does not translate
        return {"checked": False, "why": f"{type(e).__name__}: {e}"}
    cells_missing = sorted(c["id"] for c in m["cells"] if c["id"] not in bounds.types)
    dedges = [(e["from"], e["to"]) for e in m["edges"]]
    not_on_card = sorted({f"{a} -> {b}" for a, b in dedges if (a, b) not in bounds.edges})
    not_shown = sorted({f"{a} -> {b}" for a, b in dedges if (a, b) in bounds.edges and (a, b) not in bounds.confirmed})
    return {"checked": True, "same_design": m["fingerprint"] == bounds.fingerprint, "design_fingerprint": m["fingerprint"], "card_fingerprint": bounds.fingerprint,
            "cells_not_on_card": cells_missing, "edges_not_on_card": not_on_card, "edges_not_shown": not_shown,
            "card_edges_confirmed": len(bounds.confirmed), "card_edges": len(bounds.edges)}
