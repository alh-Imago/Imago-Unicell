"""
shore_core.py — Shore ICM core logic (compilable decision functions).

Shore is the resource manager that sits between Ward (per-Pond watchdog)
and the OS layer. ShoreKeeper aggregates Ward verdicts across all Ponds
and makes system-level scheduling, throttle, and eviction decisions.

These are the pure int32 decision kernels — side-effect-free functions
that the compiler can lower to ICM cells. The stateful aggregation loop
remains in Python (shorekeeper.py); these functions express the numeric
threshold logic that runs per-tick on the cell array.

Architecture:
    Ward PTT outputs → Shore cells → ShoreKeeper PTT bus → OS decisions

Shore decision outputs (written to PTT_SHORE_BASE):
    +0: system_health   (SHORE_HEALTHY / SHORE_DEGRADED / SHORE_CRITICAL)
    +1: throttle_signal (0=run / 1=throttle / 2=shed / 3=halt)
    +2: evict_candidate (pond slot index to evict, or 0xFFFFFFFF = none)
    +3: bus_pressure    (0=low / 1=normal / 2=high / 3=saturated)

Compiler status (2026-05-30):
    All functions compile via compile_int32_function().
    Uses explicit > 0 / == comparisons throughout (no bare if x:).
"""

# ── Shore health codes (written to PTT_SHORE_BASE+0) ─────────────────────
SHORE_HEALTHY  = 0
SHORE_DEGRADED = 1
SHORE_CRITICAL = 2
SHORE_HALTED   = 3

# ── Throttle signal codes (written to PTT_SHORE_BASE+1) ──────────────────
THROTTLE_RUN   = 0   # all clear
THROTTLE_SLOW  = 1   # reduce input rate
THROTTLE_SHED  = 2   # shed non-essential ponds
THROTTLE_HALT  = 3   # emergency stop

# ── Bus pressure bands ────────────────────────────────────────────────────
BUS_LOW        = 0   # < 25% utilisation
BUS_NORMAL     = 1   # 25–74%
BUS_HIGH       = 2   # 75–89%
BUS_SATURATED  = 3   # >= 90%

# ── Thresholds (all expressed as integer percentages, 0–100) ─────────────
DEGRADED_THRESHOLD  = 25   # % of ponds degraded/stalled → SHORE_DEGRADED
CRITICAL_THRESHOLD  = 50   # % of ponds degraded/stalled → SHORE_CRITICAL
THROTTLE_THRESHOLD  = 60   # % bus utilisation → throttle
SHED_THRESHOLD      = 80   # % bus utilisation → shed
HALT_THRESHOLD      = 95   # % bus utilisation → halt

# ── Pond count thresholds ─────────────────────────────────────────────────
MAX_PONDS        = 256   # maximum ponds per shore card
EVICT_HEADROOM   = 8     # keep at least this many free slots


# ── 1. System health from pond state counts ───────────────────────────────

def system_health(healthy_count: int32, degraded_count: int32,
                  stalled_count: int32, total_count: int32) -> int32:
    """
    Aggregate Ward verdicts across all Ponds into system health.
    Threshold checks use shift approximations to avoid multiply/divide:
      fault > 50% of total  ≡  fault_count * 2 > total_count
      fault > 25% of total  ≡  fault_count * 4 > total_count
    Returns SHORE_* constant.
    """
    if total_count == 0:
        return SHORE_HEALTHY

    fault_count = degraded_count + stalled_count

    # fault > 50%: fault*2 > total  (left shift fault by 1)
    if (fault_count + fault_count) > total_count:
        return SHORE_CRITICAL
    else:
        # fault > 25%: fault*4 > total  (left shift fault by 2)
        fault4 = fault_count + fault_count + fault_count + fault_count
        if fault4 > total_count:
            return SHORE_DEGRADED
        else:
            return SHORE_HEALTHY


# ── 2. Bus pressure band ──────────────────────────────────────────────────

def bus_pressure_band(armed_cells: int32, total_cells: int32) -> int32:
    """
    Classify current bus utilisation into pressure bands.
    armed_cells: number of armed (active) cells.
    total_cells: array capacity.
    Threshold checks avoid multiply/divide via shift-based comparisons:
      armed > 89%  ≡  armed * 100 / total > 89  approximated as:
        armed + armed > total  (> 50%)  then tighter checks via subtraction
    We use: armed*9 > total*8 for 89%, armed*3 > total*2 for 75%,
             armed > total/4 for 25% — all via addition chains.
    Returns BUS_* constant.
    """
    if total_cells == 0:
        return BUS_LOW

    # armed > 89% ≈ armed * 9 > total * 8
    # approximated as: (armed + armed + armed + armed + armed + armed + armed + armed + armed) > (total * 8)
    # total*8 = total shifted left 3 = total+total+total+total+total+total+total+total
    armed9  = armed_cells + armed_cells + armed_cells + armed_cells + armed_cells + armed_cells + armed_cells + armed_cells + armed_cells
    total8  = total_cells + total_cells + total_cells + total_cells + total_cells + total_cells + total_cells + total_cells
    if armed9 > total8:
        return BUS_SATURATED
    else:
        # armed > 74% ≈ armed * 4 > total * 3
        armed4 = armed_cells + armed_cells + armed_cells + armed_cells
        total3 = total_cells + total_cells + total_cells
        if armed4 > total3:
            return BUS_HIGH
        else:
            # armed > 24% ≈ armed * 4 > total
            if armed4 > total_cells:
                return BUS_NORMAL
            else:
                return BUS_LOW


# ── 3. Throttle decision ──────────────────────────────────────────────────

def throttle_decision(bus_pct: int32, shore_health: int32) -> int32:
    """
    Determine throttle level from bus utilisation and system health.
    bus_pct: integer percentage 0–100.
    shore_health: SHORE_* constant.
    Returns THROTTLE_* constant.
    """
    if shore_health == SHORE_HALTED:
        return THROTTLE_HALT
    else:
        if shore_health == SHORE_CRITICAL:
            return THROTTLE_SHED
        else:
            if bus_pct > HALT_THRESHOLD:
                return THROTTLE_HALT
            else:
                if bus_pct > SHED_THRESHOLD:
                    return THROTTLE_SHED
                else:
                    if bus_pct > THROTTLE_THRESHOLD:
                        return THROTTLE_SLOW
                    else:
                        return THROTTLE_RUN


# ── 4. Eviction pressure ──────────────────────────────────────────────────

def eviction_pressure(pond_count: int32, stalled_count: int32,
                       bus_pct: int32) -> int32:
    """
    How urgently does Shore need to evict a pond?
    Returns 0 = no pressure, 1 = gentle, 2 = urgent, 3 = emergency.
    """
    if stalled_count > 4:
        return 3   # emergency: multiple stalled ponds
    else:
        if bus_pct > SHED_THRESHOLD:
            return 2  # urgent: bus nearly full
        else:
            if pond_count > MAX_PONDS - EVICT_HEADROOM:
                return 1  # gentle: running low on slots
            else:
                if stalled_count > 0:
                    return 1  # gentle: at least one stall
                else:
                    return 0  # no pressure


# ── 5. Admission gate ─────────────────────────────────────────────────────

def can_admit(pond_count: int32, armed_cells: int32,
              total_cells: int32, new_pond_cells: int32) -> int32:
    """
    Can Shore admit a new pond requiring new_pond_cells cells?
    Returns 1 = admit, 0 = deny.
    Pond slot limit uses 247 threshold (MAX_PONDS 256 - EVICT_HEADROOM 8 - 1)
    to avoid carry-boundary issues with the 256-constant comparison.
    """
    remaining = total_cells - armed_cells
    if remaining < new_pond_cells:
        return 0   # not enough cell headroom
    else:
        if pond_count > 247:
            return 0  # too few pond slots remaining
        else:
            return 1


# ── 6. Thermal score ──────────────────────────────────────────────────────

def thermal_score(thermal_pct: int32, trend: int32) -> int32:
    """
    Combine thermal load percentage and trend into a 0–100 score.
    trend: 0=cooling, 1=stable, 2=heating.
    Returns combined score (higher = hotter).
    Note: returns thermal_pct + 0 for stable to avoid bare-passthrough path.
    """
    if trend == 2:
        return thermal_pct + 10   # heating: boost score
    else:
        if trend == 0:
            return thermal_pct - 5   # cooling: reduce score
        else:
            return thermal_pct + 0   # stable: no change (+ 0 forces ADD tile)


# ── 7. Shore heartbeat interval check ────────────────────────────────────

def should_emit_heartbeat(tick_count: int32, last_heartbeat_at: int32,
                            heartbeat_interval: int32) -> int32:
    """
    Should Shore emit a heartbeat this tick?
    Returns 1 = yes, 0 = no.
    """
    ticks_since = tick_count - last_heartbeat_at
    if ticks_since > heartbeat_interval:
        return 1
    else:
        return 0


# ── 8. Zone load balance ──────────────────────────────────────────────────

def zone_balance(zone_a_load: int32, zone_b_load: int32,
                  balance_threshold: int32) -> int32:
    """
    Are two shore zones balanced?
    Returns 0 = balanced, 1 = zone_a overloaded, 2 = zone_b overloaded.
    Avoids signed subtraction by comparing directly: a > b + thresh, b > a + thresh.
    """
    if zone_a_load > zone_b_load + balance_threshold:
        return 1   # zone_a heavier
    else:
        if zone_b_load > zone_a_load + balance_threshold:
            return 2  # zone_b heavier
        else:
            return 0  # balanced
