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
class ExposeIR:
    """`expose EXTERNAL_NAME -> SUBCELL.PORT` inside a `define` block --
    names a port of a sub-cell that the newly-defined tile itself offers
    under (possibly) a different, friendlier name. Only needed for
    PORTS -- params never need this: any sub-cell param not fixed
    directly inside `define` automatically becomes a required,
    namespaced param of the defined tile (`"subcell.param"`), exactly
    matching `ComposedTileSpec`'s own existing, already-tested behavior.
    Ports need `expose` specifically because a tile's own external port
    names are deliberately NOT required to match `"subcell.port"` (see
    `sentinel`'s own `external_ports`, e.g. `"inc"` not `"acc.inc"`)."""
    external_name: str
    subcell_name: str
    subcell_port: str
    span: Optional[SourceSpan] = None


@dataclass
class DefineIR:
    """`define NAME { place ... expose ... }` -- defines a new,
    reusable composed tile inline, registered into the compile's own
    effective tile library (`points.md #346`) so later `place`
    statements in the SAME program (or later `define`s) can reference it
    by name, exactly like a built-in or `--model`-loaded Tier-1 tile.
    `subcells` reuses `PlaceIR` (its `row`/`col` mean a RELATIVE OFFSET
    here, not an absolute grid position -- same node shape, different
    interpretation depending on context, same discipline the module
    docstring above already uses for spans)."""
    name: str
    subcells: List[PlaceIR] = dc_field(default_factory=list)
    exposes: List[ExposeIR] = dc_field(default_factory=list)
    span: Optional[SourceSpan] = None


@dataclass
class ProgramIR:
    name: str
    statements: List[Union[PlaceIR, DefineIR]] = dc_field(default_factory=list)
    span: Optional[SourceSpan] = None
