"""
ward_core.py — Ward ICM core logic (compilable decision functions).

The Ward is the per-Pond watchdog. Its full runtime object (ward.py) is
stateful: it holds emission histories, timers, and Python object refs.
This module expresses the *decision kernels* as pure int32 functions that
the compiler can lower to ICM cells.

These functions are the logic Ward applies each tick to the values it reads
from the PTT bus (written there by Sentinel). They are side-effect-free
and can run concurrently on the cell array alongside the pond they watch.

Architecture:
    Sentinel cells write health values to PTT_BASE addresses each tick.
    Ward cells read those addresses, compute a verdict, and write to their
    own PTT output addresses so the Companion and ShoreKeeper can act.

Ward decision outputs (per pond, at PTT_WARD_BASE + entry*4):
    +0: health_verdict   (WARD_HEALTHY / WARD_DEGRADED / WARD_STALLED / WARD_OFFLINE)
    +1: throttle_flag    (0 = normal, 1 = shed load)
    +2: eviction_flag    (0 = keep, 1 = evict pond)
    +3: stall_ticks      (saturating counter of consecutive zero-emission ticks)

Compiler status (2026-05-30):
    All functions below compile via compile_int32_function().
    NEEDS LOOP_BACK: stall_counter_step (persistent counter — wired separately)
    NEEDS MULTI_OUTPUT: full_ward_tick (writes to 4 PTT addresses)
"""

# ── Ward verdict codes (written to PTT_WARD_BASE) ─────────────────────────
WARD_IDLE     = 0
WARD_HEALTHY  = 1
WARD_DEGRADED = 2
WARD_STALLED  = 3
WARD_SILENT   = 4
WARD_OFFLINE  = 5

# ── Emission band thresholds ───────────────────────────────────────────────
# Compared against emissions_this_tick (packet count from MONITOR bridge).
EMISSION_LOW   = 1     # below this → suspect silence
EMISSION_HIGH  = 128   # above this → overloaded

# ── Stall / silence detection ──────────────────────────────────────────────
# Ward enters STALLED when stall_ticks exceeds pipeline_depth.
# Ward enters SILENT when stall_ticks exceeds silence_threshold.
STALL_THRESHOLD   = 8   # ticks of zero emissions → STALLED
SILENCE_THRESHOLD = 32  # ticks of zero emissions → SILENT (peripheral)

# ── Throttle / eviction thresholds ────────────────────────────────────────
THROTTLE_STALL_TICKS  = 16   # sustained stall → throttle signal
EVICT_STALL_TICKS     = 64   # prolonged stall → evict signal


# ── 1. Emission classifier ─────────────────────────────────────────────────

def emission_band(emissions: int32, low: int32, high: int32) -> int32:
    """
    Classify this tick's emission count into a band.
      0 = ZERO   (nothing emitted — stall candidate)
      1 = LOW    (below low threshold — underloaded)
      2 = NORMAL (between thresholds)
      3 = HIGH   (above high threshold — overloaded)
    """
    if emissions == 0:
        return 0    # ZERO
    else:
        if emissions < low:
            return 1  # LOW
        else:
            if emissions > high:
                return 3  # HIGH
            else:
                return 2  # NORMAL


# ── 2. Stall counter step ─────────────────────────────────────────────────

def stall_counter_step(current_ticks: int32, emissions: int32) -> int32:
    """
    Saturating stall counter.
    Resets to 0 when emissions > 0.
    Increments each tick emissions == 0, capping at SILENCE_THRESHOLD.
    Called each tick — output feeds back as next tick's current_ticks
    via LOOP_BACK cell wiring (not yet in compiler; wired manually).
    """
    if emissions > 0:
        return 0
    else:
        if current_ticks < SILENCE_THRESHOLD:
            return current_ticks + 1
        else:
            return SILENCE_THRESHOLD   # saturate


# ── 3. Process Ward verdict ────────────────────────────────────────────────

def process_verdict(emissions: int32, stall_ticks: int32,
                    bridge_alive: int32, pipeline_depth: int32) -> int32:
    """
    PROCESS pond Ward verdict for one tick.
    bridge_alive: 1 = bridge cells present, 0 = gone.
    Returns one of the WARD_* constants.
    """
    if bridge_alive == 0:
        return WARD_OFFLINE
    else:
        if stall_ticks > pipeline_depth:
            return WARD_STALLED
        else:
            if emissions > 0:
                return WARD_HEALTHY
            else:
                return WARD_DEGRADED


# ── 4. Peripheral Ward verdict ────────────────────────────────────────────

def peripheral_verdict(emissions: int32, stall_ticks: int32,
                        bridge_alive: int32) -> int32:
    """
    PERIPHERAL pond Ward verdict.
    A peripheral that has gone silent (after prior activity) → WARD_SILENT.
    """
    if bridge_alive == 0:
        return WARD_OFFLINE
    else:
        if stall_ticks > SILENCE_THRESHOLD:
            return WARD_SILENT
        else:
            if emissions > 0:
                return WARD_HEALTHY
            else:
                return WARD_IDLE


# ── 5. Throttle decision ──────────────────────────────────────────────────

def throttle_flag(stall_ticks: int32, emission_band_val: int32) -> int32:
    """
    Should we signal upstream to shed load?
    Throttle when stall has persisted or overload detected.
    Returns 1 = throttle, 0 = normal.
    """
    if stall_ticks > THROTTLE_STALL_TICKS:
        return 1
    else:
        if emission_band_val == 3:
            return 1   # HIGH band → throttle
        else:
            return 0


# ── 6. Eviction decision ──────────────────────────────────────────────────

def eviction_flag(stall_ticks: int32, verdict: int32) -> int32:
    """
    Should we evict (reclaim) this pond?
    Evict when stall is prolonged OR pond is offline.
    Returns 1 = evict, 0 = keep.
    """
    if verdict == WARD_OFFLINE:
        return 1
    else:
        if stall_ticks > EVICT_STALL_TICKS:
            return 1
        else:
            return 0


# ── 7. PTT health read — sentinel value interpreter ───────────────────────

def interpret_sentinel(ptt_value: int32) -> int32:
    """
    Translate a raw Sentinel PTT value to a Ward-readable health code.
    Sentinel writes: PTT_ACTIVE=0x02, PTT_IDLE=0xFF00, PTT_STALLED=0xDEAD00,
    PTT_COLLISION=0xBAD000.
    Ward maps these to simple 0..3 codes for decision logic.
      0 = OK (active)
      1 = IDLE (normal silence)
      2 = STALLED
      3 = FAULT (collision or unknown)
    """
    if ptt_value == 2:
        return 0   # PTT_ACTIVE → OK
    else:
        if ptt_value == 65280:
            return 1  # PTT_IDLE (0xFF00) → IDLE
        else:
            if ptt_value == 14593280:
                return 2  # PTT_STALLED (0xDEAD00) → STALLED
            else:
                return 3  # anything else (collision, fault) → FAULT


# ── 8. Combined sentinel + ward verdict ───────────────────────────────────

def combined_verdict(sentinel_code: int32, ward_verdict: int32) -> int32:
    """
    Merge Sentinel's health code with Ward's own verdict.
    Sentinel fault escalates Ward verdict to DEGRADED minimum.
    sentinel_code: 0=OK, 1=IDLE, 2=STALLED, 3=FAULT
    ward_verdict: WARD_* constant
    Returns final verdict for PTT output.
    """
    if sentinel_code == 3:
        return WARD_DEGRADED    # sentinel fault → at least DEGRADED
    else:
        if sentinel_code == 2:
            if ward_verdict == WARD_HEALTHY:
                return WARD_DEGRADED   # sentinel stalled but ward thinks healthy
            else:
                return ward_verdict
        else:
            return ward_verdict
