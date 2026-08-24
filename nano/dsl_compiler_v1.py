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
the first statement's own failure. Parser-level errors now follow the
same discipline (`points.md #372`) -- real, statement-level panic-mode
recovery in `dsl_parser_v1.py` means multiple independent syntax errors
in one file are all reported together, not just the first. Lex errors
remain the one real, honest exception: an illegal character still stops
compilation outright (lexing itself already collects every bad
character it finds, but a badly-lexed file has no reliable statement
boundaries to recover parsing against).

`define`/`expose` (`points.md #346`): a program can now define its own
reusable composed tile inline -- `define NAME { place ... expose ... }`
builds a real `ComposedTileSpec` and registers it, entirely via THIS
FILE'S OWN new `_process_define()`. Zero changes needed to
`composed_tile_library_v1.py`'s core model -- a `DefineIR` compiles down
to exactly the same `ComposedTileSpec`/`SubCellPlacement` shape a
Python-authored or `--model`-loaded tile already uses (`#340`-`#345`),
so `place_composed()` runs it identically either way.

NAMING HYGIENE LINT (`points.md #350`, per Alan: undisciplined name
reuse "make[s] code hard to follow, that at least should be shown, and
warned against"): `_lint_names()` collects real, WARNING-severity
diagnostics (never blocking compilation, shown alongside everything
else) for two concrete, checkable hazards -- two top-level statements
(`place` or `define`) sharing one local name within a program, and two
sub-cells sharing one local name within the SAME `define` block (the
latter is genuinely ambiguous, not just hard to read, since `expose`
resolves a sub-cell by name).

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
from typing import Dict, List, Optional, Set, Tuple, Union

sys.path.insert(0, os.path.dirname(__file__))

from dsl_lexer_v1 import tokenize
from dsl_parser_v1 import parse_source
from dsl_diagnostics_v1 import CompileDiagnostic
from program_ir_v1 import ProgramIR, PlaceIR, DefineIR

import icm_v3 as v3
import icm_v4 as v4
from super_tile_library_v1 import super_tile_library, place as tier0_place, SuperTileSpec
from composed_tile_library_v1 import composed_tile_library, place_composed, ComposedTileSpec, \
    SubCellPlacement, ComposedTileLibrary
# Imported for its own self-registration side effect (points.md #485) --
# this is the ONE line a future tile-kind module needs added here to be
# resolvable by name; nothing else in this file names "dsp_wrapper" at all.
import dsp_wrapper_tile_library_v1  # noqa: F401
from tile_source_registry_v1 import find_source_for, all_known_tile_names


def compile_source(source: str, program_name_hint: str = "",
                    composed_library=None) -> Tuple[Optional["v3.IcmV3File | v4.IcmV4File"], List[CompileDiagnostic]]:
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
        return None, parse_diags   # the program's own header itself was unrecoverable
    if any(d.severity == "error" for d in parse_diags):
        # real statement-level recovery (#372) may have found MULTIPLE
        # independent syntax errors and still produced a ProgramIR (with
        # the broken statements simply missing) -- but a program with
        # known-missing statements can never be a valid compile target,
        # so stop here and surface every error found, not just the first.
        return None, parse_diags

    icm, backend_diags = compile_program_ir(program_ir, program_name_hint, composed_library=composed_library)
    return icm, parse_diags + backend_diags


def compile_program_ir(program_ir: ProgramIR, program_name_hint: str = "",
                        composed_library=None) -> Tuple[Optional["v3.IcmV3File | v4.IcmV4File"], List[CompileDiagnostic]]:
    """The real backend, frontend-agnostic (`#344`). Returns
    (icm_file, diagnostics) -- `icm_file` is `None` if any error-severity
    diagnostic was produced anywhere; `diagnostics` may contain warnings
    even when `icm_file` is not `None`.

    REAL, BACKWARD-COMPATIBLE OUTPUT TYPE (`#485`): a program that
    places no DSP wrapper tiles produces the exact same real
    `v3.IcmV3File` this function has always returned -- zero behavior
    change for any existing caller/test. Only a program that DOES
    place at least one DSP wrapper tile produces the new, real, mixed
    `v4.IcmV4File` instead. This mirrors `#480`-`#484`'s own real
    "config vs. runtime state" and "new format number, not a silent
    v3 extension" discipline, applied here to the compiler's OWN
    output selection: the shape of what comes out honestly reflects
    what the program actually contains, not a blanket format bump.

    Wraps `composed_library` (whatever was given, or the module-level
    built-in default) in a FRESH per-call library (`#346`) -- any
    `define` statement registers into that fresh scope, never into the
    caller's own library object or the global built-in registry.

    TWO PASSES over `program_ir.statements` (`#347`): every `define` is
    processed first, in real DEPENDENCY order (a topological sort,
    `#373` -- not textual order), THEN every `place` is resolved. This
    gives forward declarations for BOTH `place` (it may reference any
    `define` in the file, regardless of textual position) AND, as of
    `#373`, `define` itself -- a `define` may now reference another
    `define` appearing LATER in the source text, as long as there's no
    real cycle between them. A genuine circular define reference (A
    contains B contains A) is still a real, reported error -- that
    would mean infinite physical cell expansion, which can't exist on
    real hardware, not something dependency ordering can paper over."""
    if composed_library is None:
        composed_library = composed_tile_library
    effective_library = ComposedTileLibrary(parent=composed_library)

    diagnostics: List[CompileDiagnostic] = []
    diagnostics.extend(_lint_names(program_ir))
    all_records: List["v3.IcmV3Record"] = []
    dsp_wrapper_records: List["v4.DspWrapperRecord"] = []
    occupied: Dict[Tuple[int, int], str] = {}

    define_stmts = [s for s in program_ir.statements if isinstance(s, DefineIR)]
    place_stmts = [s for s in program_ir.statements if isinstance(s, PlaceIR)]

    ordered_defines, sort_diags = _topological_sort_defines(define_stmts)
    diagnostics.extend(sort_diags)
    for stmt in ordered_defines:
        diagnostics.extend(_process_define(stmt, effective_library))

    for stmt in place_stmts:
        result, stmt_diags = _resolve_and_place(stmt, effective_library)
        diagnostics.extend(stmt_diags)
        if result is None:
            continue
        # `result` is {bucket_name: [record, ...]} -- one bucket for a
        # composed-tile placement's own real IcmV3Record list, or one
        # bucket for whichever real TileSource resolved a Tier-0-shaped
        # placement (points.md #485). Position collisions are checked
        # GLOBALLY across every bucket -- two records of ANY kind can
        # never legally share one physical cell.
        for bucket_name, recs in result.items():
            for rec in recs:
                key = (rec.row, rec.col)
                if key in occupied:
                    diagnostics.append(CompileDiagnostic(
                        severity="error", stage="place",
                        what=f"placing '{stmt.name}' (tile '{stmt.tile_name}')",
                        problem=f"cell ({rec.row},{rec.col}) is already occupied by {occupied[key]!r}",
                        why="two different placements can't share one physical cell -- "
                            "each cell in a real grid can only run one core/wrapper at a time",
                        suggestion="choose a different 'at' position for this placement, or "
                                   "check whether an earlier placement's own footprint "
                                   "already reaches this cell",
                        span=stmt.span,
                    ))
                    continue
                occupied[key] = f"{stmt.name}.{rec.cell_id}"
                if bucket_name == "dsp_wrapper_records":
                    dsp_wrapper_records.append(rec)
                else:
                    all_records.append(rec)

    if any(d.severity == "error" for d in diagnostics):
        return None, diagnostics

    if dsp_wrapper_records:
        icm = v4.IcmV4File(
            name=program_name_hint or program_ir.name,
            super_records=all_records, dsp_wrapper_records=dsp_wrapper_records,
            description=f"compiled from a Unicell-S program named '{program_ir.name}' "
                        f"(real, mixed icm-v4 -- includes at least one DSP wrapper cell)",
        )
    else:
        icm = v3.IcmV3File(
            name=program_name_hint or program_ir.name, records=all_records,
            description=f"compiled from a Unicell-S program named '{program_ir.name}'",
        )
    return icm, diagnostics


def _lint_names(program_ir: ProgramIR) -> List[CompileDiagnostic]:
    """Naming hygiene, not correctness -- WARNING severity, never blocks
    compilation, but always shown (`points.md #350`). Two real,
    concrete checks, not a vague "write better code" gesture:

    1. Two top-level statements (`place` OR `define`) sharing one local
       name within a program -- confusing to read and to debug (an
       error message naming "r1" is ambiguous about which "r1" it
       means), even where nothing downstream currently breaks
       functionally because of it.
    2. Two sub-cells sharing one local name within the SAME `define`
       block -- genuinely ambiguous, not just hard to read: `expose`
       resolves a sub-cell by name, so a duplicate makes "which one did
       this expose actually mean" unanswerable even in principle."""
    diagnostics: List[CompileDiagnostic] = []

    seen: Dict[str, object] = {}
    for stmt in program_ir.statements:
        if stmt.name in seen:
            diagnostics.append(CompileDiagnostic(
                severity="warning", stage="lint",
                what=f"program statement '{stmt.name}'",
                problem=f"the local name '{stmt.name}' is reused for more than one "
                        f"top-level statement in this program",
                why="reusing local names makes error messages and generated cell "
                    "IDs ambiguous about which statement they actually refer to -- "
                    "a real readability hazard even when nothing downstream "
                    "currently breaks because of it",
                suggestion="give each place/define statement its own distinct local name",
                span=stmt.span,
            ))
        else:
            seen[stmt.name] = stmt

        if isinstance(stmt, DefineIR):
            sub_seen: Dict[str, object] = {}
            for sub in stmt.subcells:
                if sub.name in sub_seen:
                    diagnostics.append(CompileDiagnostic(
                        severity="warning", stage="lint",
                        what=f"define '{stmt.name}', sub-cell '{sub.name}'",
                        problem=f"the sub-cell name '{sub.name}' is reused more than "
                                f"once inside this define block",
                        why="expose statements resolve a sub-cell by name -- a "
                            "duplicate makes 'which sub-cell did this expose actually "
                            "mean' genuinely ambiguous, not just hard to read",
                        suggestion="give each sub-cell inside this define its own "
                                   "distinct local name",
                        span=sub.span,
                    ))
                else:
                    sub_seen[sub.name] = sub

    return diagnostics


def _resolve_and_place(stmt: PlaceIR, composed_library) -> Tuple[Optional[Dict[str, list]], List[CompileDiagnostic]]:
    """Returns `{bucket_name: [record, ...]}` on success -- a composed
    placement always yields `{"super_records": [...]}` (`place_
    composed()` only ever emits `IcmV3Record`s); a Tier-0-shaped
    placement yields whichever real bucket its `TileSource` names
    (`points.md #485`) -- `"super_records"` for the pre-existing
    super-cell library, `"dsp_wrapper_records"` for the new DSP
    wrapper one, or whatever a FUTURE registered kind names. This
    function itself never mentions "dsp_wrapper" by name anywhere --
    it only ever asks the registry, matching this whole mechanism's
    own point."""
    diagnostics: List[CompileDiagnostic] = []

    is_composed = stmt.tile_name in composed_library.names()
    tile_source = None if is_composed else find_source_for(stmt.tile_name)
    if not is_composed and tile_source is None:
        known = sorted(set(composed_library.names()) | set(all_known_tile_names()))
        diagnostics.append(CompileDiagnostic(
            severity="error", stage="resolve",
            what=f"placing '{stmt.name}' as tile '{stmt.tile_name}'",
            problem=f"no tile named {stmt.tile_name!r} exists in any registered library",
            why="a place statement's tile name has to match something real, registered "
                "in the Tier-1 composed library or one of the Tier-0-shaped tile "
                "libraries hooked into the compiler",
            suggestion=f"known tiles: {', '.join(known)}",
            span=stmt.span,
        ))
        return None, diagnostics

    tile = composed_library.get(stmt.tile_name) if is_composed else tile_source.library.get(stmt.tile_name)
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
            return {"super_records": records}, diagnostics
        else:
            rec = tile_source.place_fn(tile, stmt.row, stmt.col, port_directions, params,
                                        cell_id=f"{stmt.name}@{stmt.row},{stmt.col}")
            return {tile_source.bucket: [rec]}, diagnostics
    except ValueError as e:
        diagnostics.append(CompileDiagnostic(
            severity="error", stage="place",
            what=f"placing '{stmt.name}' (tile '{stmt.tile_name}') at ({stmt.row},{stmt.col})",
            problem=str(e),
            why="the tile's own port/param contract wasn't fully satisfied by this "
                "placement's fields -- see the problem above for exactly which "
                "requirement failed (this message is carried straight through from "
                "the tile's own place()/place_composed() validation)",
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
    never appear as something the tile's own caller is asked to supply.

    GENERALIZED (`points.md #485`): a Tier-0-SHAPED tile of ANY
    registered kind (real, checked via `hasattr`, not an
    `isinstance(tile, SuperTileSpec)` check that would silently miss
    a future kind's own tile class) just has a flat `param_names`
    list -- only `ComposedTileSpec` doesn't, since ITS params are
    computed by recursing into sub-cells instead."""
    if hasattr(tile, "param_names"):
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


def _topological_sort_defines(define_stmts: List[DefineIR]) -> Tuple[List[DefineIR], List[CompileDiagnostic]]:
    """Sorts define statements into DEPENDENCY order (a define that
    references another define is processed AFTER it), enabling real
    forward references (`points.md #373`): a define may now reference
    ANOTHER define appearing later in the source text, as long as
    there's no cycle. Per Alan's own suggestion: pass 1 here IS the
    real "table" -- `by_name`/`define_names` -- built once, up front,
    purely for checking/ordering, before any define is actually
    resolved.

    Standard DFS-based topological sort with real cycle detection: a
    composed tile can never legitimately contain itself, directly or
    transitively (that would mean infinite physical cell expansion),
    so a cycle is always a genuine, reportable error, never something
    to silently work around. On a cycle, the involved defines are
    simply left out of the returned order (unregistered) -- any
    `place` statement later trying to use one of them gets a real,
    separate "tile not found" diagnostic from the normal resolution
    path, which is an honest, correct fallback, not a special case to
    maintain."""
    diagnostics: List[CompileDiagnostic] = []
    by_name: Dict[str, DefineIR] = {stmt.name: stmt for stmt in define_stmts}
    define_names = set(by_name.keys())

    # The dependency graph only needs DEFINE -> DEFINE edges -- a
    # reference to a Tier-0 primitive or an already-registered composed
    # tile needs no ordering at all, it's always immediately available.
    deps: Dict[str, Set[str]] = {}
    for stmt in define_stmts:
        referenced = {sp.tile_name for sp in stmt.subcells if sp.tile_name in define_names}
        deps[stmt.name] = referenced

    ordered: List[str] = []
    state: Dict[str, str] = {}   # name -> "visiting" | "done"
    path: List[str] = []

    def visit(name: str) -> bool:
        if state.get(name) == "done":
            return True
        if state.get(name) == "visiting":
            cycle = path[path.index(name):] + [name]
            diagnostics.append(CompileDiagnostic(
                severity="error", stage="resolve",
                what=f"defining tile '{name}'",
                problem=f"circular define reference: {' -> '.join(cycle)}",
                why="a define block's own sub-cells physically contain "
                    "whatever tile they reference -- a cycle would mean "
                    "infinite physical cell expansion, which can't exist "
                    "on real hardware",
                span=by_name[name].span,
            ))
            return False
        state[name] = "visiting"
        path.append(name)
        ok = True
        for dep in sorted(deps[name]):   # sorted for deterministic diagnostic order
            if not visit(dep):
                ok = False
                break
        path.pop()
        state[name] = "done"
        if ok:
            ordered.append(name)
        return ok

    for stmt in define_stmts:
        if state.get(stmt.name) != "done":
            visit(stmt.name)

    return [by_name[n] for n in ordered], diagnostics


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
