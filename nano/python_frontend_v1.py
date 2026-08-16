"""
python_frontend_v1.py — a second, real frontend for the shared
`program_ir_v1.ProgramIR` backend, built specifically to PROVE the
frontend/backend split (`points.md #344`) actually works, not just to
assert it in a docstring. This is deliberately the SMALLEST possible
second frontend that's still real: it builds `ProgramIR` directly from
plain Python data structures (dicts/lists), with no DSL syntax, no
lexing, no parsing involved at all -- proof that `compile_program_ir()`
genuinely doesn't care where its input came from.

WHY THIS, NOT A FULL PYTHON-AST FRONTEND, RIGHT NOW: a real Python
frontend in the spirit of `compiler.py`'s own precedent (walking
`ast.parse()`'s output, extracting function defs, translating Python
control flow into placements) is a substantially bigger undertaking --
worth its own design conversation given how different Python's own
semantics are from "place a tile at a position." This file answers a
narrower, more urgent question first: does the IR/backend split
ACTUALLY decouple the backend from the DSL, or did the refactor only
look clean without being tested by a second, real consumer? Proving
that cheaply now, with dict-based `ProgramIR` construction, de-risks a
future full Python-AST frontend without committing to designing one
yet.

C AND RUST, STATED HONESTLY: hand-writing a real C or Rust parser is not
a reasonable undertaking for this project -- both are large, mature
grammars that exist specifically because parsing them correctly is hard.
A real C/Rust frontend would need an existing, external parser library
to produce the initial AST, with only the "translate that AST's
placement-like constructs into `ProgramIR`" step being genuinely
project-specific work. Not attempted here; flagged for a real design
conversation before committing to either.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from program_ir_v1 import ProgramIR, PlaceIR, FieldIR
from dsl_compiler_v1 import compile_program_ir
from dsl_diagnostics_v1 import CompileDiagnostic

import icm_v3 as v3

FieldValue = Union[str, List[str], int]


def program_ir_from_dict(name: str, placements: List[dict]) -> ProgramIR:
    """Builds a real `ProgramIR` from plain Python data -- the smallest
    possible non-DSL frontend. Each placement dict: `{"name": str,
    "tile": str, "at": (row, col), "fields": {key: value, ...}}`. No
    source spans (a dict literally has none to offer -- `FieldIR.span`/
    `PlaceIR.span` stay `None`, exactly as `program_ir_v1.py`'s own
    docstring says a frontend is allowed to do when it has nothing
    meaningful to attach)."""
    statements = []
    for p in placements:
        row, col = p["at"]
        fields = [FieldIR(key=k, value=v) for k, v in p.get("fields", {}).items()]
        statements.append(PlaceIR(name=p["name"], tile_name=p["tile"], row=row, col=col, fields=fields))
    return ProgramIR(name=name, statements=statements)


def compile_from_dict(name: str, placements: List[dict]) -> Tuple[Optional["v3.IcmV3File"], List[CompileDiagnostic]]:
    """The whole point: calls `compile_program_ir()` DIRECTLY -- never
    touches `dsl_lexer_v1`/`dsl_parser_v1` at all. If this produces the
    same kind of correct `IcmV3File` (or the same kind of correct
    diagnostics on a broken input) the DSL frontend does, the backend is
    genuinely frontend-agnostic, not just structured to look that way."""
    program_ir = program_ir_from_dict(name, placements)
    return compile_program_ir(program_ir, program_name_hint=name)
