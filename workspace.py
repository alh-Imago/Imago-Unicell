"""
workspace.py — WORKSPACE Pond

The user's desk. Every interactive session has one WORKSPACE pond that holds:
  - The currently loaded program (from .icm or compiled from source)
  - Named input values the user has set
  - Named output values from the last run
  - The file system index for the session (programs the user has saved)
  - A search index over loaded programs and named values

The WORKSPACE pond is the bridge between the user (CLI, workbench UI) and
PROCESS ponds. It manages the full lifecycle:

  User types "ws set a 5"
       ↓
  WorkspacePond stores {a: 5} in named_values
       ↓
  User types "ws run"
       ↓
  WorkspacePond injects {0x1000: 5} into controller
  Controller runs the loaded PROCESS region
  WorkspacePond reads outputs back, stores {result: 8}
       ↓
  User types "ws get result" → 8

One WorkspacePond per session. Created by the Workbench at startup.
"""

import json
import os
import time
import traceback
from typing import Optional


class WorkspacePond:
    """
    The user's interactive session context.

    Holds a loaded program, named values, and the session file index.
    Wraps ImagoController for program execution.
    """

    VERSION = "1.0"

    def __init__(self, controller, name: str = "workspace"):
        self._ctrl         = controller
        self.name          = name
        self.created_at    = time.time()

        # Currently loaded program
        self._program_name: str       = ""
        self._region_id:    str       = ""
        self._input_map:    dict      = {}   # {param_name: bus_address}
        self._output_map:   dict      = {}   # {param_name: bus_address}
        self._output_addrs: list      = []   # [bus_address, ...]
        self._records:      list      = []   # CellMapRecord list (for re-run)
        self._source:       str       = ""   # source if compiled from text
        self._icm_path:     str       = ""   # path if loaded from .icm
        self._cell_count:   int       = 0
        self._known_values: dict      = {}   # compile-time constants

        # User-set named values (inputs + last-run outputs together)
        self.named_values:  dict      = {}   # {name: value}

        # Run history
        self._runs:         list      = []   # [{inputs, outputs, cycle, ok}]
        self._last_run_ok:  bool      = False
        self._last_error:   str       = ""

        # Session file system: {filename: {path, name, cells, source}}
        self._fs:           dict      = {}

        # Programming space: multi-file editor state
        self._prog_files:   dict      = {}   # {filename: source}
        self._prog_active:  str       = ""   # active file name

    # ── program loading ───────────────────────────────────────────────────────

    def load_icm(self, path: str) -> dict:
        """Load a .icm file into the workspace."""
        try:
            with open(path) as f:
                icm = json.load(f)
        except Exception as e:
            return self._err(f"Cannot read '{path}': {e}")

        return self._load_from_icm(icm, icm_path=path)

    def load_icm_dict(self, icm: dict) -> dict:
        """Load a .icm dict (e.g. from browser upload) into the workspace."""
        return self._load_from_icm(icm, icm_path="")

    def _load_from_icm(self, icm: dict, icm_path: str) -> dict:
        """Internal: reconstruct CellMapRecords from an icm dict and load."""
        try:
            from controller import CellMapRecord
            records = [
                CellMapRecord(
                    r["gs"],
                    r["in"],
                    r["out"],
                    input_b_address=r.get("inB"),
                    initial_value=r.get("init"),
                )
                for r in icm.get("records", [])
            ]
            name       = icm.get("name", os.path.basename(icm_path) or "program")
            # inputs/outputs: may be explicit (compiled .icm) or derived from ranges
            inputs  = icm.get("inputs",  {})
            outputs = icm.get("outputs", {})
            known   = icm.get("known_values", {})

            # Fall back to ranges if inputs/outputs absent (e.g. Composer .icm)
            if not inputs and not outputs:
                for r in icm.get("ranges", []):
                    kind = r.get("kind", "")
                    nm   = r.get("name", "")
                    addr = r.get("bus_address", 0)
                    if kind in ("INPUT", "ACCUMULATOR") and nm:
                        inputs[nm] = addr
                    elif kind == "OUTPUT" and nm and not nm.startswith("output_b"):
                        outputs[nm] = addr

            # If still no named inputs, try to infer from record in-addresses
            if not inputs:
                seen_in  = {}
                seen_out = {}
                for i, r in enumerate(icm.get("records", [])):
                    seen_in[r.get("in", 0)]  = f"in_{i}"
                    seen_out[r.get("out", 0)] = f"out_{i}"
                # Only inputs not used as outputs of any other cell
                all_outs = {r.get("out", 0) for r in icm.get("records", [])}
                for addr, name in seen_in.items():
                    if addr not in all_outs:
                        inputs[name] = addr
                for addr, name in seen_out.items():
                    all_ins = {r.get("in", 0) for r in icm.get("records", [])}
                    if addr not in all_ins:
                        outputs[name] = addr

            # Normalise: hex strings → ints
            inputs  = {k: int(v, 16) if isinstance(v, str) else int(v) for k, v in inputs.items()}
            outputs = {k: int(v, 16) if isinstance(v, str) else int(v) for k, v in outputs.items()}
            known   = {(int(k, 16) if isinstance(k, str) else k): v for k, v in known.items()}

            return self._install(records, name, inputs, outputs,
                                 known_values=known, icm_path=icm_path)
        except Exception as e:
            return self._err(f"Failed to load ICM: {e}\n{traceback.format_exc()}")

    def compile(self, source: str, fn_name: str,
                port_names: dict = None) -> dict:
        """Compile Python source and load the result into the workspace."""
        try:
            from compiler import ImagoCompiler
            compiler = ImagoCompiler()
            records, graph, input_map, output_addrs = compiler.compile_function(
                source, fn_name, None, port_names=port_names
            )
            known = getattr(compiler, "known_values", {})
            # Use named output_map if compiler produced one, else fallback
            output_map = getattr(compiler, "output_map", None)
            if not output_map:
                output_map = {f"out_{i}": addr for i, addr in enumerate(output_addrs)}
            return self._install(records, fn_name, input_map, output_map,
                                 known_values=known, source=source)
        except Exception as e:
            return self._err(f"Compile failed: {e}\n{traceback.format_exc()}")

    def compile_int32(self, source: str, fn_name: str) -> dict:
        """Compile an INT32 source function and load into workspace."""
        try:
            from compiler_int32 import Int32Compiler, TileLibrary
            compiler = Int32Compiler(tile_library=TileLibrary())
            records, graph, input_map, output_addrs, _ = compiler.compile_int32_function(
                source, fn_name
            )
            known = getattr(compiler, "known_values", {})
            output_map = {f"out_{i}": addr for i, addr in enumerate(output_addrs)}
            return self._install(records, fn_name, input_map, output_map,
                                 known_values=known, source=source)
        except Exception as e:
            return self._err(f"INT32 compile failed: {e}\n{traceback.format_exc()}")

    def _install(self, records, name, input_map, output_map,
                 known_values=None, source="", icm_path="") -> dict:
        """Install a compiled program into the controller and update workspace state."""
        # Free previous region if any
        if self._region_id:
            try:
                self._ctrl.free(self._region_id)
            except Exception:
                pass

        rid = self._ctrl.load_map(records, name,
                                  known_values=known_values or {})
        if rid is None:
            return self._err("Controller rejected program (security gate or array full)")

        self._program_name = name
        self._region_id    = rid
        self._input_map    = dict(input_map)
        self._output_map   = dict(output_map)
        self._output_addrs = list(output_map.values())
        self._records      = records
        self._source       = source
        self._icm_path     = icm_path
        self._cell_count   = len(records)
        self._known_values = known_values or {}

        # Seed named_values with input names → 0 (user fills in real values)
        # Keep any values the user already set for params that still exist
        new_named = {}
        for param in input_map:
            new_named[param] = self.named_values.get(param, 0)
        for param in output_map:
            new_named[param] = None   # not yet computed
        self.named_values = new_named

        return {
            "ok":       True,
            "name":     name,
            "region":   rid,
            "cells":    len(records),
            "inputs":   list(input_map.keys()),
            "outputs":  list(output_map.keys()),
            "message":  f"Loaded '{name}': {len(records)} cells, "
                        f"{len(input_map)} input(s), {len(output_map)} output(s)",
        }

    # ── named value management ────────────────────────────────────────────────

    def set(self, name: str, value) -> dict:
        """Set a named input value."""
        if not self._program_name:
            return self._err("No program loaded. Use 'ws load <file>' or 'ws compile'.")
        if name not in self._input_map:
            # Allow setting anyway — might be used as a constant or annotation
            self.named_values[name] = int(value)
            return {"ok": True, "name": name, "value": int(value),
                    "warning": f"'{name}' is not a declared input of '{self._program_name}'"}
        self.named_values[name] = int(value)
        return {"ok": True, "name": name, "value": int(value)}

    def get(self, name: str) -> dict:
        """Get a named value (input or output)."""
        if name not in self.named_values:
            return self._err(f"'{name}' not in workspace values")
        return {"ok": True, "name": name, "value": self.named_values[name]}

    def values(self) -> dict:
        """Return all current named values."""
        return {
            "ok":      True,
            "program": self._program_name,
            "inputs":  {k: self.named_values.get(k) for k in self._input_map},
            "outputs": {k: self.named_values.get(k) for k in self._output_map},
        }

    # ── execution ─────────────────────────────────────────────────────────────

    def run(self) -> dict:
        """
        Inject current named_values into the loaded program and run it.
        Updates named_values with output results.
        """
        if not self._program_name:
            return self._err("No program loaded.")
        if not self._region_id:
            return self._err("No region loaded. Reload the program.")

        # Reload the map (region may have been consumed by previous run)
        rid = self._ctrl.load_map(self._records, self._program_name,
                                  known_values=self._known_values)
        if rid is None:
            return self._err("Could not reload program into controller.")
        self._region_id = rid

        # Build inputs dict: {bus_addr: value} for all named inputs
        inputs_bus = {}
        for param, addr in self._input_map.items():
            val = self.named_values.get(param, 0)
            inputs_bus[addr] = int(val) if val is not None else 0

        try:
            result = self._ctrl.run(rid,
                inputs=inputs_bus,
                capture_addresses=self._output_addrs
            )
        except Exception as e:
            self._last_run_ok  = False
            self._last_error   = str(e)
            return self._err(f"Run failed: {e}")

        # Map output addresses back to names
        outputs = {}
        for param, addr in self._output_map.items():
            val = result.get(addr) if result else None
            outputs[param] = val
            self.named_values[param] = val

        run_record = {
            "inputs":  {k: self.named_values.get(k) for k in self._input_map},
            "outputs": outputs,
            "cycle":   time.time(),
            "ok":      True,
        }
        self._runs.append(run_record)
        if len(self._runs) > 50:
            self._runs = self._runs[-50:]

        self._last_run_ok = True
        self._last_error  = ""

        return {
            "ok":      True,
            "program": self._program_name,
            "inputs":  {k: self.named_values.get(k) for k in self._input_map},
            "outputs": outputs,
        }

    # ── file system ───────────────────────────────────────────────────────────

    def fs_save(self, filename: str, source: str = None) -> dict:
        """Save current program or given source to the session file system."""
        src = source or self._source
        if not src and self._icm_path:
            return self._err("Cannot save — program was loaded from .icm, not source. "
                             "Save the .icm file directly.")
        if not src:
            return self._err("No source to save.")
        self._fs[filename] = {
            "name":    filename,
            "source":  src,
            "cells":   self._cell_count,
            "saved_at": time.time(),
        }
        return {"ok": True, "filename": filename, "bytes": len(src)}

    def fs_load(self, filename: str) -> dict:
        """Load a file from the session file system and compile it."""
        if filename not in self._fs:
            return self._err(f"'{filename}' not in session file system. "
                             f"Available: {list(self._fs.keys())}")
        entry  = self._fs[filename]
        source = entry["source"]
        # Guess function name from source
        import re
        m = re.search(r"^def\s+(\w+)", source, re.MULTILINE)
        fn = m.group(1) if m else filename.replace(".py", "")
        return self.compile(source, fn)

    def fs_list(self) -> dict:
        """List files in the session file system."""
        rows = [
            {
                "filename": name,
                "cells":    entry["cells"],
                "saved":    time.strftime("%H:%M:%S",
                                time.localtime(entry["saved_at"])),
            }
            for name, entry in self._fs.items()
        ]
        return {"ok": True, "files": rows}

    def fs_delete(self, filename: str) -> dict:
        if filename not in self._fs:
            return self._err(f"'{filename}' not found")
        del self._fs[filename]
        return {"ok": True, "filename": filename}

    # ── programming space ─────────────────────────────────────────────────────

    def prog_new(self, filename: str, template: str = "blank") -> dict:
        """Create a new file in the programming space."""
        templates = {
            "blank":   "def my_function(a, b):\n    return a and b\n",
            "int32":   "def add(a: int32, b: int32) -> int32:\n    return a + b\n",
            "not":     "def not_gate(x):\n    return not x\n",
            "mux":     "def mux(sel, a, b):\n    if sel:\n        return a\n    return b\n",
        }
        source = templates.get(template, templates["blank"])
        self._prog_files[filename] = source
        self._prog_active = filename
        return {"ok": True, "filename": filename, "source": source}

    def prog_save(self, filename: str, source: str) -> dict:
        """Save source to a file in the programming space."""
        self._prog_files[filename] = source
        self._prog_active = filename
        return {"ok": True, "filename": filename}

    def prog_load(self, filename: str) -> dict:
        """Make a programming space file active."""
        if filename not in self._prog_files:
            return self._err(f"'{filename}' not in programming space")
        self._prog_active = filename
        return {"ok": True, "filename": filename,
                "source": self._prog_files[filename]}

    def prog_list(self) -> dict:
        return {
            "ok":    True,
            "files": list(self._prog_files.keys()),
            "active": self._prog_active,
        }

    def prog_compile(self, filename: str = None, int32: bool = False) -> dict:
        """Compile the active (or named) programming space file."""
        fname = filename or self._prog_active
        if not fname or fname not in self._prog_files:
            return self._err("No file selected. Use 'prog new <name>' or 'prog load <name>'.")
        source = self._prog_files[fname]
        import re
        m = re.search(r"^def\s+(\w+)", source, re.MULTILINE)
        fn = m.group(1) if m else fname.replace(".py", "")
        if int32:
            return self.compile_int32(source, fn)
        return self.compile(source, fn)

    def prog_run(self, **kwargs) -> dict:
        """Set values, then run. Convenience for one-shot prog compile+run."""
        for k, v in kwargs.items():
            self.set(k, v)
        return self.run()

    # ── search ────────────────────────────────────────────────────────────────

    def search(self, query: str) -> dict:
        """
        Search across: named values, loaded program name, session fs files,
        programming space files. Simple substring / keyword match.
        """
        q = query.lower()
        results = []

        # named values
        for name, val in self.named_values.items():
            if q in name.lower():
                results.append({"where": "values", "name": name, "value": val})

        # loaded program
        if self._program_name and q in self._program_name.lower():
            results.append({"where": "loaded", "name": self._program_name,
                            "cells": self._cell_count})

        # session fs
        for fname, entry in self._fs.items():
            if q in fname.lower() or q in entry.get("source", "").lower():
                results.append({"where": "fs", "name": fname,
                                "cells": entry["cells"]})

        # programming space
        for fname, src in self._prog_files.items():
            if q in fname.lower() or q in src.lower():
                results.append({"where": "prog", "name": fname,
                                "preview": src[:60].replace("\n", " ")})

        return {"ok": True, "query": query, "results": results}

    # ── status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "ok":          True,
            "name":        self.name,
            "program":     self._program_name or "(none)",
            "cells":       self._cell_count,
            "region":      self._region_id or "(none)",
            "inputs":      list(self._input_map.keys()),
            "outputs":     list(self._output_map.keys()),
            "values":      dict(self.named_values),
            "runs":        len(self._runs),
            "last_ok":     self._last_run_ok,
            "fs_files":    list(self._fs.keys()),
            "prog_files":  list(self._prog_files.keys()),
            "prog_active": self._prog_active,
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    def _err(self, msg: str) -> dict:
        return {"ok": False, "error": msg}
