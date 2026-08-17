"""
dsl_parser_v1.py — recursive descent parser for the Unicell-S DSL.
Covers this slice's grammar, per the design note's own "suggested
first, low-risk step," extended with `define`/`expose` (`points.md
#346`): a `program { place ... }` with `place` AND `define` statements.

```
program     := "program" IDENT "{" stmt* "}"
stmt        := place_stmt | define_stmt
place_stmt  := "place" IDENT "as" IDENT "at" "(" NUMBER "," NUMBER ")" "{" field* "}"
define_stmt := "define" IDENT "{" place_stmt* expose_stmt* "}"
expose_stmt := "expose" IDENT "->" IDENT "." IDENT
field       := IDENT ":" value
value       := IDENT | NUMBER | "[" IDENT ("," IDENT)* "]"
```

Builds `program_ir_v1.py`'s shared `ProgramIR`/`PlaceIR`/`DefineIR`/
`ExposeIR`/`FieldIR` directly -- NOT a DSL-private AST -- so the backend
has no idea this program came from the DSL specifically, and a future
Python/C/Rust frontend can target the exact same IR without going
through this file at all. Every IR node still keeps the source span of
its own defining DSL tokens.

`define`'s own inner `place` statements reuse `parse_place()` UNCHANGED
-- the grammar is identical, only the MEANING of `row`/`col` differs
(a relative offset from the defined tile's own anchor, not an absolute
grid position). This is a deliberate reuse, not an oversight: keeping
one production for both avoids two parsers that could quietly drift.

REAL LIMITATION, HONESTLY SCOPED (previously "no recovery at all" --
now real, statement-level panic-mode recovery, per `points.md #372`):
on a syntax error inside one `place`/`define`/`expose` statement, that
WHOLE statement is abandoned and the parser skips forward to the next
plausible statement boundary (the next `place`/`define`/`expose`
keyword, or the enclosing `}`), rather than stopping at the first
error. This means `compile_source()` can report EVERY independent
syntax error in a file in one pass, not just the first. The recovery
granularity is deliberately coarse -- a broken statement is abandoned
WHOLESALE, not partially salvaged token-by-token -- a standard,
real compiler technique (not attempting mid-statement resumption, which
risks silently producing a corrupted AST). `place`/`define`/`expose`
are real, distinct `KEYWORD` tokens (never `IDENT`, see the lexer's own
`KEYWORDS` set), so synchronizing on them can never be confused with a
legitimate field value.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union

from dsl_lexer_v1 import Token
from dsl_diagnostics_v1 import CompileDiagnostic, CompileError, SourceSpan
from program_ir_v1 import ProgramIR, PlaceIR, FieldIR, FieldValue, DefineIR, ExposeIR


def _parse_number(text: str) -> int:
    return int(text, 16) if text.lower().startswith("0x") else int(text)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.diagnostics: List[CompileDiagnostic] = []
        self.depth = 0   # real, continuously-maintained brace-nesting
                          # depth -- incremented/decremented by every
                          # successful LBRACE/RBRACE consumption anywhere
                          # in the file, not reset per synchronize() call.
                          # This is what makes recovery actually correct:
                          # synchronize() needs to know the REAL current
                          # nesting level to tell "a broken statement's
                          # own still-open inner brace" apart from "the
                          # enclosing block's own real closing brace" --
                          # a naive per-call depth=0 baseline gets this
                          # wrong the moment an error occurs while a
                          # statement's own field-list brace is open.

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        t = self.tokens[self.pos]
        if t.kind != "EOF":
            self.pos += 1
        return t

    def _span_of(self, t: Token) -> SourceSpan:
        return (t.line, t.col, t.line, t.col + max(1, len(t.value)))

    def _synchronize(self, resync_keywords: Tuple[str, ...], target_depth: int) -> None:
        """Panic-mode recovery: skip tokens until back at
        `target_depth` (the real brace-nesting level statements of this
        kind live at) AND sitting on either a resync keyword or that
        block's own genuine closing brace. Tracks braces encountered
        while skipping (so a broken statement's own still-open field
        list gets fully consumed, not mistaken for the enclosing
        block's end) -- this is the piece that makes recovery safe
        past a MID-STATEMENT error, not just an error right at a
        statement's own opening keyword. Never leaves `pos` unchanged
        across a full parse-attempt + synchronize cycle (every
        `_expect*` raises WITHOUT advancing, so the bad token is still
        there for this loop's first real check; every non-matching
        token this loop then sees genuinely gets consumed) -- no
        infinite-loop risk."""
        while True:
            t = self._peek()
            if t.kind == "EOF":
                return
            if t.kind == "LBRACE":
                self.depth += 1
                self._advance()
                continue
            if t.kind == "RBRACE":
                if self.depth == target_depth:
                    return   # the enclosing block's OWN real closing brace
                self.depth -= 1
                self._advance()
                continue
            if self.depth == target_depth and t.kind == "KEYWORD" and t.value in resync_keywords:
                return
            self._advance()

    def _expect(self, kind: str, what: str) -> Token:
        t = self._peek()
        if t.kind != kind:
            raise CompileError(CompileDiagnostic(
                severity="error", stage="parse", what=what,
                problem=f"expected {kind}, found {t.kind} {t.value!r}",
                why=f"the grammar at this point requires a {kind.lower()}",
                span=self._span_of(t),
            ))
        if kind == "LBRACE":
            self.depth += 1
        elif kind == "RBRACE":
            self.depth -= 1
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

    def parse_program(self) -> Optional[ProgramIR]:
        try:
            start = self._peek()
            self._expect_keyword("program", "parsing a program declaration")
            name_tok = self._expect("IDENT", "reading the program's name")
            self._expect("LBRACE", "expecting '{' to open the program body")
        except CompileError as e:
            # the outer header itself is unrecoverable -- there's no
            # sane statement boundary to resync to without even knowing
            # the program's own name/opening brace succeeded.
            self.diagnostics.append(e.diagnostic)
            return None

        body_depth = self.depth   # 1, right after the program's own '{'
        statements: List[Union[PlaceIR, DefineIR]] = []
        while self._peek().kind not in ("RBRACE", "EOF"):
            try:
                statements.append(self.parse_statement())
            except CompileError as e:
                self.diagnostics.append(e.diagnostic)
                self._synchronize(("place", "define"), body_depth)

        if self._peek().kind == "EOF":
            # ran off the end without ever finding the closing brace --
            # still worth a real diagnostic, not a silent None
            self.diagnostics.append(CompileDiagnostic(
                severity="error", stage="parse",
                what="parsing the program body",
                problem="reached end of file without a closing '}'",
                why="every 'program NAME { ... }' body must be closed",
                span=self._span_of(self._peek()),
            ))
            return None

        end = self._expect("RBRACE", "expecting '}' to close the program body")
        return ProgramIR(name=name_tok.value, statements=statements,
                          span=(start.line, start.col, end.line, end.col))

    def parse_statement(self) -> Union[PlaceIR, DefineIR]:
        t = self._peek()
        if t.kind == "KEYWORD" and t.value == "define":
            return self.parse_define()
        return self.parse_place()

    def parse_define(self) -> DefineIR:
        start = self._expect_keyword("define", "parsing a define statement")
        name_tok = self._expect("IDENT", "reading the defined tile's name")
        self._expect("LBRACE", "expecting '{' to open the definition's body")
        body_depth = self.depth   # right after define's own '{'
        subcells: List[PlaceIR] = []
        exposes: List[ExposeIR] = []
        while self._peek().kind not in ("RBRACE", "EOF"):
            try:
                t = self._peek()
                if t.kind == "KEYWORD" and t.value == "expose":
                    exposes.append(self.parse_expose())
                else:
                    subcells.append(self.parse_place())
            except CompileError as e:
                self.diagnostics.append(e.diagnostic)
                self._synchronize(("place", "expose"), body_depth)
        end = self._expect("RBRACE", "expecting '}' to close the definition's body")
        return DefineIR(name=name_tok.value, subcells=subcells, exposes=exposes,
                         span=(start.line, start.col, end.line, end.col))

    def parse_expose(self) -> ExposeIR:
        start = self._expect_keyword("expose", "parsing an expose statement")
        external_tok = self._expect("IDENT", "reading the exposed port's external name")
        arrow_tok = self._peek()
        if arrow_tok.kind != "ARROW":
            raise CompileError(CompileDiagnostic(
                severity="error", stage="parse",
                what="parsing an expose statement",
                problem=f"expected '->', found {arrow_tok.kind} {arrow_tok.value!r}",
                why="an expose statement has the form 'expose NAME -> subcell.port'",
                span=self._span_of(arrow_tok),
            ))
        self._advance()
        ref_tok = self._expect("IDENT", "reading the 'subcell.port' reference")
        if "." not in ref_tok.value:
            raise CompileError(CompileDiagnostic(
                severity="error", stage="parse",
                what="parsing an expose statement",
                problem=f"expected 'subcell.port' (with a dot), found {ref_tok.value!r}",
                why="expose has to name a specific sub-cell's specific port, "
                    "written as 'subcell_name.port_name'",
                span=self._span_of(ref_tok),
            ))
        subcell_name, _, port_name = ref_tok.value.partition(".")
        return ExposeIR(external_name=external_tok.value, subcell_name=subcell_name,
                         subcell_port=port_name,
                         span=(start.line, start.col, ref_tok.line, ref_tok.col + len(ref_tok.value)))

    def parse_place(self) -> PlaceIR:
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
        return PlaceIR(
            name=name_tok.value, tile_name=tile_tok.value,
            row=_parse_number(row_tok.value), col=_parse_number(col_tok.value),
            fields=fields, span=(start.line, start.col, end.line, end.col),
        )

    def parse_field(self) -> FieldIR:
        key_tok = self._expect("IDENT", "reading a field name")
        self._expect("COLON", "expecting ':' after the field name")
        value, end_tok = self.parse_value()
        return FieldIR(key=key_tok.value, value=value,
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


def parse_source(tokens: List[Token]) -> Tuple[Optional[ProgramIR], List[CompileDiagnostic]]:
    p = Parser(tokens)
    node = p.parse_program()
    return node, p.diagnostics

