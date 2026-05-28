"""
test_handshake.py — Bridge Handshake ACK/REQ Tests

Validates the Bus 1 handshake field (bits 18-21):
  - build_bus1 / decode_bus1 round-trip with handshake
  - PondBridge handshake counters and state
  - INBOUND/OUTBOUND bridges participate, MONITOR/LOG do not
  - Ward-visible busy_stalled detection
  - Scope field correctly identifies handshake level
"""

from command_interface import (
    build_bus1, decode_bus1,
    _SCOPE_LOCAL, _SCOPE_SHORE, _SCOPE_EXTENDED,
    HANDSHAKE_NONE, HANDSHAKE_ACK, HANDSHAKE_NAK,
    HANDSHAKE_BUSY, HANDSHAKE_REQUEST, HANDSHAKE_GRANT,
    HANDSHAKE_DENY, HANDSHAKE_RETRY,
    CMD_DATA_WRITE, CMD_PING,
)
from pond import PondBridge, Pond

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

# ── helpers ──────────────────────────────────────────────────────────────────

def make_bridge(role, addresses=None):
    """Create a minimal PondBridge for testing."""
    if addresses is None:
        addresses = [0x1000]
    return PondBridge(addresses, role, pond=None)

# ── Bus 1 round-trip ─────────────────────────────────────────────────────────

print("\n=== Bus 1 handshake field — build/decode round-trip ===\n")

for hs_name, hs_val in [
    ("NONE",    HANDSHAKE_NONE),
    ("ACK",     HANDSHAKE_ACK),
    ("NAK",     HANDSHAKE_NAK),
    ("BUSY",    HANDSHAKE_BUSY),
    ("REQUEST", HANDSHAKE_REQUEST),
    ("GRANT",   HANDSHAKE_GRANT),
    ("DENY",    HANDSHAKE_DENY),
    ("RETRY",   HANDSHAKE_RETRY),
]:
    b1 = build_bus1(CMD_DATA_WRITE, handshake=hs_val)
    _, _, _, _, hs_out = decode_bus1(b1)
    check_eq(f"round-trip: HANDSHAKE_{hs_name}", hs_out, hs_val)

print("\n=== Handshake does not corrupt other Bus 1 fields ===\n")

b1 = build_bus1(CMD_PING, auth=0b10101010101, raw_addr=True,
                scope=_SCOPE_SHORE, handshake=HANDSHAKE_ACK)
cmd, auth, is_raw, scope, hs = decode_bus1(b1)
check_eq("cmd preserved with handshake",   cmd,    CMD_PING)
check_eq("auth preserved with handshake",  auth,   0b10101010101)
check("raw_addr preserved with handshake", is_raw)
check_eq("scope preserved with handshake", scope,  _SCOPE_SHORE)
check_eq("handshake field correct",        hs,     HANDSHAKE_ACK)

print("\n=== Scope identifies handshake level ===\n")

for scope_name, scope_val in [
    ("LOCAL",    _SCOPE_LOCAL),
    ("SHORE",    _SCOPE_SHORE),
    ("EXTENDED", _SCOPE_EXTENDED),
]:
    b1 = build_bus1(CMD_DATA_WRITE, scope=scope_val, handshake=HANDSHAKE_ACK)
    _, _, _, s_out, hs_out = decode_bus1(b1)
    check_eq(f"scope {scope_name} round-trip", s_out, scope_val)
    check_eq(f"handshake preserved at {scope_name}", hs_out, HANDSHAKE_ACK)

# ── PondBridge handshake participation ───────────────────────────────────────

print("\n=== Bridge handshake participation ===\n")

inbound  = make_bridge(PondBridge.INBOUND)
outbound = make_bridge(PondBridge.OUTBOUND)
monitor  = make_bridge(PondBridge.MONITOR)
log_br   = make_bridge(PondBridge.LOG)

check("INBOUND bridge hs_enabled",   inbound.hs_enabled)
check("OUTBOUND bridge hs_enabled",  outbound.hs_enabled)
check("MONITOR bridge hs_disabled", not monitor.hs_enabled)
check("LOG bridge hs_disabled",     not log_br.hs_enabled)

# ── Counter tracking ─────────────────────────────────────────────────────────

print("\n=== Handshake counter tracking ===\n")

b = make_bridge(PondBridge.INBOUND)

b.record_handshake_sent(HANDSHAKE_ACK)
b.record_handshake_sent(HANDSHAKE_ACK)
check_eq("ACK count", b.hs_ack_count, 2)

b.record_handshake_sent(HANDSHAKE_NAK)
check_eq("NAK count", b.hs_nak_count, 1)

b.record_handshake_sent(HANDSHAKE_GRANT)
check_eq("GRANT count", b.hs_grant_count, 1)

b.record_handshake_sent(HANDSHAKE_DENY)
check_eq("DENY count", b.hs_deny_count, 1)

b.record_handshake_sent(HANDSHAKE_RETRY)
check_eq("RETRY count", b.hs_retry_count, 1)

b.record_handshake_received(HANDSHAKE_REQUEST)
b.record_handshake_received(HANDSHAKE_REQUEST)
check_eq("REQUEST count", b.hs_request_count, 2)

check_eq("last_hs_sent",     b.last_hs_sent,     HANDSHAKE_RETRY)
check_eq("last_hs_received", b.last_hs_received, HANDSHAKE_REQUEST)

# ── MONITOR/LOG bridges ignore handshake calls ───────────────────────────────

print("\n=== MONITOR/LOG ignore handshake calls ===\n")

m = make_bridge(PondBridge.MONITOR)
m.record_handshake_sent(HANDSHAKE_ACK)
m.record_handshake_received(HANDSHAKE_REQUEST)
check_eq("MONITOR ack_count stays 0",     m.hs_ack_count,     0)
check_eq("MONITOR request_count stays 0", m.hs_request_count, 0)

# ── Busy-stall detection ─────────────────────────────────────────────────────

print("\n=== Busy-stall detection ===\n")

b = make_bridge(PondBridge.OUTBOUND)
b.busy_threshold = 3

b.record_handshake_sent(HANDSHAKE_BUSY)
check("not stalled after 1 BUSY",  not b.is_busy_stalled)
check_eq("consecutive_busy = 1",   b._consecutive_busy, 1)

b.record_handshake_sent(HANDSHAKE_BUSY)
b.record_handshake_sent(HANDSHAKE_BUSY)
check("stalled after threshold",   b.is_busy_stalled)
check_eq("busy_count = 3",         b.hs_busy_count, 3)

# ACK clears the stall
b.record_handshake_sent(HANDSHAKE_ACK)
check("stall cleared after ACK",   not b.is_busy_stalled)
check_eq("consecutive_busy reset", b._consecutive_busy, 0)

# ── handshake_status dict ────────────────────────────────────────────────────

print("\n=== handshake_status() dict ===\n")

b = make_bridge(PondBridge.INBOUND)
b.record_handshake_sent(HANDSHAKE_ACK)
b.record_handshake_received(HANDSHAKE_REQUEST)
hs = b.handshake_status()

check("status: enabled",          hs["enabled"])
check_eq("status: ack_count",     hs["ack_count"],     1)
check_eq("status: request_count", hs["request_count"], 1)
check("status: not busy_stalled", not hs["is_busy_stalled"])

# ── Bridge status() includes handshake ───────────────────────────────────────

print("\n=== bridge.status() includes handshake field ===\n")

b = make_bridge(PondBridge.INBOUND)
b.record_handshake_sent(HANDSHAKE_NAK)
st = b.status()

check("INBOUND status has handshake key",    "handshake" in st)
check_eq("status handshake nak_count",       st["handshake"]["nak_count"], 1)

m = make_bridge(PondBridge.MONITOR)
st_m = m.status()
check("MONITOR status has no handshake key", "handshake" not in st_m)

# ── Results ──────────────────────────────────────────────────────────────────

print("\n=== Results ===\n")
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("Failed:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
