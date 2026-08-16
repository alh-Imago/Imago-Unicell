"""
dsl_diagnostics_v1.py — structured compiler diagnostics for the
Unicell-S DSL, per Alan's own explicit design requirement: not a bare
exception, but something that explains WHAT was being attempted, WHAT
specifically went wrong, WHY that's a real problem, and (where one
genuinely exists) WHAT to try instead. Matches the shape
`docs/stripped-cell/design-notes/unicell_s_dsl_and_compiler_scope.md`
laid out, and the spirit of `cell_format.py`'s own
`check_pipeline_bridges()` -- a pass collects every problem it finds
across the whole input, rather than raising and stopping at the first
one (see `dsl_compiler_v1.py`'s own per-statement loop).

`suggestion` stays genuinely optional -- per the design note's own
"real, honest scope note," not every failure has one good next step
without knowing more about user intent, and fabricating a weak one just
to fill the field would be worse than leaving it empty.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

# (start_line, start_col, end_line, end_col), 1-indexed, matching how
# editors and most compiler diagnostics report position.
SourceSpan = Tuple[int, int, int, int]


@dataclass
class CompileDiagnostic:
    severity: str            # "error" | "warning"
    stage: str                 # "lex" | "parse" | "resolve" | "place" | "emit"
    what: str                   # what was being attempted, in the user's own terms
    problem: str                  # what specifically went wrong
    why: str                        # why it's a real problem, not an arbitrary rule
    suggestion: Optional[str] = None
    span: Optional[SourceSpan] = None

    def format(self, source_lines: Optional[List[str]] = None) -> str:
        loc = f"{self.span[0]}:{self.span[1]}" if self.span else "?"
        lines = [f"{self.severity.upper()} [{self.stage}] at {loc}: {self.what}",
                 f"  problem: {self.problem}",
                 f"  why: {self.why}"]
        if self.suggestion:
            lines.append(f"  try: {self.suggestion}")
        if self.span and source_lines:
            ln = self.span[0]
            if 1 <= ln <= len(source_lines):
                lines.append(f"  > {source_lines[ln - 1]}")
                lines.append("  > " + " " * max(0, self.span[1] - 1) + "^")
        return "\n".join(lines)


class CompileError(Exception):
    """Internal control-flow only -- carries ONE `CompileDiagnostic`,
    used within a single pass to short-circuit when a later step in
    THAT pass would be meaningless without this one (e.g. can't keep
    parsing a place statement's fields once its own opening brace never
    showed up). The pass that raises this catches it and appends the
    diagnostic to its own running list; it should never leak out of
    `compile_source()` itself."""

    def __init__(self, diagnostic: CompileDiagnostic):
        self.diagnostic = diagnostic
        super().__init__(diagnostic.problem)
