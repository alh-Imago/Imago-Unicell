"""
test_ward.py — Ward Watchdog Tests

Validates Ward state machines for all Pond types.

  Ward states:
    IDLE     — no data yet
    HEALTHY  — normal operation
    DEGRADED — threshold breached (throttle, request/response mismatch)
    STALLED  — PROCESS: zero emissions after activity
    SILENT   — PERIPHERAL: device gone quiet after activity
    OFFLINE  — bridge health check failed

  Per-type behaviour:
    FILE       — bridge alive → HEALTHY. Nearly nothing to watch.
    PERIPHERAL — activity then silence → SILENT
    LIBRARY    — inbound with zero outbound → DEGRADED
    PROCESS    — stall detection, throttle detection
    COMPANION  — pulse check only, always HEALTHY if bridge alive
    BOOT       — no Ward (pond.ward is None)

  Integration:
    Ward is attached to pond.ward at construction
    Ward state appears in resource_record()
    Ward.reset() clears all state back to IDLE

Run with: python3 test_ward.py
"""

import time
from unicell_array import UniCellArray
from pond import (Pond, PondManager, PondBridge,
                  OPEN, PRIVATE, HIDDEN,
                  PROCESS, FILE, PERIPHERAL, LIBRARY, COMPANION, BOOT)
from ward import Ward, WardStatus, make_ward, IDLE, HEALTHY, DEGRADED, STALLED, SILENT, OFFLINE

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    if not ok:
        print(f"    got {got!r}, expected {expected!r}")
    check(name, ok)

def make_pond(pond_type=PROCESS, bridges=3, cells=200, security=OPEN):
    arr = UniCellArray(cells)
    mgr = PondManager(arr)
    return mgr.create_pond("test", "owner_xxxxxxxx",
                            pond_type=pond_type,
                            bridge_count=bridges,
                            security_level=security)


# =============================================================================
print("\n=== Ward creation and attachment ===\n")

p_proc = make_pond(PROCESS)
check("PROCESS pond has a Ward",           p_proc.ward is not None)
check("Ward is a Ward instance",           isinstance(p_proc.ward, Ward))
check_eq("Ward starts in IDLE",            p_proc.ward.state, IDLE)
check_eq("Ward pond_type matches pond",    p_proc.ward._pond_type, PROCESS)

p_boot = make_pond(BOOT)
check("BOOT pond ward is None",            p_boot.ward is None)

p_file = make_pond(FILE)
check("FILE pond has a Ward",              p_file.ward is not None)

p_comp = make_pond(COMPANION)
check("COMPANION pond has a Ward",         p_comp.ward is not None)


# =============================================================================
print("\n=== Ward — IDLE → HEALTHY on first tick ===\n")

for ptype in (PROCESS, FILE, PERIPHERAL, LIBRARY, COMPANION):
    p = make_pond(ptype)
    w = p.ward
    check_eq(f"{ptype}: starts IDLE", w.state, IDLE)
    status = w.tick(emissions=5)
    check_eq(f"{ptype}: IDLE → HEALTHY after first tick", w.state, HEALTHY)
    check("WardStatus returned", isinstance(status, WardStatus))


# =============================================================================
print("\n=== WardStatus fields ===\n")

w = make_pond(PROCESS).ward
w.tick(10); w.tick(5); w.tick(8)
st = w.status
check("status.state is string",           isinstance(st.state, str))
check_eq("status.cycles_observed = 3",    st.cycles_observed, 3)
check("status.mean_emissions > 0",        st.mean_emissions > 0)
check_eq("status.peak_emissions = 10",    st.peak_emissions, 10)
check("status.to_dict() returns dict",    isinstance(st.to_dict(), dict))
check("to_dict has required keys",        all(k in st.to_dict() for k in
      ("state","cycles_observed","mean_emissions","peak_emissions")))


# =============================================================================
print("\n=== FILE Ward — minimal, bridge-alive check ===\n")

p_f = make_pond(FILE)
w_f = p_f.ward
# FILE Ward: any emissions → HEALTHY
for _ in range(5):
    w_f.tick(0)
check_eq("FILE: stays HEALTHY with zero emissions", w_f.state, HEALTHY)
w_f.tick(20)
check_eq("FILE: HEALTHY with nonzero emissions", w_f.state, HEALTHY)

# cycles_stalled and cycles_silent never increment for FILE
check_eq("FILE: no stall cycles", w_f.status.cycles_stalled, 0)
check_eq("FILE: no silent cycles", w_f.status.cycles_silent, 0)


# =============================================================================
print("\n=== COMPANION Ward — pulse only ===\n")

p_c = make_pond(COMPANION)
w_c = p_c.ward
for _ in range(20):
    w_c.tick(0)
check_eq("COMPANION: HEALTHY with zero emissions", w_c.state, HEALTHY)
check_eq("COMPANION: no stall cycles", w_c.status.cycles_stalled, 0)
check_eq("COMPANION: no silent cycles", w_c.status.cycles_silent, 0)


# =============================================================================
print("\n=== PROCESS Ward — healthy operation ===\n")

p_pr = make_pond(PROCESS, bridges=3)
w_pr = p_pr.ward
for i in range(30):
    w_pr.tick(emissions=10 + i % 5)
check_eq("PROCESS: HEALTHY with regular emissions", w_pr.state, HEALTHY)
check("PROCESS: cycles_healthy > 0", w_pr.status.cycles_healthy > 0)
check("PROCESS: mean_emissions > 0", w_pr.status.mean_emissions > 0)


# =============================================================================
print("\n=== PROCESS Ward — stall detection ===\n")

p_stall = make_pond(PROCESS, bridges=3)
w_stall = p_stall.ward

# Warmup with activity
for _ in range(Ward.WARMUP_CYCLES + 5):
    w_stall.tick(emissions=10)
check_eq("PROCESS pre-stall: HEALTHY", w_stall.state, HEALTHY)
check("PROCESS pre-stall: had_activity set", w_stall._had_activity)

# Now silence — should stall after STALL_THRESHOLD cycles
for _ in range(Ward.STALL_THRESHOLD - 1):
    w_stall.tick(emissions=0)
check_eq("PROCESS: still HEALTHY just before threshold",
         w_stall.state, HEALTHY)

w_stall.tick(emissions=0)  # this tick crosses the threshold
check_eq("PROCESS: STALLED after threshold", w_stall.state, STALLED)
check("PROCESS: anomaly_reason mentions cycles",
      "cycles" in w_stall.status.anomaly_reason)
check("PROCESS: cycles_stalled > 0",
      w_stall.status.cycles_stalled > 0)


# =============================================================================
print("\n=== PROCESS Ward — stall does not fire without prior activity ===\n")

p_no_act = make_pond(PROCESS, bridges=3)
w_no_act = p_no_act.ward
# Pure silence from the start — should NOT stall (warmup requires activity)
for _ in range(Ward.STALL_THRESHOLD * 2):
    w_no_act.tick(emissions=0)
check_eq("PROCESS: no stall if never active", w_no_act.state, HEALTHY)


# =============================================================================
print("\n=== PROCESS Ward — recovery from stall (activity resumes) ===\n")

p_rec = make_pond(PROCESS, bridges=3)
w_rec = p_rec.ward
# Warmup
for _ in range(Ward.WARMUP_CYCLES + 5):
    w_rec.tick(10)
# Stall
for _ in range(Ward.STALL_THRESHOLD + 1):
    w_rec.tick(0)
check_eq("PROCESS: STALLED", w_rec.state, STALLED)

# Activity resumes — consecutive_zeros resets, should return to HEALTHY
w_rec.tick(emissions=15)
check_eq("PROCESS: HEALTHY after activity resumes", w_rec.state, HEALTHY)


# =============================================================================
print("\n=== PROCESS Ward — throttle detection ===\n")

p_thr = make_pond(PROCESS, bridges=3)
monitor = p_thr.ward._get_monitor()
if monitor:
    # Feed the monitor enough emissions to cross throttle threshold (80%)
    # capacity_per_cycle is the Pond's inbound_lanes (integer).
    # Use full capacity (100%) to reliably exceed the 80% threshold.
    capacity = monitor.capacity_per_cycle
    overload = capacity   # 100% utilisation > 80% threshold
    for _ in range(monitor.utilisation_window + 5):
        monitor.record_cycle(overload)

    w_thr = p_thr.ward
    for _ in range(Ward.WARMUP_CYCLES + 1):
        w_thr.tick(overload)

    check_eq("PROCESS: DEGRADED when monitor throttled",
             w_thr.state, DEGRADED)
    check("PROCESS: anomaly_reason mentions throttle",
          "throttl" in w_thr.status.anomaly_reason.lower())
else:
    check("PROCESS throttle: MONITOR bridge present (bridge_count=3)", False)


# =============================================================================
print("\n=== PERIPHERAL Ward — healthy operation ===\n")

p_per = make_pond(PERIPHERAL, bridges=3)
w_per = p_per.ward
for _ in range(20):
    w_per.tick(emissions=5)
check_eq("PERIPHERAL: HEALTHY with regular emissions", w_per.state, HEALTHY)


# =============================================================================
print("\n=== PERIPHERAL Ward — silence detection ===\n")

p_sil = make_pond(PERIPHERAL, bridges=3)
w_sil = p_sil.ward

# Warmup with device activity
for _ in range(Ward.WARMUP_CYCLES + 5):
    w_sil.tick(emissions=8)
check_eq("PERIPHERAL pre-silence: HEALTHY", w_sil.state, HEALTHY)

# Device goes silent
for _ in range(Ward.SILENCE_THRESHOLD - 1):
    w_sil.tick(emissions=0)
check_eq("PERIPHERAL: HEALTHY just before silence threshold",
         w_sil.state, HEALTHY)

w_sil.tick(emissions=0)
check_eq("PERIPHERAL: SILENT after threshold", w_sil.state, SILENT)
check("PERIPHERAL: cycles_silent > 0", w_sil.status.cycles_silent > 0)
check("PERIPHERAL: anomaly_reason mentions silent",
      "silent" in w_sil.status.anomaly_reason.lower())


# =============================================================================
print("\n=== PERIPHERAL Ward — silence threshold is shorter than PROCESS stall ===\n")

check("SILENCE_THRESHOLD < STALL_THRESHOLD",
      Ward.SILENCE_THRESHOLD < Ward.STALL_THRESHOLD)


# =============================================================================
print("\n=== PERIPHERAL Ward — device reconnects (silence clears) ===\n")

p_rec2 = make_pond(PERIPHERAL, bridges=3)
w_rec2 = p_rec2.ward
for _ in range(Ward.WARMUP_CYCLES + 5):
    w_rec2.tick(8)
for _ in range(Ward.SILENCE_THRESHOLD + 1):
    w_rec2.tick(0)
check_eq("PERIPHERAL: SILENT", w_rec2.state, SILENT)

w_rec2.tick(emissions=12)
check_eq("PERIPHERAL: HEALTHY after device resumes",
         w_rec2.state, HEALTHY)


# =============================================================================
print("\n=== LIBRARY Ward — healthy operation ===\n")

p_lib = make_pond(LIBRARY, bridges=2)
w_lib = p_lib.ward
# No requests yet — should be HEALTHY (not DEGRADED; zero-zero is not a mismatch)
for _ in range(20):
    w_lib.tick(0)
check_eq("LIBRARY: HEALTHY with no requests", w_lib.state, HEALTHY)


# =============================================================================
print("\n=== LIBRARY Ward — request/response mismatch ===\n")

p_lib2 = make_pond(LIBRARY, bridges=2)
w_lib2 = p_lib2.ward

# Simulate inbound requests accumulating
inbound = w_lib2._get_bridge_role("INBOUND")
outbound = w_lib2._get_bridge_role("OUTBOUND")
if inbound and outbound:
    # Drive inbound packets but leave outbound at zero
    for _ in range(5):
        inbound.packets_passed += 3

    for _ in range(Ward.WARMUP_CYCLES + 1):
        w_lib2.tick(5)

    check_eq("LIBRARY: DEGRADED when inbound > 0 and outbound = 0",
             w_lib2.state, DEGRADED)
    check("LIBRARY: anomaly reason mentions outbound",
          "outbound" in w_lib2.status.anomaly_reason.lower())
else:
    check("LIBRARY mismatch test: bridges found", False)


# =============================================================================
print("\n=== LIBRARY Ward — outbound responses arrive, recovers ===\n")

p_lib3 = make_pond(LIBRARY, bridges=2)
w_lib3 = p_lib3.ward
inbound3  = w_lib3._get_bridge_role("INBOUND")
outbound3 = w_lib3._get_bridge_role("OUTBOUND")

if inbound3 and outbound3:
    for _ in range(5):
        inbound3.packets_passed += 3

    for _ in range(Ward.WARMUP_CYCLES + 1):
        w_lib3.tick(5)
    check_eq("LIBRARY: DEGRADED before fix", w_lib3.state, DEGRADED)

    # Outbound starts responding
    outbound3.packets_passed += 10
    w_lib3.tick(5)
    check_eq("LIBRARY: HEALTHY after outbound responds",
             w_lib3.state, HEALTHY)


# =============================================================================
print("\n=== OFFLINE state — bridge deallocated ===\n")

p_off = make_pond(PROCESS, bridges=3)
w_off = p_off.ward
w_off.tick(10)
check_eq("Pre-offline: HEALTHY", w_off.state, HEALTHY)

# Simulate bridge deallocation by clearing bridges list
p_off.bridges.clear()
w_off.tick(5)
check_eq("OFFLINE after bridge deallocation", w_off.state, OFFLINE)
check("OFFLINE: anomaly_reason set", len(w_off.status.anomaly_reason) > 0)


# =============================================================================
print("\n=== Ward.reset() ===\n")

p_rst = make_pond(PROCESS, bridges=3)
w_rst = p_rst.ward
for _ in range(Ward.WARMUP_CYCLES + Ward.STALL_THRESHOLD + 5):
    if _ < Ward.WARMUP_CYCLES + 5:
        w_rst.tick(10)
    else:
        w_rst.tick(0)

check("STALLED before reset",     w_rst.state == STALLED)
check("cycles_stalled > 0",       w_rst.status.cycles_stalled > 0)

w_rst.reset()
check_eq("After reset: state = IDLE",        w_rst.state, IDLE)
check_eq("After reset: cycles_observed = 0", w_rst.status.cycles_observed, 0)
check_eq("After reset: cycles_stalled = 0",  w_rst.status.cycles_stalled, 0)
check_eq("After reset: peak_emissions = 0",  w_rst.status.peak_emissions, 0)
check("After reset: had_activity cleared",   not w_rst._had_activity)


# =============================================================================
print("\n=== Ward state appears in resource_record() ===\n")

p_rr = make_pond(PROCESS, bridges=3)
p_rr.ward.tick(10)
rr = p_rr.resource_record()

check("resource_record has 'ward' key",     "ward" in rr)
check("resource_record ward is dict",       isinstance(rr["ward"], dict))
check("resource_record ward.state = HEALTHY", rr["ward"]["state"] == HEALTHY)
check("resource_record ward has cycles_observed",
      "cycles_observed" in rr["ward"])

# BOOT pond has ward = None in resource_record
p_boot2 = make_pond(BOOT)
rr_boot = p_boot2.resource_record()
check("BOOT: resource_record ward = None", rr_boot["ward"] is None)


# =============================================================================
print("\n=== Ward emission statistics ===\n")

p_stat = make_pond(PROCESS, bridges=3)
w_stat = p_stat.ward
emissions_seq = [10, 20, 5, 15, 0, 8]
for e in emissions_seq:
    w_stat.tick(e)

check_eq("peak_emissions = 20", w_stat.status.peak_emissions, 20)
expected_mean = sum(emissions_seq) / len(emissions_seq)
check("mean_emissions approximately correct",
      abs(w_stat.status.mean_emissions - expected_mean) < 0.1)
check("last_nonzero_at set after nonzero emission",
      w_stat.status.last_nonzero_at is not None)


# =============================================================================
print("\n=== Ward WARMUP_CYCLES guard ===\n")

# The WARMUP guard prevents stall detection until cycles_observed >= WARMUP_CYCLES.
# If activity occurred but cycles_observed is still below WARMUP_CYCLES, no stall.
p_wu = make_pond(PROCESS, bridges=3)
w_wu = p_wu.ward
# Tick once with activity (cycles_observed = 1 < WARMUP_CYCLES=10)
# then silence — stall threshold cannot fire until warmup completes.
w_wu.tick(10)   # cycles_observed = 1, had_activity = True
# Add STALL_THRESHOLD-1 zeros while still within warmup window
for _ in range(Ward.WARMUP_CYCLES - 2):  # cycles_observed reaches WARMUP_CYCLES-1
    w_wu.tick(0)
check_eq("PROCESS: no stall before warmup cycles complete",
         w_wu.state, HEALTHY)

# Confirm: once cycles_observed >= WARMUP_CYCLES and zeros >= STALL_THRESHOLD,
# stall fires. This confirms the threshold is enforced, not bypassed.
p_wu2 = make_pond(PROCESS, bridges=3)
w_wu2 = p_wu2.ward
for _ in range(Ward.WARMUP_CYCLES + 5):
    w_wu2.tick(10)
for _ in range(Ward.STALL_THRESHOLD + 1):
    w_wu2.tick(0)
check_eq("PROCESS: STALLED after full warmup + stall threshold",
         w_wu2.state, STALLED)


# =============================================================================
print("\n=== Results ===\n")

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
total  = len(results)
print(f"Results: {passed} passed, {failed} failed out of {total} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for status, name in results:
        if status == "FAIL":
            print(f"  [FAIL] {name}")
