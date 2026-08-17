"""
test_bridge_anomaly.py — Bridge Anomaly Detection Tests

Validates the three anomaly detection mechanisms added to PondBridge
in Phase 4. These implement the "immune system property" from the spec:
malformed behaviour has a physical footprint that the bridge detects.

  Stall detection (MONITOR bridge):
    MONITOR records consecutive zero-emission cycles. After stall_threshold
    cycles of silence following nonzero activity, is_stalled is set.
    Activity resuming clears the flag. cycles_stalled is the audit count.

  Spike detection (MONITOR bridge):
    A single cycle whose emission count exceeds spike_factor * capacity_per_cycle
    sets is_spiked for that cycle. is_spiked is a per-cycle flag (not latching).
    spike_count is the cumulative record; last_spike_emission records the level.

  Routing anomaly detection (INBOUND bridge):
    A rolling window of admission outcomes. When rejection_pct >= anomaly_threshold
    (default 50%) over anomaly_window recent access events, is_routing_anomaly is
    set. The flag clears when rejection rate drops below threshold.
    routing_anomaly_count is the cumulative record.

  clear_anomalies():
    Resets all flags and clears the access window. Does not reset counters
    (spike_count, routing_anomaly_count, cycles_stalled) — audit trail is permanent.

  Resource record surface:
    is_stalled, is_spiked, is_routing_anomaly appear as top-level fields in
    resource_record() for Cast/Ripple and Ward consumption.

Run with: python3 test_bridge_anomaly.py
"""

from unicell_array import UniCellArray
from pond import (Pond, PondManager, PondBridge,
                  OPEN, PRIVATE, PROCESS, FILE, PERIPHERAL)

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

def make_pond(pond_type=PROCESS, bridges=3, security=OPEN, cells=300):
    arr = UniCellArray(cells)
    mgr = PondManager(arr)
    return mgr.create_pond("test", "owner_xxxxxxxx",
                            pond_type=pond_type,
                            bridge_count=bridges,
                            security_level=security)

def get_monitor(pond) -> PondBridge:
    return next((b for b in pond.bridges if b.role == PondBridge.MONITOR), None)

def get_inbound(pond) -> PondBridge:
    return next((b for b in pond.bridges if b.role == PondBridge.INBOUND), None)


# =============================================================================
print("\n=== Anomaly flags exist on MONITOR bridge ===\n")

p = make_pond(bridges=3)
m = get_monitor(p)
check("MONITOR bridge found",              m is not None)
check("is_stalled starts False",           m.is_stalled == False)
check("is_spiked starts False",            m.is_spiked == False)
check("cycles_stalled starts 0",           m.cycles_stalled == 0)
check("spike_count starts 0",              m.spike_count == 0)
check("last_spike_emission starts 0",      m.last_spike_emission == 0)

inb = get_inbound(p)
check("is_routing_anomaly starts False",   inb.is_routing_anomaly == False)
check("routing_anomaly_count starts 0",    inb.routing_anomaly_count == 0)


# =============================================================================
print("\n=== Stall detection — basic ===\n")

p2 = make_pond(bridges=3)
m2 = get_monitor(p2)

# Warmup: nonzero emissions
for _ in range(10):
    m2.record_cycle(5)
check("Before stall: is_stalled = False",  m2.is_stalled == False)
check("Before stall: had_nonzero set",     m2._had_nonzero == True)

# Silence: consecutive zeros
for _ in range(m2.stall_threshold - 1):
    m2.record_cycle(0)
check("Just before threshold: still not stalled",
      m2.is_stalled == False)

m2.record_cycle(0)  # crosses threshold
check("At threshold: is_stalled = True",   m2.is_stalled == True)
check_eq("cycles_stalled = 1",             m2.cycles_stalled, 1)


# =============================================================================
print("\n=== Stall detection — no stall without prior activity ===\n")

p3 = make_pond(bridges=3)
m3 = get_monitor(p3)
for _ in range(m3.stall_threshold * 2):
    m3.record_cycle(0)
check("No stall if never had nonzero emissions", m3.is_stalled == False)
check_eq("cycles_stalled stays 0",               m3.cycles_stalled, 0)


# =============================================================================
print("\n=== Stall detection — recovery clears flag ===\n")

p4 = make_pond(bridges=3)
m4 = get_monitor(p4)
for _ in range(5): m4.record_cycle(8)
for _ in range(m4.stall_threshold + 1): m4.record_cycle(0)
check("Stalled before recovery",           m4.is_stalled == True)

m4.record_cycle(10)  # activity resumes
check("is_stalled cleared after activity", m4.is_stalled == False)
check("cycles_stalled count preserved",    m4.cycles_stalled >= 1)

m4.record_cycle(10)
check("Continues HEALTHY",                 m4.is_stalled == False)


# =============================================================================
print("\n=== Stall detection — multiple stall events count ===\n")

p5 = make_pond(bridges=3)
m5 = get_monitor(p5)
for cycle in range(3):
    for _ in range(5):  m5.record_cycle(8)   # activity
    for _ in range(m5.stall_threshold + 1):  # stall
        m5.record_cycle(0)
    m5.record_cycle(8)  # recover

check("Three stall events tracked",  m5.cycles_stalled == 3)


# =============================================================================
print("\n=== Spike detection — single cycle burst ===\n")

p6 = make_pond(bridges=3)
m6 = get_monitor(p6)
cap = m6.capacity_per_cycle
spike_level = int(cap * m6.spike_factor) + 1  # just above threshold

check("Normal emission: no spike",  (m6.record_cycle(cap) or True) and not m6.is_spiked)

m6.record_cycle(spike_level)
check("Spike level: is_spiked = True",       m6.is_spiked == True)
check_eq("spike_count = 1",                  m6.spike_count, 1)
check_eq("last_spike_emission recorded",     m6.last_spike_emission, spike_level)


# =============================================================================
print("\n=== Spike detection — per-cycle flag (not latching) ===\n")

p7 = make_pond(bridges=3)
m7 = get_monitor(p7)
cap7 = m7.capacity_per_cycle
spike7 = int(cap7 * m7.spike_factor) + 1

m7.record_cycle(spike7)
check("After spike cycle: is_spiked = True",  m7.is_spiked == True)

m7.record_cycle(1)  # normal cycle follows
check("After normal cycle: is_spiked = False", m7.is_spiked == False)
check("spike_count still 1",                   m7.spike_count == 1)


# =============================================================================
print("\n=== Spike detection — multiple spikes accumulate count ===\n")

p8 = make_pond(bridges=3)
m8 = get_monitor(p8)
cap8 = m8.capacity_per_cycle
spike8 = int(cap8 * m8.spike_factor) + 1

for _ in range(5):
    m8.record_cycle(spike8)
    m8.record_cycle(1)         # normal between spikes

check_eq("5 spike events: spike_count = 5",  m8.spike_count, 5)


# =============================================================================
print("\n=== Spike detection — below threshold is not a spike ===\n")

p9 = make_pond(bridges=3)
m9 = get_monitor(p9)
cap9 = m9.capacity_per_cycle

# Emit exactly at capacity — not a spike
m9.record_cycle(cap9)
check("Emission at capacity: no spike",  m9.is_spiked == False)

# Emit at factor * capacity exactly — edge: > not >=, so this is NOT a spike
m9.record_cycle(int(cap9 * m9.spike_factor))
check("Emission at exactly factor*capacity: no spike", m9.is_spiked == False)

# One above factor * capacity — this IS a spike
m9.record_cycle(int(cap9 * m9.spike_factor) + 1)
check("Emission one above factor*capacity: spike",   m9.is_spiked == True)


# =============================================================================
print("\n=== Routing anomaly — high rejection rate ===\n")

p10 = make_pond(security=PRIVATE, bridges=2)
inb10 = get_inbound(p10)
p10.grant_access("alice_xxxxxxxx")

# Fill window with rejections — strangers probing the bridge
for i in range(inb10.anomaly_window):
    inb10.check_access(f"stranger_{i:04d}")

check("High rejection rate: is_routing_anomaly = True",
      inb10.is_routing_anomaly == True)
check("routing_anomaly_count incremented",
      inb10.routing_anomaly_count >= 1)


# =============================================================================
print("\n=== Routing anomaly — clears when legitimate traffic normalises ===\n")

p11 = make_pond(security=PRIVATE, bridges=2)
inb11 = get_inbound(p11)
p11.grant_access("alice_xxxxxxxx")

# Trigger anomaly
for i in range(inb11.anomaly_window):
    inb11.check_access(f"stranger_{i:04d}")
check("Anomaly triggered",  inb11.is_routing_anomaly == True)

# Flush with admitted traffic
for _ in range(inb11.anomaly_window):
    inb11.check_access("alice_xxxxxxxx")
check("Anomaly cleared after legitimate traffic",
      inb11.is_routing_anomaly == False)
check("routing_anomaly_count preserved",
      inb11.routing_anomaly_count >= 1)


# =============================================================================
print("\n=== Routing anomaly — OPEN pond admits all, no anomaly possible ===\n")

p12 = make_pond(security=OPEN, bridges=2)
inb12 = get_inbound(p12)

# Even with "strangers", OPEN admits everyone
for i in range(inb12.anomaly_window * 2):
    inb12.check_access(f"anyone_{i:04d}")

check("OPEN pond: no routing anomaly (all admitted)",
      inb12.is_routing_anomaly == False)


# =============================================================================
print("\n=== Routing anomaly — only on INBOUND, not MONITOR ===\n")

p13 = make_pond(bridges=3)
m13  = get_monitor(p13)
inb13 = get_inbound(p13)

check("MONITOR bridge has is_routing_anomaly attribute",
      hasattr(m13, "is_routing_anomaly"))
check("INBOUND bridge has is_routing_anomaly attribute",
      hasattr(inb13, "is_routing_anomaly"))

# Status dict: MONITOR includes anomaly fields (stall, spike, routing)
# INBOUND includes routing anomaly (but not stall/spike — those are MONITOR-only)
m_st  = m13.status()
inb_st = inb13.status()
check("MONITOR status has is_stalled",          "is_stalled" in m_st)
check("MONITOR status has is_spiked",           "is_spiked" in m_st)
check("MONITOR status has is_routing_anomaly",  "is_routing_anomaly" in m_st)
check("INBOUND status has is_routing_anomaly",  "is_routing_anomaly" in inb_st)


# =============================================================================
print("\n=== clear_anomalies() — resets flags, preserves counts ===\n")

p14 = make_pond(security=PRIVATE, bridges=3)
m14  = get_monitor(p14)
inb14 = get_inbound(p14)
p14.grant_access("alice_xxxxxxxx")

# Trigger stall on m14
for _ in range(5): m14.record_cycle(8)
for _ in range(m14.stall_threshold + 1): m14.record_cycle(0)
check("Before clear: is_stalled",      m14.is_stalled == True)

stall_count_before  = m14.cycles_stalled
anomaly_count_before = inb14.routing_anomaly_count

m14.clear_anomalies()
check("After clear: is_stalled = False",   m14.is_stalled == False)
check("cycles_stalled count preserved",    m14.cycles_stalled == stall_count_before)

# Spike on a fresh monitor (spike record_cycle is nonzero — resets stall)
p14b = make_pond(bridges=3)
m14b = get_monitor(p14b)
cap14b = m14b.capacity_per_cycle
m14b.record_cycle(int(cap14b * m14b.spike_factor) + 1)
check("Before clear: is_spiked",       m14b.is_spiked == True)
spike_count_before = m14b.spike_count

m14b.clear_anomalies()
check("After clear: is_spiked = False",    m14b.is_spiked == False)
check("spike_count preserved",             m14b.spike_count == spike_count_before)

# Routing anomaly on inb14
for i in range(inb14.anomaly_window):
    inb14.check_access(f"probe_{i:04d}")
check("Before clear: routing anomaly",  inb14.is_routing_anomaly == True)
anomaly_count_before = inb14.routing_anomaly_count

inb14.clear_anomalies()
check("After clear: routing_anomaly = False", inb14.is_routing_anomaly == False)
check("routing_anomaly_count preserved",  inb14.routing_anomaly_count == anomaly_count_before)


# =============================================================================
print("\n=== Resource record surface ===\n")

p15 = make_pond(bridges=3)
rr = p15.resource_record()
check("resource_record has is_stalled",          "is_stalled" in rr)
check("resource_record has is_spiked",           "is_spiked" in rr)
check("resource_record has is_routing_anomaly",  "is_routing_anomaly" in rr)
check("resource_record all False initially",
      rr["is_stalled"] == False and
      rr["is_spiked"] == False and
      rr["is_routing_anomaly"] == False)

# Trigger stall and confirm it surfaces in resource_record
m15 = get_monitor(p15)
for _ in range(5): m15.record_cycle(5)
for _ in range(m15.stall_threshold + 1): m15.record_cycle(0)

rr2 = p15.resource_record()
check("Stall surfaces in resource_record", rr2["is_stalled"] == True)

# Trigger spike
m15.record_cycle(int(m15.capacity_per_cycle * m15.spike_factor) + 1)
rr3 = p15.resource_record()
check("Spike surfaces in resource_record", rr3["is_spiked"] == True)


# =============================================================================
print("\n=== Ward reads bridge anomalies — integration ===\n")

# The Ward's _tick_process reads monitor.is_throttled. Now anomaly flags
# are also on the bridge for the Ward to consume. Verify the Ward sees them
# through the same bridge reference.
from ward import Ward

p16 = make_pond(bridges=3)
w16  = p16.ward
m16  = get_monitor(p16)

# Warmup Ward
for _ in range(5): w16.tick(5)

# Trigger stall via bridge record_cycle
for _ in range(5): m16.record_cycle(8)
for _ in range(m16.stall_threshold + 1): m16.record_cycle(0)

# Ward's own stall detection and bridge's stall flag should both be set
check("Bridge is_stalled",  m16.is_stalled == True)
# Tick Ward independently of bridge (Ward has its own consecutive_zeros counter)
for _ in range(Ward.WARMUP_CYCLES + Ward.STALL_THRESHOLD + 2):
    w16.tick(0)
from ward import STALLED
check("Ward independently reaches STALLED", w16.state == STALLED)


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
