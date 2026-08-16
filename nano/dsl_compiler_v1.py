"""
dsl_compiler_v1.py — the Unicell-S compiler's backend, plus the DSL's
own thin entry point on top of it. Ties lex -> parse -> resolve -> place
-> emit together for DSL source text, per `docs/stripped-cell/design-
notes/unicell_s_dsl_and_compiler_scope.md`'s own pipeline.

FRONTEND-AGNOSTIC BACKEND (`points.md #344`): `compile_program_ir()` is
the real backend -- it takes a `program_ir_v1.ProgramIR`, produced by
ANY frontend, and does resolve/place/emit. It has no idea whether that
IR came from the DSL, a future Python frontend (walking Python's own
`ast` module, matching `compiler.py`'s existing precedent for the old
full-cell format), or anything else. `compile_source()` is the DSL's own
thin wrapper: lex + parse DSL text into a `ProgramIR`, then hand off to
the shared backend. A Python/C/Rust frontend would be its own separate
module producing the SAME `ProgramIR` shape and calling the SAME
`compile_program_ir()` -- no changes needed here to add one.

RESOLVE/PLACE reuse `place()`/`place_composed()` DIRECTLY rather than
reimplementing their validation -- every existing port/param check those
functions already do (built and tested across `#338`-`#342`) still
applies here unchanged; this file's only new job is wrapping their
`ValueError`s into `CompileDiagnostic`s with real source spans attached,
and adding the one check neither of those functions does on its own:
whole-program placement-collision detection (two statements claiming
the same physical cell).

"COLLECT EVERY PROBLEM, DON'T STOP AT THE FIRST" -- per Alan's own
recollection of the old compiler and `cell_format.py`'s own
`check_pipeline_bridges()` precedent: every place statement in a
program is resolved/validated/placed independently, and ALL of their
diagnostics are collected before returning, rather than returning after
the first statement's own failure. Real, honest exception: lex/parse
errors (see `dsl_parser_v1.py`'s own docstring) -- recovery there is a
genuinely harder, separate problem, not solved here.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))

from dsl_lexer_v1 import tokenize
from dsl_parser_v1 import parse_source
from dsl_diagnostics_v1 import CompileDiagnostic
from program_ir_v1 import ProgramIR, PlaceIR

import icm_v3 as v3
from super_tile_library_v1 import super_tile_library, place as tier0_place, SuperTileSpec
from composed_tile_library_v1 import composed_tile_library, place_composed, ComposedTileSpec


def compile_source(source: str, program_name_hint: str = "") -> Tuple[Optional["v3.IcmV3File"], List[CompileDiagnostic]]:
    """The DSL's own entry point: lex + parse DSL source text, then hand
    off to the shared, frontend-agnostic backend. A different frontend
    doesn't call this -- it calls `compile_program_ir()` directly with
    its own translated `ProgramIR`."""
    tokens, lex_diags = tokenize(source)
    if lex_diags:
        return None, lex_diags   # no lex-error recovery yet, stated honestly

    program_ir, parse_diags = parse_source(tokens)
    if program_ir is None:
        return None, parse_diags   # no parser-error recovery yet, stated honestly

    icm, backend_diags = compile_program_ir(program_ir, program_name_hint)
    return icm, parse_diags + backend_diags


def compile_program_ir(program_ir: ProgramIR, program_name_hint: str = "") -> Tuple[Optional["v3.IcmV3File"], List[CompileDiagnostic]]:
    """The real backend, frontend-agnostic (`#344`). Returns
    (icm_file, diagnostics) -- `icm_file` is `None` if any error-severity
    diagnostic was produced anywhere; `diagnostics` may contain warnings
    even when `icm_file` is not `None`."""
    diagnostics: List[CompileDiagnostic] = []
    all_records: List["v3.IcmV3Record"] = []
    occupied: Dict[Tuple[int, int], str] = {}

    for stmt in program_ir.statements:
        records, stmt_diags = _resolve_and_place(stmt)
        diagnostics.extend(stmt_diags)
        if records is None:
            continue
        for rec in records:
            key = (rec.row, rec.col)
            if key in occupied:
                diagnostics.append(CompileDiagnostic(
                    severity="error", stage="place",
                    what=f"placing '{stmt.name}' (tile '{stmt.tile_name}')",
                    problem=f"cell ({rec.row},{rec.col}) is already occupied by {occupied[key]!r}",
                    why="two different placements can't share one physical cell -- "
                        "each SuperCell in a real grid can only run one core at a time",
                    suggestion="choose a different 'at' position for this placement, or "
                               "check whether an earlier placement's own footprint "
                               "already reaches this cell",
                    span=stmt.span,
                ))
                continue
            occupied[key] = f"{stmt.name}.{rec.cell_id}"
            all_records.append(rec)

    if any(d.severity == "error" for d in diagnostics):
        return None, diagnostics

    icm = v3.IcmV3File(
        name=program_name_hint or program_ir.name, records=all_records,
        description=f"compiled from a Unicell-S program named '{program_ir.name}'",
    )
    return icm, diagnostics


def _resolve_and_place(stmt: PlaceIR) -> Tuple[Optional[List["v3.IcmV3Record"]], List[CompileDiagnostic]]:
    diagnostics: List[CompileDiagnostic] = []

    is_composed = stmt.tile_name in composed_tile_library.names()
    is_tier0 = stmt.tile_name in super_tile_library.names()
    if not is_composed and not is_tier0:
        known = sorted(set(super_tile_library.names()) | set(composed_tile_library.names()))
        diagnostics.append(CompileDiagnostic(
            severity="error", stage="resolve",
            what=f"placing '{stmt.name}' as tile '{stmt.tile_name}'",
            problem=f"no tile named {stmt.tile_name!r} exists in either library",
            why="a place statement's tile name has to match something real, registered "
                "in either the Tier-0 or Tier-1 tile library",
            suggestion=f"known tiles: {', '.join(known)}",
            span=stmt.span,
        ))
        return None, diagnostics

    tile = composed_tile_library.get(stmt.tile_name) if is_composed else super_tile_library.get(stmt.tile_name)
    port_names = set(tile.port_names())
    param_names = set(_param_names(tile))

    port_directions: Dict[str, object] = {}
    params: Dict[str, object] = {}
    for f in stmt.fields:
        if f.key in port_names:
            port_directions[f.key] = f.value
        elif f.key in param_names:
            params[f.key] = f.value
        else:
            diagnostics.append(CompileDiagnostic(
                severity="error", stage="resolve",
                what=f"field '{f.key}' on placement '{stmt.name}'",
                problem=f"'{f.key}' is neither a port nor a param of tile '{stmt.tile_name}'",
                why=f"tile '{stmt.tile_name}' only has ports {sorted(port_names)} "
                    f"and params {sorted(param_names)}",
                span=f.span,
            ))

    if diagnostics:
        return None, diagnostics

    try:
        if is_composed:
            records = place_composed(tile, stmt.row, stmt.col, port_directions, params)
        else:
            records = [tier0_place(tile, stmt.row, stmt.col, port_directions, params,
                                    cell_id=f"{stmt.name}@{stmt.row},{stmt.col}")]
        return records, diagnostics
    except ValueError as e:
        diagnostics.append(CompileDiagnostic(
            severity="error", stage="place",
            what=f"placing '{stmt.name}' (tile '{stmt.tile_name}') at ({stmt.row},{stmt.col})",
            problem=str(e),
            why="the tile's own port/param contract wasn't fully satisfied by this "
                "placement's fields -- see the problem above for exactly which "
                "requirement failed (this message is carried straight through from "
                "place()/place_composed()'s own validation, already tested in #338-#342)",
            span=stmt.span,
        ))
        return None, diagnostics


def _param_names(tile) -> List[str]:
    """Tier-0 tiles just have `param_names`. Composed tiles namespace
    their leaf params (`"cmp.threshold"`) -- collected here by walking
    the same sub-cell structure `place_composed()` itself walks, so this
    always matches what that function will actually accept, at any
    nesting depth (`#342`)."""
    if isinstance(tile, SuperTileSpec):
        return list(tile.param_names)
    names: List[str] = []
    for sub in tile.subcells:
        sub_tile = composed_tile_library.get(sub.tile_name) if sub.tile_name in composed_tile_library.names() \
            else super_tile_library.get(sub.tile_name)
        for p in _param_names(sub_tile):
            names.append(f"{sub.name}.{p}")
    return names
