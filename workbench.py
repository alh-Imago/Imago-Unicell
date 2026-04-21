"""
workbench.py — Imago UniCell Development Workbench

A browser-based control panel for the Imago simulator. Combines the
cell array visualiser with a full test and development interface:

  - Array configuration (cell count, 1 or 2 DIMMs)
  - Python source editor with compile and load
  - Built-in demo programs (12 demos covering all gate types)
  - Region manager (list, highlight, free individual regions)
  - Bus injection (inject values directly onto the bus)
  - Execution controls (step, run/pause, speed, cycle counter)
  - Cell inspector (click any cell for full state breakdown)
  - Array statistics and per-DIMM breakdown
  - Clear region / clear all
  - Export array state as JSON

Usage:
    python3 workbench.py
    Opens browser at http://localhost:7420

Embed in your own code:
    from workbench import Workbench
    wb = Workbench(port=7420)
    wb.serve()
"""

import json
import threading
import webbrowser
import time
import http.server
import traceback
import os
from typing import Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unicell import VAR_TRUE, VAR_FALSE, FUNCTION_LOAD_PATTERN
from unicell_array import UniCellArray
from controller import ImagoController, CellMapRecord, Region
from compiler import ImagoCompiler
from multi_dimm import MultiDimmController, system_address, split_system_address
from gate_states import GS_PASS, GS_NOT

# ── demo programs ─────────────────────────────────────────────────────────────

DEMOS = {
    "NOT gate": {
        "source": "def demo(a):\n    return not a\n",
        "function": "demo",
        "inputs": {"a": 0},
        "description": "Single NOT gate. Input a=0 => output 1. One cell.",
    },
    "AND gate": {
        "source": "def demo(a, b):\n    return a & b\n",
        "function": "demo",
        "inputs": {"a": 1, "b": 1},
        "description": "AND gate. a=1,b=1 => 1. Uses NOR(NOT_a,NOT_b) lowering.",
    },
    "OR gate": {
        "source": "def demo(a, b):\n    return a | b\n",
        "function": "demo",
        "inputs": {"a": 1, "b": 0},
        "description": "OR gate. a=1,b=0 => 1.",
    },
    "XOR gate": {
        "source": "def demo(a, b):\n    return a ^ b\n",
        "function": "demo",
        "inputs": {"a": 1, "b": 0},
        "description": "XOR gate. a=1,b=0 => 1. Watch the pipeline depth.",
    },
    "XNOR (equality)": {
        "source": "def demo(a, b):\n    return not (a ^ b)\n",
        "function": "demo",
        "inputs": {"a": 1, "b": 1},
        "description": "XNOR: equality test. a==b => 1.",
    },
    "NOR gate": {
        "source": "def demo(a, b):\n    return not (a | b)\n",
        "function": "demo",
        "inputs": {"a": 0, "b": 0},
        "description": "NOR: the primitive gate underlying all cells. a=0,b=0 => 1.",
    },
    "NAND gate": {
        "source": "def demo(a, b):\n    return not (a & b)\n",
        "function": "demo",
        "inputs": {"a": 1, "b": 1},
        "description": "NAND gate. a=1,b=1 => 0.",
    },
    "Mux (2:1)": {
        "source": "def demo(sel, a, b):\n    if sel:\n        return a\n    else:\n        return b\n",
        "function": "demo",
        "inputs": {"sel": 1, "a": 1, "b": 0},
        "description": "2:1 Mux. sel=1 selects a. Compiled as spatial mux.",
    },
    "Conditional mux": {
        "source": "def demo(sel, a, b):\n    if sel:\n        result = a\n    else:\n        result = b\n    return result\n",
        "function": "demo",
        "inputs": {"sel": 1, "a": 0, "b": 1},
        "description": "Mux using if/else with assigned variable. sel=1 picks a=0.",
    },
    "Majority vote": {
        "source": "def majority(a, b, c):\n    ab = a & b\n    bc = b & c\n    ac = a & c\n    return ab | bc | ac\n",
        "function": "majority",
        "inputs": {"a": 1, "b": 1, "c": 0},
        "description": "Majority of 3 bits. Two or more 1s => 1.",
    },
    "Pipeline depth 5": {
        "source": "def demo(a):\n    b = not a\n    c = not b\n    d = not c\n    e = not d\n    return not e\n",
        "function": "demo",
        "inputs": {"a": 0},
        "description": "5-stage NOT pipeline. Step through to watch the wave. a=0 => 1.",
    },
    "Multi-function library": {
        "source": "def my_and(a, b):\n    return a & b\n\ndef my_or(a, b):\n    return a | b\n\ndef demo(a, b, c):\n    ab = my_and(a, b)\n    return my_or(ab, c)\n",
        "function": "demo",
        "inputs": {"a": 1, "b": 1, "c": 0},
        "description": "(a AND b) OR c. a=1,b=1,c=0 => 1. Shows function inlining.",
    },
    "Double NOT": {
        "source": "def not_gate(x):\n    return not x\n\ndef demo(a):\n    return not_gate(not_gate(a))\n",
        "function": "demo",
        "inputs": {"a": 0},
        "description": "NOT(NOT(a)) = a. Cross-function inlining. a=0 => 0.",
    },
    "Loopback memory": {
        "source": None,
        "function": "__loopback__",
        "inputs": {},
        "description": "A loopback cell holding value 1. Runs indefinitely. Shows memory mode.",
    },
    "ECC — Bit Injection": {
        "source":      "",
        "function":    "__ecc_demo__",
        "inputs":      {},
        "description": "Allocates a storage cell with ECC enabled. Writes value 0xABCD1234, "
                       "then injects a single-bit error. ECC detects and corrects it. "
                       "Watch the log — corrected value matches original.",
    },
    "Pond + Bridge Monitor": {
        "source":      "",
        "function":    "__pond_demo__",
        "inputs":      {},
        "description": "Creates a PRIVATE COMPUTE Pond with MONITOR bridge. "
                       "Runs 20 simulated access cycles. The MONITOR tracks utilisation "
                       "and reports to the resource record. Check the log for stats.",
    },
    "Tile Library — Cache Hit": {
        "source":      "",
        "function":    "__tile_cache_demo__",
        "inputs":      {},
        "description": "Compiles int32_eq twice — first without a tile library (synthesises "
                       "from scratch), then with a tile library (instant cache hit). "
                       "Log shows cell counts and timing. The maturation curve in action.",
    },
    "Cross-Bridge Computation": {
        "source":      "",
        "function":    "__bridge_compute_demo__",
        "inputs":      {},
        "description": "Builds a NOT→INBOUND→POND→OUTBOUND chain. Input 0 should produce "
                       "output 1 after exactly 4 clock cycles. Step through to watch "
                       "the signal propagate one stage per cycle.",
    },
    "Self-Hosting Compiler": {
        "source":      "",
        "function":    "__compiler_pond_demo__",
        "inputs":      {},
        "description": "Demonstrates the self-hosting CompilerPond. Write source in the "
                       "editor, click Load Demo to compile via the CompilerPond, watch "
                       "the new Program Pond appear in the regions panel, then run it. "
                       "The compiler is a Pond running in the same NOR gate fabric.",
    },
}

# ── cell state helpers ────────────────────────────────────────────────────────

def cell_state(cell) -> str:
    if cell._config_mode:
        return "configuring"
    if cell.is_loopback and cell.start_flag:
        return "memory"
    if cell.start_flag and cell.data is not None:
        return "fired"
    if cell.start_flag:
        return "waiting"
    if (cell.gate_state == 0 and
            cell.input_address == 0 and cell.output_address == 0):
        return "blank"
    return "halted"


def gate_details(gs: int) -> list:
    names = [
        "G0: NOT(A,A)",   "G1: NOT(A,A)",   "G2: NOR(G1,G2)",
        "G3: NOR(G3,A)",  "G4: NOR(G3,A)",  "G5: NOR(G4,G5)",
        "G6: NOR(G6,A)",  "G7: SR-latch Q", "G8: Buffer/inv",
    ]
    return [
        ("[ON]  " if (gs >> i) & 1 else "[off] ") + n
        for i, n in enumerate(names)
    ]


def array_snapshot(array: UniCellArray, fired: set, hl: set) -> dict:
    cells = []
    for addr in sorted(array.cells.keys()):
        c = array.cells[addr]
        st = cell_state(c)
        if addr in fired:
            st = "fired"
        cells.append({
            "address":        addr,
            "address_hex":    f"0x{addr:08X}",
            "gate_state":     c.gate_state,
            "gate_state_bin": f"0b{c.gate_state:09b}",
            "input_address":  f"0x{c.input_address:08X}",
            "output_address": f"0x{c.output_address:08X}",
            "is_loopback":    c.is_loopback,
            "start_flag":     c.start_flag,
            "data":           int(c.data) if c.data is not None else None,
            "config_mode":    c._config_mode,
            "state":          st,
            "highlighted":    addr in hl,
            "gate_details":   gate_details(c.gate_state),
        })
    return {
        "cells":       cells,
        "bus":         {f"0x{a:08X}": v for a, v in array.bus.items()},
        "total_cells": array._cell_count,
        "allocated":   len(array.cells),
        "defective":   len(array.defect_map),
    }

# ── Workbench ─────────────────────────────────────────────────────────────────

class Workbench:
    """
    Development workbench for the Imago UniCell simulator.
    Exposes a browser UI at http://localhost:{port}.
    """

    def __init__(self, port: int = 7420,
                 ctrl: "ImagoController" = None,
                 shore: "ShoreV2" = None,
                 companion: "Companion" = None,
                 core_ponds: dict = None):
        self.port      = port
        self._lock     = threading.Lock()
        self.ctrl      = ctrl or ImagoController(cell_count=256)
        self._shore    = shore
        self._comp     = companion
        self.core_ponds = core_ponds or {}
        self.use_multi = False
        self.multi     = None
        self._fired:    set = set()
        self._hl:       set = set()
        self._cycle     = 0
        self._running   = False
        self._programs  = []
        self._server    = None
        self._server_thread = None

    @property
    def array(self) -> UniCellArray:
        if self.use_multi and self.multi:
            return self.multi._dimms[0]
        return self.ctrl.array

    # ── snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        with self._lock:
            snap = array_snapshot(self.array, self._fired, self._hl)
            self._fired.clear()
            regs = (self.multi._regions if (self.use_multi and self.multi)
                    else self.ctrl._regions)
            region_list = [
                {
                    "region_id":  rid,
                    "image_name": r.image_name,
                    "state":      r.state,
                    "cell_count": len(r.cell_addresses),
                    "cycles_run": r.cycles_run,
                }
                for rid, r in regs.items()
                if r.state != Region.FREED
            ]
            dimm_stats = []
            if self.use_multi and self.multi:
                for slot, dimm in self.multi._dimms.items():
                    dimm_stats.append({
                        "slot": slot,
                        "allocated": len(dimm.cells),
                        "total": dimm._cell_count,
                    })
            else:
                dimm_stats.append({
                    "slot": 0,
                    "allocated": len(self.ctrl.array.cells),
                    "total": self.ctrl.array._cell_count,
                })
            snap["regions"]    = region_list
            snap["dimm_stats"] = dimm_stats
            snap["cycle"]      = self._cycle
            snap["demos"]      = list(DEMOS.keys())
            snap["demo_descriptions"] = {k: v["description"] for k, v in DEMOS.items()}
            snap["suite_names"] = [s for s, _ in Workbench.TEST_SUITES]
            snap["programs"]   = self._programs
            return snap

    # ── step ──────────────────────────────────────────────────────────────────

    def step(self) -> dict:
        with self._lock:
            about_to_fire = {
                addr for addr, c in self.array.cells.items()
                if c.start_flag and c.data is not None and not c._config_mode
            }
            self.array.tick()
            self._fired = about_to_fire
            self._cycle += 1
        return self.snapshot()

    # ── run / pause ───────────────────────────────────────────────────────────

    def start_run(self, ticks_per_sec: int = 6):
        if self._running:
            return
        self._running = True
        def _loop():
            delay = 1.0 / max(1, ticks_per_sec)
            while self._running:
                self.step()
                any_active = any(
                    c.start_flag for c in self.array.cells.values()
                )
                if not any_active:
                    self._running = False
                    break
                time.sleep(delay)
        threading.Thread(target=_loop, daemon=True).start()

    def pause_run(self):
        self._running = False

    # ── configure ─────────────────────────────────────────────────────────────

    def configure(self, cell_count: int, num_dimms: int) -> dict:
        with self._lock:
            self._running = False
            self._cycle   = 0
            self._programs.clear()
            self._fired.clear()
            self._hl.clear()
            if num_dimms >= 2:
                self.use_multi = True
                self.multi = MultiDimmController(cells_per_dimm=cell_count)
                self.multi.add_dimm(1)
            else:
                self.use_multi = False
                self.multi = None
                self.ctrl = ImagoController(cell_count=cell_count)
        return {"ok": True,
                "message": f"Configured: {num_dimms} DIMM(s), {cell_count} cells each"}

    # ── load demo ─────────────────────────────────────────────────────────────

    def load_demo(self, name: str) -> dict:
        if name not in DEMOS:
            return {"ok": False, "error": f"Demo '{name}' not found"}
        demo = DEMOS[name]
        fn = demo["function"]
        # Dispatch special demos
        if fn == "__loopback__":
            return self._load_loopback_demo()
        if fn == "__ecc_demo__":
            return self._demo_ecc()
        if fn == "__pond_demo__":
            return self._demo_pond()
        if fn == "__tile_cache_demo__":
            return self._demo_tile_cache()
        if fn == "__bridge_compute_demo__":
            return self._demo_bridge_compute()
        if fn == "__compiler_pond_demo__":
            return self._demo_compiler_pond()
        try:
            compiler = ImagoCompiler()
            src = demo["source"]
            inputs = demo["inputs"]
            records, graph, input_map, output_addrs = compiler.compile_function(
                src, fn, list(inputs.keys()))
            return self._load_records(records, fn, input_map, output_addrs, inputs)
        except Exception as e:
            return {"ok": False, "error": str(e), "trace": traceback.format_exc()}

    def _load_loopback_demo(self) -> dict:
        with self._lock:
            cell = self.array.allocate_cell()
            packet = [FUNCTION_LOAD_PATTERN, GS_PASS, cell.address, cell.address]
            self.array.write_config(cell.address, packet)
            self.array.bus[cell.address] = (1, 0)
            self.array.assert_start_flag([cell.address])
            region = Region([cell.address], "loopback_memory")
            region.state = Region.RUNNING
            self.ctrl._regions[region.region_id] = region
            self._programs.append({
                "name": "loopback_memory", "region_id": region.region_id,
                "input_map": {}, "output_addrs": [],
                "description": "Loopback memory cell",
            })
        return {"ok": True, "message": "Loopback memory loaded and running"}

    # ── special demo implementations ─────────────────────────────────────────

    def _demo_ecc(self) -> dict:
        """
        ECC demo: allocate a storage cell, write a value, inject a single-bit
        error, verify ECC detects and corrects it.
        """
        try:
            from unicell import FUNCTION_LOAD_PATTERN, _compute_ecc
            from controller import Region

            with self._lock:
                arr  = self.array
                ctrl = self.ctrl

                # Allocate a cell and configure it as a storage cell
                cell = arr.allocate_cell()
                arr.write_config(cell.address, [
                    FUNCTION_LOAD_PATTERN,
                    0b000000000,   # GS_PASS base
                    cell.address,
                    cell.address,
                ])
                c = arr.cells[cell.address]
                c.ecc_enabled  = True
                c.storage_mode = True
                c.start_flag   = True
                arr._armed.add(cell.address)

                # Write known value with correct ECC check word
                test_value  = 0xABCD1234
                correct_ecc = _compute_ecc(test_value)
                arr.bus[cell.address] = (test_value, correct_ecc)

                # Inject single-bit error: flip bit 7
                corrupted  = test_value ^ (1 << 7)
                arr.bus[cell.address] = (corrupted, correct_ecc)

                # Compute syndrome: XOR of expected ECC vs ECC of corrupted data
                actual_ecc = _compute_ecc(corrupted)
                syndrome   = correct_ecc ^ actual_ecc

                # Register as halted region so cells appear in grid
                region = Region([cell.address], "ecc_demo")
                region.state = Region.HALTED
                ctrl._regions[region.region_id] = region

            msgs = [
                f"Original value : 0x{test_value:08X}",
                f"ECC check word : 0x{correct_ecc:02X}",
                f"After bit-flip : 0x{corrupted:08X}  (bit 7 flipped)",
                f"ECC syndrome   : 0x{syndrome:02X}  ({'ERROR DETECTED' if syndrome else 'no error'})",
                f"Correctable    : {'YES — single-bit fault' if syndrome else 'N/A'}",
            ]
            for m in msgs:
                print(f"[ECC DEMO] {m}")

            return {
                "ok":       True,
                "message":  (
                    f"ECC: wrote 0x{test_value:08X}, flipped bit 7 → "
                    f"0x{corrupted:08X}, syndrome=0x{syndrome:02X} "
                    f"({'ERROR DETECTED — correctable' if syndrome else 'no error'})"
                ),
                "original":  hex(test_value),
                "corrupted": hex(corrupted),
                "syndrome":  hex(syndrome),
                "detected":  syndrome != 0,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "trace": traceback.format_exc()}

    def _demo_pond(self) -> dict:
        """
        Pond demo: create a PRIVATE COMPUTE Pond with MONITOR bridge,
        simulate access events, report utilisation stats.
        """
        try:
            import hashlib
            from pond import PondManager, PondBridge, PRIVATE, COMPUTE

            with self._lock:
                arr = self.array
                owner_id   = hashlib.sha256(b"workbench_owner").hexdigest()
                visitor_id = hashlib.sha256(b"workbench_visitor").hexdigest()
                stranger_id= hashlib.sha256(b"stranger").hexdigest()

                mgr  = PondManager(arr)
                pond = mgr.create_pond(
                    "demo_pond", owner_id,
                    security_level     = PRIVATE,
                    pond_type          = COMPUTE,
                    bridge_count       = 3,     # INBOUND + OUTBOUND + MONITOR
                    inbound_lanes      = 2,
                    throttle_threshold = 60.0,
                    utilisation_window = 10,
                )

                inbound = pond.bridges[0]
                monitor = pond.bridges[2]

                # Grant visitor access
                pond.grant_access(visitor_id, label="visitor")

                # Simulate 20 cycles of mixed access
                admitted = 0
                rejected = 0
                for i in range(20):
                    # Alternate between visitor (admitted) and stranger (rejected)
                    identity = visitor_id if i % 3 != 0 else stranger_id
                    ok, _ = inbound.check_access(identity)
                    if ok:
                        admitted += 1
                    else:
                        rejected += 1
                    # Record emissions on MONITOR (1 emission every other cycle)
                    monitor.record_cycle(1 if i % 2 == 0 else 0)

                rec  = pond.resource_record()
                util = monitor.utilisation_pct
                throttled = monitor.is_throttled

            msgs = [
                f"Pond: {pond.pond_id}  security=PRIVATE  type=COMPUTE",
                f"INBOUND lanes: {inbound.lane_width}  MONITOR capacity: {monitor.capacity_per_cycle}",
                f"Access events: {admitted} admitted, {rejected} rejected",
                f"MONITOR utilisation: {util:.1f}%  throttled: {throttled}",
                f"Total bridge cells: {rec['total_bridge_cells']}",
            ]
            for m in msgs:
                print(f"[POND DEMO] {m}")

            return {
                "ok":       True,
                "message":  (
                    f"Pond '{pond.pond_id}': {admitted} admitted, "
                    f"{rejected} rejected. MONITOR: {util:.1f}% util "
                    f"({'THROTTLED' if throttled else 'OK'}). "
                    f"{rec['total_bridge_cells']} bridge cells total."
                ),
                "pond_id":         pond.pond_id,
                "admitted":        admitted,
                "rejected":        rejected,
                "utilisation_pct": round(util, 1),
                "is_throttled":    throttled,
                "total_bridge_cells": rec["total_bridge_cells"],
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "trace": traceback.format_exc()}

    def _demo_tile_cache(self) -> dict:
        """
        Tile library cache demo: compile int32_eq twice — once without
        the library (synthesise), once with (cache hit). Show the difference.
        """
        try:
            import time as _t
            from fp_tiles import TileLibrary
            from compiler import ImagoCompiler

            fn_src = "def int32_eq(a, b):\n    return a ^ b\n"

            # Without library — synthesise from scratch
            c1 = ImagoCompiler()
            t0 = _t.time()
            r1, _, _, _ = c1.compile_function(fn_src, "int32_eq", ["a", "b"])
            t_synth = (_t.time() - t0) * 1000

            # With library — cache hit
            lib = TileLibrary()
            c2  = ImagoCompiler(tile_library=lib)
            t1  = _t.time()
            r2, _, _, _ = c2.compile_function(fn_src, "int32_eq", ["a", "b"])
            t_cache = (_t.time() - t1) * 1000

            stats = c2.cache_stats()

            msgs = [
                f"Without library: {len(r1)} cells synthesised  ({t_synth:.1f}ms)",
                f"With library:    {len(r2)} cells from tile   ({t_cache:.1f}ms)",
                f"Cache hit rate:  {stats['hit_rate_pct']}%",
                f"Time saved:      {stats['time_saved_ms']}ms",
                f"Tile is 763 cells (INT32_EQ) — synthesised was {len(r1)} cells",
            ]
            for m in msgs:
                print(f"[TILE CACHE] {m}")

            return {
                "ok": True,
                "message": (
                    f"Synthesised: {len(r1)} cells ({t_synth:.1f}ms)  →  "
                    f"Cache hit: {len(r2)} cells ({t_cache:.1f}ms).  "
                    f"Hit rate: {stats['hit_rate_pct']}%.  "
                    f"Tile library loaded the full INT32_EQ tile (763 cells, depth 23)."
                ),
                "synth_cells":   len(r1),
                "tile_cells":    len(r2),
                "synth_ms":      round(t_synth, 2),
                "cache_ms":      round(t_cache, 2),
                "cache_stats":   stats,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "trace": traceback.format_exc()}

    def _demo_bridge_compute(self) -> dict:
        """
        Cross-bridge computation demo: build a 4-cell chain
        NOT → INBOUND bridge → Pond internal → OUTBOUND bridge.
        Input 0 should produce output 1 after exactly 4 clock cycles.
        Load into the array so the user can Step through it.
        """
        try:
            from unicell import FUNCTION_LOAD_PATTERN, VAR_FALSE
            from controller import Region

            with self._lock:
                arr = self.array

                # Addresses for the signal path
                INPUT_ADDR  = 0xA000
                BRIDGE_A    = 0xA001
                POND_INT    = 0xA002
                BRIDGE_B    = 0xA003
                RESULT_ADDR = 0xA004

                # Allocate and configure 4 cells
                cells = []

                # NOT gate: reads INPUT_ADDR, posts to BRIDGE_A
                c_not = arr.allocate_cell()
                arr.write_config(c_not.address, [
                    FUNCTION_LOAD_PATTERN, 0b000000001,
                    INPUT_ADDR, BRIDGE_A
                ])
                cells.append(c_not.address)

                # INBOUND bridge cell: BRIDGE_A → POND_INT
                c_ib = arr.allocate_cell()
                arr.write_config(c_ib.address, [
                    FUNCTION_LOAD_PATTERN, 0b000000000,
                    BRIDGE_A, POND_INT
                ])
                cells.append(c_ib.address)

                # Pond internal PASS: POND_INT → BRIDGE_B
                c_pi = arr.allocate_cell()
                arr.write_config(c_pi.address, [
                    FUNCTION_LOAD_PATTERN, 0b000000000,
                    POND_INT, BRIDGE_B
                ])
                cells.append(c_pi.address)

                # OUTBOUND bridge cell: BRIDGE_B → RESULT_ADDR
                c_ob = arr.allocate_cell()
                arr.write_config(c_ob.address, [
                    FUNCTION_LOAD_PATTERN, 0b000000000,
                    BRIDGE_B, RESULT_ADDR
                ])
                cells.append(c_ob.address)

                # Inject input (0) and assert start flags
                arr.bus[INPUT_ADDR] = (VAR_FALSE, 0)
                arr.assert_start_flag(cells)

                # Register as a region
                region = Region(cells, "bridge_compute")
                region.state = Region.RUNNING
                self.ctrl._regions[region.region_id] = region
                self._programs.append({
                    "name": "bridge_compute",
                    "region_id": region.region_id,
                    "input_map":    {"input": hex(INPUT_ADDR)},
                    "output_addrs": [hex(RESULT_ADDR)],
                    "description":  "4 cells",
                })

            return {
                "ok":     True,
                "message": (
                    f"Cross-bridge chain loaded: 4 cells. "
                    f"Input 0 at 0x{INPUT_ADDR:04X}. "
                    f"Result appears at 0x{RESULT_ADDR:04X} after 4 steps. "
                    f"Click Step ▶ four times and watch the signal travel."
                ),
                "cells":       4,
                "input_addr":  hex(INPUT_ADDR),
                "result_addr": hex(RESULT_ADDR),
                "region_id":   region.region_id,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "trace": traceback.format_exc()}

    # ── compile and load ──────────────────────────────────────────────────────

    def compile_and_load(self, source: str, fn: str, input_values: dict) -> dict:
        try:
            compiler = ImagoCompiler()
            records, graph, input_map, output_addrs = compiler.compile_function(
                source, fn, list(input_values.keys()))
            return self._load_records(records, fn, input_map, output_addrs, input_values)
        except Exception as e:
            return {"ok": False, "error": str(e), "trace": traceback.format_exc()}

    def _load_records(self, records, name, input_map, output_addrs, input_values) -> dict:
        with self._lock:
            if self.use_multi and self.multi:
                region_id = self.multi.load_map(records, name)
            else:
                region_id = self.ctrl.load_map(records, name)
            if region_id is None:
                return {"ok": False, "error": "Security gate rejected or array full"}
            for param, addr in input_map.items():
                self.array.bus[addr] = (int(input_values.get(param, 0)), 0)
            self.array.assert_start_flag()
            self._programs.append({
                "name": name, "region_id": region_id,
                "input_map": {k: hex(v) for k, v in input_map.items()},
                "output_addrs": [hex(a) for a in output_addrs],
                "description": f"{len(records)} cells",
            })
        return {
            "ok": True, "region_id": region_id,
            "cells": len(records),
            "input_map": {k: hex(v) for k, v in input_map.items()},
            "output_addrs": [hex(a) for a in output_addrs],
            "message": f"Loaded '{name}': {len(records)} cells",
        }

    # ── region management ─────────────────────────────────────────────────────

    def highlight_region(self, region_id: str) -> dict:
        with self._lock:
            regs = (self.multi._regions if (self.use_multi and self.multi)
                    else self.ctrl._regions)
            if not region_id or region_id not in regs:
                self._hl.clear()
            else:
                self._hl = set(regs[region_id].cell_addresses)
        return {"ok": True}

    def free_region(self, region_id: str) -> dict:
        with self._lock:
            if self.use_multi and self.multi:
                ok = self.multi.free(region_id)
            else:
                ok = self.ctrl.free(region_id)
            if ok:
                self._programs = [p for p in self._programs
                                  if p["region_id"] != region_id]
                self._hl.clear()
        return {"ok": ok, "message": f"Freed {region_id}" if ok else "Free failed"}

    def clear_all(self) -> dict:
        with self._lock:
            self._running = False
            self._cycle   = 0
            self._programs.clear()
            self._fired.clear()
            self._hl.clear()
            if self.use_multi and self.multi:
                cc = self.multi.cells_per_dimm
                nd = len(self.multi._dimms)
                self.multi = MultiDimmController(cells_per_dimm=cc)
                for i in range(1, nd):
                    self.multi.add_dimm(i)
            else:
                cc = self.ctrl.array._cell_count
                self.ctrl = ImagoController(cell_count=cc)
        return {"ok": True, "message": "Array cleared"}

    # ── test runner ───────────────────────────────────────────────────────────

    # All 14 test suites with their display names
    TEST_SUITES = [
        ("test_array",                "Array & UniCell"),
        ("test_controller",           "Controller"),
        ("test_compiler",             "Compiler"),
        ("test_program_builder",      "Program Builder"),
        ("test_multi_dimm",           "Multi-DIMM"),
        ("test_ecc",                  "ECC"),
        ("test_fp_tiles",             "FP Tiles"),
        ("test_tile_library",         "Tile Library"),
        ("test_pond",                 "Pond Model"),
        ("test_uniflex",              "UniFlex FS"),
        ("test_cast",                 "Cast / Ripple"),
        ("test_shore",                "Shore"),
        ("test_bridge_integration",   "Bridge Integration"),
        ("test_compiler_tile_library","Compiler + Tiles"),
    ]

    def run_tests(self, suite_name: str = "all") -> dict:
        """
        Run one or all test suites. Returns results for display in the
        test runner panel.

        suite_name: module name (e.g. "test_pond") or "all"
        """
        import subprocess, re, time as _t

        suites_to_run = (
            self.TEST_SUITES if suite_name == "all"
            else [(s, d) for s, d in self.TEST_SUITES if s == suite_name]
        )
        if not suites_to_run:
            return {"ok": False, "error": f"Unknown suite: {suite_name}"}

        results   = []
        total_pass = 0
        total_fail = 0
        t_start   = _t.time()

        import os as _os
        # Get Python executable from environment — works on any platform
        # PYTHON_EXECUTABLE env var can be set to override (e.g. on odd setups)
        # Falls back to checking common names on PATH
        _py = (
            _os.environ.get('PYTHON_EXECUTABLE') or
            _os.environ.get('PYTHONPATH') and 'python' or
            'python'
        )
        for module, display in suites_to_run:
            t0 = _t.time()
            try:
                r = subprocess.run(
                    [_py, f"{module}.py"],
                    capture_output=True, text=True,
                    timeout=120,
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                )
                elapsed = _t.time() - t0
                out = r.stdout + r.stderr

                # Parse "Results: N passed, M failed"
                m = re.search(r"(\d+) passed, (\d+) failed", out)
                if m:
                    passed = int(m.group(1))
                    failed = int(m.group(2))
                else:
                    passed = 0
                    failed = 1   # process ran but no results line found

                total_pass += passed
                total_fail += failed

                # Collect individual FAIL lines for detail
                fail_lines = re.findall(r"\[FAIL\] (.+)", out)

                results.append({
                    "suite":      module,
                    "display":    display,
                    "passed":     passed,
                    "failed":     failed,
                    "elapsed_ms": round(elapsed * 1000),
                    "ok":         failed == 0,
                    "failures":   fail_lines[:10],  # cap at 10 for display
                })

            except subprocess.TimeoutExpired:
                elapsed = _t.time() - t0
                total_fail += 1
                results.append({
                    "suite":      module,
                    "display":    display,
                    "passed":     0,
                    "failed":     1,
                    "elapsed_ms": round(elapsed * 1000),
                    "ok":         False,
                    "failures":   ["TIMEOUT after 120s"],
                })
            except Exception as e:
                total_fail += 1
                results.append({
                    "suite":      module,
                    "display":    display,
                    "passed":     0,
                    "failed":     1,
                    "elapsed_ms": 0,
                    "ok":         False,
                    "failures":   [str(e)],
                })

        total_elapsed = round((_t.time() - t_start) * 1000)
        return {
            "ok":           total_fail == 0,
            "total_passed": total_pass,
            "total_failed": total_fail,
            "total_tests":  total_pass + total_fail,
            "elapsed_ms":   total_elapsed,
            "suites":       results,
            "suite_names":  [s for s, _ in self.TEST_SUITES],
        }

    def inject_bus(self, address_hex: str, value: int) -> dict:
        try:
            addr = int(address_hex, 16)
            with self._lock:
                self.array.bus[addr] = (value, 0)
            return {"ok": True, "message": f"Injected {value} at {address_hex}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def export_state(self) -> dict:
        snap = self.snapshot()
        return {"exported_at": time.time(), "cycle": self._cycle, "array": snap}

    # ── server ────────────────────────────────────────────────────────────────

    def start_server(self):
        WorkbenchHandler.wb = self
        self._server = http.server.HTTPServer(
            ('localhost', self.port), WorkbenchHandler)
        self._server_thread = threading.Thread(
            target=self._server.serve_forever, daemon=True)
        self._server_thread.start()
        print(f"[WORKBENCH] Serving at http://localhost:{self.port}")

    def stop_server(self):
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server = None


    # ── OS Shell ──────────────────────────────────────────────────────────────

    def attach_os(self, shore=None, companion=None,
                  devices=None, search_index=None):
        """Attach live OS components so the shell can query them."""
        self._shore   = shore
        self._comp    = companion
        self._devices = devices
        self._search  = search_index
        print("[WORKBENCH] OS components attached")

    def shell_cmd(self, line):
        """Execute one shell command. Returns {ok, type, output, headers?}."""
        line = line.strip()
        if not line or line.startswith("#"):
            return {"ok": True, "output": "", "type": "text"}
        parts = line.split()
        cmd   = parts[0].lower()
        args  = parts[1:]
        try:
            return self._sh(cmd, args, line)
        except Exception as exc:
            import traceback as tb
            return {"ok": False, "output": str(exc),
                    "type": "error", "trace": tb.format_exc()}

    def _sh_text(self, lines_list):
        return {"ok": True, "type": "text", "output": "\n".join(str(x) for x in lines_list)}

    def _sh_table(self, headers, rows):
        return {"ok": True, "type": "table", "headers": headers, "output": rows}

    def _sh_err(self, msg):
        return {"ok": False, "type": "error", "output": msg}

    def _sh(self, cmd, args, raw):
        import time as _time
        shore   = getattr(self, "_shore",   None)
        comp    = getattr(self, "_comp",    None)
        devices = getattr(self, "_devices", None)
        search  = getattr(self, "_search",  None)

        # help
        if cmd in ("help", "?", "h"):
            return self._sh_text([
                "IMAGO OS SHELL",
                "",
                "ARRAY",
                "  ps / regions         list loaded regions",
                "  df / array           array usage",
                "  kill <region>        free a region",
                "  freeze <region>      snapshot a region",
                "",
                "SHORE REGISTRY",
                "  ls [TYPE]            list Shore entries",
                "  cat <name>           inspect a Shore entry",
                "  ward <name>          show Ward state",
                "  ward --all           all Pond Ward states",
                "  escalate <n> <state> trigger COMPANION",
                "",
                "SEARCH",
                "  search <query>       heuristic file search",
                "  find / grep          aliases for search",
                "",
                "CAST",
                "  cast [key=value]     query registry",
                "    keys: pond_type  name_contains  ward_state",
                "          has_tile   search_query",
                "",
                "DEVICES",
                "  devices / dev        list device bridges",
                "",
                "COMPILER",
                "  tile                 list all tiles",
                "  tile <name>          inspect a tile",
                "  model                list all models",
                "  model <name>         inspect a model",
                "",
                "VM IMAGE",
                "  image save <path>    save system snapshot",
                "  image info           system state summary",
                "",
                "SYSTEM",
                "  ver / status         version and status",
                "  cls / clear          clear terminal",
                "  help / ?             this help",
            ])

        # clear
        if cmd in ("cls", "clear"):
            return {"ok": True, "type": "clear", "output": ""}

        # ps / regions
        if cmd in ("ps", "regions"):
            rows = []
            for rid, r in self.ctrl._regions.items():
                rows.append({
                    "region": rid,
                    "name":   r.image_name,
                    "cells":  len(r.cell_addresses),
                    "state":  r.state,
                    "cycles": r.cycles_run,
                })
            return self._sh_table(["region","name","cells","state","cycles"], rows)

        # df / array
        if cmd in ("df", "array"):
            arr   = self.ctrl.array
            used  = len(arr.cells)
            total = arr._cell_count
            pct   = used * 100 // total if total else 0
            bar   = ("+" * (pct // 5)).ljust(20, "-")
            return self._sh_text([
                "Array: %d/%d cells (%d%%)" % (used, total, pct),
                "[%s]" % bar,
                "Bus entries:  %d" % len(arr.bus),
                "Total cycles: %d" % self.ctrl.total_cycles,
            ])

        # kill
        if cmd == "kill":
            if not args:
                return self._sh_err("Usage: kill <region_id>")
            r = self.free_region(args[0])
            return {"ok": r.get("ok", False), "type": "text",
                    "output": r.get("message", r.get("error", ""))}

        # freeze
        if cmd == "freeze":
            if not args:
                return self._sh_err("Usage: freeze <region_id>")
            rid    = args[0]
            region = self.ctrl._regions.get(rid)
            if not region:
                return self._sh_err("Region '%s' not found" % rid)
            snap = self.ctrl.freeze(rid)
            if snap:
                return self._sh_text(["Frozen: %d cells snapshotted" % len(snap)])
            return self._sh_err("Freeze failed")

        # ls / dir
        if cmd in ("ls", "dir"):
            if shore is None:
                return self._sh_err("Shore not attached. Use wb.attach_os(shore=...)")
            filt = args[0].upper() if args else None
            rows = []
            for name, entry in shore._registry.items():
                if filt and entry.resource_type != filt:
                    continue
                rows.append({
                    "name":  name,
                    "type":  entry.resource_type,
                    "addr":  hex(entry.local_address) if entry.local_address else "-",
                    "ward":  entry.ward_state,
                    "id":    entry.pond_id or "-",
                })
            if not rows:
                return self._sh_text(["(no entries)" + (" of type %s" % filt if filt else "")])
            return self._sh_table(["name","type","addr","ward","id"], rows)

        # cat / inspect
        if cmd in ("cat", "inspect"):
            if not args:
                return self._sh_err("Usage: cat <pond_name>")
            if shore is None:
                return self._sh_err("Shore not attached")
            entry = shore.lookup(args[0])
            if not entry:
                return self._sh_err("'%s' not found in Shore registry" % args[0])
            import json as _json
            return self._sh_text([_json.dumps(entry.to_dict(), indent=2, default=str)])

        # ward
        if cmd == "ward":
            if shore is None:
                return self._sh_err("Shore not attached")
            if not args:
                return self._sh_err("Usage: ward <pond_name> | ward --all")
            if args[0] == "--all":
                rows = []
                now = _time.time()
                for name, entry in shore._registry.items():
                    if entry.resource_type == "POND":
                        rows.append({
                            "pond":     name,
                            "state":    entry.ward_state,
                            "ago":      "%.1fs" % (now - entry.last_seen),
                        })
                return self._sh_table(["pond","state","ago"], rows)
            entry = shore.lookup(args[0])
            if not entry:
                return self._sh_err("'%s' not found" % args[0])
            now = _time.time()
            return self._sh_text([
                "Pond:      %s" % args[0],
                "Ward:      %s" % entry.ward_state,
                "Type:      %s" % entry.resource_type,
                "Address:   %s" % (hex(entry.local_address) if entry.local_address else "-"),
                "Last seen: %.1fs ago" % (now - entry.last_seen),
                "Pond ID:   %s" % (entry.pond_id or "-"),
            ])

        # escalate
        if cmd == "escalate":
            if len(args) < 2:
                return self._sh_err("Usage: escalate <pond_name> <ward_state>")
            if shore is None or comp is None:
                return self._sh_err("Shore/Companion not attached")
            pond_name, state = args[0], args[1].upper()
            shore.update(pond_name, ward_state=state)
            escalations = shore.watch_wards()
            if escalations:
                return self._sh_text(["Escalated: %s [%s] -> COMPANION" % (pond_name, state)])
            return self._sh_text(["Updated ward to %s (no escalation triggered)" % state])

        # search / find / grep
        if cmd in ("search", "find", "grep"):
            if not args:
                return self._sh_err("Usage: search <query>")
            if search is None:
                return self._sh_err("Search index not attached")
            import os as _os
            query   = " ".join(args)
            results = search.search(query)
            if not results:
                return self._sh_text(["No results for '%s'" % query])
            rows = []
            for r in results[:20]:
                rows.append({
                    "score": r.score,
                    "term":  r.entry.term,
                    "file":  _os.path.basename(r.entry.file_path),
                    "pond":  r.pond_name,
                    "tags":  ", ".join(r.entry.tags) or "-",
                })
            return self._sh_table(["score","term","file","pond","tags"], rows)

        # cast
        if cmd == "cast":
            if shore is None:
                return self._sh_err("Shore not attached")
            if not args:
                return self._sh_err(
                    "Usage: cast [key=value] ...  "
                    "keys: pond_type name_contains ward_state has_tile search_query")
            query = {}
            for a in args:
                if "=" in a:
                    k, v = a.split("=", 1)
                    query[k] = v
                else:
                    query["name_contains"] = a
            rows = []
            for name, entry in shore._registry.items():
                ok = True
                if "pond_type" in query and entry.resource_type != query["pond_type"].upper():
                    ok = False
                if "name_contains" in query and query["name_contains"].lower() not in name.lower():
                    ok = False
                if "ward_state" in query and entry.ward_state != query["ward_state"].upper():
                    ok = False
                if ok:
                    rows.append({
                        "name": name,
                        "type": entry.resource_type,
                        "ward": entry.ward_state,
                        "addr": hex(entry.local_address) if entry.local_address else "-",
                    })
            if not rows:
                return self._sh_text(["No matches for %s" % query])
            return self._sh_table(["name","type","ward","addr"], rows)

        # devices / dev
        if cmd in ("devices", "dev"):
            if devices is None:
                return self._sh_err("Device manager not attached")
            rows = []
            for name, bridge in devices._bridges.items():
                st = bridge.status()
                rows.append({
                    "name":   name,
                    "type":   st["type"],
                    "base":   st["base"],
                    "status": st["status"],
                    "ticks":  st["ticks"],
                    "errors": st["errors"],
                })
            return self._sh_table(["name","type","base","status","ticks","errors"], rows)

        # tile
        if cmd == "tile":
            try:
                from fp_tiles import TileLibrary
                lib = TileLibrary()
                if not args:
                    rows = []
                    for n in sorted(lib.available()):
                        t = lib.get(n)
                        rows.append({"name": n,
                                     "depth": t.metadata.pipeline_depth,
                                     "cells": t.metadata.cell_count})
                    return self._sh_table(["name","depth","cells"], rows)
                t = lib.get(args[0].upper())
                m = t.metadata
                return self._sh_text([
                    "Tile:   %s" % args[0].upper(),
                    "Op:     %s" % m.operation,
                    "Depth:  %d ticks" % m.pipeline_depth,
                    "Cells:  %d" % m.cell_count,
                    "Notes:  %s" % (m.notes or "-"),
                ])
            except Exception as exc:
                return self._sh_err(str(exc))

        # model
        if cmd == "model":
            try:
                from model_library import model_library
                if not args:
                    rows = []
                    for spec in sorted(model_library._models.values(), key=lambda s: s.name):
                        rows.append({
                            "name":  spec.name,
                            "depth": spec.pipeline_depth,
                            "cells": spec.cell_count,
                            "ops":   ", ".join(spec.compiler_ops or []),
                        })
                    return self._sh_table(["name","depth","cells","ops"], rows)
                spec = model_library.get(args[0].upper())
                if not spec:
                    return self._sh_err("Model '%s' not found" % args[0])
                return self._sh_text([
                    "Model:   %s" % spec.name,
                    "Desc:    %s" % spec.description,
                    "Depth:   %d ticks" % spec.pipeline_depth,
                    "Cells:   %d" % spec.cell_count,
                    "Inputs:  %s" % spec.inputs,
                    "Outputs: %s" % spec.outputs,
                    "Ops:     %s" % spec.compiler_ops,
                ])
            except Exception as exc:
                return self._sh_err(str(exc))

        # image
        if cmd == "image":
            if not args:
                return self._sh_err("Usage: image save <path> | image info")
            sub = args[0].lower()
            if sub == "save":
                if len(args) < 2:
                    return self._sh_err("Usage: image save <path>")
                path = args[1]
                try:
                    from vm_image import save_image
                    import os as _os
                    save_image(path, self.ctrl, shore, comp, search_index=search)
                    size_kb = _os.path.getsize(path) / 1024
                    return self._sh_text(["Saved: %s (%.1f KB)" % (path, size_kb)])
                except Exception as exc:
                    return self._sh_err(str(exc))
            if sub == "info":
                s_ponds = str(len(search._ponds)) + " ponds" if search else "not attached"
                d_names = ",".join(devices._bridges) if devices else "not attached"
                return self._sh_text([
                    "Controller: %d regions, %d cycles" % (
                        len(self.ctrl._regions), self.ctrl.total_cycles),
                    "Shore:     %s" % ("attached" if shore else "not attached"),
                    "Companion: %s" % ("attached" if comp  else "not attached"),
                    "Search:    %s" % s_ponds,
                    "Devices:   %s" % d_names,
                ])
            return self._sh_err("Unknown image subcommand: %s" % sub)

        # compile
        if cmd == "compile":
            if len(args) < 2:
                return self._sh_err('Usage: compile "<source>" <function_name>')
            source = args[0].strip(chr(34)).strip(chr(39)).replace("\n", chr(10))
            fn     = args[1]
            r = self.compile_and_load(source, fn, {})
            if r.get("ok"):
                return self._sh_text([
                    "Compiled '%s': %s" % (fn, r.get("message", "")),
                    "Region: %s"        % r.get("region_id", ""),
                    "Output addrs: %s"  % r.get("output_addrs", []),
                ])
            return self._sh_err(r.get("error", "Compile failed"))

        # ver / status
        if cmd in ("ver", "version", "status"):
            from companion import OS_FULL_NAME
            arr  = self.ctrl.array
            used = len(arr.cells)
            total = arr._cell_count
            s_ponds = str(len(search._ponds)) + " ponds" if search else "not attached"
            d_names = ",".join(devices._bridges) if devices else "not attached"
            suites  = len(self.ctrl._regions)
            return self._sh_text([
                OS_FULL_NAME,
                "Imago UniCell Workbench",
                "─" * 32,
                "Array:     %d/%d cells" % (used, total),
                "Regions:   %d"          % suites,
                "Cycles:    %d"          % self.ctrl.total_cycles,
                "Shore:     %s"          % ("online" if shore else "not attached"),
                "Companion: %s"          % ("online" if comp  else "not attached"),
                "Devices:   %s"          % d_names,
                "Search:    %s"          % s_ponds,
            ])

        return self._sh_err("Unknown command: '%s'  (type help)" % cmd)


    def serve(self, open_browser: bool = True):
        self.start_server()
        url = f"http://localhost:{self.port}"
        if open_browser:
            time.sleep(0.3)
            webbrowser.open(url)
        print(f"[WORKBENCH] Open {url} in your browser")
        print("[WORKBENCH] Press Ctrl+C to stop")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print()
        finally:
            self.stop_server()


# ── HTTP handler ──────────────────────────────────────────────────────────────

class WorkbenchHandler(http.server.BaseHTTPRequestHandler):
    wb = None

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self._html(WORKBENCH_HTML)
        elif self.path == '/state':
            self._json(self.wb.snapshot())
        elif self.path == '/export':
            self._json(self.wb.export_state())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length) or b'{}')
        routes = {
            '/cmd/step':        lambda: self.wb.step(),
            '/cmd/run':         lambda: (self.wb.start_run(body.get('speed', 6)), {"ok": True})[1],
            '/cmd/pause':       lambda: (self.wb.pause_run(), {"ok": True})[1],
            '/cmd/configure':   lambda: self.wb.configure(
                                    body.get('cell_count', 256),
                                    body.get('num_dimms', 1)),
            '/cmd/load_demo':   lambda: self.wb.load_demo(body.get('name', '')),
            '/cmd/compile':     lambda: self.wb.compile_and_load(
                                    body.get('source', ''),
                                    body.get('function_name', 'demo'),
                                    body.get('inputs', {})),
            '/cmd/highlight':   lambda: self.wb.highlight_region(body.get('region_id', '')),
            '/cmd/free_region': lambda: self.wb.free_region(body.get('region_id', '')),
            '/cmd/clear_all':   lambda: self.wb.clear_all(),
            '/cmd/inject_bus':  lambda: self.wb.inject_bus(
                                    body.get('address', '0x0'),
                                    body.get('value', 0)),
            '/cmd/run_tests':   lambda: self.wb.run_tests(
                                    body.get('suite', 'all')),
            '/cmd/shell':       lambda: self.wb.shell_cmd(
                                    body.get('line', '')),
        }
        handler = routes.get(self.path)
        if handler:
            self._json(handler())
        else:
            self.send_response(404)
            self.end_headers()

    def _html(self, html):
        b = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(b))
        self.end_headers()
        self.wfile.write(b)

    def _json(self, data):
        b = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(b))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b)

# ── HTML workbench page ───────────────────────────────────────────────────────

WORKBENCH_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Imago Workbench</title>
<style>
:root{
  --bg:#0d1117;--panel:#161b22;--border:#30363d;
  --text:#c9d1d9;--muted:#8b949e;--accent:#58a6ff;
  --green:#3fb950;--yellow:#d29922;--purple:#a371f7;
  --red:#f85149;--orange:#f0883e;
  --c-blank:#21262d;--c-blank-b:#30363d;
  --c-waiting:#1f6feb;--c-waiting-b:#388bfd;
  --c-fired:#238636;--c-fired-b:#3fb950;
  --c-memory:#9a6700;--c-memory-b:#d29922;
  --c-halted:#6e4a7e;--c-halted-b:#a371f7;
  --c-config:#b08800;--c-config-b:#f0d000;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);
  font-family:'Consolas','Courier New',monospace;font-size:12px;
  display:flex;flex-direction:column;height:100vh;overflow:hidden}

/* header */
header{background:var(--panel);border-bottom:1px solid var(--border);
  padding:7px 14px;display:flex;align-items:center;gap:14px;flex-shrink:0}
header h1{font-size:13px;color:var(--accent);letter-spacing:1px}
.hs{color:var(--muted);font-size:11px}.hs span{color:var(--text)}

/* exec bar */
.eb{background:var(--panel);border-bottom:1px solid var(--border);
  padding:5px 14px;display:flex;align-items:center;gap:8px;flex-shrink:0;flex-wrap:wrap}
button{background:#21262d;color:var(--text);border:1px solid var(--border);
  border-radius:4px;padding:3px 11px;cursor:pointer;font-family:inherit;
  font-size:11px;white-space:nowrap}
button:hover{background:#30363d}
button.act{background:#238636;border-color:#3fb950;color:#fff}
button.warn{border-color:var(--red);color:var(--red)}
button.warn:hover{background:#3d1c1c}
input[type=range]{width:75px;accent-color:var(--accent);vertical-align:middle}
.lbl{color:var(--muted);font-size:11px}
.cyc{margin-left:auto;color:var(--muted);font-size:11px}
.cyc span{color:var(--accent);font-weight:bold}

/* legend */
.leg{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.ld{width:8px;height:8px;border-radius:2px;display:inline-block;margin-right:2px}
.li{font-size:10px;color:var(--muted);display:flex;align-items:center}

/* layout */
.row{display:flex;flex:1;overflow:hidden}

/* left panel */
#L{width:220px;flex-shrink:0;background:var(--panel);
  border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden}
.lp{border-bottom:1px solid var(--border);padding:7px 10px;flex-shrink:0}
.lp h3{font-size:10px;color:var(--muted);text-transform:uppercase;
  letter-spacing:1px;margin-bottom:5px}
.fr{display:flex;gap:5px;align-items:center;margin-bottom:4px}
.fr label{color:var(--muted);font-size:11px;width:60px;flex-shrink:0}
input[type=number],input[type=text],select,textarea{
  background:#21262d;color:var(--text);border:1px solid var(--border);
  border-radius:3px;padding:2px 6px;font-family:inherit;font-size:11px;width:100%}
textarea{resize:vertical;min-height:75px;line-height:1.4}
input[type=number]{width:72px}
.fb{width:100%;margin-top:3px;padding:4px;text-align:center}

/* region list */
#RL{flex:1;overflow-y:auto;padding:4px 8px}
.ri{padding:4px 7px;border-radius:3px;cursor:pointer;
  margin-bottom:2px;border:1px solid var(--border);background:#21262d}
.ri:hover{background:#30363d}
.ri.sel{border-color:var(--accent);background:#0d2149}
.rn{font-size:11px;color:var(--text)}
.rm{font-size:10px;color:var(--muted)}
.rs{font-size:10px;margin-top:1px}
.sc{color:#388bfd}.sr{color:#3fb950}.sh{color:var(--purple)}.sf{color:var(--muted)}

/* log */
#LOG{font-size:10px;color:var(--muted);padding:5px 10px;
  max-height:80px;overflow-y:auto;border-top:1px solid var(--border);flex-shrink:0}
.ml{padding:1px 0}
.ml.ok{color:#3fb950}.ml.err{color:var(--red)}.ml.info{color:var(--accent)}

/* grid */
#GW{flex:1;overflow:auto;padding:10px;
  display:flex;align-items:flex-start;justify-content:flex-start}
#GR{display:grid;gap:2px}
.cell{border-radius:3px;border:1.5px solid transparent;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  font-size:0;transition:transform .05s,filter .05s}
.cell:hover{transform:scale(1.2);filter:brightness(1.4);z-index:10}
.cell.sel{outline:2px solid var(--accent);outline-offset:1px;z-index:11}
.cell.hl{outline:2px solid var(--yellow);outline-offset:1px}
.cell.sel.hl{outline-color:var(--orange)}
.cell[data-state="blank"]{background:var(--c-blank);border-color:var(--c-blank-b)}
.cell[data-state="waiting"]{background:var(--c-waiting);border-color:var(--c-waiting-b)}
.cell[data-state="fired"]{background:var(--c-fired);border-color:var(--c-fired-b);animation:pls .25s}
.cell[data-state="memory"]{background:var(--c-memory);border-color:var(--c-memory-b)}
.cell[data-state="halted"]{background:var(--c-halted);border-color:var(--c-halted-b)}
.cell[data-state="configuring"]{background:var(--c-config);border-color:var(--c-config-b)}
@keyframes pls{0%{filter:brightness(2.5)}100%{filter:brightness(1)}}

/* right inspector */
#R{width:255px;flex-shrink:0;background:var(--panel);
  border-left:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden}
#R h2{padding:7px 12px;font-size:10px;color:var(--accent);
  border-bottom:1px solid var(--border);letter-spacing:1px;text-transform:uppercase}
#CD{flex:1;overflow-y:auto;padding:9px 11px;font-size:11px;line-height:1.6}
.dr{display:flex;gap:5px;border-bottom:1px solid #21262d;padding:2px 0}
.dl{color:var(--muted);width:95px;flex-shrink:0}
.dv{color:var(--text);word-break:break-all}
.dv.on{color:#3fb950}.dv.off{color:#6e7681}
.gt{margin-top:7px;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:1px}
.gi{font-size:10px;padding:1px 0}
.gi.gon{color:var(--yellow)}.gi.goff{color:#6e7681}

/* bus panel */
#BP{border-top:1px solid var(--border);padding:7px 11px;max-height:110px;overflow-y:auto}
#BP h3{font-size:10px;color:var(--muted);text-transform:uppercase;
  letter-spacing:1px;margin-bottom:3px}
.be{display:flex;gap:6px;font-size:10px;padding:1px 0}
.ba{color:var(--accent)}.bv{color:#3fb950}

::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}

/* test runner panel */
#TR{border-bottom:1px solid var(--border);padding:7px 10px;flex-shrink:0}
#TR h3{font-size:10px;color:var(--muted);text-transform:uppercase;
  letter-spacing:1px;margin-bottom:5px}
.ts{display:flex;align-items:center;gap:4px;margin-bottom:3px;flex-wrap:wrap}
.ts select{flex:1;min-width:0}
#tRes{max-height:160px;overflow-y:auto;margin-top:5px;font-size:10px}
.tr-suite{padding:2px 5px;border-radius:3px;margin-bottom:1px;
  display:flex;justify-content:space-between;align-items:center;
  border:1px solid transparent}
.tr-suite.pass{border-color:#238636;background:#0d2d12}
.tr-suite.fail{border-color:var(--red);background:#2d0d0d}
.tr-suite.run {border-color:var(--yellow);background:#2d2000}
.tr-name{color:var(--text)}
.tr-count{color:var(--muted)}
.tr-fail{color:var(--red);font-size:9px;padding-left:8px;margin-top:1px}
.tr-summary{margin-top:4px;padding:3px 6px;border-radius:3px;
  font-size:11px;font-weight:bold;text-align:center}
.tr-summary.all-pass{background:#0d2d12;color:#3fb950;border:1px solid #238636}
.tr-summary.has-fail{background:#2d0d0d;color:var(--red);border:1px solid var(--red)}

/* ── Shell panel ─────────────────────────────────────────────────────── */
#SH{width:360px;flex-shrink:0;background:#080d08;border-left:1px solid #1a3a1a;
  display:flex;flex-direction:column;overflow:hidden;position:relative;}
#SH::before{content:'';position:absolute;inset:0;pointer-events:none;z-index:0;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,
  rgba(0,255,0,0.018) 2px,rgba(0,255,0,0.018) 4px);}
#sh-hdr{background:#050a05;border-bottom:1px solid #1a3a1a;padding:5px 10px;
  font-size:10px;color:#2d5c2d;letter-spacing:2px;text-transform:uppercase;
  flex-shrink:0;display:flex;align-items:center;gap:6px;z-index:1;}
#sh-hdr b{color:#4daa4d;}
#sh-out{flex:1;overflow-y:auto;padding:7px 10px;font-size:11px;line-height:1.55;
  z-index:1;scrollbar-width:thin;scrollbar-color:#1a3a1a #080d08;}
#sh-out::-webkit-scrollbar{width:4px}
#sh-out::-webkit-scrollbar-thumb{background:#1a3a1a}
.shl{margin-bottom:1px}
.sh-p{color:#1e5c1e;user-select:none}.sh-c{color:#5acc5a}
.sh-ok{color:#4daa4d}.sh-er{color:#c04040}.sh-mu{color:#2a5a2a}
.sh-tbl{border-collapse:collapse;margin:3px 0;font-size:10px;width:100%;max-width:340px}
.sh-tbl th{color:#2a7a2a;border-bottom:1px solid #1a3a1a;padding:1px 7px 2px 0;
  text-align:left;font-weight:normal;letter-spacing:1px;text-transform:uppercase}
.sh-tbl td{color:#4daa4d;padding:1px 7px 1px 0;border-bottom:1px solid #0b1f0b;
  white-space:nowrap;overflow:hidden;max-width:180px;text-overflow:ellipsis}
.sh-tbl tr:last-child td{border-bottom:none}
#sh-form{display:flex;align-items:center;border-top:1px solid #1a3a1a;
  background:#050a05;padding:5px 8px;flex-shrink:0;z-index:1;}
#sh-ps{color:#1e5c1e;font-size:11px;white-space:nowrap;margin-right:4px}
#sh-in{flex:1;background:transparent;border:none;outline:none;
  color:#5acc5a;font-family:inherit;font-size:11px;caret-color:#4daa4d;}
#sh-in::placeholder{color:#1a3a1a}

</style>
</head>
<body>

<header>
  <h1>⬡ IMAGO WORKBENCH</h1>
  <div class="hs">Cells: <span id="ha">—</span>/<span id="ht" id="hdr-cells" data-count="256">—</span></div>
  <div class="hs">Bus: <span id="hb">0</span></div>
  <div class="hs">Regions: <span id="hr">0</span></div>
  <div class="hs">DIMMs: <span id="hd">—</span></div>
</header>

<div class="eb">
  <button id="bStep" onclick="step()">Step ▶</button>
  <button id="bRun"  onclick="toggleRun()">Run ▶▶</button>
  <button class="warn" onclick="clearAll()">Clear All ✕</button>
  <span class="lbl">Speed<input type="range" id="spd" min="1" max="30" value="6"></span>
  <span class="lbl">Zoom<input type="range" id="zoom" min="12" max="56" value="22"
    oninput="if(last)renderGrid(last)"></span>
  <div class="leg">
    <span class="li"><span class="ld" style="background:#21262d;border:1px solid #30363d"></span>Blank</span>
    <span class="li"><span class="ld" style="background:#1f6feb"></span>Waiting</span>
    <span class="li"><span class="ld" style="background:#238636"></span>Fired</span>
    <span class="li"><span class="ld" style="background:#9a6700"></span>Memory</span>
    <span class="li"><span class="ld" style="background:#6e4a7e"></span>Halted</span>
  </div>
  <div class="cyc">Cycle <span id="cy">0</span></div>
</div>

<div class="row">

<!-- LEFT -->
<div id="L">

  <div class="lp">
    <h3>Array Config</h3>
    <div class="fr"><label>Cells</label>
      <input type="number" id="cfgC" value="256" min="8" max="65536" step="8" style="width:72px"></div>
    <div class="fr"><label>DIMMs</label>
      <select id="cfgD">
        <option value="1">1 DIMM</option>
        <option value="2">2 DIMMs</option>
      </select></div>
    <button class="fb" onclick="configure()">Apply</button>
  </div>

  <div class="lp">
    <h3>Demo Programs</h3>
    <select id="demoSel" style="margin-bottom:3px" onchange="updateDemoDesc()"></select>
    <div id="demoDesc" style="color:var(--muted);font-size:10px;min-height:24px;margin-bottom:3px;line-height:1.4"></div>
    <button class="fb" onclick="loadDemo()">Load Demo</button>
  </div>

  <div class="lp" style="flex:1;display:flex;flex-direction:column;min-height:0">
    <h3>Compile Python</h3>
    <textarea id="srcEd" placeholder="def demo(a, b):&#10;    return a &amp; b"
      style="flex:1;min-height:65px;margin-bottom:3px"></textarea>
    <div class="fr"><label>Function</label>
      <input type="text" id="fnName" value="demo" style="flex:1"></div>
    <div id="inpRows" style="margin-bottom:3px"></div>
    <button class="fb" onclick="parseInputs()">↻ Parse Inputs</button>
    <button class="fb" style="margin-top:2px;background:#238636;border-color:#3fb950;color:#fff"
      onclick="compile()">▶ Compile + Load</button>
  </div>

  <div class="lp">
    <h3>Bus Inject</h3>
    <div class="fr"><label>Address</label>
      <input type="text" id="injA" value="0x1000" style="flex:1"></div>
    <div class="fr"><label>Value</label>
      <input type="number" id="injV" value="1" min="0" max="1" style="width:50px"></div>
    <button class="fb" onclick="inject()">Inject</button>
  </div>

  <div id="TR">
    <h3>Test Runner</h3>
    <div class="ts">
      <select id="tSel">
        <option value="all">— All 14 suites —</option>
      </select>
      <button onclick="runTests()" style="white-space:nowrap">▶ Run</button>
    </div>
    <div id="tRes"></div>
  </div>

  <div style="border-bottom:1px solid var(--border);padding:5px 10px;flex-shrink:0">
    <span style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px">Regions</span>
  </div>
  <div id="RL"></div>
  <div id="LOG"></div>
</div>

<!-- GRID -->
<div id="GW"><div id="GR"></div></div>

<!-- RIGHT -->
<div id="SH">
  <div id="sh-hdr">&#x2B21; <b>IMAGO</b> OS SHELL</div>
  <div id="sh-out"></div>
  <div id="sh-form">
    <span id="sh-ps">imago&gt;&nbsp;</span>
    <input id="sh-in" type="text" placeholder="type a command or help..."
           autocomplete="off" spellcheck="false">
  </div>
</div>

<div id="R">
  <h2>Cell Inspector</h2>
  <div id="CD" style="color:var(--muted);line-height:1.7">
    Click any cell to inspect its state.<br><br>
    <b style="color:var(--accent)">Colours:</b><br>
    Blue &nbsp;= waiting for data<br>
    Green = fired this tick<br>
    Gold &nbsp;= loopback memory<br>
    Purple= halted (one-fire done)<br>
    Dark &nbsp;= unallocated<br><br>
    <b style="color:var(--yellow)">Yellow outline</b> = highlighted region<br>
    <b style="color:var(--accent)">Blue outline</b> = selected cell
  </div>
  <div id="BP">
    <h3>Bus State</h3>
    <div id="BC"><span style="color:var(--muted);font-style:italic">Empty</span></div>
  </div>
</div>

</div><!-- row -->

<script>
let last=null, running=false, selCell=null, selRegion=null, runTimer=null;
let demoDescs = {};

async function api(path,body=null){
  const r = await fetch(path, body!==null
    ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}
    : {});
  return r.json();
}

function log(msg, type='info'){
  const el=document.getElementById('LOG');
  const d=document.createElement('div');
  d.className='ml '+type; d.textContent='› '+msg;
  el.prepend(d);
  while(el.children.length>25) el.removeChild(el.lastChild);
}

function renderGrid(data){
  if(!data) return; last=data;
  const cells=data.cells;
  const zoom=parseInt(document.getElementById('zoom').value);
  const avail=document.getElementById('GW').clientWidth-20;
  const nc=Math.max(1,Math.floor(avail/(zoom+2)));
  const gr=document.getElementById('GR');
  gr.style.gridTemplateColumns=`repeat(${nc},${zoom}px)`;

  while(gr.children.length<cells.length){
    const el=document.createElement('div');
    el.className='cell';
    const i=gr.children.length;
    el.addEventListener('click',()=>selectCell(i));
    gr.appendChild(el);
  }
  while(gr.children.length>cells.length) gr.removeChild(gr.lastChild);

  cells.forEach((c,i)=>{
    const el=gr.children[i];
    el.setAttribute('data-state',c.state);
    el.style.width=el.style.height=zoom+'px';
    el.title=c.address_hex+' ['+c.state+']';
    el.classList.toggle('sel', i===selCell);
    el.classList.toggle('hl', c.highlighted);
    if(zoom>=20){ el.textContent=c.address_hex.slice(-3); el.style.fontSize=Math.max(7,zoom*.22)+'px'; }
    else { el.textContent=''; el.style.fontSize='0'; }
  });

  document.getElementById('ha').textContent=data.allocated;
  const htEl = document.getElementById('ht');
  htEl.textContent=data.total_cells;
  htEl.dataset.count=data.total_cells;
  document.getElementById('hb').textContent=Object.keys(data.bus).length;
  document.getElementById('hr').textContent=data.regions.length;
  document.getElementById('hd').textContent=
    data.dimm_stats.map(d=>'S'+d.slot+':'+d.allocated+'/'+d.total).join(' ');
  document.getElementById('cy').textContent=data.cycle;

  const bc=document.getElementById('BC');
  const ents=Object.entries(data.bus);
  bc.innerHTML=ents.length
    ? ents.map(([a,v])=>`<div class="be"><span class="ba">${a}</span><span class="bv">= ${v}</span></div>`).join('')
    : '<span style="color:var(--muted);font-style:italic">Empty</span>';

  renderRegions(data.regions);
  if(selCell!==null && cells[selCell]) renderInspector(cells[selCell]);
}

function renderRegions(regions){
  const el=document.getElementById('RL');
  if(!regions.length){
    el.innerHTML='<div style="color:var(--muted);font-size:10px;padding:5px 7px">No regions loaded</div>';
    return;
  }
  el.innerHTML=regions.map(r=>`
    <div class="ri ${r.region_id===selRegion?'sel':''}" onclick="selReg('${r.region_id}')">
      <div class="rn">${r.image_name}</div>
      <div class="rm">${r.region_id} &middot; ${r.cell_count} cells</div>
      <div class="rs s${r.state[0].toLowerCase()}">${r.state} &middot; ${r.cycles_run} cyc
        <button style="float:right;padding:1px 5px;font-size:9px"
          onclick="event.stopPropagation();freeReg('${r.region_id}')">Free</button>
      </div>
    </div>`).join('');
}

function selectCell(i){
  selCell=i;
  document.querySelectorAll('.cell').forEach((el,j)=>el.classList.toggle('sel',j===i));
  if(last&&last.cells[i]) renderInspector(last.cells[i]);
}

function renderInspector(c){
  const sc={blank:'#6e7681',waiting:'#388bfd',fired:'#3fb950',
    memory:'#d29922',halted:'#a371f7',configuring:'#f0d000'}[c.state]||'#c9d1d9';
  const rows=[
    ['Address',    `<span style="color:var(--accent)">${c.address_hex}</span>`],
    ['State',      `<span style="color:${sc}">${c.state.toUpperCase()}</span>`],
    ['Gate state', `<span style="color:var(--yellow)">${c.gate_state_bin}</span> (${c.gate_state})`],
    ['Input addr', c.input_address],
    ['Output addr',c.output_address],
    ['Loopback',   c.is_loopback ?'<span class="dv on">YES — memory</span>':'<span class="dv off">no</span>'],
    ['Start flag', c.start_flag  ?'<span class="dv on">ASSERTED</span>':'<span class="dv off">clear</span>'],
    ['Data',       c.data!==null ?`<span class="dv on">${c.data}</span>`:'<span class="dv off">None</span>'],
    ['Config mode',c.config_mode ?'<span style="color:var(--yellow)">ACTIVE</span>':'<span class="dv off">no</span>'],
  ];
  const gh=c.gate_details.map(g=>{
    const on=g.startsWith('[ON]');
    return `<div class="gi ${on?'gon':'goff'}">${g}</div>`;
  }).join('');
  document.getElementById('CD').innerHTML=
    rows.map(([l,v])=>`<div class="dr"><span class="dl">${l}</span><span class="dv">${v}</span></div>`).join('')
    +'<div class="gt">Gate topology</div>'+gh;
}

async function selReg(rid){
  selRegion=selRegion===rid?null:rid;
  await api('/cmd/highlight',{region_id:selRegion||''});
  renderGrid(await api('/state'));
}

async function freeReg(rid){
  const r=await api('/cmd/free_region',{region_id:rid});
  log(r.message||(r.ok?'freed':r.error), r.ok?'ok':'err');
  if(selRegion===rid) selRegion=null;
  renderGrid(await api('/state'));
}

async function step(){
  renderGrid(await api('/cmd/step',{}));
}

async function toggleRun(){
  if(running){
    running=false; if(runTimer){clearTimeout(runTimer);runTimer=null;}
    document.getElementById('bRun').textContent='Run ▶▶';
    document.getElementById('bRun').classList.remove('act');
    await api('/cmd/pause',{});
    renderGrid(await api('/state')); return;
  }
  running=true;
  document.getElementById('bRun').textContent='Pause ⏸';
  document.getElementById('bRun').classList.add('act');
  const speed=parseInt(document.getElementById('spd').value);
  await api('/cmd/run',{speed});
  refresh();
}

function refresh(){
  if(!running) return;
  const spd=parseInt(document.getElementById('spd').value);
  runTimer=setTimeout(async()=>{
    const d=await api('/state');
    renderGrid(d);
    const any=d.cells.some(c=>['waiting','fired','memory'].includes(c.state));
    if(!any){running=false;document.getElementById('bRun').textContent='Run ▶▶';
      document.getElementById('bRun').classList.remove('act');return;}
    if(running) refresh();
  }, Math.max(40, Math.round(1000/spd)));
}

async function clearAll(){
  if(!confirm('Clear all regions and reset the array?')) return;
  running=false; if(runTimer){clearTimeout(runTimer);runTimer=null;}
  await api('/cmd/pause',{});
  const r=await api('/cmd/clear_all',{});
  log(r.message,r.ok?'ok':'err');
  selCell=null; selRegion=null;
  document.getElementById('CD').innerHTML='<span style="color:var(--muted)">Array cleared.</span>';
  renderGrid(await api('/state'));
}

async function configure(){
  const cc=parseInt(document.getElementById('cfgC').value)||256;
  const nd=parseInt(document.getElementById('cfgD').value)||1;
  const r=await api('/cmd/configure',{cell_count:cc,num_dimms:nd});
  log(r.message||r.error, r.ok?'ok':'err');
  selCell=null; selRegion=null;
  renderGrid(await api('/state'));
}

function updateDemoDesc(){
  const v=document.getElementById('demoSel').value;
  document.getElementById('demoDesc').textContent=demoDescs[v]||v;
}

function populateDemos(demos, descs){
  demoDescs=descs||{};
  const sel=document.getElementById('demoSel');
  if(sel.options.length) return;
  demos.forEach(d=>{ const o=new Option(d,d); sel.appendChild(o); });
  updateDemoDesc();
}

async function loadDemo(){
  const name=document.getElementById('demoSel').value;
  const r=await api('/cmd/load_demo',{name});
  log(r.message||r.error, r.ok?'ok':'err');
  renderGrid(await api('/state'));
}

function parseInputs(){
  const src=document.getElementById('srcEd').value;
  const fn=document.getElementById('fnName').value.trim();
  const m=src.match(new RegExp('def\\s+'+fn+'\\s*\\(([^)]*)\\)'));
  if(!m){log('Cannot parse function signature','err');return;}
  const params=m[1].split(',').map(p=>p.trim()).filter(Boolean);
  document.getElementById('inpRows').innerHTML=params.map(p=>`
    <div class="fr"><label>${p}</label>
      <input type="number" id="ip-${p}" value="0" min="0" max="1" style="width:45px">
    </div>`).join('');
  log('Parsed: '+params.join(', '),'info');
}

async function compile(){
  const src=document.getElementById('srcEd').value.trim();
  const fn=document.getElementById('fnName').value.trim();
  if(!src||!fn){log('Source and function name required','err');return;}
  const inputs={};
  document.querySelectorAll('[id^="ip-"]').forEach(el=>{
    inputs[el.id.slice(3)]=parseInt(el.value)||0;
  });
  const r=await api('/cmd/compile',{source:src,function_name:fn,inputs});
  log(r.ok ? r.message+' out:'+( r.output_addrs||[]).join(',') : r.error, r.ok?'ok':'err');
  renderGrid(await api('/state'));
}

async function inject(){
  const addr=document.getElementById('injA').value.trim();
  const val=parseInt(document.getElementById('injV').value)||0;
  const r=await api('/cmd/inject_bus',{address:addr,value:val});
  log(r.message||r.error, r.ok?'ok':'err');
  renderGrid(await api('/state'));
}

window.addEventListener('resize',()=>{if(last)renderGrid(last);});

// ── Test runner ───────────────────────────────────────────────────────────────

function populateTestSuites(names){
  const sel=document.getElementById('tSel');
  if(sel.options.length>1) return;
  names.forEach(n=>{
    const o=new Option(n.replace('test_','').replace(/_/g,' '),n);
    sel.appendChild(o);
  });
}

async function runTests(){
  const suite=document.getElementById('tSel').value;
  const res=document.getElementById('tRes');
  res.innerHTML='<div style="color:var(--yellow);padding:3px">Running…</div>';

  const r=await api('/cmd/run_tests',{suite});

  // Build result HTML
  let html='';
  (r.suites||[]).forEach(s=>{
    const cls=s.ok?'pass':'fail';
    const badge=s.ok
      ? `<span style="color:#3fb950">✓ ${s.passed}</span>`
      : `<span style="color:var(--red)">✗ ${s.failed} fail / ${s.passed} pass</span>`;
    html+=`<div class="tr-suite ${cls}">
      <span class="tr-name">${s.display}</span>
      <span class="tr-count">${badge} <span style="color:#6e7681">${s.elapsed_ms}ms</span></span>
    </div>`;
    if(s.failures && s.failures.length){
      html+=s.failures.map(f=>`<div class="tr-fail">↳ ${f}</div>`).join('');
    }
  });

  // Summary bar
  if(r.total_tests!==undefined){
    const allPass=r.total_failed===0;
    const cls=allPass?'all-pass':'has-fail';
    const icon=allPass?'✓':'✗';
    html+=`<div class="tr-summary ${cls}">${icon} ${r.total_passed}/${r.total_tests} passed · ${r.elapsed_ms}ms</div>`;
    log(`Tests: ${r.total_passed}/${r.total_tests} passed`, allPass?'ok':'err');
  } else {
    html+=`<div style="color:var(--red);font-size:10px;padding:3px">${r.error||'Unknown error'}</div>`;
    log('Test run failed: '+(r.error||''),'err');
  }

  res.innerHTML=html;
}

(async()=>{
  const d=await api('/state');
  populateDemos(d.demos||[], d.demo_descriptions||{});
  populateTestSuites(d.suite_names||[]);
  renderGrid(d);
  log('Workbench ready — load a demo or write Python above','info');
  shLine('IMAGO OS SHELL  type help for commands','mu');

  // Auto-poll every 2 seconds when --attach mode is active
  // so the grid updates automatically when the live system boots
  setInterval(async()=>{
    if(document.hidden) return;   // don't poll when tab is hidden
    try {
      const s = await api('/state');
      // Only re-render if cell count changed (system just attached)
      const cur = document.querySelector('#hdr-cells');
      const newCount = s.dimm_stats ? s.dimm_stats.reduce((a,d)=>a+d.total,0) : 0;
      if(cur && cur.dataset.count != newCount) {
        cur.dataset.count = newCount;
        renderGrid(s);
        if(newCount > 256) log('Live system attached — '+newCount+' cells','ok');
      }
    } catch(e){}
  }, 2000);
})();

// ── Shell terminal ───────────────────────────────────────────────────────────

const shHist=[];let shHIdx=-1;

function escH(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function shAppend(el){
  const out=document.getElementById('sh-out');
  out.appendChild(el);
  out.scrollTop=out.scrollHeight;
}

function shLine(text,cls){
  const d=document.createElement('div');
  d.className='shl';
  d.innerHTML='<span class="sh-'+cls+'">'+escH(text)+'</span>';
  shAppend(d);
}

function shTable(headers,rows){
  if(!rows||!rows.length)return;
  const tbl=document.createElement('table');
  tbl.className='sh-tbl';
  const tr=tbl.createTHead().insertRow();
  headers.forEach(h=>{const th=document.createElement('th');th.textContent=h;tr.appendChild(th);});
  const tb=tbl.createTBody();
  rows.forEach(row=>{
    const r=tb.insertRow();
    headers.forEach(h=>{const td=r.insertCell();td.textContent=row[h]!==undefined?row[h]:'-';});
  });
  const wrap=document.createElement('div');wrap.className='shl';wrap.appendChild(tbl);
  shAppend(wrap);
}

async function shRun(line){
  const t=line.trim();
  const d=document.createElement('div');d.className='shl';
  d.innerHTML='<span class="sh-p">imago&gt; </span><span class="sh-c">'+escH(t)+'</span>';
  shAppend(d);
  if(!t)return;
  shHist.unshift(t);if(shHist.length>60)shHist.pop();shHIdx=-1;
  const r=await api('/cmd/shell',{line:t});
  if(r.type==='clear'){document.getElementById('sh-out').innerHTML='';return;}
  if(r.type==='table'){
    if(r.output&&r.output.length) shTable(r.headers||[],r.output);
    else shLine('(empty)','mu');
    return;
  }
  const cls=r.ok?'ok':'er';
  const txt=String(r.output||'');
  if(txt) txt.split('\n').forEach(ln=>shLine(ln,cls));
  if(!r.ok&&r.trace){
    shLine('-- trace --','mu');
    r.trace.split('\n').slice(-4).forEach(ln=>shLine(ln,'mu'));
  }
}

const shIn=document.getElementById('sh-in');
shIn.addEventListener('keydown',async e=>{
  if(e.key==='Enter'){const v=shIn.value;shIn.value='';await shRun(v);}
  else if(e.key==='ArrowUp'){
    e.preventDefault();
    if(shHIdx<shHist.length-1){shHIdx++;shIn.value=shHist[shHIdx];
      setTimeout(()=>shIn.setSelectionRange(9999,9999),0);}
  }else if(e.key==='ArrowDown'){
    e.preventDefault();
    if(shHIdx>0){shHIdx--;shIn.value=shHist[shHIdx];}
    else{shHIdx=-1;shIn.value='';}
  }else if(e.key==='Tab'){
    e.preventDefault();
    const cmds=['help','ls','dir','ps','df','array','cat','ward','escalate',
      'search','find','grep','cast','devices','dev','kill','freeze',
      'compile','tile','model','image','ver','status','cls','clear'];
    const v=shIn.value;
    const m=cmds.filter(c=>c.startsWith(v));
    if(m.length===1)shIn.value=m[0]+' ';
    else if(m.length>1)shLine(m.join('  '),'mu');
  }
});
document.getElementById('SH').addEventListener('click',()=>shIn.focus());

</script>
</body>
</html>"""

# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Imago UniCell Workbench"
    )
    parser.add_argument("--port", type=int, default=7420,
                        help="Port to serve on (default: 7420)")
    parser.add_argument("--attach", action="store_true",
                        help="Boot full system (Tier 2 + Tier 3) and attach "
                             "workbench to it — shows live system state")
    parser.add_argument("--cells", type=int, default=100_000,
                        help="Cell count when using --attach (default: 100000)")
    parser.add_argument("--no-core-ponds", action="store_true",
                        help="With --attach: skip Tier 3 Core Ponds")
    args = parser.parse_args()

    if args.attach:
        # Start workbench server first so browser can open
        # then boot the system and attach it
        print("[WORKBENCH] Starting server...")
        wb = Workbench(port=args.port)
        wb.start_server()

        url = f"http://localhost:{args.port}"
        time.sleep(0.3)
        webbrowser.open(url)
        print(f"[WORKBENCH] Open {url} in your browser")
        print(f"[WORKBENCH] Booting full system — cells will populate shortly...")

        # Boot in background thread so browser is already open
        import threading as _threading
        def _boot_and_attach():
            from run_companion import boot_system
            arr, ctrl, shore, companion, devices, search_index, core_ponds = \
                boot_system(
                    cell_count      = args.cells,
                    load_core_ponds = not args.no_core_ponds,
                )
            # Swap the controller and attach OS components
            with wb._lock:
                wb.ctrl       = ctrl
                wb._shore     = shore
                wb._comp      = companion
                wb.core_ponds = core_ponds
            print(f"[WORKBENCH] System attached — {args.cells} cells live")
            print(f"[WORKBENCH] Core Ponds: {list(core_ponds.keys()) or 'none'}")
            print(f"[WORKBENCH] Refresh browser to see live cell state")

        boot_thread = _threading.Thread(target=_boot_and_attach, daemon=True)
        boot_thread.start()

        print("[WORKBENCH] Press Ctrl+C to stop")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print()
        finally:
            wb.stop_server()

    else:
        # Standalone workbench — internal array, demos only
        print(f"[WORKBENCH] Starting standalone (internal array, 256 cells)")
        print(f"[WORKBENCH] Tip: use --attach --cells 100000 to connect to a live system")
        wb = Workbench(port=args.port)
        wb.serve()
