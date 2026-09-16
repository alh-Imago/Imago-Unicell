"""
vix_compiler_v1.py — points.md #756: the real, first backend targeting
the VIX Carrier lineage / hierarchical ICM format (`icm_vix_v1.py`,
#747), mirroring `dsl_compiler_v1.py`'s own real `compile_program_ir()`
exactly, for the shape it already handles correctly today (Tier-0
tiles only, absolute placement decided entirely by the frontend, no
composed tiles, no addon_config) -- the same real "boring, bounded
foundation" scope Alan directly asked for: "start there... it's a path
we have trodden before."

REAL, DELIBERATE SCOPE, matching the existing backend's own real
division of labor exactly: this function does NOT do placement. Same
as `compile_program_ir()`, a `PlaceIR`'s own `row`/`col` are already
absolute, real, frontend-decided positions -- this function's own real
job is resolve (does the named tile exist, are its ports/params
satisfied) + collision-check + emit, nothing more.

REAL, DELIBERATE SIMPLIFICATION for this first, bounded pass: every
resolved cell is wrapped into ONE, single, whole-program `HierPattern`,
placed via ONE `HierPlacement` at `(0, 0)` -- so a `PlaceIR`'s own
absolute `row`/`col` becomes the cell's own `rel_row`/`rel_col`
directly, unchanged. This is real, honestly NOT the eventual, general
shape `icm_vix_v1.py`'s own real design (`#737`-`#742`) supports --
multiple, deduplicated, reused patterns -- but it produces a real,
correct, loadable `IcmVixFile` for exactly the same real programs the
old-lineage backend already compiles correctly today, with zero new
placement/DAG-solving logic needed. Real, separate, deliberately
deferred work: recognizing when two placements share an identical real
shape and deserve to become instances of ONE reusable pattern, rather
than N separate one-off ones.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from dsl_diagnostics_v1 import CompileDiagnostic
from program_ir_v1 import ProgramIR, PlaceIR
import icm_vix_v1 as vix
import vix_tile_library_v1 as vtl


def compile_program_ir_vix(program_ir: ProgramIR, program_name_hint: str = ""
                            ) -> Tuple[Optional[vix.IcmVixFile], List[CompileDiagnostic]]:
    """The real, first VIX-targeting backend. Returns `(icm_vix_file,
    diagnostics)` -- `icm_vix_file` is `None` if any error-severity
    diagnostic was produced. Real, deliberate scope: `define` statements
    (Tier-1 composed tiles) are not yet supported here -- a real,
    separate, later extension, not attempted in this first, bounded
    pass, matching `#748`'s own real, stated Tier-0-only scope for
    `vix_tile_library_v1.py` itself."""
    diagnostics: List[CompileDiagnostic] = []
    place_stmts = [s for s in program_ir.statements if isinstance(s, PlaceIR)]
    define_stmts = [s for s in program_ir.statements if not isinstance(s, PlaceIR)]
    if define_stmts:
        diagnostics.append(CompileDiagnostic(
            severity="error", stage="resolve",
            what="compiling for the VIX Carrier target",
            problem=f"{len(define_stmts)} real 'define' statement(s) found",
            why="composed (Tier-1) tiles aren't supported by the VIX-targeting "
                "backend yet -- vix_tile_library_v1.py is real, stated Tier-0-only "
                "scope (#748); real, separate, later work",
            suggestion="remove define statements, or compile for the old lineage instead",
        ))
        return None, diagnostics

    cells: List[vix.HierCell] = []
    occupied: Dict[Tuple[int, int], str] = {}

    for stmt in place_stmts:
        cell, stmt_diags = _resolve_and_place_vix(stmt)
        diagnostics.extend(stmt_diags)
        if cell is None:
            continue
        key = (cell.rel_row, cell.rel_col)
        if key in occupied:
            diagnostics.append(CompileDiagnostic(
                severity="error", stage="place",
                what=f"placing '{stmt.name}' (tile '{stmt.tile_name}')",
                problem=f"cell ({cell.rel_row},{cell.rel_col}) is already occupied by {occupied[key]!r}",
                why="two different placements can't share one physical cell -- "
                    "each cell in a real grid can only run one core at a time",
                suggestion="choose a different 'at' position for this placement",
                span=stmt.span,
            ))
            continue
        occupied[key] = f"{stmt.name}.{cell.cell_id}"
        cells.append(cell)

    if any(d.severity == "error" for d in diagnostics):
        return None, diagnostics

    icm = vix.IcmVixFile(
        patterns={"main": vix.HierPattern(cells=cells)},
        placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
        name=program_name_hint or program_ir.name,
        description=f"compiled from a Unicell-S program named '{program_ir.name}' "
                    f"(real, VIX Carrier target, #756)",
    )
    return icm, diagnostics


def _resolve_and_place_vix(stmt: PlaceIR) -> Tuple[Optional[vix.HierCell], List[CompileDiagnostic]]:
    """Real, direct mirror of `dsl_compiler_v1._resolve_and_place()`,
    scoped to Tier-0 VIX tiles only -- same real port/param
    disambiguation logic (a field is a port if the tile names it as
    one, a param if the tile names it as one, otherwise a real,
    reported error), reusing `vix_tile_library_v1.place()` directly
    rather than re-deriving its own validation."""
    diagnostics: List[CompileDiagnostic] = []

    tile = vtl.vix_tile_library.get(stmt.tile_name)
    if tile is None:
        known = sorted(vtl.vix_tile_library.keys())
        diagnostics.append(CompileDiagnostic(
            severity="error", stage="resolve",
            what=f"placing '{stmt.name}' as tile '{stmt.tile_name}'",
            problem=f"no VIX tile named {stmt.tile_name!r} exists",
            why="a place statement's tile name has to match something real, "
                "registered in vix_tile_library_v1.py",
            suggestion=f"known VIX tiles: {', '.join(known)}",
            span=stmt.span,
        ))
        return None, diagnostics

    port_names = set(tile.port_names())
    param_names = set(tile.param_names)
    port_directions: Dict[str, object] = {}
    params: Dict[str, object] = {}
    addon_config: Dict[str, object] = {}
    preload_value: Optional[int] = None
    for f in stmt.fields:
        if f.key.startswith("addon."):
            addon_config[f.key[len("addon."):]] = f.value
        elif f.key == "preload":
            # points.md #756: a real, dedicated field, not part of any
            # tile's own port/param contract -- preload_value lives on
            # HierCell directly (icm_vix_v1.py), the real, correct
            # mechanism for a one-shot compile-time constant (flowing-
            # mode ram, offering exactly once), confirmed the hard way
            # this same session (#742/#748/#750): a fixed_mode source
            # continuously re-offers and silently double-counts at any
            # two-arrival consumer. Matches the same real "addon." field
            # convention's own precedent -- a real, reserved name
            # recognized generically, not part of the tile's own
            # declared contract.
            preload_value = int(f.value)  # type: ignore[arg-type]
        elif f.key in port_names:
            port_directions[f.key] = f.value
        elif f.key in param_names:
            params[f.key] = f.value
        else:
            diagnostics.append(CompileDiagnostic(
                severity="error", stage="resolve",
                what=f"field '{f.key}' on placement '{stmt.name}'",
                problem=f"'{f.key}' is neither a port nor a param of VIX tile '{stmt.tile_name}'",
                why=f"tile '{stmt.tile_name}' only has ports {sorted(port_names)} "
                    f"and params {sorted(param_names)} (or a real 'addon.<name>' or "
                    f"'preload' field)",
                span=f.span,
            ))
    if diagnostics:
        return None, diagnostics

    try:
        cell = vtl.place(tile, port_directions, params,
                          cell_id=f"{stmt.name}@{stmt.row},{stmt.col}",
                          rel_row=stmt.row, rel_col=stmt.col,
                          addon_config=addon_config or None,
                          preload_value=preload_value)
        return cell, diagnostics
    except ValueError as e:
        diagnostics.append(CompileDiagnostic(
            severity="error", stage="place",
            what=f"placing '{stmt.name}' (tile '{stmt.tile_name}') at ({stmt.row},{stmt.col})",
            problem=str(e),
            why="the tile's own port/param contract wasn't fully satisfied by this "
                "placement's fields",
            span=stmt.span,
        ))
        return None, diagnostics
