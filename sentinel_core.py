"""
sentinel_core.py — Sentinel ICM core logic.

A Sentinel is a small resident program loaded alongside every pond.
Its cells watch the pond's bus addresses and write status values to
the pond's PTT bus range. Ward reads those addresses every tick to
make scheduling and health decisions.

Architecture:
    Pond cells ──> [compute]
         │
         ├──> Sentinel heartbeat cell  ──> PTT_BASE + entry*4 + 0  (Ward: ALIVE?)
         ├──> Sentinel stall cell      ──> PTT_BASE + entry*4 + 1  (Ward: STALLED?)
         ├──> Sentinel collision cell  ──> PTT_BASE + entry*4 + 2  (Ward: COLLISION?)
         └──> Sentinel throughput cell ──> PTT_BASE + entry*4 + 3  (Ward: HOW BUSY?)

Each Sentinel function compiles to an ICM via the ImagoCompiler.
The Sentinel ICM is loaded at pond admission time, shares the same
cell array, and runs concurrently with the pond it monitors.

PTT tick values (what Ward reads):
    PTT_TICK_ACTIVE     = 0x02  — pond is processing, all good
    PTT_TICK_IDLE       = 0xFF00 — no input for a few cycles (normal)
    PTT_TICK_IDLE_WARN  = 0xFF0000 — no input for many cycles (investigate)
    PTT_TICK_WAITING    = 0x01  — pond is waiting for upstream data

Compiler status (2026-05-30):
    COMPILES NOW: heartbeat_status, stall_status, health_verdict,
                  collision_flag, throughput_band, ptt_write_value
    NEEDS LOOP_BACK: stall_counter (requires persistent counter cell)
    NEEDS MULTI_OUTPUT: full_sentinel_tick (writes to 4 PTT addresses)
"""

# ── PTT status constants ───────────────────────────────────────────────────
# These are written to the PTT bus so Ward can read them.
PTT_ACTIVE      = 0x02
PTT_IDLE        = 0xFF00
PTT_IDLE_WARN   = 0xFF0000
PTT_WAITING     = 0x01
PTT_STALLED     = 0xDEAD00    # fault: stall detected
PTT_COLLISION   = 0xBAD000    # fault: address collision detected
PTT_HEALTHY     = 0x02        # alias for ACTIVE

# ── Sentinel state codes (internal) ───────────────────────────────────────
STATE_HEALTHY  = 2
STATE_IDLE     = 3
STATE_DEGRADED = 4
STATE_STALLED  = 5
STATE_FAULT    = 6


# ── 1. Heartbeat ──────────────────────────────────────────────────────────
# The simplest Sentinel. One GS_SENTRY cell watches the pond's primary
# input address and re-emits to PTT on every arrival.
# The existing GS_SENTRY (GS_PASS | GS_LATCH_IN) already does this.
# This function expresses the DECISION logic Ward applies to what it reads.

def heartbeat_status(tick_value: int32, idle_threshold: int32) -> int32:
    """
    Given the last value written by the Sentinel heartbeat cell,
    return the health status Ward should record.
    tick_value > 0  → pond fired this epoch → ACTIVE
    tick_value == 0 → nothing fired → consult idle_threshold
    """
    if tick_value > 0:
        return PTT_ACTIVE
    else:
        return PTT_IDLE


# ── 2. Stall detection ────────────────────────────────────────────────────
# A stall is when the pond has received input but produced no output
# within pipeline_depth ticks. The stall counter increments each tick
# input is present but output is absent.
#
# NOTE: the counter itself requires GS_LOOP_BACK (output feeds own input).
# That is not yet in the compiler. This function computes the THRESHOLD
# CHECK once the counter value is available.

def stall_status(ticks_since_output: int32, pipeline_depth: int32) -> int32:
    """
    Given how many ticks since the pond last produced output,
    and the expected pipeline depth, return stall status.
    """
    if ticks_since_output > pipeline_depth:
        return PTT_STALLED
    else:
        return PTT_ACTIVE


def stall_increment(current_count: int32, output_arrived: int32) -> int32:
    """
    Counter step for the stall detector.
    If output arrived this tick: reset to 0.
    Otherwise: increment.
    This is called each tick by a LOOP_BACK cell — output feeds
    back as input, so current_count is the previous count.
    COMPILES TODAY. Wiring (LOOP_BACK) needs compiler support.
    """
    if output_arrived:
        return 0
    else:
        return current_count + 1


# ── 3. Collision detection ────────────────────────────────────────────────
# A collision is two cells writing to the same bus address in one tick.
# Two layers:
#   Static  — checked at ICM load time (output_address uniqueness scan)
#   Runtime — a Sentinel cell watching the bus for double-writes
#
# The runtime version stores the "first writer this tick" in a_data
# (two-arrival model). If a second write arrives at the same address
# in the same tick, the cell fires → collision event to PTT.

def collision_flag(first_value: int32, second_value: int32) -> int32:
    """
    Called when a Sentinel cell fires on SECOND arrival at a watched address.
    First arrival was stored as a_data. Second arrival triggers this.
    Any second arrival at a watched-output address is a collision.
    Returns the collision code to write to PTT.
    """
    return PTT_COLLISION


def no_collision() -> int32:
    """Healthy tick — no collision detected."""
    return PTT_ACTIVE


# ── 4. Throughput band ───────────────────────────────────────────────────
# Classify the pond's activity level into bands Ward can act on.
# Feeds the throughput PTT address.

def throughput_band(packets_this_epoch: int32,
                    low_threshold: int32,
                    high_threshold: int32) -> int32:
    """
    Classify pond throughput into three bands:
      LOW  (< low_threshold)  → may be idle or stalled
      MID  (normal range)     → healthy
      HIGH (> high_threshold) → overloaded, may need throttling
    """
    if packets_this_epoch < low_threshold:
        return 1    # LOW
    else:
        if packets_this_epoch > high_threshold:
            return 3  # HIGH
        else:
            return 2  # MID


# ── 5. Health verdict ─────────────────────────────────────────────────────
# Ward's final per-tick decision based on all Sentinel inputs.
# This is what Ward computes from the PTT addresses, not what the
# Sentinel writes — but expressing it here shows the full chain.

def health_verdict(heartbeat: int32,
                   stall_ticks: int32,
                   collision: int32,
                   pipeline_depth: int32) -> int32:
    """
    Combine all Sentinel signals into a single health verdict.
    Ward reads the four PTT addresses and calls this.
    Returns one of the STATE_* constants.
    """
    if collision:
        return STATE_FAULT
    else:
        if stall_ticks > pipeline_depth:
            return STATE_STALLED
        else:
            if heartbeat:
                return STATE_HEALTHY
            else:
                return STATE_IDLE


# ── 6. PTT write value ───────────────────────────────────────────────────
# The final value written to the PTT bus address each tick.
# Encodes health state into the PTT_TICK_* constant Ward expects.

def ptt_write_value(health_state: int32) -> int32:
    """
    Map internal health state to the PTT tick value Ward reads.
    Ward's check_staleness() uses these values.
    """
    if health_state == STATE_HEALTHY:
        return PTT_ACTIVE           # 0x02
    else:
        if health_state == STATE_IDLE:
            return PTT_IDLE         # 0xFF00
        else:
            if health_state == STATE_STALLED:
                return PTT_STALLED  # 0xDEAD00
            else:
                return PTT_COLLISION  # fault


