"""
dsl_lexer_v1.py — hand-written tokenizer for the Unicell-S DSL. No
parser-generator dependency (nothing else in this project pulls one
in; `compiler.py`'s own precedent uses Python's `ast` module because it
parses real Python, which doesn't apply to a brand-new grammar). Every
token carries its own (line, col) so downstream diagnostics can always
point at real source, never "somewhere in your program."

Comments: `#` to end of line, matching the DSL syntax sketch in
`docs/stripped-cell/design-notes/unicell_s_dsl_and_compiler_scope.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from dsl_diagnostics_v1 import CompileDiagnostic

KEYWORDS = {"program", "place", "as", "at", "use", "expose", "define"}

_PUNCT = {
    "{": "LBRACE", "}": "RBRACE", "(": "LPAREN", ")": "RPAREN",
    "[": "LBRACKET", "]": "RBRACKET", ":": "COLON", ",": "COMMA",
}


@dataclass
class Token:
    kind: str      # "IDENT" | "NUMBER" | "KEYWORD" | a name from _PUNCT.values() | "ARROW" | "EOF"
    value: str
    line: int
    col: int


def tokenize(source: str) -> Tuple[List[Token], List[CompileDiagnostic]]:
    """Never raises -- an illegal character is a real, collected lex
    diagnostic, not an exception, matching the "collect every problem"
    discipline this whole pipeline is built around. Lexing continues
    past it (skipping the one bad character) so a source file with two
    unrelated typos gets BOTH reported, not just the first."""
    tokens: List[Token] = []
    diagnostics: List[CompileDiagnostic] = []
    line, col = 1, 1
    i, n = 0, len(source)

    while i < n:
        c = source[i]

        if c == "\n":
            line += 1
            col = 1
            i += 1
            continue
        if c in " \t\r":
            i += 1
            col += 1
            continue
        if c == "#":
            while i < n and source[i] != "\n":
                i += 1
            continue
        if c == "-" and i + 1 < n and source[i + 1] == ">":
            tokens.append(Token("ARROW", "->", line, col))
            i += 2
            col += 2
            continue
        if c in _PUNCT:
            tokens.append(Token(_PUNCT[c], c, line, col))
            i += 1
            col += 1
            continue
        if c.isdigit():
            start, start_col = i, col
            if c == "0" and i + 1 < n and source[i + 1] in "xX":
                i += 2
                col += 2
                while i < n and source[i].isalnum():
                    i += 1
                    col += 1
            else:
                while i < n and source[i].isdigit():
                    i += 1
                    col += 1
            tokens.append(Token("NUMBER", source[start:i], line, start_col))
            continue
        if c.isalpha() or c == "_":
            start, start_col = i, col
            while i < n and (source[i].isalnum() or source[i] in "_."):
                i += 1
                col += 1
            word = source[start:i]
            kind = "KEYWORD" if word in KEYWORDS else "IDENT"
            tokens.append(Token(kind, word, line, start_col))
            continue

        diagnostics.append(CompileDiagnostic(
            severity="error", stage="lex",
            what="reading the program's source text",
            problem=f"unexpected character {c!r}",
            why="identifiers, numbers (plain or 0x-prefixed hex), and the "
                "punctuation { } ( ) [ ] : , -> are the only things a token "
                "can start with in this DSL",
            span=(line, col, line, col + 1),
        ))
        i += 1
        col += 1

    tokens.append(Token("EOF", "", line, col))
    return tokens, diagnostics
