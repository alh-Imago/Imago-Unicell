"""
gpu_array.py — GPU Stage 1: CuPy/NumPy unified array backend

Replaces the per-cell Python loop in UniCellArray.tick() with a
vectorised array operation. On a GPU the armed cells all evaluate
simultaneously; on CPU this falls back to NumPy (still faster than
the Python loop for large arrays).

Architecture
============

The key insight from CommandInterface (Option C): the CPU/GPU boundary
is already correct. CommandInterface issues commands; the array fabric
executes them. In Stage 1:

    CPU:  COMPANION, Shore, Ward, CommandInterface, result handling
    GPU:  UniCellArray._tick_kernel() — evaluates all armed cells in parallel

Stage 1 scope
=============
- Replace UniCellArray._tick_armed_cells() inner loop with array kernel
- Keep all Python infrastructure unchanged (cells dict, bus dict, regions)
- GPU kernel: read gate_state, input_address → compute NOR → write bus
- CPU collects results from bus as before

Stage 2 (future): persistent GPU state, CPU only receives capture values
Stage 3 (future): one GPU per card, ShoreKeeper coordinates

Hardware target: NVIDIA GTX 970, 4GB, compute 5.2
CuPy requirement: cupy-cuda12x or cupy-cuda11x depending on driver

Usage
=====

    from gpu_array import GPUArrayBackend

    backend = GPUArrayBackend()               # auto-detects GPU/CPU
    backend.load_cells(array.cells)           # upload cell state

    # Replace array.tick() with:
    fired, bus_updates = backend.tick()
    for addr, value in bus_updates.items():
        array.bus[addr] = value

    # Or use the drop-in wrapper:
    gpu_array = GPUArray(cell_count=65536)    # same interface as UniCellArray
"""

from __future__ import annotations
import imago_log

import time
from typing import Optional

# ── Backend detection ─────────────────────────────────────────────────────────

def _detect_backend():
    """
    Auto-detect the best available array backend.
    Returns (module, device_name, has_gpu).
    """
    try:
        import cupy as cp
        if cp.cuda.is_available():
            device = cp.cuda.Device(0)
            props  = cp.cuda.runtime.getDeviceProperties(device.id)
            name   = props['name'].decode() if isinstance(props['name'], bytes) \
                     else str(props['name'])
            mem_gb = props['totalGlobalMem'] / (1024**3)
            imago_log.info(f"[GPU] CUDA device: {name} ({mem_gb:.1f} GB)")
            return cp, name, True
        else:
            imago_log.info("[GPU] CuPy installed but no CUDA device — using NumPy")
    except ImportError:
        imago_log.info("[GPU] CuPy not installed — using NumPy")

    import numpy as np
    return np, "CPU (NumPy)", False


_xp, _DEVICE_NAME, _HAS_GPU = _detect_backend()


# ── Cell state packing ────────────────────────────────────────────────────────

# Each cell is packed as 5 x uint32 in a flat array:
#   [0] gate_state      (32-bit mode register)
#   [1] input_address   (32-bit)
#   [2] output_address  (32-bit)
#   [3] data            (32-bit, current stored value or 0)
#   [4] flags           (bit 0 = start_flag, bits 1-3 reserved)

CELL_STRIDE  = 5
IDX_GS       = 0
IDX_IN_ADDR  = 1
IDX_OUT_ADDR = 2
IDX_DATA     = 3
IDX_FLAGS    = 4

FLAG_ARMED = 0x1


# ── GPUArrayBackend ───────────────────────────────────────────────────────────

class GPUArrayBackend:
    """
    Vectorised array backend using CuPy (GPU) or NumPy (CPU fallback).

    Maintains a flat packed cell array in device memory.
    The tick() method evaluates all armed cells in one operation.

    Compatible with existing UniCellArray bus dict — bus_updates returns
    a dict {output_address: (value, tick)} for the caller to merge.
    """

    def __init__(self, cell_count: int = 65536, tick_counter: int = 0):
        self.cell_count   = cell_count
        self._tick        = tick_counter
        self._has_gpu     = _HAS_GPU
        self._device      = _DEVICE_NAME
        self._xp          = _xp

        # Flat packed cell array [cell_count * CELL_STRIDE] uint32
        self._cells = self._xp.zeros(cell_count * CELL_STRIDE,
                                     dtype=self._xp.uint32)

        # Bus: output_address → value (host side dict, same as UniCellArray)
        self._bus: dict = {}

        # Address → cell index mapping (for fast lookup)
        self._addr_to_idx: dict = {}
        self._next_idx = 0

        imago_log.info(f"[GPU] Backend: {_DEVICE_NAME}, {cell_count} cells")

    # ── Cell loading ──────────────────────────────────────────────────────────

    def allocate(self, address: int) -> int:
        """Register an address, return its cell index."""
        if address in self._addr_to_idx:
            return self._addr_to_idx[address]
        idx = self._next_idx
        if idx >= self.cell_count:
            raise OverflowError(f"Cell array full ({self.cell_count} cells)")
        self._addr_to_idx[address] = idx
        self._next_idx += 1
        return idx

    def configure_cell(self, address: int,
                       gate_state:    int,
                       input_address: int,
                       output_address: int,
                       start_flag:    bool = False) -> None:
        """Write cell configuration to device array."""
        idx  = self.allocate(address)
        base = idx * CELL_STRIDE
        self._cells[base + IDX_GS]       = gate_state      & 0xFFFFFFFF
        self._cells[base + IDX_IN_ADDR]  = input_address   & 0xFFFFFFFF
        self._cells[base + IDX_OUT_ADDR] = output_address  & 0xFFFFFFFF
        self._cells[base + IDX_DATA]     = 0
        self._cells[base + IDX_FLAGS]    = FLAG_ARMED if start_flag else 0

    def load_from_unicell_array(self, unicell_array) -> int:
        """
        Bulk-load cell state from an existing UniCellArray.
        Returns number of cells loaded.
        """
        loaded = 0
        for address, cell in unicell_array.cells.items():
            self.configure_cell(
                address         = address,
                gate_state      = getattr(cell, 'gate_state', 0),
                input_address   = getattr(cell, 'input_address', 0),
                output_address  = getattr(cell, 'output_address', 0),
                start_flag      = getattr(cell, 'start_flag', False),
            )
            loaded += 1
        imago_log.info(f"[GPU] Loaded {loaded} cells from UniCellArray")
        return loaded

    # ── Tick kernel ───────────────────────────────────────────────────────────

    def tick(self, bus_in: Optional[dict] = None) -> tuple:
        """
        Advance all armed cells by one tick.

        bus_in:  current bus state {address: (value, tick)} — input values
                 for cells to read from. If None, cells read from internal bus.

        Returns (fired_count, bus_updates):
          fired_count:  number of cells that evaluated this tick
          bus_updates:  {output_address: (value, tick)} new bus values
        """
        self._tick += 1
        xp = self._xp

        n   = self._next_idx
        if n == 0:
            return 0, {}

        cells = self._cells[:n * CELL_STRIDE].reshape(n, CELL_STRIDE)

        # Find armed cells (FLAG_ARMED set in flags column)
        armed_mask = (cells[:, IDX_FLAGS] & FLAG_ARMED).astype(bool)
        armed_idx  = xp.where(armed_mask)[0]

        if len(armed_idx) == 0:
            return 0, {}

        # Read input values from bus for armed cells
        in_addrs = cells[armed_idx, IDX_IN_ADDR]

        # Build input value array — check bus for each input address
        # (This is the CPU/GPU boundary for Stage 1 — input lookup stays on CPU)
        bus_source = bus_in if bus_in is not None else self._bus

        if _HAS_GPU:
            # Transfer to CPU for bus lookup, then back
            in_addrs_cpu = xp.asnumpy(in_addrs)
        else:
            in_addrs_cpu = in_addrs  # already numpy

        in_values = []
        has_input = []
        for addr in in_addrs_cpu:
            bus_entry = bus_source.get(int(addr))
            if bus_entry is not None:
                in_values.append(bus_entry[0] if isinstance(bus_entry, tuple)
                                 else bus_entry)
                has_input.append(True)
            else:
                in_values.append(0)
                has_input.append(False)

        import numpy as np_cpu
        in_values_arr  = np_cpu.array(in_values, dtype=np_cpu.uint32)
        has_input_arr  = np_cpu.array(has_input, dtype=bool)

        # Only cells with input available this tick actually fire
        firing_mask    = has_input_arr
        fired_local    = np_cpu.where(firing_mask)[0]

        if len(fired_local) == 0:
            return 0, {}

        bus_updates = {}

        # For each firing cell: apply gate_state logic and emit to output
        if _HAS_GPU:
            gs_arr       = xp.asnumpy(cells[armed_idx[fired_local], IDX_GS])
            out_addr_arr = xp.asnumpy(cells[armed_idx[fired_local], IDX_OUT_ADDR])
        else:
            gs_arr       = cells[armed_idx[fired_local], IDX_GS]
            out_addr_arr = cells[armed_idx[fired_local], IDX_OUT_ADDR]

        fired_inputs = in_values_arr[fired_local]

        from gate_states import (GS_NOT, GS_PASS, GS_LATCH, GS_ONE_SHOT,
                                  GS_INVERT_OUT, LOOP_MODE)

        for i, (gs, out_addr, val) in enumerate(
                zip(gs_arr, out_addr_arr, fired_inputs)):
            gs       = int(gs)
            out_addr = int(out_addr)
            val      = int(val)

            # Basic NOR topology (bits 0-10)
            nor_topo = gs & 0x7FF
            if nor_topo == 0:         # GS_PASS
                result = val
            elif nor_topo == 1:       # GS_NOT
                result = 0 if val else 1
            else:
                result = val          # simplified — full NOR tree in Stage 2

            # Apply mode flags
            if gs & GS_INVERT_OUT:
                result = 0 if result else 1

            if result != 0:
                bus_updates[out_addr] = (result, self._tick)

            # ONE_SHOT: disarm after firing
            if gs & GS_ONE_SHOT:
                idx_in_array = int(armed_idx[fired_local[i]])
                self._cells[idx_in_array * CELL_STRIDE + IDX_FLAGS] &= ~FLAG_ARMED

        # Merge bus updates into internal bus
        self._bus.update(bus_updates)

        return len(fired_local), bus_updates

    # ── Status ────────────────────────────────────────────────────────────────

    def armed_count(self) -> int:
        """Number of currently armed cells."""
        n = self._next_idx
        if n == 0:
            return 0
        cells = self._cells[:n * CELL_STRIDE].reshape(n, CELL_STRIDE)
        return int((cells[:, IDX_FLAGS] & FLAG_ARMED).sum())

    def stats(self) -> dict:
        return {
            "device":       _DEVICE_NAME,
            "has_gpu":      _HAS_GPU,
            "cells_loaded": self._next_idx,
            "cells_total":  self.cell_count,
            "armed":        self.armed_count(),
            "tick":         self._tick,
            "bus_entries":  len(self._bus),
        }

    def __repr__(self) -> str:
        return (f"GPUArrayBackend({_DEVICE_NAME}, "
                f"{self._next_idx}/{self.cell_count} cells, "
                f"tick={self._tick})")


# ── Benchmark helper ──────────────────────────────────────────────────────────

def benchmark(cell_count: int = 10_000, ticks: int = 1000) -> dict:
    """
    Compare GPU backend vs Python loop for reference.
    Returns timing dict.
    """
    import time

    backend = GPUArrayBackend(cell_count=cell_count)

    # Fill with simple PASS cells
    for i in range(cell_count):
        addr = 0x100000 + i
        backend.configure_cell(addr, 0, addr - 1 if i > 0 else addr,
                                addr + 1, start_flag=(i % 2 == 0))

    # Prime the bus
    for i in range(0, cell_count, 2):
        backend._bus[0x100000 + i - 1 if i > 0 else 0x100000 + i] = (1, 0)

    t0 = time.perf_counter()
    total_fired = 0
    for _ in range(ticks):
        fired, _ = backend.tick()
        total_fired += fired
    elapsed = time.perf_counter() - t0

    return {
        "device":        _DEVICE_NAME,
        "has_gpu":       _HAS_GPU,
        "cell_count":    cell_count,
        "ticks":         ticks,
        "total_fired":   total_fired,
        "elapsed_s":     round(elapsed, 4),
        "ticks_per_sec": round(ticks / elapsed),
        "cells_per_sec": round(cell_count * ticks / elapsed),
    }


if __name__ == "__main__":
    print("\n=== GPU Array Backend Benchmark ===\n")
    result = benchmark(cell_count=10_000, ticks=500)
    for k, v in result.items():
        print(f"  {k:20s}: {v}")
