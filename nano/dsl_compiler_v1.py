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

`define`/`expose` (`points.md #346`): a program can now define its own
reusable composed tile inline -- `define NAME { place ... expose ... }`
builds a real `ComposedTileSpec` and registers it, entirely via THIS
FILE'S OWN new `_process_define()`. Zero changes needed to
`composed_tile_library_v1.py`'s core model -- a `DefineIR` compiles down
to exactly the same `ComposedTileSpec`/`SubCellPlacement` shape a
Python-authored or `--model`-loaded tile already uses (`#340`-`#345`),
so `place_composed()` runs it identically either way.

SCOPE, updated (`points.md #347`): a sub-cell's own PARAM can now be
fixed directly inside `define` -- giving a field matching a sub-cell's
own param name (not a port) bakes it into `SubCellPlacement.fixed_params`
(`composed_tile_library_v1.py`), removing it entirely from what the
newly-defined tile requires from ITS OWN caller. `_param_names()` skips
anything in `fixed_params` when computing what's required, so a fixed
param genuinely never surfaces to the outside.

FORWARD DECLARATIONS (`points.md #347`): a `place` statement may now
reference a `define` appearing LATER in the same program -- all
`define` statements are processed in a first pass (still in their own
textual order relative to EACH OTHER, so a later `define` can reference
an earlier one, but not vice versa -- a real, stated, narrower limit),
then all `place` statements in a second pass, once every define in the
file is already registered.

EVERY COMPILE CALL GETS ITS OWN FRESH, DISPOSABLE LIBRARY SCOPE: a
`define`-produced tile is registered into a per-call
`ComposedTileLibrary(parent=<given-or-default>)`, never the caller's own
library object and never the module-level built-in registry. This
matters even without `define` in the picture (it also protects
`#345`'s `--model`-loaded tiles from any surprise cross-call mutation),
but became load-bearing once `compile_program_ir()` started actually
mutating a library rather than only reading from one.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Tuple, Union

sys.path.insert(0, os.path.dirname(__file__))

from dsl_lexer_v1 import tokenize
from dsl_parser_v1 import parse_source
from dsl_diagnostics_v1 import CompileDiagnostic
from program_ir_v1 import ProgramIR, PlaceIR, DefineIR

import icm_v3 as v3
from super_tile_library_v1 import super_tile_library, place as tier0_place, SuperTileSpec
from composed_tile_library_v1 import composed_tile_library, place_composed, ComposedTileSpec, \
    SubCellPlacement, ComposedTileLibrary


def compile_source(source: str, program_name_hint: str = "",
                    composed_library=None) -> Tuple[Optional["v3.IcmV3File"], List[CompileDiagnostic]]:
    """The DSL's own entry point: lex + parse DSL source text, then hand
    off to the shared, frontend-agnostic backend. A different frontend
    doesn't call this -- it calls `compile_program_ir()` directly with
    its own translated `ProgramIR`.

    `composed_library`, per `#345`: an optional `ComposedTileLibrary` to
    resolve Tier-1 tile names against INSTEAD OF the module-level
    built-in `composed_tile_library` -- typically a fresh
    `ComposedTileLibrary(parent=composed_tile_library)` with one or more
    user models registered into it (`dsl_cli_v1.py`'s `--model` flag),
    so user tiles shadow same-named built-ins while everything else
    still falls through to the real built-in registry."""
    tokens, lex_diags = tokenize(source)
    if lex_diags:
        return None, lex_diags   # no lex-error recovery yet, stated honestly

    program_ir, parse_diags = parse_source(tokens)
    if program_ir is None:
        return None, parse_diags   # no parser-error recovery yet, stated honestly

    icm, backend_diags = compile_program_ir(program_ir, program_name_hint, composed_library=composed_library)
    return icm, parse_diags + backend_diags


def compile_program_ir(program_ir: ProgramIR, program_name_hint: str = "",
                        composed_library=None) -> Tuple[Optional["v3.IcmV3File"], List[CompileDiagnostic]]:
    """The real backend, frontend-agnostic (`#344`). Returns
    (icm_file, diagnostics) -- `icm_file` is `None` if any error-severity
    diagnostic was produced anywhere; `diagnostics` may contain warnings
    even when `icm_file` is not `None`.

    Wraps `composed_library` (whatever was given, or the module-level
    built-in default) in a FRESH per-call library (`#346`) -- any
    `define` statement registers into that fresh scope, never into the
    caller's own library object or the global built-in registry.

    TWO PASSES over `program_ir.statements` (`#347`): every `define` is
    processed first, in the program's own relative ORDER among defines
    only, THEN every `place` is resolved. This gives forward
    declarations for `place` (it may reference any `define` in the
    file, regardless of textual position) while keeping a narrower,
    honestly-stated limit: a `define` can still only reference an
    EARLIER `define`, not a later one -- full mutual forward references
    among defines would need real dependency resolution, not attempted
    here."""
    if composed_library is None:
        composed_library = composed_tile_library
    effective_library = ComposedTileLibrary(parent=composed_library)

    diagnostics: List[CompileDiagnostic] = []
    all_records: List["v3.IcmV3Record"] = []
    occupied: Dict[Tuple[int, int], str] = {}

    define_stmts = [s for s in program_ir.statements if isinstance(s, DefineIR)]
    place_stmts = [s for s in program_ir.statements if isinstance(s, PlaceIR)]

    for stmt in define_stmts:
        diagnostics.extend(_process_define(stmt, effective_library))

    for stmt in place_stmts:
        records, stmt_diags = _resolve_and_place(stmt, effective_library)
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


def _resolve_and_place(stmt: PlaceIR, composed_library) -> Tuple[Optional[List["v3.IcmV3Record"]], List[CompileDiagnostic]]:
    diagnostics: List[CompileDiagnostic] = []

    is_composed = stmt.tile_name in composed_library.names()
    is_tier0 = stmt.tile_name in super_tile_library.names()
    if not is_composed and not is_tier0:
        known = sorted(set(super_tile_library.names()) | set(composed_library.names()))
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

    tile = composed_library.get(stmt.tile_name) if is_composed else super_tile_library.get(stmt.tile_name)
    port_names = set(tile.port_names())
    param_names = set(_param_names(tile, composed_library))

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
            records = place_composed(tile, stmt.row, stmt.col, port_directions, params,
                                      composed_library=composed_library)
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


def _param_names(tile, composed_library) -> List[str]:
    """Tier-0 tiles just have `param_names`. Composed tiles namespace
    their leaf params (`"cmp.threshold"`) -- collected here by walking
    the same sub-cell structure `place_composed()` itself walks, so this
    always matches what that function will actually accept, at any
    nesting depth (`#342`). Takes the SAME `composed_library` the
    calling resolve step is using (`#345`), so a nested reference inside
    a user-supplied tile resolves against the right registry too.

    Params in a sub-cell's own `fixed_params` (`#347`) are SKIPPED here
    -- a fixed param is baked into the tile's own definition, so it must
    never appear as something the tile's own caller is asked to supply."""
    if isinstance(tile, SuperTileSpec):
        return list(tile.param_names)
    names: List[str] = []
    for sub in tile.subcells:
        sub_tile = composed_library.get(sub.tile_name) if sub.tile_name in composed_library.names() \
            else super_tile_library.get(sub.tile_name)
        for p in _param_names(sub_tile, composed_library):
            if p in sub.fixed_params:
                continue
            names.append(f"{sub.name}.{p}")
    return names


def _resolve_tile_by_name(name: str, composed_library):
    """Shared lookup: composed library first (nested/user tiles take
    precedence, matching `place_composed()`'s own precedence rule from
    `#342`), Tier-0 second. Returns `None` if neither has it -- caller
    decides how to report that."""
    if name in composed_library.names():
        return composed_library.get(name)
    if name in super_tile_library.names():
        return super_tile_library.get(name)
    return None


def _process_define(stmt: DefineIR, library) -> List[CompileDiagnostic]:
    """Builds a real `ComposedTileSpec` from a `define` block and
    registers it into `library` (`#346`) -- the SAME shape a Python-
    authored or `--model`-loaded Tier-1 tile already uses, so
    `place_composed()` treats it identically. Validates EAGERLY, at
    define-time, rather than deferring to whenever the tile is later
    placed: every sub-cell's own port either gets a direction directly
    in its own `place` block (internal wiring) or a matching `expose`
    (external port) -- exactly `place_composed()`'s own existing
    coverage check, just run earlier so a broken definition is caught
    immediately, not when someone tries to use it."""
    diagnostics: List[CompileDiagnostic] = []
    subcells: List[SubCellPlacement] = []

    for sub_place in stmt.subcells:
        sub_tile = _resolve_tile_by_name(sub_place.tile_name, library)
        if sub_tile is None:
            known = sorted(set(super_tile_library.names()) | set(library.names()))
            diagnostics.append(CompileDiagnostic(
                severity="error", stage="resolve",
                what=f"defining tile '{stmt.name}': sub-cell '{sub_place.name}' as tile '{sub_place.tile_name}'",
                problem=f"no tile named {sub_place.tile_name!r} exists in either library",
                why="a define block's own sub-cells have to reference something real, "
                    "just like a top-level place statement does",
                suggestion=f"known tiles: {', '.join(known)}",
                span=sub_place.span,
            ))
            continue

        port_names = set(sub_tile.port_names())
        param_names = set(_param_names(sub_tile, library))
        internal_directions: Dict[str, object] = {}
        fixed_params: Dict[str, object] = {}
        for f in sub_place.fields:
            if f.key in port_names:
                internal_directions[f.key] = f.value
            elif f.key in param_names:
                fixed_params[f.key] = f.value   # baked in -- never asked of this tile's own caller (#347)
            else:
                diagnostics.append(CompileDiagnostic(
                    severity="error", stage="resolve",
                    what=f"defining tile '{stmt.name}': sub-cell '{sub_place.name}', field '{f.key}'",
                    problem=f"'{f.key}' is neither a port nor a param of tile '{sub_place.tile_name}'",
                    why=f"tile '{sub_place.tile_name}' only has ports {sorted(port_names)} "
                        f"and params {sorted(param_names)}",
                    span=f.span,
                ))

        subcells.append(SubCellPlacement(
            name=sub_place.name, offset=(sub_place.row, sub_place.col),
            tile_name=sub_place.tile_name, internal_directions=internal_directions,
            fixed_params=fixed_params,
        ))

    subcell_names = {s.name for s in stmt.subcells}
    external_ports: Dict[str, Tuple[str, str]] = {}
    for exp in stmt.exposes:
        if exp.subcell_name not in subcell_names:
            diagnostics.append(CompileDiagnostic(
                severity="error", stage="resolve",
                what=f"defining tile '{stmt.name}': expose '{exp.external_name}'",
                problem=f"'{exp.subcell_name}' is not a sub-cell name declared in this define block",
                why=f"known sub-cells here: {sorted(subcell_names)}",
                span=exp.span,
            ))
            continue
        external_ports[exp.external_name] = (exp.subcell_name, exp.subcell_port)

    if diagnostics:
        return diagnostics   # a broken sub-cell reference makes the coverage check below meaningless

    # Eager coverage check -- every real sub-cell port must be either
    # internally wired or exposed, matching place_composed()'s own check
    # but run now, not deferred to placement time.
    exposed_pairs = {(v[0], v[1]) for v in external_ports.values()}
    for sub_place, subcell in zip(stmt.subcells, subcells):
        sub_tile = _resolve_tile_by_name(subcell.tile_name, library)
        for port in sub_tile.port_names():
            if port in subcell.internal_directions:
                continue
            if (subcell.name, port) in exposed_pairs:
                continue
            diagnostics.append(CompileDiagnostic(
                severity="error", stage="resolve",
                what=f"defining tile '{stmt.name}'",
                problem=f"sub-cell '{subcell.name}''s port '{port}' is neither "
                        f"internally wired nor exposed",
                why="every port on every sub-cell has to resolve one way or the other -- "
                    "otherwise there'd be no way to ever tell this cell which direction "
                    "to use for it",
                suggestion=f"add 'expose SOME_NAME -> {subcell.name}.{port}', or give it a "
                           f"direction directly inside {subcell.name}'s own block if it's "
                           f"meant to be wired internally",
                span=stmt.span,
            ))

    if diagnostics:
        return diagnostics

    tile = ComposedTileSpec(
        name=stmt.name, description=f"defined inline in a Unicell-S DSL program (define '{stmt.name}')",
        subcells=subcells, external_ports=external_ports,
    )
    try:
        library.register(tile)
    except ValueError as e:
        diagnostics.append(CompileDiagnostic(
            severity="error", stage="resolve",
            what=f"defining tile '{stmt.name}'",
            problem=str(e),
            why="a tile name can only be defined once per compile -- two 'define' "
                "blocks (or a define colliding with a --model-loaded tile) used "
                "the same name",
            span=stmt.span,
        ))

    return diagnostics
