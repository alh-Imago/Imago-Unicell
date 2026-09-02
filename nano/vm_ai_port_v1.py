"""
vm_ai_port_v1.py — a real, defined port for connecting an AI (or any
other external driver -- a script, a test, a human at a REPL) directly
to the Unicell-S VM (`points.md #216` item 6). Alan's own explicit
choice: smaller than item 3 (dual CPU/GPU execution), do this one
first.

WHY THIS SHAPE, not literally embedding a language model: `#216` item
6's own real precedent, `companion.py`'s `attach_ai()`, loads an actual
HuggingFace model as a reasoning layer for the OLD Shore/Ward system.
That pattern doesn't transfer directly here -- it needs `torch`/
`transformers`, and more importantly it conflates two genuinely
separate concerns: (1) a clean, structured INTERFACE an AI (or anything
else) can drive the VM through, and (2) actually attaching a specific
reasoning model to make decisions through that interface. This file is
(1) -- the port itself, matching `current/PLAN.md`'s own standing
requirement ("Composer, the compiler, the library keeper, and the VM
should each be designed with a genuine AI-interaction port from the
start, not bolted on after"). (2) -- actually wiring a real model in --
is a separate, later, optional layer that can sit on TOP of this port
without this file needing to change at all.

WHAT MAKES THIS THE RIGHT FIRST SLICE: it's the first thing this
session that ties the WHOLE pipeline together into one clean object --
compile (DSL or Python-AST) -> real ICM v3 -> real running VM -> real
JSON introspection -- all through one entry point, rather than an AI
(or a human) needing to know how to wire `dsl_compiler_v1.py`,
`icm_v3.py`, `unicell_super_automaton_v1.py`, and `vm_introspection_
v1.py` together by hand. This is genuinely the "space to try things out
in" this session's own earlier conversation pointed at -- a session
object that goes from source text to inspectable, running state in one
call.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dsl_compiler_v1 import compile_source
from python_ast_frontend_v1 import compile_python_source
from unicell_super_automaton_v1 import SuperGrid
from dsl_diagnostics_v1 import CompileDiagnostic
import vm_introspection_v1 as vi
import icm_v3 as v3
import vm_mirror_v1


class CompileFailure(Exception):
    """Raised when a `from_dsl()`/`from_python()` call's source doesn't
    compile -- carries the real `CompileDiagnostic`s, not just a
    string, so an AI driving this port gets the same structured
    what/problem/why/suggestion information a human would (`#343`)."""

    def __init__(self, diagnostics: List[CompileDiagnostic]):
        self.diagnostics = diagnostics
        errors = [d for d in diagnostics if d.severity == "error"]
        super().__init__(f"compile failed: {len(errors)} error(s)")

    def format(self, source_lines: Optional[List[str]] = None) -> str:
        return "\n\n".join(d.format(source_lines) for d in self.diagnostics)


class VMSession:
    """One running Unicell-S VM, plus the ONE clean surface for driving
    and inspecting it -- compile a program, run it, watch it, poke it,
    read it back out. Every method here either wraps something already
    real and tested this session, or is a thin, obvious composition of
    two of them -- no new VM semantics are introduced by this file."""

    def __init__(self, grid: Optional[SuperGrid] = None):
        self.grid: SuperGrid = grid if grid is not None else SuperGrid([])
        #: diagnostics from whatever compile produced this session's
        #: program, if any -- warnings can be real even on a successful
        #: compile (e.g. #350's naming-hygiene lint), kept here so an AI
        #: driving this port can see them without re-compiling.
        self.diagnostics: List[CompileDiagnostic] = []
        #: points.md #601: set only by from_man() -- None means this is
        #: a real, honest "free mode" session with no claimed card
        #: correspondence. A simulated Walker (or anything else needing
        #: to know "is this session mirroring a real card") should
        #: check this rather than assume.
        self.mirror_bounds: Optional["vm_mirror_v1.MirrorBounds"] = None

    # ── Construction ────────────────────────────────────────────────

    @classmethod
    def from_dsl(cls, source: str) -> "VMSession":
        """Compile a Unicell-S DSL program and load it into a fresh,
        ready-to-run session. Raises `CompileFailure` (carrying the
        real diagnostics) on any error -- never returns a session for a
        program that didn't actually compile."""
        icm, diagnostics = compile_source(source)
        if icm is None:
            raise CompileFailure(diagnostics)
        session = cls(SuperGrid.from_icm(icm))
        session.diagnostics = diagnostics
        return session

    @classmethod
    def from_python(cls, source: str) -> "VMSession":
        """Same as `from_dsl()`, but for the real Python-AST frontend
        (`#348`) -- a declarative Python subset, not general Python."""
        icm, diagnostics = compile_python_source(source)
        if icm is None:
            raise CompileFailure(diagnostics)
        session = cls(SuperGrid.from_icm(icm))
        session.diagnostics = diagnostics
        return session

    @classmethod
    def from_icm_file(cls, path: str) -> "VMSession":
        """Load a previously-compiled, saved `.icm` file directly --
        no recompilation needed."""
        return cls(SuperGrid.from_icm(v3.IcmV3File.load(path)))

    @classmethod
    def from_man(cls, man_path: str, cells: int, *, dsl: Optional[str] = None,
                 python: Optional[str] = None, icm_path: Optional[str] = None) -> "VMSession":
        """points.md #601: the real MAN -> mirrored-VM construction --
        the prerequisite a simulated Walker needs to have an honest
        target. Exactly one of `dsl=`/`python=`/`icm_path=` must be
        given (the program to load); it's compiled/loaded the same way
        `from_dsl()`/`from_python()`/`from_icm_file()` already do -- no
        new compile path, no duplicated logic.

        Real, direct difference from those: every placed cell is
        checked against `vm_mirror_v1.load_mirror_bounds()` -- the same
        real row-major layout `project_assemble_v1.py` would use for an
        ACTUAL Quartus build of `cells` cells on this MAN file's own
        card. Raises `vm_mirror_v1.MirrorFitError` (not a silent
        accept) if any real placed cell falls outside that layout or
        collides with another. On success, `session.mirror_bounds` is
        set, so a caller can see the real, honest card context this
        session was actually built against."""
        given = [x for x in (dsl, python, icm_path) if x is not None]
        if len(given) != 1:
            raise ValueError("from_man() needs exactly one of dsl=/python=/icm_path=")

        bounds = vm_mirror_v1.load_mirror_bounds(man_path, cells)

        diagnostics: List[CompileDiagnostic] = []
        if dsl is not None:
            icm, diagnostics = compile_source(dsl)
            if icm is None:
                raise CompileFailure(diagnostics)
        elif python is not None:
            icm, diagnostics = compile_python_source(python)
            if icm is None:
                raise CompileFailure(diagnostics)
        else:
            icm = v3.IcmV3File.load(icm_path)

        problems = vm_mirror_v1.check_records_fit(icm.records, bounds)
        if problems:
            raise vm_mirror_v1.MirrorFitError(problems)

        session = cls(SuperGrid.from_icm(icm))
        session.diagnostics = diagnostics
        session.mirror_bounds = bounds
        return session

    # ── Driving the VM ──────────────────────────────────────────────

    def inject(self, row: int, col: int, value: int) -> None:
        self.grid.inject(row, col, value)

    def deliver(self, row: int, col: int, arrivals: Dict[int, int],
                injected: Optional[int] = None) -> Tuple[bool, Optional[Tuple[int, int]]]:
        """Direct, low-level delivery to one cell -- the same mechanism
        this session's own tests use to drive a specific directional
        input precisely (e.g. an accumulator's `inc`/`dec` from an
        external source with no upstream cell of its own)."""
        if (row, col) not in self.grid.cells:
            raise KeyError(f"no cell placed at ({row},{col}) -- known positions: "
                            f"{sorted(self.grid.cells.keys())}")
        return self.grid.cells[(row, col)].deliver(arrivals, injected)

    def tick(self, n: int = 1) -> Dict[Tuple[int, int], bool]:
        """Advance the VM `n` ticks. Returns the LAST tick's active-cell
        map (which cells did something that tick) -- matches `SuperGrid.
        tick()`'s own return shape for a single call."""
        active: Dict[Tuple[int, int], bool] = {}
        for _ in range(n):
            active = self.grid.tick()
        return active

    def run_to_quiescence(self, max_ticks: int = 10000) -> int:
        """Matches `SuperGrid.run_to_quiescence()` directly -- raises
        `TimeoutError` honestly on a grid containing a continuously-live
        core with a real downstream target, exactly as that method
        already does (`#337`'s own stated behavior, not changed here)."""
        return self.grid.run_to_quiescence(max_ticks=max_ticks)

    # ── Reading state back out ─────────────────────────────────────

    def describe(self) -> Dict[str, Any]:
        """Full grid state, as JSON-ready plain dicts (`#354`)."""
        return vi.grid_to_dict(self.grid)

    def describe_cell(self, row: int, col: int) -> Dict[str, Any]:
        return vi.cell_at(self.grid, row, col)

    def diagnostics_text(self, source: Optional[str] = None) -> str:
        """Human/AI-readable rendering of whatever diagnostics came out
        of the compile that built this session (warnings included, even
        on an otherwise-successful compile)."""
        lines = source.splitlines() if source else None
        return "\n\n".join(d.format(lines) for d in self.diagnostics)
