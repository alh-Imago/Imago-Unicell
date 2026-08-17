"""
test_bridge_log.py -- Bridge Log System Tests

Covers:
  - BridgeCrossingRecord structure
  - BridgeLog: denied_log, capture_log, sequence counter
  - Denial push to ShoreKeeper
  - Capture window activation (manual, Ward trigger, spike trigger)
  - Owner-gated access
  - Pond.last_active_at updated on admitted crossings
  - PondManager.reap_stale()
  - resource_record() includes bridge log status
"""

import time
from unicell_array import UniCellArray
from pond import (
    Pond, PondManager, PondBridge,
    BridgeCrossingRecord, BridgeLog,
    OPEN, PRIVATE, HIDDEN, PROCESS,
)

results = []

def check(label, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    print(f"  [{status}] {label}")

def check_eq(label, got, expected):
    ok = got == expected
    if not ok:
        print(f"    got {got!r}, expected {expected!r}")
    check(label, ok)

def section(title):
    print(f"\n=== {title} ===\n")

OWNER   = "owner_id_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
BOB     = "bob_id_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
STRANGER= "stranger_id_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ---- BridgeCrossingRecord ---------------------------------------------------
section("BridgeCrossingRecord structure")

rec = BridgeCrossingRecord(
    timestamp   = time.time(),
    sequence    = 1,
    identity_id = BOB,
    bridge_role = "INBOUND",
    admitted    = True,
    reason      = "WHITELISTED",
    ptt_index   = 3,
    handshake   = 1,
)
check("record: admitted",           rec.admitted)
check("record: bridge_role",        rec.bridge_role == "INBOUND")
check("record: ptt_index",          rec.ptt_index == 3)
check("record: handshake",          rec.handshake == 1)
check("record: metadata empty",     rec.metadata == {})

d = rec.to_dict()
check("to_dict: has sequence",      "sequence" in d)
check("to_dict: identity truncated", d["identity"].endswith("..."))
check("to_dict: has reason",        "reason" in d)

# ---- BridgeLog basic --------------------------------------------------------
section("BridgeLog basic operation")

bl = BridgeLog()
check("initial sequence 0",   bl.status()["sequence"] == 0)
check("initial no denials",   not bl.has_denials())
check("initial not capturing", not bl.is_capturing)

# Record admitted crossing -- not stored in denied_log
bl.record(BOB, "INBOUND", True, "OPEN")
check("sequence increments",   bl.status()["sequence"] == 1)
check("admitted not in denied", bl.denied_count() == 0)

# Record denied crossing -- stored in denied_log
bl.record(STRANGER, "INBOUND", False, "REJECTED")
check("denied count 1",        bl.denied_count() == 1)
check("has_denials True",      bl.has_denials())
check("sequence now 2",        bl.status()["sequence"] == 2)

# ---- Denied log access control ----------------------------------------------
section("Denied log access control")

bl2 = BridgeLog()
bl2.record(STRANGER, "INBOUND", False, "EXPIRED")

log = bl2.get_denied(OWNER, OWNER)
check("owner reads denied log",     len(log) == 1)
check("denied entry not admitted",  not log[0]["admitted"])
check("denied entry reason",        log[0]["reason"] == "EXPIRED")

perm_err = False
try:
    bl2.get_denied(BOB, OWNER)
except PermissionError:
    perm_err = True
check("non-owner cannot read denied log", perm_err)

# ---- Denied log cap ---------------------------------------------------------
section("Denied log cap at DENIED_CAP")

bl3 = BridgeLog()
bl3.DENIED_CAP = 5
for i in range(7):
    bl3.record(f"id_{i}", "INBOUND", False, "REJECTED")
check("cap enforced at 5", bl3.denied_count() == 5)

# ---- Capture window ---------------------------------------------------------
section("Capture window")

bl4 = BridgeLog()
check("not capturing initially", not bl4.is_capturing)

bl4.start_capture(3)
check("capturing after start", bl4.is_capturing)
check("capture buffer empty",  len(bl4._capture) == 0)

bl4.record(BOB,     "INBOUND", True,  "OPEN")
bl4.record(STRANGER,"INBOUND", False, "REJECTED")
bl4.record(BOB,     "OUTBOUND",True,  "OPEN")
check("3 records captured",    len(bl4._capture) == 3)
check("capture auto-stopped",  not bl4.is_capturing)

# Capture includes admitted and denied
admitted_in_capture = [r for r in bl4._capture if r.admitted]
denied_in_capture   = [r for r in bl4._capture if not r.admitted]
check("capture has admitted",  len(admitted_in_capture) == 2)
check("capture has denied",    len(denied_in_capture) == 1)

# get_capture owner-gated
cap = bl4.get_capture(OWNER, OWNER)
check("owner reads capture",   len(cap) == 3)
perm_err2 = False
try:
    bl4.get_capture(BOB, OWNER)
except PermissionError:
    perm_err2 = True
check("non-owner cannot read capture", perm_err2)

# ---- ShoreKeeper push -------------------------------------------------------
section("Denial push to ShoreKeeper")

class MockSK:
    def __init__(self):
        self.denials  = []
        self.captures = []
    def receive_denial(self, rec):
        self.denials.append(rec)
    def receive_capture(self, recs):
        self.captures.append(recs)

sk = MockSK()
bl5 = BridgeLog()
bl5.attach_shorekeeper(sk)

bl5.record(BOB,     "INBOUND", True,  "OPEN")      # admitted -- not pushed
bl5.record(STRANGER,"INBOUND", False, "REJECTED")  # denied -- pushed

check("ShoreKeeper received 1 denial", len(sk.denials) == 1)
check("pushed denial not admitted",    not sk.denials[0].admitted)
check("admitted not pushed",           len(sk.denials) == 1)

# Capture completion pushed to ShoreKeeper
bl5.start_capture(2)
bl5.record(BOB, "INBOUND", True, "OPEN")
bl5.record(BOB, "INBOUND", True, "OPEN")
check("capture pushed to ShoreKeeper", len(sk.captures) == 1)
check("capture has 2 records",         len(sk.captures[0]) == 2)

# ---- Pond integration -------------------------------------------------------
section("Pond bridge_log integration")

arr = UniCellArray(cell_count=500)
arr.enforce_emission_limits = False
mgr = PondManager(arr)
p = mgr.create_pond("test_pond", OWNER,
                     security_level=PRIVATE, pond_type=PROCESS)

p.grant_access(BOB, label="bob")
inbound = next(b for b in p.bridges if b.role == PondBridge.INBOUND)

# Admitted crossing
inbound.check_access(BOB)
check("admitted: sequence 1",   p.bridge_log.status()["sequence"] == 1)
check("admitted: no denial",    p.bridge_log.denied_count() == 0)
check("last_active_at updated", p.last_active_at > 0)

# Denied crossing
t_before = p.last_active_at
inbound.check_access(STRANGER)
check("denied: sequence 2",     p.bridge_log.status()["sequence"] == 2)
check("denied: denial count 1", p.bridge_log.denied_count() == 1)
check("denied: last_active unchanged", p.last_active_at == t_before)

# Owner reads denied log
log = p.get_denied_log(OWNER)
check("pond denied log: 1 entry",     len(log) == 1)
check("pond denied log: not admitted", not log[0]["admitted"])

perm_err3 = False
try:
    p.get_denied_log(BOB)
except PermissionError:
    perm_err3 = True
check("pond denied log: non-owner blocked", perm_err3)

# ---- resource_record includes log status ------------------------------------
section("resource_record includes bridge log status")

rec2 = p.resource_record()
check("resource_record has log key",    "log" in rec2)
check("log has denied_count",          "denied_count" in rec2["log"])
check("log has has_denials",           "has_denials" in rec2["log"])
check("log has sequence",              "sequence" in rec2["log"])
check("log denied_count correct",     rec2["log"]["denied_count"] == 1)
check("log has_denials True",         rec2["log"]["has_denials"])

# ---- Capture trigger via start_capture --------------------------------------
section("Manual capture trigger")

p.start_capture(OWNER, n=3)
check("capture active after trigger",  p.bridge_log.is_capturing)
inbound.check_access(BOB)
inbound.check_access(STRANGER)
inbound.check_access(BOB)
check("capture stopped after N",       not p.bridge_log.is_capturing)
cap2 = p.get_capture_log(OWNER)
check("capture log has 3 entries",     len(cap2) == 3)

perm_err4 = False
try:
    p.start_capture(BOB, n=3)
except PermissionError:
    perm_err4 = True
check("non-owner cannot start capture", perm_err4)

# ---- PondManager.reap_stale -------------------------------------------------
section("PondManager.reap_stale")

arr2 = UniCellArray(cell_count=1000)
arr2.enforce_emission_limits = False
mgr2 = PondManager(arr2)

p_active = mgr2.create_pond("active_pond", OWNER,
                              security_level=OPEN, pond_type=PROCESS)
p_stale  = mgr2.create_pond("stale_pond",  OWNER,
                              security_level=OPEN, pond_type=PROCESS)

# Force stale pond to appear old
p_stale.last_active_at = time.time() - 7200   # 2 hours ago

reaped = mgr2.reap_stale(idle_threshold=3600.0)
check("stale pond reaped",     "stale_pond" in [mgr2._name_index.get("stale_pond", "stale_pond")] or
                                len(reaped) == 1)
check("active pond not reaped", mgr2.get_pond_by_name("active_pond") is not None)
check("stale pond gone",        mgr2.get_pond_by_name("stale_pond") is None)

# ---- Results ----------------------------------------------------------------
print("\n=== Results ===\n")
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
total  = len(results)
print(f"Results: {passed} passed, {failed} failed out of {total} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("Failed:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
