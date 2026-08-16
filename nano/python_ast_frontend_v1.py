"""
python_ast_frontend_v1.py — a real Python-AST-based frontend for the
Unicell-S compiler, in the spirit of `compiler.py`'s own established
precedent (parses real Python via `ast.parse()`/AST walking, never
`exec()`s it). Distinct from `python_frontend_v1.py` (`points.md #344`),
which builds `ProgramIR` directly from plain Python DICTS purely to
prove the IR/backend split works -- this file parses REAL PYTHON
SYNTAX, the genuinely separate, bigger undertaking `#344`/`#346` both
flagged as open, now built (`points.md #348`).

DELIBERATE SCOPE: a DECLARATIVE SUBSET of Python, not general Python
semantics. No loops, no conditionals, no variables, no arithmetic --
only:
  - exactly one top-level `def program_name(): ...` per file, whose own
    name becomes the compiled program's name
  - `place(name, tile, (row, col), **fields)` calls
  - `with define("tile_name"): ...` blocks, containing their own nested
    `place(...)`/`expose(external_name, "subcell.port")` calls (`with`
    is the natural Python shape for a nested scope, chosen deliberately
    over inventing new syntax)
Every argument must be a Python LITERAL (string/number/tuple/list/dict)
-- anything requiring real execution (a variable reference, a function
call, an f-string, a loop) is rejected with a real, explained
`CompileDiagnostic` carrying a genuine source span (from the AST node's
own `lineno`/`col_offset`), not a raw Python exception.

WHY A SUBSET, NOT FULL PYTHON SEMANTICS: real functions/loops/control-
flow support is a genuinely bigger, separate design question (flagged
explicitly in `#344`'s own "what this doesn't attempt" section) -- how
would a `for` loop over placements even become real Unicell-S
structure? Not resolved here. This file answers a narrower question
first: can real Python SYNTAX (not just Python data literals) reach the
same shared IR/backend everything else already targets? Confirmed: yes,
including `#347`'s own `define`/`expose`/fixed-params/forward-reference
behavior, inherited for free since this frontend produces the exact
same `ProgramIR` shape.
"""

from __future__ import annotations

import ast
import os
import sys
from typing import List, Optional, Tuple, Union

sys.path.insert(0, os.path.dirname(__file__))

from program_ir_v1 import ProgramIR, PlaceIR, FieldIR, DefineIR, ExposeIR
from dsl_diagnostics_v1 import CompileDiagnostic, SourceSpan
from dsl_compiler_v1 import compile_program_ir


class _PythonSyntaxError(Exception):
    def __init__(self, diagnostic: CompileDiagnostic):
        self.diagnostic = diagnostic


def _span(node: ast.AST) -> SourceSpan:
    end_line = getattr(node, "end_lineno", node.lineno)
    end_col = getattr(node, "end_col_offset", node.col_offset) + 1
    return (node.lineno, node.col_offset + 1, end_line, end_col)


def _literal(node: ast.AST, what: str):
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        raise _PythonSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"expected a literal value, found {type(node).__name__}",
            why="this frontend only accepts a declarative subset of Python -- every "
                "argument has to be a plain literal (string/number/tuple/list/dict), "
                "not something requiring real execution (a variable, a function call, "
                "an f-string, ...)",
            span=_span(node),
        ))


def _extract_call_kwargs(call: ast.Call, what: str) -> dict:
    fields = {}
    for kw in call.keywords:
        if kw.arg is None:
            unpacked = _literal(kw.value, what)
            if not isinstance(unpacked, dict):
                raise _PythonSyntaxError(CompileDiagnostic(
                    severity="error", stage="parse", what=what,
                    problem="'**' unpacking here must be a literal dict",
                    why="e.g. **{'in': 'w', 'threshold': 8} -- used to supply "
                        "reserved-keyword-named fields like 'in', which Python "
                        "won't allow as a plain keyword argument",
                    span=_span(kw.value),
                ))
            fields.update(unpacked)
        else:
            fields[kw.arg] = _literal(kw.value, what)
    return fields


def _parse_place_call(call: ast.Call) -> PlaceIR:
    what = "parsing a place(...) call"
    if len(call.args) != 3:
        raise _PythonSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"expected place(name, tile, (row, col), **fields) -- "
                    f"got {len(call.args)} positional argument(s)",
            why="a place() call always needs exactly three positional arguments: "
                "the local name, the tile name, and a (row, col) position",
            span=_span(call),
        ))
    name = _literal(call.args[0], what)
    tile_name = _literal(call.args[1], what)
    pos = _literal(call.args[2], what)
    if not (isinstance(pos, tuple) and len(pos) == 2):
        raise _PythonSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"the third argument must be a (row, col) tuple, got {pos!r}",
            why="e.g. place('r1', 'ram_constant', (0, 0), out='e')",
            span=_span(call.args[2]),
        ))
    fields_dict = _extract_call_kwargs(call, what)
    fields = [FieldIR(key=k, value=v, span=_span(call)) for k, v in fields_dict.items()]
    return PlaceIR(name=name, tile_name=tile_name, row=pos[0], col=pos[1],
                    fields=fields, span=_span(call))


def _parse_expose_call(call: ast.Call) -> ExposeIR:
    what = "parsing an expose(...) call"
    if len(call.args) != 2:
        raise _PythonSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"expected expose(external_name, 'subcell.port') -- "
                    f"got {len(call.args)} positional argument(s)",
            why="e.g. expose('inc', 'acc.inc')",
            span=_span(call),
        ))
    external_name = _literal(call.args[0], what)
    ref = _literal(call.args[1], what)
    if not (isinstance(ref, str) and "." in ref):
        raise _PythonSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"expected 'subcell.port' (a string with a dot), got {ref!r}",
            why="expose has to name a specific sub-cell's specific port",
            span=_span(call.args[1]),
        ))
    subcell_name, _, port_name = ref.partition(".")
    return ExposeIR(external_name=external_name, subcell_name=subcell_name,
                     subcell_port=port_name, span=_span(call))


def _parse_define_with(with_stmt: ast.With) -> DefineIR:
    what = "parsing a 'with define(...):' block"
    if len(with_stmt.items) != 1:
        raise _PythonSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem="a 'with' block here must have exactly one context manager",
            why='expected \'with define("tile_name"):\'',
            span=_span(with_stmt),
        ))
    call = with_stmt.items[0].context_expr
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "define"):
        raise _PythonSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem='expected \'define("tile_name")\' as the with-block\'s context manager',
            why='a define block always starts \'with define("name"):\'',
            span=_span(with_stmt),
        ))
    if len(call.args) != 1:
        raise _PythonSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=what,
            problem=f"define(...) takes exactly one argument, got {len(call.args)}",
            why="e.g. define('my_sentinel')",
            span=_span(call),
        ))
    tile_name = _literal(call.args[0], what)

    subcells: List[PlaceIR] = []
    exposes: List[ExposeIR] = []
    for stmt in with_stmt.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            inner = stmt.value
            fn_name = inner.func.id if isinstance(inner.func, ast.Name) else None
            if fn_name == "place":
                subcells.append(_parse_place_call(inner))
                continue
            if fn_name == "expose":
                exposes.append(_parse_expose_call(inner))
                continue
        raise _PythonSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what=f"inside 'define({tile_name!r})' block",
            problem="unsupported statement -- only place(...) and expose(...) calls "
                    "are understood inside a define block",
            why="a define block's own body is sub-cell placements and port exposures only",
            span=_span(stmt),
        ))
    return DefineIR(name=tile_name, subcells=subcells, exposes=exposes, span=_span(with_stmt))


def _parse_body(stmts: List[ast.stmt]) -> Tuple[List[PlaceIR], List[DefineIR]]:
    places: List[PlaceIR] = []
    defines: List[DefineIR] = []
    for stmt in stmts:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            fn_name = call.func.id if isinstance(call.func, ast.Name) else None
            if fn_name == "place":
                places.append(_parse_place_call(call))
                continue
            raise _PythonSyntaxError(CompileDiagnostic(
                severity="error", stage="parse", what="reading a statement",
                problem=f"unrecognized call {fn_name or '(complex expression)'}(...)",
                why="only place(...) calls and 'with define(...):' blocks are "
                    "understood at this level",
                span=_span(stmt),
            ))
        if isinstance(stmt, ast.With):
            defines.append(_parse_define_with(stmt))
            continue
        raise _PythonSyntaxError(CompileDiagnostic(
            severity="error", stage="parse", what="reading a statement",
            problem=f"unsupported statement type {type(stmt).__name__}",
            why="this frontend only understands place(...) calls and "
                "'with define(...):' blocks -- no loops, conditionals, or "
                "assignments",
            span=_span(stmt),
        ))
    return places, defines


def parse_python_source(source: str) -> Tuple[Optional[ProgramIR], List[CompileDiagnostic]]:
    """Parses real Python syntax into a `ProgramIR`. Uses `ast.parse()`
    only -- never `exec()`/`eval()`s the source itself (only individual
    LITERAL argument nodes go through `ast.literal_eval()`, which cannot
    execute arbitrary code, by design)."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        col = (e.offset or 1)
        return None, [CompileDiagnostic(
            severity="error", stage="parse", what="parsing Python source",
            problem=str(e.msg),
            why="the source isn't valid Python syntax at all",
            span=(e.lineno or 1, col, e.lineno or 1, col + 1),
        )]

    fn_defs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(fn_defs) != 1:
        return None, [CompileDiagnostic(
            severity="error", stage="parse", what="finding the program function",
            problem=f"expected exactly one top-level function definition, found {len(fn_defs)}",
            why="this frontend treats one 'def program_name():' as one Unicell-S program",
            span=(1, 1, 1, 1),
        )]
    fn = fn_defs[0]

    try:
        places, defines = _parse_body(fn.body)
    except _PythonSyntaxError as e:
        return None, [e.diagnostic]

    # defines first in source order, then places -- readability only;
    # compile_program_ir() re-splits by isinstance() itself (#347), so
    # this ordering isn't load-bearing.
    statements: List[Union[PlaceIR, DefineIR]] = [*defines, *places]
    program_ir = ProgramIR(name=fn.name, statements=statements, span=_span(fn))
    return program_ir, []


def compile_python_source(source: str, composed_library=None):
    """The whole pipeline: parse real Python source, hand off to the
    SAME shared backend every other frontend uses -- proves this
    frontend is a real peer of the DSL and dict-based frontends, not a
    special case needing its own compilation logic."""
    program_ir, parse_diags = parse_python_source(source)
    if program_ir is None:
        return None, parse_diags
    icm, backend_diags = compile_program_ir(program_ir, composed_library=composed_library)
    return icm, parse_diags + backend_diags
