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

    def __init__(self, controller, name: str = "workspace",
                 pond_manager=None, owner_id: str = "workspace_user"):
        self._ctrl         = controller
        self.name          = name
        self.created_at    = time.time()

        # Currently loaded program (single-program legacy path)
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
        self._fn_type:      str       = 'logic'  # 'logic' | 'int32' | 'icm'
        self._preloaded_a:  dict      = {}   # static preloads from ICM init= fields

        self._type_map:     dict      = {}   # {param_name: type_name_str}

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

        # ── PondManager-backed multi-program support ──────────────────────────
        # If pond_manager is supplied, the workspace is backed by a real Pond
        # with Ward health monitoring, PTT tracking, and bridge security.
        # If None, the legacy bare-controller path is used (workbench default).
        self._pond_mgr:     object    = pond_manager
        self._owner_id:     str       = owner_id
        self._ws_pond:      object    = None   # WORKSPACE Pond (Pond object)
        self._active_programs: dict   = {}     # {handle_id: ProgramHandle}
        self._handle_counter: int     = 0

        if pond_manager is not None:
            self._ws_pond = pond_manager.spawn_workspace(
                owner_id = owner_id,
                name     = name,
            )

    # ── PondManager multi-program API ─────────────────────────────────────────

    def launch_program(self, icm: dict, cell_count: int = 8192) -> dict:
        """
        Load an ICM into its own PRIVATE PROCESS pond and wire it to this
        workspace. Requires pond_manager to have been passed at construction.

        Returns a ProgramHandle dict:
          {handle_id, program_name, pond_id, input_map, output_map, connection}

        The handle_id is used for run_program() and disconnect_program() calls.
        Multiple programs can be active simultaneously.
        """
        if self._pond_mgr is None:
            return self._err(
                "launch_program requires a PondManager. "
                "Construct WorkspacePond with pond_manager= to use this API."
            )
        try:
            program_pond = self._pond_mgr.spawn_pond_from_icm(
                icm,
                owner_id   = self._owner_id,
                cell_count = cell_count,
            )
            connection = self._pond_mgr.connect(self._ws_pond, program_pond)

            self._handle_counter += 1
            handle_id = f"prog_{self._handle_counter:04d}"

            handle = {
                "handle_id":    handle_id,
                "program_name": program_pond.name,
                "pond_id":      program_pond.pond_id,
                "input_map":    program_pond._input_map,
                "output_map":   program_pond._output_map,
                "connection":   connection,
                "_pond":        program_pond,
            }
            self._active_programs[handle_id] = handle

            return {
                "ok":           True,
                "handle_id":    handle_id,
                "program_name": program_pond.name,
                "pond_id":      program_pond.pond_id,
                "inputs":       list(program_pond._input_map.keys()),
                "outputs":      list(program_pond._output_map.keys()),
                "cells":        len(icm.get("records", [])),
                "message":      f"Launched '{program_pond.name}' as {handle_id}",
            }
        except Exception as e:
            return self._err(f"launch_program failed: {e}")

    def run_program(self, handle_id: str, **inputs) -> dict:
        """
        Run a connected program pond by handle_id.

        Injects the supplied inputs via the workspace's OUTBOUND bridge to
        the program's INBOUND bridge, runs one tick, captures output from
        the program's OUTBOUND (which routes back to this workspace's INBOUND).

        Also accepts inputs as a dict: run_program(handle_id, inputs={...})
        """
        if self._pond_mgr is None:
            return self._err("run_program requires a PondManager.")

        handle = self._active_programs.get(handle_id)
        if handle is None:
            return self._err(f"Unknown handle '{handle_id}'. "
                             f"Active: {list(self._active_programs)}")

        prog_pond  = handle["_pond"]
        input_map  = handle["input_map"]
        output_map = handle["output_map"]
        ctrl       = prog_pond._controller
        rid        = prog_pond._region_id

        # Accept inputs dict or kwargs
        if "inputs" in inputs and isinstance(inputs["inputs"], dict):
            inputs = inputs["inputs"]

        try:
            # Reload region (consumed by each run)
            from controller import CellMapRecord
            records_raw = handle["_pond"]._controller._regions[rid].cell_addresses
            # Re-use the existing controller — just re-run with new inputs
            inputs_bus = {}
            for name, addr in input_map.items():
                val = inputs.get(name, self.named_values.get(name, 0))
                inputs_bus[addr] = int(val) if val is not None else 0

            # Transition TILE_IN entries IDLE → WAITING in program PTT
            prog_ptt = prog_pond._ptt
            if prog_ptt is not None:
                from pond_ptt import STATUS_WAITING, STATUS_IDLE
                for port_name, idx in getattr(prog_pond, '_input_ptt_indices', {}).items():
                    entry = prog_ptt.get(idx)
                    if entry is not None and entry.status == STATUS_IDLE:
                        prog_ptt.transition(idx, STATUS_WAITING)

            output_addrs = list(output_map.values())
            result = ctrl.run(rid, inputs=inputs_bus,
                              capture_addresses=output_addrs)

            outputs = {}
            for port_name, addr in output_map.items():
                val = result.get(addr) if result else None
                outputs[port_name] = val
                self.named_values[f"{handle['program_name']}.{port_name}"] = val

            run_record = {
                "handle_id": handle_id,
                "inputs":    {k: inputs.get(k) for k in input_map},
                "outputs":   outputs,
                "cycle":     time.time(),
                "ok":        True,
            }
            self._runs.append(run_record)
            if len(self._runs) > 50:
                self._runs = self._runs[-50:]

            return {
                "ok":      True,
                "handle":  handle_id,
                "program": handle["program_name"],
                "inputs":  {k: inputs.get(k) for k in input_map},
                "outputs": outputs,
            }

        except Exception as e:
            return self._err(f"run_program failed for {handle_id}: {e}")

    def disconnect_program(self, handle_id: str) -> dict:
        """
        Disconnect and destroy a program pond by handle_id.
        Revokes whitelist grants, frees cells, removes PTT entries from workspace.
        """
        if self._pond_mgr is None:
            return self._err("disconnect_program requires a PondManager.")

        handle = self._active_programs.get(handle_id)
        if handle is None:
            return self._err(f"Unknown handle '{handle_id}'.")

        try:
            prog_pond = handle["_pond"]

            # Revoke whitelist grants both ways
            if self._ws_pond is not None:
                self._ws_pond.revoke_access(self._owner_id)
            prog_pond.revoke_access(self._owner_id)

            # Remove workspace PTT entries for this program's outputs
            if self._ws_pond is not None and self._ws_pond._ptt is not None:
                prog_pond_id = prog_pond.pond_id
                to_remove = [
                    idx for idx, e in self._ws_pond._ptt._entries.items()
                    if e.metadata.get("program_pond") == prog_pond_id
                ]
                for idx in to_remove:
                    try:
                        self._ws_pond._ptt.remove(idx)
                    except Exception:
                        pass

            # Destroy the program pond
            self._pond_mgr.destroy_pond(
                prog_pond.pond_id,
                requester_id = self._owner_id,
            )

            del self._active_programs[handle_id]

            return {
                "ok":      True,
                "handle":  handle_id,
                "program": handle["program_name"],
                "message": f"Disconnected and destroyed '{handle['program_name']}'",
            }
        except Exception as e:
            return self._err(f"disconnect_program failed: {e}")

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

            type_map = {}
            for k, v in (icm.get("input_types") or {}).items():
                type_map[k] = v
            for k, v in (icm.get("output_types") or {}).items():
                type_map[k] = v

            return self._install(records, name, inputs, outputs,
                                 known_values=known, icm_path=icm_path,
                                 type_map=type_map, fn_type='icm')
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
            self._ir_preload_map = getattr(compiler, "_ir_preload_map", {})
            self._pending_fn_type = 'logic'
            output_map = getattr(compiler, "output_map", None)
            if not output_map:
                output_map = {f"out_{i}": addr for i, addr in enumerate(output_addrs)}
            # Build type_map: {param_name: type_name_str} from compiler
            type_map = getattr(compiler, "input_types", {})
            type_map.update(getattr(compiler, "output_types", {}))
            return self._install(records, fn_name, input_map, output_map,
                                 known_values=known, source=source,
                                 type_map=type_map)
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
            self._pending_fn_type = 'int32'
            return self._install(records, fn_name, input_map, output_map,
                                 known_values=known, source=source)
        except Exception as e:
            return self._err(f"INT32 compile failed: {e}\n{traceback.format_exc()}")

    def _install(self, records, name, input_map, output_map,
                 known_values=None, source="", icm_path="",
                 type_map=None, fn_type=None) -> dict:
        """Install a compiled program into the controller and update workspace state."""
        # Free previous region if any
        if self._region_id:
            try:
                self._ctrl.free(self._region_id)
            except Exception:
                pass

        # Build preloaded_a from records' initial_value fields (ICM init= field).
        # Static preloads (NOT cells, constant operands) are baked into the ICM
        # at compile time. No runtime detection needed.
        preloaded_a = {
            rec.output_address: rec.initial_value
            for rec in records
            if getattr(rec, 'initial_value', None) is not None
        } or None

        rid = self._ctrl.load_map(records, name,
                                  known_values=known_values or {},
                                  preloaded_a=preloaded_a)
        if rid is None:
            return self._err("Controller rejected program (security gate or array full)")

        self._program_name  = name
        self._region_id     = rid
        self._input_map     = dict(input_map)
        self._fn_type       = fn_type or getattr(self, '_pending_fn_type', 'logic')
        self._preloaded_a   = preloaded_a   # stored for subsequent run() calls
        self._output_map    = dict(output_map)
        self._output_addrs  = list(output_map.values())
        self._records      = records
        self._source       = source
        self._icm_path     = icm_path
        self._cell_count   = len(records)
        self._known_values = known_values or {}
        self._type_map     = dict(type_map or {})   # {param_name: type_name_str}

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
        """
        Set a named input value. Type-aware:
          signed   — accepts negative ints, packs two's complement into
                     primary (low 32) + complement (high 32) cells
          datetime — accepts int (Unix seconds) or datetime object
          alpha    — accepts str, packs as character bytes
          numeric  — int value, single cell
        """
        if not self._program_name:
            return self._err("No program loaded. Use 'ws load <file>' or 'ws compile'.")

        port_type = self._type_map.get(name, "numeric")

        if port_type == "signed":
            # Pack as signed int64: primary=low32, complement=high32
            v = int(value)
            v64 = v & 0xFFFFFFFFFFFFFFFF   # two's complement 64-bit
            lo = v64 & 0xFFFFFFFF
            hi = (v64 >> 32) & 0xFFFFFFFF
            self.named_values[name] = v      # store as Python int (may be negative)
            self.named_values[f"_{name}_hi"] = hi
            # Inject complement addr if present in input_map
            if f"_{name}_hi" in self._input_map:
                pass   # run() will inject via input_map
            return {"ok": True, "name": name, "value": v,
                    "type": "signed", "lo": lo, "hi": hi}

        elif port_type == "datetime":
            # Accept int (Unix seconds), float, or datetime object
            try:
                import datetime as _dt
                if isinstance(value, _dt.datetime):
                    v = int(value.timestamp())
                elif isinstance(value, _dt.date):
                    v = int(_dt.datetime(value.year, value.month, value.day).timestamp())
                else:
                    v = int(value)
            except Exception:
                v = int(value)
            self.named_values[name] = v
            self.named_values[f"_{name}_hi"] = 0   # subsecond/tz (future)
            return {"ok": True, "name": name, "value": v, "type": "datetime"}

        elif port_type == "alpha":
            # Store as string; run() will pack bytes into cell addresses
            self.named_values[name] = str(value)
            return {"ok": True, "name": name, "value": str(value), "type": "alpha"}

        else:
            # numeric — single unsigned int
            if name not in self._input_map:
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

    def _run_via_compiler(self) -> dict:
        """
        Fast path: run a source-compiled function through run_compiled_function
        or run_int32_function. These handle the preloaded-A forward sim
        correctly on each call, avoiding the stale preload problem.
        """
        fn_name = self._program_name
        source  = self._source
        operands = {k: self.named_values.get(k, 0)
                    for k in self._input_map.keys()
                    if not k.startswith('_')}
        try:
            if self._fn_type == 'int32':
                from compiler_int32 import run_int32_function, TileLibrary
                result = run_int32_function(source, fn_name, operands,
                                            tile_library=TileLibrary())
                outputs = {'output': result}
            else:
                from compiler import run_compiled_function
                result = run_compiled_function(source, fn_name, operands)
                # Normalise to single bit
                outputs = {'output': 1 if result else 0}
        except Exception as e:
            return self._err(f"Run failed: {e}")

        self.named_values.update(outputs)
        self._last_run_ok = True
        self._last_error  = ""
        return {
            "ok":      True,
            "program": fn_name,
            "inputs":  {k: self.named_values.get(k) for k in self._input_map},
            "outputs": outputs,
        }

    def run(self) -> dict:
        """
        Inject current named_values into the loaded program and run it.
        Updates named_values with output results.
        """
        if not self._program_name:
            return self._err("No program loaded.")

        # Fast path: if program was compiled from source, route through
        # run_compiled_function / run_int32_function which handle the
        # preloaded-A forward sim correctly for each call.
        if self._source and self._fn_type in ('logic', 'int32'):
            return self._run_via_compiler()

        if not self._region_id:
            return self._err("No region loaded. Reload the program.")

        # Reload the map (region consumed by previous run).
        # Use static preloads from ICM init= fields stored at load time.
        rid = self._ctrl.load_map(self._records, self._program_name,
                                  known_values=self._known_values,
                                  preloaded_a=self._preloaded_a or None)
        if rid is None:
            return self._err("Could not reload program into controller.")
        self._region_id = rid

        # Build inputs dict: {bus_addr: value} for all named inputs
        # Type-aware: signed and datetime pack lo/hi across primary+complement
        inputs_bus = {}
        for param, addr in self._input_map.items():
            val = self.named_values.get(param, 0)
            port_type = self._type_map.get(param, "numeric")

            if port_type == "signed":
                v = int(val) if val is not None else 0
                v64 = v & 0xFFFFFFFFFFFFFFFF
                inputs_bus[addr] = v64 & 0xFFFFFFFF           # low 32 bits
                hi_param = f"_{param}_hi"
                if hi_param in self._input_map:
                    inputs_bus[self._input_map[hi_param]] = (v64 >> 32) & 0xFFFFFFFF

            elif port_type == "datetime":
                v = int(val) if val is not None else 0
                inputs_bus[addr] = v & 0xFFFFFFFF
                hi_param = f"_{param}_hi"
                if hi_param in self._input_map:
                    inputs_bus[self._input_map[hi_param]] = (v >> 32) & 0xFFFFFFFF

            elif port_type == "alpha":
                # Pack first 4 chars as bytes into the primary address
                # (full string handling needs sequential cells — noted for future)
                s = str(val) if val else ""
                packed = 0
                for i, ch in enumerate(s[:4]):
                    packed |= (ord(ch) & 0xFF) << (i * 8)
                inputs_bus[addr] = packed

            else:
                # Numeric: normalise to 32-bit bus word.
                # Non-zero = 0xFFFFFFFF (true), zero = 0x00000000 (false).
                # This matches the VM bus word convention throughout the system.
                raw = int(val) if val is not None else 0
                inputs_bus[addr] = 0xFFFFFFFF if raw else 0

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
            # Normalise 32-bit bus word to single bit for display
            if val is not None:
                val = 1 if val else 0
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
        # Active programs (PondManager path)
        active_programs = {}
        for handle_id, handle in self._active_programs.items():
            prog_pond = handle["_pond"]
            ptt_status = {}
            if prog_pond._ptt is not None:
                from pond_ptt import STATUS_NAMES, TYPE_PRIMITIVE, TYPE_TILE_IN
                for idx, entry in prog_pond._ptt._entries.items():
                    if entry.entry_type in (TYPE_PRIMITIVE, TYPE_TILE_IN):
                        ptt_status[entry.label] = STATUS_NAMES.get(entry.status, str(entry.status))
            active_programs[handle_id] = {
                "program":  handle["program_name"],
                "pond_id":  handle["pond_id"],
                "inputs":   list(handle["input_map"].keys()),
                "outputs":  list(handle["output_map"].keys()),
                "ptt":      ptt_status,
            }

        return {
            "ok":               True,
            "name":             self.name,
            "pond_manager":     self._pond_mgr is not None,
            "ws_pond_id":       self._ws_pond.pond_id if self._ws_pond else None,
            "program":          self._program_name or "(none)",
            "cells":            self._cell_count,
            "region":           self._region_id or "(none)",
            "inputs":           list(self._input_map.keys()),
            "outputs":          list(self._output_map.keys()),
            "values":           dict(self.named_values),
            "runs":             len(self._runs),
            "last_ok":          self._last_run_ok,
            "fs_files":         list(self._fs.keys()),
            "prog_files":       list(self._prog_files.keys()),
            "prog_active":      self._prog_active,
            "active_programs":  active_programs,
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    def _err(self, msg: str) -> dict:
        return {"ok": False, "error": msg}
