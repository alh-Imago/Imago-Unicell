"""
dsl_parser_v1.py — recursive descent parser for the Unicell-S DSL.
Covers exactly this first slice's grammar, per the design note's own
"suggested first, low-risk step": a `program { place ... }` with one or
more `place` statements. No `use`/`expose` yet -- those extend this same
structure when the grammar grows, not replace it.

```
program     := "program" IDENT "{" place_stmt* "}"
place_stmt  := "place" IDENT "as" IDENT "at" "(" NUMBER "," NUMBER ")" "{" field* "}"
field       := IDENT ":" value
value       := IDENT | NUMBER | "[" IDENT ("," IDENT)* "]"
```

Every AST node keeps the source span of its own defining tokens, so a
diagnostic raised against that node always has somewhere real to point.

REAL, HONEST LIMITATION (stated in the design note, not glossed over
here): no parser error recovery yet. One unrecoverable syntax error
stops parsing there -- `compile_source()` returns that one diagnostic
rather than a full list of every syntax problem in the file. Real
recovery (skip to a plausible resync point, keep parsing) is a genuinely
harder, separate problem for a later pass at this file, not assumed
solved by writing the loop hopefully.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import List, Optional, Tuple, Union

from dsl_lexer_v1 import Token
from dsl_diagnostics_v1 import CompileDiagnostic, CompileError, SourceSpan

FieldValue = Union[str, List[str], int]


@dataclass
class FieldNode:
    key: str
    value: FieldValue
    span: SourceSpan


@dataclass
class PlaceNode:
    name: str
    tile_name: str
    row: int
    col: int
    fields: List[FieldNode]
    span: SourceSpan


@dataclass
class ProgramNode:
    name: str
    statements: List[PlaceNode] = dc_field(default_factory=list)
    span: Optional[SourceSpan] = None


def _parse_number(text: str) -> int:
    return int(text, 16) if text.lower().startswith("0x") else int(text)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.diagnostics: List[CompileDiagnostic] = []

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        t = self.tokens[self.pos]
        if t.kind != "EOF":
            self.pos += 1
        return t

    def _span_of(self, t: Token) -> SourceSpan:
        return (t.line, t.col, t.line, t.col + max(1, len(t.value)))

    def _expect(self, kind: str, what: str) -> Token:
        t = self._peek()
        if t.kind != kind:
            raise CompileError(CompileDiagnostic(
                severity="error", stage="parse", what=what,
                problem=f"expected {kind}, found {t.kind} {t.value!r}",
                why=f"the grammar at this point requires a {kind.lower()}",
                span=self._span_of(t),
            ))
        return self._advance()

    def _expect_keyword(self, word: str, what: str) -> Token:
        t = self._peek()
        if t.kind != "KEYWORD" or t.value != word:
            raise CompileError(CompileDiagnostic(
                severity="error", stage="parse", what=what,
                problem=f"expected keyword {word!r}, found {t.kind} {t.value!r}",
                why=f"the grammar at this point requires the keyword {word!r}",
                span=self._span_of(t),
            ))
        return self._advance()

    def parse_program(self) -> Optional[ProgramNode]:
        try:
            start = self._peek()
            self._expect_keyword("program", "parsing a program declaration")
            name_tok = self._expect("IDENT", "reading the program's name")
            self._expect("LBRACE", "expecting '{' to open the program body")
            statements = []
            while self._peek().kind not in ("RBRACE", "EOF"):
                statements.append(self.parse_place())
            end = self._expect("RBRACE", "expecting '}' to close the program body")
            return ProgramNode(name=name_tok.value, statements=statements,
                                span=(start.line, start.col, end.line, end.col))
        except CompileError as e:
            self.diagnostics.append(e.diagnostic)
            return None

    def parse_place(self) -> PlaceNode:
        start = self._expect_keyword("place", "parsing a place statement")
        name_tok = self._expect("IDENT", "reading the placement's local name")
        self._expect_keyword("as", "expecting 'as' after the placement's local name")
        tile_tok = self._expect("IDENT", "reading the tile name")
        self._expect_keyword("at", "expecting 'at' before the placement's position")
        self._expect("LPAREN", "expecting '(' to open the position")
        row_tok = self._expect("NUMBER", "reading the row coordinate")
        self._expect("COMMA", "expecting ',' between row and column")
        col_tok = self._expect("NUMBER", "reading the column coordinate")
        self._expect("RPAREN", "expecting ')' to close the position")
        self._expect("LBRACE", "expecting '{' to open the placement's fields")
        fields = []
        while self._peek().kind not in ("RBRACE", "EOF"):
            fields.append(self.parse_field())
        end = self._expect("RBRACE", "expecting '}' to close the placement's fields")
        return PlaceNode(
            name=name_tok.value, tile_name=tile_tok.value,
            row=_parse_number(row_tok.value), col=_parse_number(col_tok.value),
            fields=fields, span=(start.line, start.col, end.line, end.col),
        )

    def parse_field(self) -> FieldNode:
        key_tok = self._expect("IDENT", "reading a field name")
        self._expect("COLON", "expecting ':' after the field name")
        value, end_tok = self.parse_value()
        return FieldNode(key=key_tok.value, value=value,
                          span=(key_tok.line, key_tok.col, end_tok.line, end_tok.col))

    def parse_value(self) -> Tuple[FieldValue, Token]:
        t = self._peek()
        if t.kind == "LBRACKET":
            self._advance()
            items: List[str] = []
            while self._peek().kind != "RBRACKET":
                item_tok = self._expect("IDENT", "reading an item in a direction list")
                items.append(item_tok.value)
                if self._peek().kind == "COMMA":
                    self._advance()
            end_tok = self._expect("RBRACKET", "expecting ']' to close the direction list")
            return items, end_tok
        if t.kind == "NUMBER":
            self._advance()
            return _parse_number(t.value), t
        if t.kind == "IDENT":
            self._advance()
            return t.value, t
        raise CompileError(CompileDiagnostic(
            severity="error", stage="parse", what="reading a field's value",
            problem=f"expected a direction, a number, or a [list], found {t.kind} {t.value!r}",
            why="a field value is either a bare direction/identifier, a plain or "
                "0x-prefixed number, or a bracketed list of directions",
            span=self._span_of(t),
        ))


def parse_source(tokens: List[Token]) -> Tuple[Optional[ProgramNode], List[CompileDiagnostic]]:
    p = Parser(tokens)
    node = p.parse_program()
    return node, p.diagnostics
