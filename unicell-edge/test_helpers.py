"""
test_helpers.py — UniCell Edge timing constants and test utilities.

Central point for timing-dependent test values. When the edge model
changes, update CELL_LATENCY here and all tests pick it up automatically.

Edge model timing:
  Tick N:   A arrives (posedge), B arrives (negedge) → cell fires
            Result → output buffer
  Tick N+1: Output buffer → bus (posedge if GS_OUT_POSEDGE, else negedge)

So a single cell has latency of 2 ticks (compute + drain).
A chain of N cells has latency of N * 2 ticks.
"""

# ── Timing constants ──────────────────────────────────────────────────────────

# Ticks of latency per cell in a feed-forward chain (compute tick + drain tick).
CELL_LATENCY = 2

def chain_latency(n_cells: int) -> int:
    """Total ticks for a linear feed-forward chain of n cells."""
    return n_cells * CELL_LATENCY

def parallel_latency(n_cells: int) -> int:
    """Parallel cells all fire in the same tick — latency is one cell."""
    return CELL_LATENCY

# ── Test runner helpers ───────────────────────────────────────────────────────

def run_ticks(arr, n: int) -> dict:
    """
    Run n ticks, return {cycle: {address: value}} bus snapshots.
    Cycle numbers are 1-indexed.
    """
    history = {}
    for i in range(1, n + 1):
        arr.tick()
        history[i] = {addr: v for addr, (v, _) in arr.bus.items()}
    return history


def run_to_result(arr, *watch_addresses, max_ticks: int = 50):
    """
    Run until any watched address appears on bus.
    Returns (cycle, bus_snapshot) or (None, {}) if not found within max_ticks.
    """
    for i in range(1, max_ticks + 1):
        arr.tick()
        if any(a in arr.bus for a in watch_addresses):
            return i, {addr: v for addr, (v, _) in arr.bus.items()}
    return None, {}


def run_chain(arr, output_address: int, max_ticks: int = 100) -> tuple:
    """
    Run until output_address appears on bus.
    Returns (cycle, value) or (None, None) if not found.
    """
    cycle, snapshot = run_to_result(arr, output_address, max_ticks=max_ticks)
    if cycle is None:
        return None, None
    return cycle, snapshot.get(output_address)
