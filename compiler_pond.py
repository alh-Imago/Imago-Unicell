"""
compiler_pond.py — CompilerPond: the self-hosting compiler as a persistent Pond

Wraps ImagoCompiler and Int32Compiler as a persistent LIBRARY Pond.
Always armed. Always ready. Accepts source, returns compiled cell map.
Multiple jobs can be submitted and retrieved by reference.

This is Phase 1 of the self-hosted boot layer described in:
  09_Standalone_Boot_and_Self_Hosting.md
  10_BIOS_Plus_Boot_Sequence.md

Architecture
============

The CompilerPond sits in the Tier 3 Core Pond zone at 0x00600000.
It is loaded by the boot sequence after COMPANION and Shore are running.
It is registered with Shore as a LIBRARY Pond and issues a COMPILE key
through COMPANION.

Any Pond needing to compile source submits a job via compile() and
retrieves the result via get_result(). In the VM this is synchronous.
On silicon it would use the pipeline queue model — reference in,
cell map out after compile depth ticks.

Usage
=====

    from compiler_pond import CompilerPond, boot_compiler_pond

    # Boot the compiler pond (called by boot sequence)
    cpond = boot_compiler_pond(arr, ctrl, shore, companion)

    # Submit a compile job
    ref = cpond.compile(
        source        = 'def add(a: int32, b: int32) -> int32: return a + b',
        function_name = 'add',
        compiler_type = 'int32',   # 'general' or 'int32'
    )

    # Retrieve result
    result = cpond.get_result(ref)
    if result:
        records   = result['records']
        input_map = result['input_map']
        out_addrs = result['output_addrs']

    # Load and run compiled program
    region_id = ctrl.load_map(records, 'add_program')
    output    = ctrl.run(region_id,
                         inputs={input_map['a']: 42, input_map['b']: 17},
                         capture_addresses=out_addrs)
    print(output)   # {result_address: 59}

"""

from __future__ import annotations
import imago_log

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from unicell_array import UniCellArray
    from controller import ImagoController
    from shore_v2 import ShoreV2
    from companion import Companion


# ── Compile job result ────────────────────────────────────────────────────────

@dataclass
class CompileResult:
    """Result of one compile job."""
    job_ref:      str
    source:       str
    function_name: str
    compiler_type: str                    # 'general' or 'int32'
    records:      list                    # CellMapRecord list
    input_map:    dict                    # {param_name: address}
    output_addrs: list                    # [output_address, ...]
    graph:        object                  # IR dependency graph
    cell_count:   int
    submitted_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    error:        Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def compile_time_ms(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.submitted_at) * 1000
        return 0.0

    def summary(self) -> dict:
        return {
            "job_ref":      self.job_ref,
            "function":     self.function_name,
            "compiler":     self.compiler_type,
            "cells":        self.cell_count,
            "ok":           self.ok,
            "error":        self.error,
            "ms":           round(self.compile_time_ms, 2),
        }


# ── CompilerPond ──────────────────────────────────────────────────────────────

class CompilerPond:
    """
    The self-hosting compiler as a persistent LIBRARY Pond.

    Wraps ImagoCompiler (general) and Int32Compiler (int32 specialised).
    Always armed. Accepts compile jobs, returns CellMapRecord lists.

    In the VM this is a Python object. On silicon it would be a spatial
    program running in the cell fabric at base_address=0x00600000.

    Boot tier: 3
    Boot order: 1 (COMPILER_POND) and 2 (INT32_COMPILER_POND)
    """

    BASE_ADDRESS      = 0x00600000
    INT32_BASE_ADDRESS = 0x00610000
    POND_NAME         = "compiler"

    def __init__(self,
                 array:      "UniCellArray",
                 shore:      "ShoreV2",
                 companion:  "Companion",
                 controller: "ImagoController"):
        self._array      = array
        self._shore      = shore
        self._companion  = companion
        self._ctrl       = controller
        self._jobs:  dict[str, CompileResult] = {}
        self._stats: dict = {
            "total_jobs":   0,
            "success":      0,
            "errors":       0,
            "total_cells":  0,
        }

        # Lazy-load compilers (heavy imports)
        self._general_compiler = None
        self._int32_compiler   = None

        imago_log.info(f"[COMPILER_POND] Initialised @ {hex(self.BASE_ADDRESS)}")

    # ── Compiler access ───────────────────────────────────────────────────────

    @property
    def general(self):
        if self._general_compiler is None:
            from compiler import ImagoCompiler
            self._general_compiler = ImagoCompiler()
        return self._general_compiler

    @property
    def int32(self):
        if self._int32_compiler is None:
            from compiler_int32 import Int32Compiler
            from fp_tiles import TileLibrary
            self._int32_compiler = Int32Compiler(tile_library=TileLibrary())
        return self._int32_compiler

    # ── Compile jobs ──────────────────────────────────────────────────────────

    def compile(self,
                source:        str,
                function_name: str,
                param_names:   Optional[list] = None,
                compiler_type: str = 'general',
                job_ref:       Optional[str] = None) -> str:
        """
        Submit a compile job. Returns job_ref.

        compiler_type: 'general' — Python AST compiler (boolean, control flow)
                       'int32'   — 32-bit integer specialised compiler

        Result available immediately in VM (synchronous).
        On silicon: result available after pipeline depth ticks.
        """
        ref = job_ref or str(uuid.uuid4())[:8]
        t0  = time.time()
        self._stats["total_jobs"] += 1

        imago_log.info(f"[COMPILER_POND] Job {ref}: compiling '{function_name}' "
              f"({compiler_type})")

        try:
            if compiler_type == 'int32':
                result = self._compile_int32(
                    ref, source, function_name, t0)
            else:
                result = self._compile_general(
                    ref, source, function_name,
                    param_names or [], t0)

            self._stats["success"]     += 1
            self._stats["total_cells"] += result.cell_count
            imago_log.info(f"[COMPILER_POND] Job {ref}: "
                  f"{result.cell_count} cells, "
                  f"{result.compile_time_ms:.1f}ms")

        except Exception as e:
            result = CompileResult(
                job_ref       = ref,
                source        = source,
                function_name = function_name,
                compiler_type = compiler_type,
                records       = [],
                input_map     = {},
                output_addrs  = [],
                graph         = None,
                cell_count    = 0,
                completed_at  = time.time(),
                error         = str(e),
            )
            self._stats["errors"] += 1
            imago_log.info(f"[COMPILER_POND] Job {ref}: ERROR — {e}")

        self._jobs[ref] = result
        return ref

    def _compile_general(self, ref, source, function_name,
                         param_names, t0) -> CompileResult:
        """Run the general Python AST compiler."""
        records, graph, input_map, output_addrs = \
            self.general.compile_function(source, function_name, param_names)

        # Include extra_records (storage cells for loops etc.)
        all_records = list(records) + list(self.general._extra_records)

        return CompileResult(
            job_ref       = ref,
            source        = source,
            function_name = function_name,
            compiler_type = 'general',
            records       = all_records,
            input_map     = input_map,
            output_addrs  = output_addrs,
            graph         = graph,
            cell_count    = len(all_records),
            completed_at  = time.time(),
        )

    def _compile_int32(self, ref, source, function_name, t0) -> CompileResult:
        """Run the int32 specialised compiler."""
        records, graph, input_bit_map, output_addrs, segments = \
            self.int32.compile_int32_function(source, function_name)

        # Flatten input_bit_map to first-bit addresses for convenience
        input_map = {
            name: bits[0] if bits else 0
            for name, bits in input_bit_map.items()
        }

        return CompileResult(
            job_ref       = ref,
            source        = source,
            function_name = function_name,
            compiler_type = 'int32',
            records       = list(records),
            input_map     = input_map,
            output_addrs  = output_addrs,
            graph         = graph,
            cell_count    = len(records),
            completed_at  = time.time(),
        )

    # ── Result retrieval ──────────────────────────────────────────────────────

    def get_result(self, job_ref: str) -> Optional[CompileResult]:
        """Retrieve a compile result by job reference. None if not found."""
        return self._jobs.get(job_ref)

    def result_ready(self, job_ref: str) -> bool:
        """True if a result exists for this job reference."""
        return job_ref in self._jobs

    def load_and_run(self,
                     job_ref:   str,
                     inputs:    dict,
                     name:      Optional[str] = None) -> Optional[dict]:
        """
        Convenience: compile result → load into array → run → return outputs.

        For 'general' compiler:
            inputs: {param_name: value} or {address: value}
            returns: {output_address: value}

        For 'int32' compiler:
            inputs: {param_name: integer_value}
            returns: {'result': integer_value}  (reconstructed from bits)

        Returns None if job not found or error.
        """
        result = self.get_result(job_ref)
        if result is None or not result.ok:
            return None

        program_name = name or f"{result.function_name}_{job_ref}"

        if result.compiler_type == 'int32':
            # Int32 uses bit-level addressing — use run_int32_function directly
            from compiler_int32 import run_int32_function
            from fp_tiles import TileLibrary
            try:
                val = run_int32_function(
                    result.source,
                    result.function_name,
                    inputs,
                    tile_library=TileLibrary(),
                )
                return {'result': val}
            except Exception as e:
                imago_log.info(f"[COMPILER_POND] load_and_run int32 error: {e}")
                return None
        else:
            # General compiler — load map and run via controller
            region_id = self._ctrl.load_map(result.records, program_name)
            if region_id is None:
                return None

            resolved_inputs = {}
            for k, v in inputs.items():
                if isinstance(k, str) and k in result.input_map:
                    resolved_inputs[result.input_map[k]] = v
                else:
                    resolved_inputs[k] = v

            return self._ctrl.run(
                region_id,
                inputs            = resolved_inputs,
                capture_addresses = result.output_addrs,
            )

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "name":          self.POND_NAME,
            "base_address":  hex(self.BASE_ADDRESS),
            "boot_tier":     3,
            "boot_order":    1,
            "always_armed":  True,
            "total_jobs":    self._stats["total_jobs"],
            "success":       self._stats["success"],
            "errors":        self._stats["errors"],
            "total_cells":   self._stats["total_cells"],
            "pending_jobs":  len(self._jobs),
        }

    def purge_jobs(self, max_age_s: float = 3600.0) -> int:
        """Remove completed jobs older than max_age_s seconds."""
        now = time.time()
        old = [ref for ref, r in self._jobs.items()
               if r.completed_at and (now - r.completed_at) > max_age_s]
        for ref in old:
            del self._jobs[ref]
        return len(old)

    def __repr__(self) -> str:
        return (f"CompilerPond("
                f"jobs={self._stats['total_jobs']} "
                f"ok={self._stats['success']} "
                f"err={self._stats['errors']})")


# ── Boot helper ───────────────────────────────────────────────────────────────

def boot_compiler_pond(array:      "UniCellArray",
                       controller: "ImagoController",
                       shore:      "ShoreV2",
                       companion:  "Companion") -> CompilerPond:
    """
    Boot the CompilerPond as part of the Tier 3 Core Pond sequence.

    Called by boot_core_ponds() in run_companion.py after Tier 2 is running.
    Registers with Shore, issues COMPILE key through COMPANION.

    Returns the live CompilerPond instance.
    """
    from shore_v2 import ShoreEntry
    from companion import KEY_TILE

    pond = CompilerPond(
        array      = array,
        shore      = shore,
        companion  = companion,
        controller = controller,
    )

    # Register with Shore as LIBRARY type
    shore.register(ShoreEntry(
        name          = "compiler",
        resource_type = "LIBRARY",
        local_address = CompilerPond.BASE_ADDRESS,
        base_address  = CompilerPond.BASE_ADDRESS,
        offset        = 0,
        pond_id       = abs(hash("compiler")) & 0xFFFF,
        ward_state    = "HEALTHY",
    ))

    # Issue compile key through COMPANION
    # (uses TILE key type — compiler is a special tile provider)
    try:
        admin_key = next(
            k for k in companion._keys.values()
            if k.key_type == "ADMIN" and k.holder_id == "companion"
        )
        companion.issue_tile_key("compiler_pond", "*", admin_key.key_id)
        imago_log.info(f"[COMPILER_POND] Compile key issued")
    except Exception as e:
        imago_log.info(f"[COMPILER_POND] Warning: could not issue compile key: {e}")

    imago_log.info(f"[COMPILER_POND] Armed @ {hex(CompilerPond.BASE_ADDRESS)}")
    imago_log.info(f"[COMPILER_POND] Compilers ready: general, int32")

    # Verify with a test compile
    ref = pond.compile(
        source        = "def test(a: int32, b: int32) -> int32: return a + b",
        function_name = "test",
        compiler_type = "int32",
        job_ref       = "boot_verify",
    )
    result = pond.get_result(ref)
    if result and result.ok:
        imago_log.info(f"[COMPILER_POND] Boot verify: OK "
              f"({result.cell_count} cells, "
              f"{result.compile_time_ms:.1f}ms)")
    else:
        imago_log.info(f"[COMPILER_POND] Boot verify: FAILED — "
              f"{result.error if result else 'no result'}")

    return pond
