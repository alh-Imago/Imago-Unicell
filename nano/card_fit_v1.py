"""
card_fit_v1.py — points.md #804: does a compiled design FIT a real, bounded card, taking into
account the FIXED positions of card-bound resources (DSP blocks, block RAM)?

WHAT A "FIT" MEANS HERE (Alan, 2026-09-21): a design headed for a card must be FOLDED to fit, the
fixed parts of the card -- DSP, BRAM -- sit where they sit, and an op that needs one must be placed
ON it. So a fit has four parts, all checked and all reported:
  1. BUDGET  -- INSTANTIATED positions <= the target's budget x its utilisation ceiling. The toolchain
                instantiates a dense near-square array (`grid_dims`), so a sparse design pays for every
                position in its array, used or not -- which is why area efficiency (compaction) matters.
  2. EXTENT  -- every cell inside the target's logical grid (routes included -- a route may not
                leave the grid).
  3. SITES   -- each resource-bound op is PINNED onto a site of its kind, and there are enough sites.
  4. NO SILENT DEGRADATION -- an op that wanted a DSP but found no free site falls back to the logic
                implementation, and the report SAYS so.
The search is over fold width (least folding that fits) and spacing, using the virtual-space placer
(`vix_virtual_layout_v1`), which is what lets cardinal ports be re-chosen as the layout folds.

REAL, HONEST LIMITS -- these matter, so they are stated up front:
  * DIE vs GRID. The MAN file gives DSP / M20K positions in DIE coordinates (Chip Planner, read by Alan);
    a UniCell design lives in a LOGICAL grid. The mapping between them is the assembler's LogicLock
    placement, and no Quartus post-fit data exists yet to pin it down (loader_v1.py says the same).
    `target_from_man()` therefore takes the mapping as an explicit PARAMETER (origin, pitch) and records
    that in the target's provenance -- it does not pretend to know it.
  * UNITS. The budget is in INSTANTIATED POSITIONS costed at a MEASURED per-position ALM figure: nano
    ~102.8 (#209), `super_v3` 1030.52 (#579), `super_v4` 1307.42 (#580). The VIX carrier has NO measured
    figure and is deliberately not a preset. (A board's raw LUT count is not a budget either: the Tang Nano
    20K's 20,736 LUT4s hold far fewer positions than 20,736.) An earlier version of this module used ~103
    ALM/cell -- the standalone nano figure -- and counted USED cells; both were wrong for the array the
    toolchain actually builds.
  * DSP LOWERING. A DSP-bound multiply is a DSP-WRAPPER cell on hardware -- a separate record class
    (`icm_v4.DspWrapperRecord`), not a VIX core. That lowering is NOT built: here `mul_dsp` lowers to
    the same `mul` core so the design still simulates, and the BINDING (which op sits on which site) is
    the reported output a card build would consume.
  * BRAM. Sites of kind "bram" are modelled and counted, but no op the frontend emits consumes one yet.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import project_assemble_v1 as pa  # noqa: E402  (grid_dims / cell_positions: the REAL array convention)
import vix_virtual_layout_v1 as V  # noqa: E402
from vix_dag_dispatcher_v1 import DagInstr  # noqa: E402
from vix_opcode_library_v1 import lookup as library_lookup  # noqa: E402

Pos = Tuple[int, int]

#: MEASURED ALM cost per INSTANTIATED grid position, by what is instantiated at each position. These are the
#: only figures the project has: nano-class stripped cell ~102.8 (points.md #209, live cells at 240/750 scale);
#: the `unicell_super_v3` shell 1030.52 (#579) and v4 1307.42 (#580) from real Quartus builds. The VIX carrier
#: has NO measured figure, so it is deliberately absent -- asking for it is an error, not a guess.
ALM_PER_POSITION = {"nano": 102.8, "super_v3": 1030.52, "super_v4": 1307.42}

#: the op that a resource-bearing site can implement, per resource kind
RESOURCE_VARIANTS = {"mul": ("mul_dsp", "dsp")}


@dataclass
class CardTarget:
    name: str
    rows: int
    cols: int
    #: INSTANTIATED grid POSITIONS at 100% (not LUTs, and not merely the cells a design uses: the real
    #: toolchain instantiates a dense array, and an unprogrammed position costs as much as a used one)
    cell_budget: int
    utilization_ceiling: float = 0.80
    #: how the array is instantiated: "generator" = `project_assemble_v1`'s near-square row-major array
    #: (`grid_dims`/`cell_positions` -- what the toolchain does TODAY and what the VM mirror mirrors),
    #: or "rect" = the design's own bounding rectangle (needs the generator's rows/cols passed explicitly).
    array_shape: str = "generator"
    #: resource kind -> ABSOLUTE positions in the logical grid
    sites: Dict[str, List[Pos]] = field(default_factory=dict)
    provenance: List[str] = field(default_factory=list)

    @property
    def max_cells(self) -> int:
        return int(self.cell_budget * self.utilization_ceiling)


@dataclass
class FitReport:
    fits: bool
    cells: int                      # cells the design USES
    max_cells: int                  # budget in instantiated positions (x utilisation ceiling)
    extent: Tuple[int, int]
    grid: Tuple[int, int]
    array_cells: int = 0            # positions the toolchain must INSTANTIATE for this design (the cost)
    fold_width: Optional[int] = None
    spacing: Optional[int] = None
    bindings: List[Tuple[str, str, Pos]] = field(default_factory=list)
    sites_available: Dict[str, int] = field(default_factory=dict)
    sites_used: Dict[str, int] = field(default_factory=dict)
    fallbacks: List[str] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def format(self) -> str:
        util = (100.0 * self.cells / self.array_cells) if self.array_cells else 0.0
        lines = [f"{'FITS' if self.fits else 'DOES NOT FIT'}: {self.array_cells}/{self.max_cells} instantiated positions "
                 f"({self.cells} used, {util:.0f}% utilised), "
                 f"extent {self.extent[0]}x{self.extent[1]} in a {self.grid[0]}x{self.grid[1]} grid"
                 + (f", folded to {self.fold_width} columns/band" if self.fold_width else "")]
        for b in self.bindings:
            lines.append(f"  bound: {b[0]} -> {b[1]} site at {b[2]}")
        for f in self.fallbacks:
            lines.append(f"  fell back to logic (no free site): {f}")
        lines += [f"  problem: {p}" for p in self.problems]
        return "\n".join(lines)


class FitFailure(ValueError):
    """The design does not fit. Carries the `FitReport`. Loud by design."""

    def __init__(self, report: FitReport):
        super().__init__("; ".join(report.problems) or "does not fit")
        self.report = report


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------

def _rows_of(col: dict) -> List[int]:
    if "y_segments" in col:
        return [y for lo, hi in col["y_segments"] for y in range(lo, hi + 1)]
    lo, hi = col["y_range"]
    return list(range(lo, hi + 1))


def target_from_man(man, *, rows: int, cols: int, origin: Pos = (0, 0), pitch: Tuple[int, int] = (1, 1),
                    shell: str = "super_v3", alm_per_position: Optional[float] = None,
                    utilization_ceiling: float = 0.80, array_shape: str = "generator") -> CardTarget:
    """Build a target from a real MAN file. DSP / M20K columns are DIE coordinates; a logical cell
    (r, c) is taken to sit at die (x0 + c*px, y0 + r*py), so a die column becomes a logical site column
    only where that lands exactly on it. `origin` and `pitch` are PARAMETERS (no post-fit data exists to
    fix them) and are recorded in the provenance.

    The cost of a position is the ALM cost of what is INSTANTIATED there: `shell` picks a MEASURED figure
    from `ALM_PER_POSITION` (default `super_v3`, the shell the assembler generates today, 1030.52 ALM,
    points.md #579). The VIX carrier has no measured figure, so `shell="vix"` requires an explicit
    `alm_per_position` -- it is never guessed."""
    if alm_per_position is None:
        if shell not in ALM_PER_POSITION:
            raise ValueError(f"no MEASURED ALM cost for shell {shell!r} (measured: {sorted(ALM_PER_POSITION)}); "
                             f"pass alm_per_position explicitly")
        alm_per_position = ALM_PER_POSITION[shell]
    if isinstance(man, (str, os.PathLike)):
        with open(man) as f:
            man = json.load(f)
    dev = man["device"]
    x0, y0 = origin
    px, py = pitch
    sites: Dict[str, List[Pos]] = {}
    for kind, key in (("dsp", "dsp"), ("bram", "m20k")):
        found: List[Pos] = []
        for col in dev.get(key, {}).get("columns", []):
            if (col["x"] - x0) % px:
                continue
            c = (col["x"] - x0) // px
            if not 0 <= c < cols:
                continue
            for y in _rows_of(col):
                if (y - y0) % py == 0 and 0 <= (y - y0) // py < rows:
                    found.append(((y - y0) // py, c))
        sites[kind] = sorted(set(found))
    budget = int(dev["alm_total"] // alm_per_position)
    prov = [f"MAN file {man.get('card_id')}: part {dev.get('part')}, alm_total={dev['alm_total']}, "
            f"dsp blocks={dev.get('dsp', {}).get('total_blocks')} (source: {str(dev.get('source', ''))[:80]}...)",
            f"budget = alm_total // {alm_per_position} = {budget} INSTANTIATED POSITIONS at 100% "
            f"({shell}: {'MEASURED' if shell in ALM_PER_POSITION and alm_per_position == ALM_PER_POSITION[shell] else 'caller-supplied'}); "
            f"the VIX carrier has NO measured ALM cost, so its real budget is an open question",
            f"die->grid mapping is a PARAMETER: cell (r,c) at die ({x0}+c*{px}, {y0}+r*{py}); no Quartus post-fit "
            f"data exists to confirm it",
            f"derived sites: dsp={len(sites['dsp'])}, bram={len(sites['bram'])} (one per die y-unit in each column's "
            f"range -- an upper bound; the card has {dev.get('dsp', {}).get('total_blocks')} DSP blocks in total)"]
    return CardTarget(name=str(man.get("card_id")), rows=rows, cols=cols, cell_budget=budget,
                      utilization_ceiling=utilization_ceiling, sites=sites, provenance=prov, array_shape=array_shape)


# ---------------------------------------------------------------------------
# Fit
# ---------------------------------------------------------------------------

def array_cells(records, shape: str = "generator") -> int:
    """How many grid POSITIONS the toolchain must instantiate to hold these records -- the real cost.
    "rect": the bounding rectangle. "generator": the smallest N such that `project_assemble_v1`'s own
    near-square row-major array (`grid_dims(N)`, `cell_positions(N, ...)`) covers every record's position
    (records are translated to the origin first, since the array starts at (0,0))."""
    if not records:
        return 0
    minr = min(r.row for r in records)
    minc = min(r.col for r in records)
    pts = {(r.row - minr, r.col - minc) for r in records}
    R = max(p[0] for p in pts) + 1
    C = max(p[1] for p in pts) + 1
    if shape == "rect":
        return R * C
    maxcol_in_row: Dict[int, int] = {}
    for r, c in pts:
        maxcol_in_row[r] = max(maxcol_in_row.get(r, -1), c)
    n = max(len(pts), 1)
    while True:
        rows, cols = pa.grid_dims(n)
        if rows >= R and cols >= C:
            last_row_len = n - (rows - 1) * cols
            # every row but the last is full; the last row holds only `last_row_len` positions
            if all(maxcol_in_row.get(rr, -1) < (cols if rr < rows - 1 else last_row_len) for rr in range(R)):
                return n
        n += 1


def check_fit(records, target: CardTarget, fold_width: Optional[int] = None, spacing: Optional[int] = None,
              bindings=None, fallbacks=None, absolute: bool = False) -> FitReport:
    """Budget and extent of a compiled design against a target. By default only the extent's SIZE is
    compared with the grid (an unplaced design -- e.g. the growth placer's, whose coordinates are relative
    and can be negative -- can be translated freely); `absolute=True` also requires every cell to sit
    inside the grid at its actual coordinates, which is what a design placed BY `fit_to_card` must satisfy."""
    rows = [r.row for r in records]
    cols = [r.col for r in records]
    extent = (max(rows) - min(rows) + 1, max(cols) - min(cols) + 1) if records else (0, 0)
    arr = array_cells(records, target.array_shape)
    rep = FitReport(fits=True, cells=len(records), max_cells=target.max_cells, extent=extent,
                    grid=(target.rows, target.cols), array_cells=arr, fold_width=fold_width, spacing=spacing,
                    bindings=list(bindings or []), fallbacks=list(fallbacks or []),
                    sites_available={k: len(v) for k, v in target.sites.items()},
                    sites_used={})
    for _, kind, _ in rep.bindings:
        rep.sites_used[kind] = rep.sites_used.get(kind, 0) + 1
    if arr > target.max_cells:
        rep.fits = False
        rep.problems.append(f"{arr} instantiated positions ({target.array_shape} array; the design USES only "
                            f"{len(records)}) exceeds the budget of {target.max_cells} "
                            f"({target.cell_budget} x {target.utilization_ceiling:.0%})")
    if records and absolute and (min(rows) < 0 or min(cols) < 0 or max(rows) >= target.rows or max(cols) >= target.cols):
        rep.fits = False
        rep.problems.append(f"extent reaches outside the {target.rows}x{target.cols} grid")
    elif records and (extent[0] > target.rows or extent[1] > target.cols):
        rep.fits = False
        rep.problems.append(f"extent {extent[0]}x{extent[1]} is larger than the {target.rows}x{target.cols} grid")
    return rep


def bind_resources(instrs: List[DagInstr], target: CardTarget) -> Tuple[List[DagInstr], List[str]]:
    """Give each op that has a resource variant a free site of that kind, in program order, until
    the sites run out. The rest fall back to the logic implementation -- and are REPORTED."""
    left = {k: len(v) for k, v in target.sites.items()}
    out: List[DagInstr] = []
    fallbacks: List[str] = []
    for ins in instrs:
        variant = RESOURCE_VARIANTS.get(ins.opcode)
        if variant and library_lookup(variant[0]) is not None:
            if left.get(variant[1], 0) > 0:
                left[variant[1]] -= 1
                out.append(DagInstr(name=ins.name, opcode=variant[0], operands=ins.operands, params=ins.params))
                continue
            if variant[1] in target.sites:        # sites exist but are exhausted -> a REPORTED fallback;
                fallbacks.append(f"{ins.name} ({ins.opcode}: no free {variant[1]} site)")   # a card with none has nothing to fall back from
        out.append(ins)
    return out, fallbacks


def _node_cell_count(instrs: List[DagInstr]) -> int:
    return sum(len(n.cells()) for n in V._build_graph(instrs))


def _max_columns(instrs: List[DagInstr]) -> int:
    nodes = V._build_graph(instrs)
    V._assign_slots(nodes)
    return max(n.depth for n in nodes) + 1


def fit_to_card(instrs: List[DagInstr], target: CardTarget, *, attempts: int = 8,
                spacings: Tuple[int, ...] = (3, 4, 5, 6, 8)):
    """Find the LEAST-FOLDED layout of `instrs` that fits `target`, honouring fixed sites. Returns
    `((icm, positions, dynamic_positions, seq_orders), FitReport)`; raises `FitFailure` otherwise."""
    bound, fallbacks = bind_resources(instrs, target)
    rows, cols = target.rows, target.cols
    empty = FitReport(False, 0, target.max_cells, (0, 0), (rows, cols),
                      sites_available={k: len(v) for k, v in target.sites.items()}, fallbacks=fallbacks)
    floor = _node_cell_count(bound)
    if floor > target.max_cells:
        empty.cells = floor
        empty.problems.append(f"the operation cells ALONE ({floor}) exceed the budget of {target.max_cells} "
                              f"instantiated positions, before any routing -- no folding can help")
        raise FitFailure(empty)
    widths: List[Optional[int]] = [None] + list(range(max(_max_columns(bound) - 1, 2), 1, -1))
    last: Optional[Exception] = None
    over_budget: Optional[FitReport] = None
    for W in widths:
        info: dict = {}
        try:
            result = V.compile_dag_routed(bound, fold_width=W, bounds=(rows, cols), sites=target.sites or None,
                                          info=info, attempts=attempts, spacings=spacings)
        except V.RouteFailure as e:
            last = e
            continue
        records, _ = result[0].flatten()
        rep = check_fit(records, target, fold_width=W, spacing=info.get("spacing"),
                        bindings=info.get("bindings"), fallbacks=fallbacks, absolute=True)
        if rep.fits:
            return result, rep
        over_budget = rep
    if over_budget is not None:
        raise FitFailure(over_budget)
    empty.problems.append(f"no layout of this design fits a {rows}x{cols} grid at any fold width"
                          + (f" (last routing failure: {str(last)[-90:]})" if last else ""))
    raise FitFailure(empty)
