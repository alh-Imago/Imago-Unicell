"""
c_frontend_v1.py — a real C-AST-based frontend for the Unicell-S
compiler, item 3 of `points.md #370`'s own priority list, scoped down
per Alan's own direct decisions (`points.md #374`): C before Rust
(`pycparser` was already installed, zero setup); plain function-call
syntax, not a macro-based DSL (simplest to parse, matches this file's
own `place(...)`/`field(...)` shape below); and a genuinely NARROWER
first pass than the DSL's own current feature set -- `place`/`field`
only, growing from there, in the exact same spirit as
`python_ast_frontend_v1.py`'s own original "declarative subset, not
full semantics" framing.

Uses `pycparser` (a real, pure-Python C99 parser -- confirmed already
installed in this environment before committing to this approach, not
assumed available) to parse REAL, valid C syntax -- never a made-up
C-like pseudo-language. The whole grammar this file understands:

```c
void PROGRAM_NAME(void) {
    place("local_name", "tile_name", ROW, COL);
    field("local_name", "field_key", value);
    field("local_name", "another_key", "another_value");
}
```

DELIBERATE, NARROWER SCOPE THAN THE DSL, stated plainly, not glossed
over:
  - Exactly ONE top-level `void PROGRAM_NAME(void) { ... }` function
    per file, matching the Python-AST frontend's own "one function, one
    program" precedent.
  - `place(name, tile, row, col)` -- exactly 4 positional args, no
    inline fields (unlike the DSL/Python-AST frontends, C has no
    natural keyword-argument or brace-block syntax to lean on for
    this cleanly) -- fields are set via SEPARATE, subsequent `field()`
    calls instead.
  - `field(name, key, value)` -- must reference a `name` already
    established by an EARLIER `place()` call in the same function body
    (C statements execute top to bottom; there's no forward-declared
    placement concept here).
  - NO `define`/`expose` (composed tiles) yet -- a real, honest,
    explicitly deferred next step, not attempted in this pass.
  - NO direction-LIST-valued fields (`[n, s]`-style, used by a few
    Tier-0 tiles like `dual_threshold_monitor`) -- only single
    string/int literal values. A real, stated gap for a later pass.
  - NO preprocessor: no `#include`, no macros. Every example is
    plain, already-valid C with no directives at all -- `pycparser`
    itself expects already-preprocessed C; running a real `#include`-
    resolving/macro-expanding pass first is a genuinely separate,
    unattempted piece.

Every argument must be a real C literal (a string or integer constant)
-- anything else (a variable reference, a function call, an
expression) is rejected with a real, explained `CompileDiagnostic`
carrying a genuine source span (from `pycparser`'s own `Coord`), not a
raw Python exception. Never executes the C source in any way --
`pycparser` only builds a syntax tree, there is no `libc`/compiler
invocation anywhere in this file.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Tuple, Union

sys.path.insert(0, os.path.dirname(__file__))

import pycparser
from pycparser import c_ast

from program_ir_v1 import ProgramIR, PlaceIR, FieldIR, DefineIR, ExposeIR
from dsl_diagnostics_v1 import CompileDiagnostic, SourceSpan
from dsl_compiler_v1 import compile_program_ir


class _CSyntaxError(Exception):
    def __init__(self, diagnostic: CompileDiagnostic):
        self.diagnostic = diagnostic


def _span_from_coord(coord, length: int = 1) -> SourceSpan:
    # pycparser's own Coord has no "end" position (unlike Python's ast
    # module) -- approximate one from the token's own rendered length,
    # matching dsl_parser_v1.py's own _span_of() precedent exactly.
    line = coord.line if coord else 1
    col = coord.column if coord else 1
    return (line, col, line, col + max(1, length))


def _unescape_c_string(raw: str) -> str:
    """`raw` is the literal token text INCLUDING its surrounding
    quotes (pycparser's own `Constant.value` keeps them, confirmed by
    inspection before writing this, not assumed). Strips the quotes and
    unescapes only the handful of escapes this project's own field
    values plausibly need -- a real, honest, narrower pass than full
    C string-literal semantics (C and Python escaping aren't identical
    in every corner; this doesn't claim to cover all of them)."""
    body = raw[1:-1]
    return (body.replace(r"\"", '"').replace(r"\\", "\\")
                .replace(r"\n", "\n").replace(r"\t", "\t"))


def _extract_constant(node: c_ast.Node, what: str) -> Union[str, int]:
    if not isinstance(node, c_ast.Constant):
        raise _CSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"expected a literal string or integer, found {type(node).__name__}",
            why="this frontend only accepts a declarative subset of C -- every "
                "argument has to be a plain string or integer literal, not "
                "something requiring real evaluation (a variable, a function "
                "call, an expression)",
            span=_span_from_coord(getattr(node, "coord", None)),
        ))
    if node.type == "string":
        return _unescape_c_string(node.value)
    if node.type == "int":
        return int(node.value, 0)   # base 0 -- handles 0x-prefixed hex too
    raise _CSyntaxError(CompileDiagnostic(
        severity="error", stage="parse", what=what,
        problem=f"expected a string or int literal, found a {node.type} constant",
        why="place()/field() arguments here are only ever names, tile names, "
            "row/col numbers, or field values -- all strings or integers",
        span=_span_from_coord(node.coord, len(str(node.value))),
    ))


def _call_name(call: c_ast.FuncCall) -> Optional[str]:
    return call.name.name if isinstance(call.name, c_ast.ID) else None


def _parse_place_call(call: c_ast.FuncCall) -> Tuple[str, PlaceIR]:
    what = "parsing a place(...) call"
    args = call.args.exprs if call.args else []
    if len(args) != 4:
        raise _CSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"expected place(name, tile, row, col) -- got {len(args)} argument(s)",
            why="a place() call always needs exactly four arguments: the local "
                "name, the tile name, the row, and the column -- fields are set "
                "separately via field() calls, not inline here",
            span=_span_from_coord(call.coord),
        ))
    name = _extract_constant(args[0], what)
    tile_name = _extract_constant(args[1], what)
    row = _extract_constant(args[2], what)
    col = _extract_constant(args[3], what)
    if not isinstance(name, str):
        raise _CSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"the first argument (local name) must be a string, got {name!r}",
            why='e.g. place("r1", "ram_constant", 0, 0)',
            span=_span_from_coord(args[0].coord),
        ))
    if not isinstance(tile_name, str):
        raise _CSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"the second argument (tile name) must be a string, got {tile_name!r}",
            why='e.g. place("r1", "ram_constant", 0, 0)',
            span=_span_from_coord(args[1].coord),
        ))
    if not (isinstance(row, int) and isinstance(col, int)):
        raise _CSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"row and col must both be integers, got {row!r} and {col!r}",
            why='e.g. place("r1", "ram_constant", 0, 0)',
            span=_span_from_coord(call.coord),
        ))
    return name, PlaceIR(name=name, tile_name=tile_name, row=row, col=col,
                          fields=[], span=_span_from_coord(call.coord))


def _parse_field_call(call: c_ast.FuncCall, placements: Dict[str, PlaceIR]) -> None:
    what = "parsing a field(...) call"
    args = call.args.exprs if call.args else []
    if len(args) != 3:
        raise _CSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"expected field(name, key, value) -- got {len(args)} argument(s)",
            why='e.g. field("r1", "out", "e") or field("r1", "init_data", 1)',
            span=_span_from_coord(call.coord),
        ))
    name = _extract_constant(args[0], what)
    key = _extract_constant(args[1], what)
    value = _extract_constant(args[2], what)
    if not (isinstance(name, str) and isinstance(key, str)):
        raise _CSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem="the name and key arguments must both be strings",
            why='e.g. field("r1", "out", "e")',
            span=_span_from_coord(call.coord),
        ))
    if name not in placements:
        raise _CSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"field() references {name!r}, but no place({name!r}, ...) "
                    f"call has appeared yet in this function",
            why="field() calls always come AFTER the place() call for the same "
                "name -- C statements execute top to bottom, there's no "
                "forward-declared placement concept here",
            suggestion=f"known names so far: {sorted(placements.keys())}" if placements else
                       "no place() calls have been made yet at this point",
            span=_span_from_coord(args[0].coord, len(name)),
        ))
    placements[name].fields.append(FieldIR(key=key, value=value,
                                            span=_span_from_coord(call.coord)))


def parse_c_source(source: str) -> Tuple[Optional[ProgramIR], List[CompileDiagnostic]]:
    """Parses real C syntax into a `ProgramIR`. Never invokes a real C
    compiler or the C preprocessor -- `pycparser` only builds a syntax
    tree from already-valid, already-preprocessed C text."""
    parser = pycparser.CParser()
    try:
        tree = parser.parse(source, "<c-source>")
    except pycparser.c_parser.ParseError as e:
        # pycparser's own message format: "filename:line:col: message"
        msg = str(e)
        line, col = 1, 1
        try:
            _, rest = msg.split(":", 1)
            line_s, rest = rest.split(":", 1)
            col_s, detail = rest.split(":", 1)
            line, col = int(line_s), int(col_s)
            msg = detail.strip()
        except ValueError:
            pass
        return None, [CompileDiagnostic(
            severity="error", stage="parse", what="parsing C source",
            problem=msg,
            why="the source isn't valid C syntax at all (or uses a construct "
                "this narrow first-pass frontend doesn't understand -- e.g. "
                "#include/macros aren't supported, see this file's own module "
                "docstring)",
            span=(line, col, line, col + 1),
        )]

    fn_defs = [n for n in tree.ext if isinstance(n, c_ast.FuncDef)]
    if len(fn_defs) != 1:
        return None, [CompileDiagnostic(
            severity="error", stage="parse", what="finding the program function",
            problem=f"expected exactly one top-level function definition, found {len(fn_defs)}",
            why="this frontend treats one 'void PROGRAM_NAME(void) { ... }' as "
                "one Unicell-S program",
            span=(1, 1, 1, 1),
        )]
    fn = fn_defs[0]
    fn_name = fn.decl.name

    placements: Dict[str, PlaceIR] = {}
    order: List[str] = []
    body = fn.body.block_items or []
    try:
        for stmt in body:
            if not isinstance(stmt, c_ast.FuncCall):
                raise _CSyntaxError(CompileDiagnostic(
                    severity="error", stage="parse", what="reading a statement",
                    problem=f"unsupported statement type {type(stmt).__name__}",
                    why="this frontend only understands place(...) and field(...) "
                        "calls -- no loops, conditionals, declarations, or "
                        "assignments (see this file's own module docstring for "
                        "the full, deliberately narrow first-pass scope)",
                    span=_span_from_coord(getattr(stmt, "coord", None)),
                ))
            fn_call_name = _call_name(stmt)
            if fn_call_name == "place":
                name, place_ir = _parse_place_call(stmt)
                if name in placements:
                    raise _CSyntaxError(CompileDiagnostic(
                        severity="error", stage="parse", what="parsing a place(...) call",
                        problem=f"'{name}' was already placed earlier in this function",
                        why="each local name can only be placed once",
                        span=_span_from_coord(stmt.coord),
                    ))
                placements[name] = place_ir
                order.append(name)
                continue
            if fn_call_name == "field":
                _parse_field_call(stmt, placements)
                continue
            raise _CSyntaxError(CompileDiagnostic(
                severity="error", stage="parse", what="reading a statement",
                problem=f"unrecognized call {fn_call_name or '(complex expression)'}(...)",
                why="only place(...) and field(...) calls are understood at "
                    "this level in this first-pass C frontend",
                span=_span_from_coord(stmt.coord),
            ))
    except _CSyntaxError as e:
        return None, [e.diagnostic]

    statements: List[Union[PlaceIR, DefineIR]] = [placements[n] for n in order]
    program_ir = ProgramIR(name=fn_name, statements=statements,
                            span=_span_from_coord(fn.coord))
    return program_ir, []


def compile_c_source(source: str, composed_library=None):
    """The whole pipeline: parse real C source, hand off to the SAME
    shared backend every other frontend uses (DSL, Python-dict,
    Python-AST) -- proves this frontend is a real peer, not a special
    case needing its own compilation logic."""
    program_ir, parse_diags = parse_c_source(source)
    if program_ir is None:
        return None, parse_diags
    icm, backend_diags = compile_program_ir(program_ir, composed_library=composed_library)
    return icm, parse_diags + backend_diags
