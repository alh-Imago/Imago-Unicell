"""
workbench_v1.py — the new Unicell-S workbench. A thin HTTP layer
directly over `vm_ai_port_v1.VMSession` (`points.md #362`/`#363`),
built per `docs/stripped-cell/design-notes/workbench_scope.md`'s own
real audit of the old `workbench.py`: everything address/`gate_state`-
keyed there is dead under the new system shape; the replacement DATA
LAYER already exists (`VMSession`, `#359`) and is reused here
unchanged, not reimplemented.

TWO REAL LAYERS, DELIBERATELY SEPARATE: `WorkbenchController` holds the
current session, its regions, and implements every real operation as a
plain Python method returning a JSON-ready dict -- it has NO knowledge
of HTTP at all, so it's directly, fully testable without a live socket.
`WorkbenchHandler` is a thin `http.server` request handler dispatching
onto a `WorkbenchController` instance -- the reusable part of the old
file's own shape (`http.server`/threading is genuine, addressing-
agnostic infrastructure, kept as the same real precedent, not
reinvented).

REGIONS (`#363`, the real new capability closing this milestone): the
old workbench's own "region" concept tracked SETS OF ADDRESSES -- dead
under cardinal wiring, no address to track. The real equivalent here is
a NAMED set of grid POSITIONS: `load_region()` compiles a program and
hands its shape to `loader_v1.bind_shape()` (`#375`, the real loader/
binder stage) -- MANUAL placement (`row_offset`/`col_offset` both
given) shifts every record by that exact offset; AUTO placement (both
omitted) finds a real, collision-free spot itself via a first-fit
search. Either way, the shape is checked for real collisions before
being added to the SAME shared grid as any other already-loaded region
(reusing the exact "cell already occupied" reasoning `#346`'s own DSL
compiler already established for a single program, applied here across
MULTIPLE independently-loaded ones). `clear_region()` removes exactly
that region's own cells, and cleans any `_pending` events that
referenced them, WITHOUT touching any other region sharing the same
grid -- confirmed by real tests running two regions side by side,
clearing one, and checking the other keeps computing correctly.

API, row/col-keyed throughout, never an address anywhere:
    GET  /               -- serves the HTML/JS page
    GET  /state           -- VMSession.describe(), as JSON
    GET  /demos             -- the real demo library, name+description only
    GET  /regions             -- every currently-loaded region and its cells
    POST /compile               -- {"source", "language": "dsl"|"python"} --
                                    REPLACES the whole session (single program)
    POST /load_demo               -- {"name"} -- loads a demo via /compile
    POST /load_region                -- {"name", "source", "language",
                                          "row_offset", "col_offset",
                                          "dsp_columns"} -- ADDS a program
                                          to the shared grid as a named
                                          region, alongside any others.
                                          Omit row_offset/col_offset (both)
                                          for real auto-placement (#375),
                                          plus dsp_columns for real DSP-
                                          column-aware auto-placement (#377).
    POST /clear_region                 -- {"name"}
    POST /set_target                     -- {"man_path", "cells", "shell"} --
                                             points.md #605/#606: establishes
                                             a real MAN-file (+ optional real
                                             shell) target (vm_mirror_v1.py/
                                             shell_compat_v1.py) -- the live
                                             grid becomes a genuine, checked
                                             reflection of that real card/
                                             cell-count/shell config, persisting
                                             across compile()/load_region()
                                             calls until changed or cleared.
    POST /clear_target                     -- returns to free mode (no real
                                               card correspondence claimed)
    GET  /target                             -- the current real target, if any
    GET  /shells                               -- points.md #606: the real,
                                                   RTL-derived shell/core
                                                   compatibility matrix
                                                   (shell_compat_v1.py)
    POST /step                           -- {"n": 1}
    POST /deliver                          -- {"row", "col", "direction", "value", "injected"}
    POST /inject                             -- {"row", "col", "value"}
"""

from __future__ import annotations

import http.server
import json
import os
import sys
import threading
import webbrowser
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vm_ai_port_v1 import VMSession, CompileFailure
from dsl_diagnostics_v1 import CompileDiagnostic
from dsl_compiler_v1 import compile_source
from python_ast_frontend_v1 import compile_python_source
from unicell_super_automaton_v1 import SuperGrid
from unicell_automaton_v1 import N, S, E, W
from loader_v1 import bind_shape
from host_registry_v1 import HostResourceRegistry
import vm_mirror_v1
import shell_compat_v1
import connection_check_v1

_DIRS = {"n": N, "s": S, "e": E, "w": W}

# ── The real demo library (points.md #363) -- every one a working,
# already-proven Unicell-S program, not lifted from the old opcode-based
# demos (which don't port -- see workbench_scope.md's own audit). ──────
DEMOS: Dict[str, Dict[str, str]] = {
    "simple_ram": {
        "description": "A single fixed-value cell, offering a constant east.",
        "language": "dsl",
        "source": (
            "program simple_ram {\n"
            "    place r1 as ram_constant at (0, 0) {\n"
            "        out: e\n"
            "        init_data: 0xCAFEBEEF\n"
            "    }\n"
            "}\n"
        ),
    },
    "adder_pair": {
        "description": "Two-input adder: in_a + in_b -> out.",
        "language": "dsl",
        "source": (
            "program adder_pair {\n"
            "    place a1 as adder at (0, 0) {\n"
            "        in_a: n\n"
            "        in_b: w\n"
            "        out: e\n"
            "    }\n"
            "}\n"
        ),
    },
    "sentinel": {
        "description": "The proven accumulator->comparator->latch monitor "
                        "(real Quartus data: 78 ALM, 272.26 MHz).",
        "language": "dsl",
        "source": (
            "program my_sentinel {\n"
            "    place s1 as sentinel at (0, 0) {\n"
            "        inc: n\n"
            "        dec: s\n"
            "        clear: s\n"
            "        out: e\n"
            "        cmp.threshold: 8\n"
            "    }\n"
            "}\n"
        ),
    },
    "dual_threshold_monitor": {
        "description": "One accumulator fanning out to independent low/high "
                        "threshold alarms.",
        "language": "dsl",
        "source": (
            "program dual {\n"
            "    place m as dual_threshold_monitor at (0, 0) {\n"
            "        inc: n\n"
            "        dec: s\n"
            "        clear_low: s\n"
            "        out_low: w\n"
            "        clear_high: n\n"
            "        out_high: e\n"
            "        cmp_low.threshold: 3\n"
            "        cmp_high.threshold: 10\n"
            "    }\n"
            "}\n"
        ),
    },
    "twin_sentinel": {
        "description": "Two wholly independent nested sentinel instances -- "
                        "a worked example of composed-tile nesting.",
        "language": "dsl",
        "source": (
            "program twins {\n"
            "    place t as twin_sentinel at (0, 0) {\n"
            "        s1_inc: n\n"
            "        s1_dec: s\n"
            "        s1_clear: s\n"
            "        s1_out: e\n"
            "        s2_inc: n\n"
            "        s2_dec: s\n"
            "        s2_clear: s\n"
            "        s2_out: e\n"
            "        s1.cmp.threshold: 8\n"
            "        s2.cmp.threshold: 4\n"
            "    }\n"
            "}\n"
        ),
    },
    "python_ast_example": {
        "description": "The same sentinel, authored via the real Python-AST "
                        "frontend instead of the DSL.",
        "language": "python",
        "source": (
            "def my_sentinel_program():\n"
            "    with define(\"my_sentinel\"):\n"
            "        place(\"acc\", \"accumulator\", (0, 0), out=\"e\", step_amount=1)\n"
            "        place(\"cmp\", \"comparator\", (0, 1), **{\"in\": \"w\", \"out\": \"e\"})\n"
            "        place(\"lat\", \"latch\", (0, 2), set=\"w\")\n"
            "        expose(\"inc\", \"acc.inc\")\n"
            "        expose(\"dec\", \"acc.dec\")\n"
            "        expose(\"clear\", \"lat.clear\")\n"
            "        expose(\"out\", \"lat.out\")\n"
            "\n"
            "    place(\"s1\", \"my_sentinel\", (0, 0), inc=\"n\", dec=\"s\", clear=\"s\",\n"
            "          out=\"e\", **{\"cmp.threshold\": 8})\n"
        ),
    },
}


def _diag_to_dict(d: CompileDiagnostic) -> Dict[str, Any]:
    return {
        "severity": d.severity, "stage": d.stage, "what": d.what,
        "problem": d.problem, "why": d.why, "suggestion": d.suggestion,
        "span": list(d.span) if d.span else None,
    }


class WorkbenchController:
    """Holds the current session, its regions, and every real API
    operation -- zero HTTP knowledge, directly testable.

    Two placement modes, both real: `compile()` REPLACES the whole
    session with a single program (the simple case, unchanged from
    `#362`). `load_region()` ADDS a program to the SAME shared grid as
    a named region, alongside any others already loaded -- the real new
    capability this entry closes the workbench milestone with."""

    def __init__(self):
        self.session: Optional[VMSession] = None
        self.regions: Dict[str, List[Tuple[int, int]]] = {}
        # the real, standalone host resource registry (#400) -- kept in
        # sync alongside self.regions rather than replacing it outright,
        # a deliberate, safe choice: self.regions is the already-tested
        # code path every existing test relies on; the registry is the
        # real, separately-queryable authority Alan asked for, added
        # without risking a regression in what already works.
        self.registry = HostResourceRegistry()
        # points.md #606: real shell/version target, alongside the MAN
        # target (#605) -- "the VM is a reflection of the supplied
        # file" extends naturally to include which real shell a real
        # assembler invocation would use, not just card/cell-count.
        self.shell_version: Optional[str] = None
        self.shell_path: Optional[str] = None
        # points.md #606: raw core_config kept alongside self.regions,
        # keyed by real grid position -- needed because SuperCell
        # unpacks core_config into individual typed attributes on
        # load and doesn't retain the original dict, but the real
        # cross-cell connection check (connection_check_v1.py) needs
        # the original per-core field names to work from.
        self._records: Dict[Tuple[int, int], object] = {}

    # ── real target reflection (points.md #605) ────────────────────
    #
    # "the VM is a reflection of the supplied file from the assembler,
    # and it's this the workbench connects to" -- Alan's own direct
    # framing. Establishes a real MAN-file target (matching what
    # tools/project_assemble_v1.py would actually build for `cells`
    # cells on that card, via vm_mirror_v1.py/#601) that PERSISTS
    # across compile()/load_region() calls until changed or cleared --
    # the workbench's live grid becomes a genuine, checked reflection
    # of that real config, not an arbitrary unconstrained shape.

    def set_target(self, man_path: str, cells: int, shell: Optional[str] = None) -> Dict[str, Any]:
        """Real, honest reset: establishes the target and starts a
        fresh, empty, mirror-bound session -- same "clean starting
        point" semantics `compile()` already has for a single program.
        Any program/region loaded from here on (via `compile()` or
        `load_region()`) is checked against this real card layout, and
        (points.md #606) against `shell`'s own real core repertoire if
        given -- "the VM is a reflection of the supplied file from the
        assembler" extends to the shell, not just the card/cell-count."""
        try:
            bounds = vm_mirror_v1.load_mirror_bounds(man_path, cells)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        shell_path = None
        if shell:
            versions = shell_compat_v1.discover_shell_versions()
            if shell not in versions:
                return {"ok": False, "error": f"unknown shell {shell!r} -- real shells found on disk: {sorted(versions)}"}
            shell_path = versions[shell]
        self.session = VMSession(SuperGrid([]))
        self.session.mirror_bounds = bounds
        self.shell_version = shell
        self.shell_path = shell_path
        self.regions = {}
        self._records = {}
        self.registry = HostResourceRegistry()
        return {
            "ok": True,
            "target": {"card_id": bounds.card_id, "man_path": bounds.man_path,
                       "cells": bounds.cells, "rows": bounds.rows, "cols": bounds.cols,
                       "shell": shell, "shell_cores": sorted(shell_compat_v1.supported_cores(shell_path)) if shell_path else None},
            "state": self.session.describe(),
        }

    def clear_target(self) -> Dict[str, Any]:
        """Real, explicit return to free mode -- no card or shell
        correspondence claimed, matching every pre-#605/#606 session's
        own real behavior."""
        self.session = VMSession(SuperGrid([]))
        self.shell_version = None
        self.shell_path = None
        self.regions = {}
        self._records = {}
        self.registry = HostResourceRegistry()
        return {"ok": True, "state": self.session.describe()}

    def list_shells(self) -> Dict[str, Any]:
        """points.md #606: the real, RTL-derived compatibility matrix
        (shell_compat_v1.py) -- lets the UI populate a real, current
        shell-version list rather than a hardcoded one that could
        silently drift from what's actually on disk."""
        return {"ok": True, "shells": shell_compat_v1.compatibility_matrix()}

    def current_target(self) -> Dict[str, Any]:
        bounds = self.session.mirror_bounds if self.session is not None else None
        if bounds is None:
            return {"ok": True, "target": None}
        return {"ok": True, "target": {"card_id": bounds.card_id, "man_path": bounds.man_path,
                                        "cells": bounds.cells, "rows": bounds.rows, "cols": bounds.cols,
                                        "shell": self.shell_version,
                                        "shell_cores": sorted(shell_compat_v1.supported_cores(self.shell_path)) if self.shell_path else None}}

    def _check_shell_and_connections(self, new_records) -> Tuple[Optional[str], List[str]]:
        """points.md #606: real, two-tier check run before ANY new
        records are written into the grid.

        TIER 1, hard: if a real shell target is set, every new record's
        own core type must actually be instantiated in that shell's
        real RTL (shell_compat_v1.py) -- a real hardware impossibility,
        not a style preference, so this returns a real rejection
        string (not None) on any failure, same "reject before
        committing" tier as vm_mirror_v1's own topology check.

        TIER 2, soft: cardinal-connection sanity across the FULL grid
        (existing records + these new ones) via connection_check_v1.py
        -- real, useful PROMPTS per Alan's own framing, never a
        rejection; returned as a real list of hint strings alongside
        a None error."""
        if self.shell_path is not None:
            for rec in new_records:
                ok, reason = shell_compat_v1.check_core_compatible(self.shell_path, rec.core)
                if not ok:
                    return reason, []
        combined = dict(self._records)
        for rec in new_records:
            combined[(rec.row, rec.col)] = rec
        hints = connection_check_v1.check_connections(combined.values())
        return None, hints

    # ── single-program mode (#362, unchanged) ──────────────────────

    def compile(self, source: str, language: str = "dsl") -> Dict[str, Any]:
        target = self.session.mirror_bounds if self.session is not None else None

        # Compile once here (the same real compile_source()/
        # compile_python_source() functions VMSession.from_dsl()/
        # from_man() use internally) so the real ICM records --
        # original core_config field names, needed by the shell/
        # connection checks below -- are available BEFORE the session
        # is replaced. VMSession's own from_*() methods are still used
        # afterward to actually build the session, so construction
        # logic isn't duplicated, only the (cheap) parse step.
        if language == "python":
            icm, diagnostics = compile_python_source(source)
        else:
            icm, diagnostics = compile_source(source)
        if icm is None:
            return {"ok": False, "diagnostics": [_diag_to_dict(d) for d in diagnostics]}

        # points.md #606: shell-compatibility (hard) + connection (soft)
        # checks run against the real, freshly-compiled records BEFORE
        # anything replaces the current session.
        shell_error, connection_hints = self._check_shell_and_connections(icm.records)
        if shell_error:
            return {"ok": False, "error": f"shell incompatibility: {shell_error}"}

        try:
            if target is not None:
                kwargs = {"python": source} if language == "python" else {"dsl": source}
                session = VMSession.from_man(target.man_path, target.cells, **kwargs)
            elif language == "python":
                session = VMSession.from_python(source)
            else:
                session = VMSession.from_dsl(source)
        except CompileFailure as e:
            return {"ok": False, "diagnostics": [_diag_to_dict(d) for d in e.diagnostics]}
        except vm_mirror_v1.MirrorFitError as e:
            return {"ok": False, "error": "program doesn't fit the real target ("
                                           f"{target.card_id}, {target.cells} cells): " + "; ".join(e.problems)}

        self.session = session
        self.regions = {}
        self._records = {(r.row, r.col): r for r in icm.records}
        self.registry = HostResourceRegistry()
        return {
            "ok": True,
            "diagnostics": [_diag_to_dict(d) for d in session.diagnostics],
            "connection_hints": connection_hints,
            "state": session.describe(),
        }

    def load_demo(self, name: str) -> Dict[str, Any]:
        if name not in DEMOS:
            return {"ok": False, "error": f"unknown demo {name!r} -- known demos: {sorted(DEMOS)}"}
        demo = DEMOS[name]
        return self.compile(demo["source"], demo["language"])

    # ── multi-program region mode (#363, new) ──────────────────────

    def load_region(self, name: str, source: str, language: str = "dsl",
                     row_offset: Optional[int] = None, col_offset: Optional[int] = None,
                     dsp_columns: Optional[List[int]] = None) -> Dict[str, Any]:
        if name in self.regions:
            return {"ok": False, "error": f"region {name!r} is already loaded -- "
                                           f"clear it first or choose a different name"}
        if language == "python":
            icm, diagnostics = compile_python_source(source)
        else:
            icm, diagnostics = compile_source(source)
        if icm is None:
            return {"ok": False, "diagnostics": [_diag_to_dict(d) for d in diagnostics]}

        if self.session is None:
            self.session = VMSession(SuperGrid([]))

        # the real loader/binder stage (#375/#377) -- omit BOTH row_offset
        # and col_offset for auto-placement (plain first-fit, or DSP-column
        # -aware if dsp_columns is also given), or give both offsets for
        # manual placement, the same behavior this method always had.
        bound, bind_diags = bind_shape(icm.records, self.session.grid.cells,
                                        row_offset=row_offset, col_offset=col_offset,
                                        dsp_columns=dsp_columns,
                                        what=f"loading region {name!r}")
        if bound is None:
            return {"ok": False, "error": bind_diags[0].problem}

        # points.md #605: if a real target is set (set_target()), this
        # region's own real placements are checked against it too --
        # not just "doesn't collide with what's already loaded"
        # (bind_shape's own real job above), but "corresponds to a
        # position a real Quartus build of this card/cell-count would
        # actually have." Checked BEFORE mutating the grid, so a
        # rejected region never partially loads.
        if self.session.mirror_bounds is not None:
            fit_problems = vm_mirror_v1.check_records_fit(bound, self.session.mirror_bounds)
            # a region's own records never collide with each other
            # (bind_shape already guarantees that) -- only report real
            # out-of-layout placements here, not the "collides" wording,
            # which would be misleading for a single incoming region.
            fit_problems = [p for p in fit_problems if "outside the real" in p]
            if fit_problems:
                return {"ok": False, "error": "region doesn't fit the real target ("
                                               f"{self.session.mirror_bounds.card_id}): " + "; ".join(fit_problems)}

        # points.md #606: shell-compatibility (hard) + connection (soft,
        # checked across the FULL grid -- existing regions plus this
        # one, catching cross-region mismatches too) checks, same
        # "reject before writing anything" discipline as the topology
        # check just above.
        shell_error, connection_hints = self._check_shell_and_connections(bound)
        if shell_error:
            return {"ok": False, "error": f"shell incompatibility: {shell_error}"}

        from unicell_super_automaton_v1 import SuperCell
        positions = []
        for rec in bound:
            self.session.grid.cells[(rec.row, rec.col)] = SuperCell.from_record(rec)
            self._records[(rec.row, rec.col)] = rec
            positions.append((rec.row, rec.col))
        self.regions[name] = positions
        self.registry.register_load(name, positions, metadata={"language": language})

        return {
            "ok": True,
            "diagnostics": [_diag_to_dict(d) for d in diagnostics],
            "connection_hints": connection_hints,
            "region": {"name": name, "positions": positions},
            "state": self.session.describe(),
        }

    def clear_region(self, name: str) -> Dict[str, Any]:
        if self.session is None or name not in self.regions:
            return {"ok": False, "error": f"no region named {name!r} is loaded -- "
                                           f"known regions: {sorted(self.regions)}"}
        positions = set(self.regions.pop(name))
        self.registry.register_unload(name)
        for pos in positions:
            self.session.grid.cells.pop(pos, None)
            self._records.pop(pos, None)
        # real cleanup, not just deleting the cell entries: drop any
        # pending event whose ORIGIN was one of the removed cells (it
        # can never be acked now) or whose DESTINATION was removed
        # entirely (nothing left to receive it).
        grid = self.session.grid
        for dest in list(grid._pending.keys()):
            if dest in positions:
                del grid._pending[dest]
                continue
            grid._pending[dest] = [ev for ev in grid._pending[dest] if ev[0] not in positions]
            if not grid._pending[dest]:
                del grid._pending[dest]
        return {"ok": True, "state": self.session.describe()}

    def list_regions(self) -> Dict[str, Any]:
        return {"ok": True, "regions": {name: {"positions": positions, "cell_count": len(positions)}
                                         for name, positions in self.regions.items()}}

    def list_demos(self) -> Dict[str, Any]:
        return {"ok": True, "demos": {name: {"description": d["description"], "language": d["language"]}
                                       for name, d in DEMOS.items()}}

    # ── shared operations (#362, unchanged) ────────────────────────

    def state(self) -> Dict[str, Any]:
        if self.session is None:
            return {"ok": False, "error": "no program compiled yet"}
        state = self.session.describe()
        # annotate which region each cell belongs to, for UI highlighting
        cell_to_region = {}
        for name, positions in self.regions.items():
            for pos in positions:
                cell_to_region[f"{pos[0]},{pos[1]}"] = name
        for key, cell in state["cells"].items():
            cell["region"] = cell_to_region.get(key)
        return {"ok": True, "state": state}

    def step(self, n: int = 1) -> Dict[str, Any]:
        if self.session is None:
            return {"ok": False, "error": "no program compiled yet"}
        self.session.tick(n)
        return self.state()

    def deliver(self, row: int, col: int, direction: Optional[str] = None,
                value: int = 0, injected: bool = False) -> Dict[str, Any]:
        if self.session is None:
            return {"ok": False, "error": "no program compiled yet"}
        try:
            if injected:
                accepted, _forward = self.session.deliver(row, col, {}, value)
            else:
                if direction not in _DIRS:
                    return {"ok": False, "error": f"unknown direction {direction!r}, "
                                                   f"expected one of n/s/e/w"}
                accepted, _forward = self.session.deliver(row, col, {_DIRS[direction]: value}, None)
        except KeyError as e:
            return {"ok": False, "error": str(e)}
        result = self.state()
        result["accepted"] = accepted
        return result

    def inject(self, row: int, col: int, value: int) -> Dict[str, Any]:
        if self.session is None:
            return {"ok": False, "error": "no program compiled yet"}
        self.session.inject(row, col, value)
        return self.state()


WORKBENCH_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Unicell-S Workbench</title>
<style>
  body { font-family: 'Courier New', monospace; background: #1a1a1a; color: #ddd; margin: 0; padding: 16px; }
  h2 { margin: 0 0 12px 0; color: #6cf; }
  .panel { background: #222; border: 1px solid #444; border-radius: 4px; padding: 12px; margin-bottom: 12px; }
  .panel h3 { margin: 0 0 8px 0; color: #9cf; font-size: 13px; text-transform: uppercase; }
  textarea { width: 100%; height: 130px; background: #111; color: #9f9; border: 1px solid #444;
             font-family: inherit; box-sizing: border-box; padding: 6px; }
  select, input[type=number] { background: #111; color: #ddd; border: 1px solid #444; padding: 4px; }
  button { background: #333; color: #ddd; border: 1px solid #555; padding: 6px 12px;
           margin: 4px 4px 4px 0; cursor: pointer; font-family: inherit; }
  button:hover { background: #444; }
  button.danger { border-color: #844; }
  button.danger:hover { background: #533; }
  #grid { display: grid; gap: 4px; margin-top: 8px; }
  .cell { border: 2px solid #555; padding: 6px; min-width: 100px; font-size: 11px; background: #1e1e1e; }
  .cell .core { color: #6cf; font-weight: bold; }
  .cell .pos { color: #777; font-size: 10px; }
  .cell .dirs { font-size: 10px; margin: 2px 0; }
  #diagnostics { color: #f88; white-space: pre-wrap; margin-top: 8px; font-size: 12px; }
  #tickcount { color: #9f9; font-weight: bold; }
  .region-row { display: flex; justify-content: space-between; align-items: center;
                padding: 4px 0; border-bottom: 1px solid #333; }
  .region-swatch { display: inline-block; width: 10px; height: 10px; margin-right: 6px; }
  .row { display: flex; gap: 16px; flex-wrap: wrap; }
  .col { flex: 1; min-width: 320px; }
  label { font-size: 12px; color: #999; }
</style>
</head>
<body>
<h2>Unicell-S Workbench</h2>

<div class="row">
  <div class="col">
    <div class="panel">
      <h3>Real target (points.md #605/#606)</h3>
      <div style="color:#999;font-size:12px;margin-bottom:6px;">Optional. Set this
        to make the grid below a genuine, checked reflection of a real
        card/cell-count -- exactly what <code>tools/project_assemble_v1.py</code>
        would build. Leave unset for free mode (no real card correspondence).</div>
      <label>MAN file path</label> <input type="text" id="manPath" value="docs/man/mustang-f100-a10.man.json" size="30">
      <label>cells</label> <input type="number" id="targetCells" value="4" size="4">
      <label>shell (optional -- a version1 may not support the same cores as a version3)</label>
      <select id="targetShell" onchange="showShellCoreInfo()"><option value="">(no shell check)</option></select>
      <div id="shellCoreInfo" style="color:#777;font-size:11px;margin:2px 0;"></div>
      <button onclick="setTarget()">Set target</button>
      <button onclick="clearTarget()">Clear target (free mode)</button>
      <div id="targetStatus" style="color:#9cf;font-size:12px;margin-top:4px;"></div>
    </div>

    <div class="panel">
      <h3>Demos</h3>
      <select id="demoSelect"></select>
      <button onclick="loadSelectedDemo()">Load as single program</button>
      <div id="demoDescription" style="color:#999;font-size:12px;margin-top:4px;"></div>
    </div>

    <div class="panel">
      <h3>Program source</h3>
      <select id="language"><option value="dsl">DSL</option><option value="python">Python-AST</option></select>
      <textarea id="source" placeholder="program p { place r1 as ram_constant at (0,0) { out: e init_data: 42 } }"></textarea><br>
      <button onclick="compileProgram()">Compile (replaces everything)</button>
      <br>
      <label>Region name</label> <input type="text" id="regionName" value="r1" size="8">
      <label>row offset</label> <input type="number" id="rowOffset" value="0" size="3" placeholder="auto">
      <label>col offset</label> <input type="number" id="colOffset" value="0" size="3" placeholder="auto">
      <span style="color:#777;font-size:11px;">(clear both for auto-placement)</span>
      <button onclick="loadRegion()">Load as region (adds to grid)</button>
      <div id="diagnostics"></div>
      <div id="connectionHints" style="color:#fc6;font-size:11px;white-space:pre-line;"></div>
    </div>

    <div class="panel">
      <h3>Regions loaded</h3>
      <div id="regionList"></div>
    </div>

    <div class="panel">
      <h3>Execution</h3>
      <button onclick="step(1)">Step</button>
      <button onclick="step(10)">Step 10</button>
      <button onclick="refresh()">Refresh</button>
      <span id="tickcount"></span>
      <br><br>
      <label>row</label> <input type="number" id="dRow" value="0" size="3">
      <label>col</label> <input type="number" id="dCol" value="0" size="3">
      <label>dir</label>
      <select id="dDir"><option>n</option><option>s</option><option>e</option><option>w</option></select>
      <label>value</label> <input type="number" id="dVal" value="1" size="4">
      <button onclick="deliverCell()">Deliver</button>
    </div>
  </div>

  <div class="col">
    <div class="panel">
      <h3>Grid</h3>
      <div id="grid"></div>
    </div>
  </div>
</div>

<script>
const DEMOS = {};
const REGION_COLORS = ["#6cf", "#f96", "#9f6", "#f6c", "#fc6", "#6fc"];
function colorForRegion(name) {
  if (!name) return "#555";
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return REGION_COLORS[h % REGION_COLORS.length];
}

async function post(path, body) {
  const r = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body || {})});
  return r.json();
}
async function get(path) {
  const r = await fetch(path);
  return r.json();
}

// points.md #606: real, client-side mirror of connection_check_v1.py's
// own per-core direction-field mapping -- display only (the real gate
// lives server-side); kept in the same shape so it can't silently say
// something different from what the server actually checked. branch/
// sequencer deliberately omitted, same real reasons as the server side
// (dynamic output; no real VM dispatch yet).
const CORE_OUT_FIELD = {ram: "downstream_mask", adder: "downstream_mask", accumulator: "downstream_mask",
                         compare: "downstream_mask", latch: "downstream_mask", nano: "routing_mask"};
const CORE_IN_FIELDS = {ram: ["upstream_mask"], adder: ["upstream_mask"], accumulator: ["inc_dir", "dec_dir"],
                         compare: ["upstream_mask"], latch: ["set_dir", "clear_dir"], nano: []};

function activeDirs(mask) {
  const dirs = [];
  if (mask & 1) dirs.push("N");
  if (mask & 2) dirs.push("S");
  if (mask & 4) dirs.push("E");
  if (mask & 8) dirs.push("W");
  return dirs;
}

function cellDirections(core, coreState) {
  coreState = coreState || {};
  const outField = CORE_OUT_FIELD[core];
  const out = outField ? activeDirs(coreState[outField] || 0) : [];
  let inMask = 0;
  for (const f of (CORE_IN_FIELDS[core] || [])) inMask |= (coreState[f] || 0);
  const inDirs = CORE_IN_FIELDS[core] !== undefined ? activeDirs(inMask) : [];
  return {out, in: inDirs};
}

function renderState(state) {
  document.getElementById("tickcount").textContent = "tick " + state.tick_count;
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  let maxCol = 0;
  for (const key in state.cells) maxCol = Math.max(maxCol, state.cells[key].col);
  grid.style.gridTemplateColumns = `repeat(${maxCol + 1}, auto)`;
  const cells = Object.values(state.cells).sort((a, b) => (a.row - b.row) || (a.col - b.col));
  for (const c of cells) {
    const div = document.createElement("div");
    div.className = "cell";
    div.style.borderColor = colorForRegion(c.region);
    div.style.gridColumn = c.col + 1;
    div.style.gridRow = c.row + 1;
    const dirs = cellDirections(c.core, c[c.core]);
    const dirLine = `<div class="dirs">` +
      `<span style="color:#6f6;">out: ${dirs.out.length ? dirs.out.join(",") : "-"}</span> &nbsp; ` +
      `<span style="color:#69f;">in: ${dirs.in.length ? dirs.in.join(",") : (c.core === "nano" ? "any" : "-")}</span></div>`;
    div.innerHTML = `<div class="core">${c.core}</div><div class="pos">(${c.row},${c.col}) ${c.region || ""}</div>` +
      dirLine +
      Object.entries(c[c.core] || {}).map(([k,v]) => `${k}: ${JSON.stringify(v)}`).join("<br>");
    grid.appendChild(div);
  }
}

function renderDiagnostics(diags) {
  document.getElementById("diagnostics").textContent =
    (diags || []).map(d => `${d.severity.toUpperCase()} [${d.stage}]: ${d.problem}`).join("\n");
}

function renderConnectionHints(hints) {
  // points.md #606: real, non-blocking prompts -- "hints/directions
  // of connections before they are made," per Alan's own framing.
  // Never an error; a cell can be deliberately left unconnected.
  const div = document.getElementById("connectionHints");
  div.textContent = (hints && hints.length) ? "HINT: " + hints.join("\nHINT: ") : "";
}

async function renderRegions() {
  const result = await get("/regions");
  const div = document.getElementById("regionList");
  div.innerHTML = "";
  if (!result.ok) return;
  for (const name in result.regions) {
    const r = result.regions[name];
    const row = document.createElement("div");
    row.className = "region-row";
    row.innerHTML = `<span><span class="region-swatch" style="background:${colorForRegion(name)}"></span>` +
      `${name} (${r.cell_count} cells)</span>`;
    const btn = document.createElement("button");
    btn.className = "danger";
    btn.textContent = "Clear";
    btn.onclick = () => clearRegion(name);
    row.appendChild(btn);
    div.appendChild(row);
  }
}

async function loadDemos() {
  const result = await get("/demos");
  if (!result.ok) return;
  const select = document.getElementById("demoSelect");
  for (const name in result.demos) {
    DEMOS[name] = result.demos[name];
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  }
  select.onchange = () => {
    document.getElementById("demoDescription").textContent = DEMOS[select.value].description;
  };
  if (select.value) select.onchange();
}

async function loadSelectedDemo() {
  const name = document.getElementById("demoSelect").value;
  const result = await post("/load_demo", {name: name});
  renderDiagnostics(result.diagnostics);
  if (result.ok) { renderState(result.state); renderRegions(); }
}

async function compileProgram() {
  const source = document.getElementById("source").value;
  const language = document.getElementById("language").value;
  const result = await post("/compile", {source: source, language: language});
  renderDiagnostics(result.diagnostics || (result.error ? [{severity: "error", stage: "compile", problem: result.error}] : []));
  renderConnectionHints(result.connection_hints);
  if (result.ok) { renderState(result.state); renderRegions(); }
}

async function loadRegion() {
  const source = document.getElementById("source").value;
  const language = document.getElementById("language").value;
  const name = document.getElementById("regionName").value;
  // real loader/binder stage (#375): leave BOTH offset fields blank
  // for auto-placement, or fill in BOTH for a manual position.
  const rowRaw = document.getElementById("rowOffset").value.trim();
  const colRaw = document.getElementById("colOffset").value.trim();
  const rowOffset = rowRaw === "" ? null : parseInt(rowRaw);
  const colOffset = colRaw === "" ? null : parseInt(colRaw);
  const result = await post("/load_region", {source, language, name, row_offset: rowOffset, col_offset: colOffset});
  renderDiagnostics(result.diagnostics || [{severity: "error", stage: "region", problem: result.error || ""}]);
  renderConnectionHints(result.connection_hints);
  if (result.ok) { renderState(result.state); renderRegions(); }
}

async function clearRegion(name) {
  const result = await post("/clear_region", {name: name});
  if (result.ok) { renderState(result.state); renderRegions(); }
}

async function step(n) {
  const result = await post("/step", {n: n});
  if (result.ok) renderState(result.state);
}

async function deliverCell() {
  const row = parseInt(document.getElementById("dRow").value);
  const col = parseInt(document.getElementById("dCol").value);
  const direction = document.getElementById("dDir").value;
  const value = parseInt(document.getElementById("dVal").value);
  const result = await post("/deliver", {row, col, direction, value});
  if (result.ok) renderState(result.state);
  else renderDiagnostics([{severity: "error", stage: "deliver", problem: result.error}]);
}

async function refresh() {
  const result = await get("/state");
  if (result.ok) renderState(result.state);
}

async function setTarget() {
  const man_path = document.getElementById("manPath").value;
  const cells = parseInt(document.getElementById("targetCells").value);
  const shell = document.getElementById("targetShell").value || null;
  const result = await post("/set_target", {man_path, cells, shell});
  if (result.ok) {
    const shellNote = result.target.shell ? `, shell ${result.target.shell}` : "";
    document.getElementById("targetStatus").textContent =
      `Target set: ${result.target.card_id}, ${result.target.cells} cells (${result.target.rows}x${result.target.cols})${shellNote} -- grid reset.`;
    renderState(result.state);
    renderRegions();
  } else {
    document.getElementById("targetStatus").textContent = "Error: " + result.error;
  }
}

async function clearTarget() {
  const result = await post("/clear_target", {});
  if (result.ok) {
    document.getElementById("targetStatus").textContent = "Free mode -- no real card target.";
    renderState(result.state);
    renderRegions();
  }
}

async function refreshTargetStatus() {
  const result = await get("/target");
  if (result.ok && result.target) {
    const shellNote = result.target.shell ? `, shell ${result.target.shell}` : "";
    document.getElementById("targetStatus").textContent =
      `Target: ${result.target.card_id}, ${result.target.cells} cells (${result.target.rows}x${result.target.cols})${shellNote}`;
  } else {
    document.getElementById("targetStatus").textContent = "Free mode -- no real card target.";
  }
}

async function loadShells() {
  const result = await get("/shells");
  if (!result.ok) return;
  const sel = document.getElementById("targetShell");
  for (const version in result.shells) {
    const opt = document.createElement("option");
    opt.value = version;
    opt.textContent = version;
    sel.appendChild(opt);
  }
  window._shellCores = {};
  for (const version in result.shells) window._shellCores[version] = Object.keys(result.shells[version]).sort();
  sel.value = "v3" in result.shells ? "v3" : "";
  showShellCoreInfo();
}

function showShellCoreInfo() {
  const version = document.getElementById("targetShell").value;
  const info = document.getElementById("shellCoreInfo");
  if (!version || !window._shellCores || !window._shellCores[version]) { info.textContent = ""; return; }
  info.textContent = "real cores on " + version + ": " + window._shellCores[version].join(", ");
}

loadDemos();
loadShells();
refreshTargetStatus();
</script>
</body>
</html>
"""


class WorkbenchHandler(http.server.BaseHTTPRequestHandler):
    controller: Optional[WorkbenchController] = None

    def _json_response(self, data: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html_response(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if self.path == "/state":
            self._json_response(self.controller.state())
        elif self.path == "/demos":
            self._json_response(self.controller.list_demos())
        elif self.path == "/regions":
            self._json_response(self.controller.list_regions())
        elif self.path == "/target":
            self._json_response(self.controller.current_target())
        elif self.path == "/shells":
            self._json_response(self.controller.list_shells())
        elif self.path in ("/", "/index.html"):
            self._html_response(WORKBENCH_HTML)
        else:
            self._json_response({"ok": False, "error": "not found"}, status=404)

    def do_POST(self):
        body = self._read_json_body()
        if self.path == "/compile":
            self._json_response(self.controller.compile(body.get("source", ""),
                                                          body.get("language", "dsl")))
        elif self.path == "/load_demo":
            self._json_response(self.controller.load_demo(body.get("name", "")))
        elif self.path == "/load_region":
            self._json_response(self.controller.load_region(
                body.get("name", ""), body.get("source", ""), body.get("language", "dsl"),
                body.get("row_offset"), body.get("col_offset"), body.get("dsp_columns")))
        elif self.path == "/clear_region":
            self._json_response(self.controller.clear_region(body.get("name", "")))
        elif self.path == "/set_target":
            self._json_response(self.controller.set_target(
                body.get("man_path", ""), body.get("cells", 0), body.get("shell")))
        elif self.path == "/clear_target":
            self._json_response(self.controller.clear_target())
        elif self.path == "/step":
            self._json_response(self.controller.step(body.get("n", 1)))
        elif self.path == "/deliver":
            self._json_response(self.controller.deliver(
                body.get("row"), body.get("col"), body.get("direction"),
                body.get("value", 0), body.get("injected", False)))
        elif self.path == "/inject":
            self._json_response(self.controller.inject(
                body.get("row"), body.get("col"), body.get("value", 0)))
        else:
            self._json_response({"ok": False, "error": "not found"}, status=404)

    def log_message(self, fmt, *args):
        pass   # quiet -- matches the old workbench's own convention


def serve(port: int = 7420, open_browser: bool = False) -> http.server.HTTPServer:
    WorkbenchHandler.controller = WorkbenchController()
    server = http.server.HTTPServer(("localhost", port), WorkbenchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if open_browser:
        webbrowser.open(f"http://localhost:{port}")
    return server


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7420
    server = serve(port, open_browser=True)
    print(f"Unicell-S workbench serving at http://localhost:{port}")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.shutdown()
