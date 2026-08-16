"""
program_ir_v1.py — the frontend-agnostic IR every Unicell-S frontend
compiles down to. Pulled out of `dsl_parser_v1.py` deliberately (per
Alan: "what of other languages -- Python, C, Rust, etc, they would need
their own frontend parser") -- until this file existed, the backend
(`dsl_compiler_v1.py`'s resolve/place/emit logic) consumed the DSL
parser's own AST node types directly, which meant only the DSL's own
parser could ever feed it. A second frontend would have had nowhere
real to plug in without either duplicating that logic or being forced
through DSL syntax first.

This IR is deliberately THIN -- it's exactly the shape the backend
already needed (confirmed by extraction, not designed speculatively):
a program is a list of placements, each a local name + a tile reference
+ a position + a set of key/value fields (ports or params, disambiguated
later by the resolver against the actual tile's own contract, same as
before). `span` stays `Optional` on every node -- a frontend translating
from a language with a very different structure (e.g. a Python AST walk
where "this placement" doesn't correspond to one contiguous source
region the way a DSL statement does) may not always have a single
meaningful span to offer, and the IR shouldn't force one.

WHAT DOESN'T LIVE HERE: nothing about tokens, grammar, or any one
language's own syntax. Those are entirely each frontend's problem --
`dsl_lexer_v1.py`/`dsl_parser_v1.py` remain the DSL's own concern, now
producing THIS shape rather than a DSL-private one.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import List, Optional, Union

from dsl_diagnostics_v1 import SourceSpan

FieldValue = Union[str, List[str], int]


@dataclass
class FieldIR:
    key: str
    value: FieldValue
    span: Optional[SourceSpan] = None


@dataclass
class PlaceIR:
    name: str
    tile_name: str
    row: int
    col: int
    fields: List[FieldIR] = dc_field(default_factory=list)
    span: Optional[SourceSpan] = None


@dataclass
class ProgramIR:
    name: str
    statements: List[PlaceIR] = dc_field(default_factory=list)
    span: Optional[SourceSpan] = None
