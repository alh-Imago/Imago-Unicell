#!/usr/bin/env python3
"""
bootloader/tests/test_icms.py — Standalone functional tests for bootloader ICMs.

Tests each sentinel and ward ICM in isolation using the controller/VM,
completely independent of the main test suite.

Run from repo root:
    python3 bootloader/tests/test_icms.py

Or a specific group:
    python3 bootloader/tests/test_icms.py sentinel
    python3 bootloader/tests/test_icms.py ward
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from compiler_int32 import Int32Compiler, run_int32_function
from fp_tiles import TileLibrary

ICM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icm")

# ── Test harness ──────────────────────────────────────────────────────────────

passed = 0
failed = 0


def check(name, got, expected, note=""):
    global passed, failed
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    suffix = f"  ({note})" if note else ""
    print(f"  [{status}] {name}: got={got} expected={expected}{suffix}")
    if ok:
        passed += 1
    else:
        failed += 1
    return ok


def run_fn(src_path, fn_name, inputs: dict) -> int:
    """Compile and run a single int32 function, return the 32-bit result."""
    src = open(src_path).read()
    lib = TileLibrary()
    result = run_int32_function(src, fn_name, inputs, tile_library=lib)
    return result


# ── Source paths ──────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SENTINEL_SRC = os.path.join(ROOT, "sentinel_core.py")
WARD_SRC     = os.path.join(ROOT, "ward_core.py")

# ── ICM existence check ───────────────────────────────────────────────────────

def test_icm_files():
    print("\n=== ICM file existence ===")
    expected = [
        "sentinel_heartbeat_status",
        "sentinel_stall_status",
        "sentinel_stall_increment",
        "sentinel_collision_flag",
        "sentinel_no_collision",
        "sentinel_throughput_band",
        "sentinel_health_verdict",
        "sentinel_ptt_write_value",
        "ward_emission_band",
        "ward_stall_counter_step",
        "ward_process_verdict",
        "ward_peripheral_verdict",
        "ward_throttle_flag",
        "ward_eviction_flag",
        "ward_interpret_sentinel",
        "ward_combined_verdict",
    ]
    for name in expected:
        path = os.path.join(ICM_DIR, name + ".icm")
        exists = os.path.exists(path)
        if exists:
            with open(path) as f:
                icm = json.load(f)
            cells = icm.get("cell_count", "?")
            check(f"exists {name}.icm", True, True, f"{cells} cells")
        else:
            check(f"exists {name}.icm", False, True, "FILE MISSING — run generate_icms.py")


# ── Sentinel functional tests ─────────────────────────────────────────────────

PTT_ACTIVE   = 0x02
PTT_IDLE     = 0xFF00
PTT_STALLED  = 0xDEAD00
PTT_COLLISION= 0xBAD000


def test_sentinel():
    print("\n=== sentinel_core functional tests ===")

    # heartbeat_status
    print("\n  heartbeat_status:")
    check("active tick",  run_fn(SENTINEL_SRC, "heartbeat_status", {"tick_value": 5,  "idle_threshold": 3}), PTT_ACTIVE)
    check("zero tick",    run_fn(SENTINEL_SRC, "heartbeat_status", {"tick_value": 0,  "idle_threshold": 3}), PTT_IDLE)

    # stall_status
    print("\n  stall_status:")
    check("not stalled",  run_fn(SENTINEL_SRC, "stall_status", {"ticks_since_output": 2,  "pipeline_depth": 8}), PTT_ACTIVE)
    check("stalled",      run_fn(SENTINEL_SRC, "stall_status", {"ticks_since_output": 10, "pipeline_depth": 8}), PTT_STALLED)
    check("at boundary",  run_fn(SENTINEL_SRC, "stall_status", {"ticks_since_output": 8,  "pipeline_depth": 8}), PTT_ACTIVE)

    # stall_increment
    print("\n  stall_increment:")
    check("output arrived → reset", run_fn(SENTINEL_SRC, "stall_increment", {"current_count": 7, "output_arrived": 1}), 0)
    check("no output → increment",  run_fn(SENTINEL_SRC, "stall_increment", {"current_count": 3, "output_arrived": 0}), 4)
    check("no output from 0",       run_fn(SENTINEL_SRC, "stall_increment", {"current_count": 0, "output_arrived": 0}), 1)

    # collision_flag
    print("\n  collision_flag:")
    check("any collision",  run_fn(SENTINEL_SRC, "collision_flag", {"first_value": 1, "second_value": 2}), PTT_COLLISION)

    # no_collision
    print("\n  no_collision:")
    check("healthy",  run_fn(SENTINEL_SRC, "no_collision", {}), PTT_ACTIVE)

    # throughput_band
    print("\n  throughput_band:")
    check("zero packets → LOW",     run_fn(SENTINEL_SRC, "throughput_band", {"packets_this_epoch": 0,   "low_threshold": 5,  "high_threshold": 50}), 1)
    check("normal packets → MID",   run_fn(SENTINEL_SRC, "throughput_band", {"packets_this_epoch": 20,  "low_threshold": 5,  "high_threshold": 50}), 2)
    check("high packets → HIGH",    run_fn(SENTINEL_SRC, "throughput_band", {"packets_this_epoch": 100, "low_threshold": 5,  "high_threshold": 50}), 3)
    check("at low boundary → MID",  run_fn(SENTINEL_SRC, "throughput_band", {"packets_this_epoch": 5,   "low_threshold": 5,  "high_threshold": 50}), 2)

    # health_verdict
    STATE_HEALTHY  = 2
    STATE_IDLE     = 3
    STATE_STALLED  = 5
    STATE_FAULT    = 6
    print("\n  health_verdict:")
    check("collision → FAULT",    run_fn(SENTINEL_SRC, "health_verdict", {"heartbeat": 1, "stall_ticks": 0,  "collision": 1, "pipeline_depth": 8}), STATE_FAULT)
    check("stalled → STALLED",    run_fn(SENTINEL_SRC, "health_verdict", {"heartbeat": 1, "stall_ticks": 10, "collision": 0, "pipeline_depth": 8}), STATE_STALLED)
    check("healthy → HEALTHY",    run_fn(SENTINEL_SRC, "health_verdict", {"heartbeat": 1, "stall_ticks": 0,  "collision": 0, "pipeline_depth": 8}), STATE_HEALTHY)
    check("no heartbeat → IDLE",  run_fn(SENTINEL_SRC, "health_verdict", {"heartbeat": 0, "stall_ticks": 0,  "collision": 0, "pipeline_depth": 8}), STATE_IDLE)

    # ptt_write_value
    PTT_STALLED_CODE = 0xDEAD00
    print("\n  ptt_write_value:")
    check("HEALTHY → PTT_ACTIVE",    run_fn(SENTINEL_SRC, "ptt_write_value", {"health_state": 2}), PTT_ACTIVE)
    check("IDLE → PTT_IDLE",         run_fn(SENTINEL_SRC, "ptt_write_value", {"health_state": 3}), PTT_IDLE)
    check("STALLED → PTT_STALLED",   run_fn(SENTINEL_SRC, "ptt_write_value", {"health_state": 5}), PTT_STALLED_CODE)
    check("FAULT → PTT_COLLISION",   run_fn(SENTINEL_SRC, "ptt_write_value", {"health_state": 6}), PTT_COLLISION)


# ── Ward functional tests ─────────────────────────────────────────────────────

WARD_IDLE     = 0
WARD_HEALTHY  = 1
WARD_DEGRADED = 2
WARD_STALLED  = 3
WARD_SILENT   = 4
WARD_OFFLINE  = 5
SILENCE_THRESHOLD = 32


def test_ward():
    print("\n=== ward_core functional tests ===")

    # emission_band
    print("\n  emission_band:")
    check("zero → 0",      run_fn(WARD_SRC, "emission_band", {"emissions": 0,  "low": 5, "high": 50}), 0)
    check("low → 1",       run_fn(WARD_SRC, "emission_band", {"emissions": 2,  "low": 5, "high": 50}), 1)
    check("normal → 2",    run_fn(WARD_SRC, "emission_band", {"emissions": 20, "low": 5, "high": 50}), 2)
    check("high → 3",      run_fn(WARD_SRC, "emission_band", {"emissions": 99, "low": 5, "high": 50}), 3)

    # stall_counter_step
    print("\n  stall_counter_step:")
    check("emit → reset",     run_fn(WARD_SRC, "stall_counter_step", {"current_ticks": 10, "emissions": 5}), 0)
    check("no emit → inc",    run_fn(WARD_SRC, "stall_counter_step", {"current_ticks": 4,  "emissions": 0}), 5)
    check("saturate",         run_fn(WARD_SRC, "stall_counter_step", {"current_ticks": 32, "emissions": 0}), SILENCE_THRESHOLD)
    check("near sat → inc",   run_fn(WARD_SRC, "stall_counter_step", {"current_ticks": 31, "emissions": 0}), 32)

    # process_verdict
    print("\n  process_verdict:")
    check("bridge dead → OFFLINE",  run_fn(WARD_SRC, "process_verdict", {"emissions": 10, "stall_ticks": 0,  "bridge_alive": 0, "pipeline_depth": 8}), WARD_OFFLINE)
    check("stalled → STALLED",      run_fn(WARD_SRC, "process_verdict", {"emissions": 0,  "stall_ticks": 10, "bridge_alive": 1, "pipeline_depth": 8}), WARD_STALLED)
    check("emitting → HEALTHY",     run_fn(WARD_SRC, "process_verdict", {"emissions": 5,  "stall_ticks": 0,  "bridge_alive": 1, "pipeline_depth": 8}), WARD_HEALTHY)
    check("no emit → DEGRADED",     run_fn(WARD_SRC, "process_verdict", {"emissions": 0,  "stall_ticks": 2,  "bridge_alive": 1, "pipeline_depth": 8}), WARD_DEGRADED)

    # peripheral_verdict
    print("\n  peripheral_verdict:")
    check("bridge dead → OFFLINE",  run_fn(WARD_SRC, "peripheral_verdict", {"emissions": 0, "stall_ticks": 0,  "bridge_alive": 0}), WARD_OFFLINE)
    check("long silence → SILENT",  run_fn(WARD_SRC, "peripheral_verdict", {"emissions": 0, "stall_ticks": 33, "bridge_alive": 1}), WARD_SILENT)
    check("emitting → HEALTHY",     run_fn(WARD_SRC, "peripheral_verdict", {"emissions": 5, "stall_ticks": 0,  "bridge_alive": 1}), WARD_HEALTHY)
    check("short silence → IDLE",   run_fn(WARD_SRC, "peripheral_verdict", {"emissions": 0, "stall_ticks": 2,  "bridge_alive": 1}), WARD_IDLE)

    # throttle_flag
    print("\n  throttle_flag:")
    check("long stall → throttle",  run_fn(WARD_SRC, "throttle_flag", {"stall_ticks": 20, "emission_band_val": 2}), 1)
    check("HIGH band → throttle",   run_fn(WARD_SRC, "throttle_flag", {"stall_ticks": 0,  "emission_band_val": 3}), 1)
    check("normal → no throttle",   run_fn(WARD_SRC, "throttle_flag", {"stall_ticks": 2,  "emission_band_val": 2}), 0)

    # eviction_flag
    print("\n  eviction_flag:")
    check("OFFLINE → evict",       run_fn(WARD_SRC, "eviction_flag", {"stall_ticks": 0,  "verdict": WARD_OFFLINE}),  1)
    check("prolonged stall → evict", run_fn(WARD_SRC, "eviction_flag", {"stall_ticks": 65, "verdict": WARD_STALLED}), 1)
    check("healthy → keep",        run_fn(WARD_SRC, "eviction_flag", {"stall_ticks": 2,  "verdict": WARD_HEALTHY}), 0)

    # interpret_sentinel
    print("\n  interpret_sentinel:")
    check("0x02 → OK(0)",       run_fn(WARD_SRC, "interpret_sentinel", {"ptt_value": 0x02}),     0)
    check("0xFF00 → IDLE(1)",   run_fn(WARD_SRC, "interpret_sentinel", {"ptt_value": 0xFF00}),   1)
    check("0xDEAD00 → STALL(2)", run_fn(WARD_SRC, "interpret_sentinel", {"ptt_value": 0xDEAD00}), 2)
    check("0xBAD000 → FAULT(3)", run_fn(WARD_SRC, "interpret_sentinel", {"ptt_value": 0xBAD000}), 3)

    # combined_verdict
    print("\n  combined_verdict:")
    check("sentinel OK → pass through",     run_fn(WARD_SRC, "combined_verdict", {"sentinel_code": 0, "ward_verdict": WARD_HEALTHY}),  WARD_HEALTHY)
    check("sentinel FAULT → DEGRADED",      run_fn(WARD_SRC, "combined_verdict", {"sentinel_code": 3, "ward_verdict": WARD_HEALTHY}),  WARD_DEGRADED)
    check("sentinel STALL + healthy → DEG", run_fn(WARD_SRC, "combined_verdict", {"sentinel_code": 2, "ward_verdict": WARD_HEALTHY}),  WARD_DEGRADED)
    check("sentinel STALL + stalled → pass", run_fn(WARD_SRC, "combined_verdict", {"sentinel_code": 2, "ward_verdict": WARD_STALLED}), WARD_STALLED)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    filter_arg = sys.argv[1] if len(sys.argv) > 1 else None

    test_icm_files()

    if filter_arg is None or filter_arg == "sentinel":
        test_sentinel()

    if filter_arg is None or filter_arg == "ward":
        test_ward()

    print(f"\n{'═'*60}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"FAILURES: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
