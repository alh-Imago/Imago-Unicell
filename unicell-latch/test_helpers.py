"""
test_helpers.py — UniCell Latch timing constants and test utilities.

Central point for timing-dependent test values. When the latch model
changes, update the constants here and all tests pick it up automatically.

Latch model timing:
  Tick N:   data arrives → stored in input latch (via receive())
  Tick N+1: input latch → gate tree fires → result → output latch
  Tick N+2: output latch → drives bus (Phase 1 drain)

So a single cell has a fixed latency of 2 ticks (CELL_LATENCY).

Chain latency is n+1 ticks for a chain of n cells — NOT n*2.
This is because Phase 1 (drain output latches) and Phase 2 (deliver bus)
happen in the same tick, so a downstream cell receives its input in the
same tick that its upstream cell drives the bus. Each cell adds exactly
1 tick of latency to a chain beyond the initial 2-tick load.

  n=1: 2 ticks  (load + fire)
  n=2: 3 ticks  (load + fire + fire)
  n=4: 5 ticks  (load + fire*4)
"""

# ── Timing constants ──────────────────────────────────────────────────────────

# Ticks of latency for a single cell (load input latch + fire to output latch).
CELL_LATENCY = 2

def chain_latency(n_cells: int) -> int:
    """
    Total ticks for a linear feed-forward chain of n cells.
    Formula: n + 1  (not n * CELL_LATENCY).
    Each cell beyond the first adds exactly 1 tick because Phase 1 drain
    and Phase 2 delivery happen in the same tick.
    """
    return n_cells + 1

def parallel_latency(n_cells: int) -> int:
    """
    Ticks for parallel cells (all at same depth).
    Parallel cells don't add latency — same as a single cell.
    """
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
    Useful for timing single chains without knowing depth upfront.
    """
    cycle, snapshot = run_to_result(arr, output_address, max_ticks=max_ticks)
    if cycle is None:
        return None, None
    return cycle, snapshot.get(output_address)
