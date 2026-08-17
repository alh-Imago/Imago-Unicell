"""
test_pond.py — Pond Model Tests

Validates the Pond shared resource model per the Imago architecture spec:

  Security levels:
    - OPEN by default at creation (any identity admitted)
    - Owner can change to PRIVATE (whitelist enforced)
    - Owner can change to HIDDEN (not discoverable to non-whitelisted)
    - Only owner may change security level

  Bridge cells:
    - 2 bridges minimum (INBOUND, OUTBOUND)
    - Optional MONITOR (bridge 3) and LOG (bridge 4)
    - Bridge cells are real UniCells (PASS gate) in the array
    - Each bridge tracks packets passed / rejected

  Whitelist:
    - Owner grants access: permanent, time-limited, single-use, scheduled
    - Owner revokes access: immediate, structural
    - Expired grants are rejected
    - Single-use grants auto-revoke after first admission
    - Non-owner cannot grant or revoke

  Visit log:
    - Every access attempt recorded (admitted or rejected)
    - Only owner may read visit log

  Resource record:
    - Returns Pond state for discovery (Cast/Ripple)
    - Hidden Ponds invisible to non-whitelisted identities in discover()

  Cell pool:
    - Owner contributes cells to Pond pool
    - Admitted identities request cells from pool
    - Released cells return to pool

Run with: python3 test_pond.py
"""

import time
from unicell_array import UniCellArray
from pond import (Pond, PondManager, PondBridge, AccessGrant,
                  OPEN, PRIVATE, HIDDEN)

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

# Identity hashes (simulate biometric/machine key derived IDs)
import hashlib
def make_id(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()

OWNER   = make_id("alice")
BOB     = make_id("bob")
CHARLIE = make_id("charlie")
STRANGER = make_id("stranger")

# =============================================================================
print("\n=== Pond Creation — security level defaults ===\n")

arr = UniCellArray(cell_count=1000)
arr.enforce_emission_limits = False
mgr = PondManager(arr)

# Default: OPEN
pond_open = mgr.create_pond("workshop", OWNER)
check("Creation: security_level defaults to OPEN",
      pond_open.security_level == OPEN)
check("Creation: pond has pond_id", pond_open.pond_id.startswith("pond_"))
check("Creation: pond name stored", pond_open.name == "workshop")
check("Creation: owner_id stored", pond_open.owner_id == OWNER)

# Explicit PRIVATE at creation
pond_priv = mgr.create_pond("private_lab", OWNER, security_level=PRIVATE)
check("Creation: explicit PRIVATE level", pond_priv.security_level == PRIVATE)

# Explicit HIDDEN at creation
pond_hidden = mgr.create_pond("secret_vault", OWNER, security_level=HIDDEN)
check("Creation: explicit HIDDEN level", pond_hidden.security_level == HIDDEN)

# Invalid level rejected
err = False
try:
    mgr.create_pond("bad", OWNER, security_level="CLASSIFIED")
except ValueError:
    err = True
check("Creation: invalid security level raises ValueError", err)

# =============================================================================
print("\n=== Security Level Changes ===\n")

arr2 = UniCellArray(cell_count=500)
arr2.enforce_emission_limits = False
mgr2 = PondManager(arr2)
p = mgr2.create_pond("changeable", OWNER)

check("Change: starts OPEN", p.security_level == OPEN)

ok = p.set_security_level(PRIVATE, OWNER)
check("Change: owner changes OPEN → PRIVATE", ok and p.security_level == PRIVATE)

ok2 = p.set_security_level(HIDDEN, OWNER)
check("Change: owner changes PRIVATE → HIDDEN", ok2 and p.security_level == HIDDEN)

ok3 = p.set_security_level(OPEN, OWNER)
check("Change: owner changes HIDDEN → OPEN", ok3 and p.security_level == OPEN)

# Non-owner cannot change level
ok4 = p.set_security_level(PRIVATE, BOB)
check("Change: non-owner rejected", not ok4 and p.security_level == OPEN)

# =============================================================================
print("\n=== Bridge Cells ===\n")

arr3 = UniCellArray(cell_count=500)
arr3.enforce_emission_limits = False
mgr3 = PondManager(arr3)

# 2 bridges (minimum)
p2 = mgr3.create_pond("two_bridge", OWNER, bridge_count=2)
check("Bridges: 2 bridges created", len(p2.bridges) == 2)
check("Bridges: bridge 0 is INBOUND",  p2.bridges[0].role == PondBridge.INBOUND)
check("Bridges: bridge 1 is OUTBOUND", p2.bridges[1].role == PondBridge.OUTBOUND)
check("Bridges: no MONITOR bridge",  not p2.has_bridge(PondBridge.MONITOR))
check("Bridges: no LOG bridge",      not p2.has_bridge(PondBridge.LOG))

# Bridge cells are real UniCells in the array
check("Bridges: INBOUND cell in array",
      p2.bridges[0].cell_address in arr3.cells)
check("Bridges: OUTBOUND cell in array",
      p2.bridges[1].cell_address in arr3.cells)

# 4 bridges (full)
p4 = mgr3.create_pond("four_bridge", OWNER, bridge_count=4)
check("Bridges: 4 bridges created", len(p4.bridges) == 4)
check("Bridges: bridge 2 is MONITOR", p4.bridges[2].role == PondBridge.MONITOR)
check("Bridges: bridge 3 is LOG",     p4.bridges[3].role == PondBridge.LOG)
check("Bridges: has MONITOR", p4.has_bridge(PondBridge.MONITOR))
check("Bridges: has LOG",     p4.has_bridge(PondBridge.LOG))

# Bridge cell count consumed from array
cells_used = len(arr3.cells)
check("Bridges: cells allocated in array (2+4=6 bridge cells)",
      cells_used >= 6)

# Invalid bridge count
err2 = False
try:
    mgr3.create_pond("bad_bridge", OWNER, bridge_count=1)
except ValueError:
    err2 = True
check("Bridges: bridge_count < 2 raises ValueError", err2)

# =============================================================================
print("\n=== OPEN Pond — any identity admitted ===\n")

arr4 = UniCellArray(cell_count=500)
arr4.enforce_emission_limits = False
mgr4 = PondManager(arr4)
p_open = mgr4.create_pond("open_space", OWNER, security_level=OPEN)

# Any identity passes inbound bridge
admitted, reason = p_open.bridges[0].check_access(STRANGER)
check("OPEN: stranger admitted", admitted)
check("OPEN: reason is OPEN", reason == "OPEN")

admitted2, reason2 = p_open.bridges[0].check_access(BOB)
check("OPEN: bob admitted", admitted2)

admitted3, reason3 = p_open.bridges[0].check_access(OWNER)
check("OPEN: owner admitted (OWNER reason)", admitted3 and reason3 == "OWNER")

# Bridge counters update
check("OPEN: inbound packets_passed = 3", p_open.bridges[0].packets_passed == 3)

# =============================================================================
print("\n=== PRIVATE Pond — whitelist enforced ===\n")

arr5 = UniCellArray(cell_count=500)
arr5.enforce_emission_limits = False
mgr5 = PondManager(arr5)
p_priv = mgr5.create_pond("members_only", OWNER, security_level=PRIVATE)

# Stranger rejected
admitted, reason = p_priv.bridges[0].check_access(STRANGER)
check("PRIVATE: stranger rejected", not admitted)
check("PRIVATE: reason is REJECTED", reason == "REJECTED")

# Owner always admitted
admitted2, reason2 = p_priv.bridges[0].check_access(OWNER)
check("PRIVATE: owner admitted", admitted2 and reason2 == "OWNER")

# Grant Bob access
grant = p_priv.grant_access(BOB, label="bob_device")
check("PRIVATE: grant created", isinstance(grant, AccessGrant))
check("PRIVATE: bob in whitelist", BOB in p_priv._whitelist)

# Bob now admitted
admitted3, reason3 = p_priv.bridges[0].check_access(BOB)
check("PRIVATE: bob admitted after grant", admitted3)
check("PRIVATE: reason is WHITELISTED", reason3 == "WHITELISTED")

# Charlie still rejected
admitted4, reason4 = p_priv.bridges[0].check_access(CHARLIE)
check("PRIVATE: charlie still rejected", not admitted4)

# Revoke Bob
ok_rev = p_priv.revoke_access(BOB)
check("PRIVATE: bob revoked", ok_rev)
check("PRIVATE: bob no longer in whitelist", BOB not in p_priv._whitelist)

admitted5, reason5 = p_priv.bridges[0].check_access(BOB)
check("PRIVATE: bob rejected after revoke", not admitted5)

# Non-owner cannot grant
perm_err = False
try:
    p_priv.grant_access(CHARLIE, requester_id=BOB)
except PermissionError:
    perm_err = True
check("PRIVATE: non-owner cannot grant", perm_err)

# =============================================================================
print("\n=== Time-limited and single-use grants ===\n")

arr6 = UniCellArray(cell_count=500)
arr6.enforce_emission_limits = False
mgr6 = PondManager(arr6)
p_timed = mgr6.create_pond("timed_pond", OWNER, security_level=PRIVATE)

# Expired grant — set expiry in the past
past = time.time() - 3600   # 1 hour ago
p_timed.grant_access(BOB, label="bob_expired", expires_at=past)
admitted, reason = p_timed.bridges[0].check_access(BOB)
check("Time-limited: expired grant rejected", not admitted)
check("Time-limited: reason is EXPIRED", reason == "EXPIRED")

# Future grant — valid
future = time.time() + 3600   # 1 hour from now
p_timed.grant_access(CHARLIE, label="charlie_future", expires_at=future)
admitted2, reason2 = p_timed.bridges[0].check_access(CHARLIE)
check("Time-limited: future grant admitted", admitted2)

# Single-use grant
p_timed.grant_access(STRANGER, label="stranger_once", single_use=True)
check("Single-use: stranger in whitelist", STRANGER in p_timed._whitelist)

admitted3, _ = p_timed.bridges[0].check_access(STRANGER)
check("Single-use: admitted on first use", admitted3)
check("Single-use: removed from whitelist after use",
      STRANGER not in p_timed._whitelist)

admitted4, reason4 = p_timed.bridges[0].check_access(STRANGER)
check("Single-use: rejected on second attempt", not admitted4)

# =============================================================================
print("\n=== HIDDEN Pond — not discoverable to strangers ===\n")

arr7 = UniCellArray(cell_count=500)
arr7.enforce_emission_limits = False
mgr7 = PondManager(arr7)

p_vis  = mgr7.create_pond("visible_pond",  OWNER, security_level=OPEN)
p_priv2 = mgr7.create_pond("private_pond", OWNER, security_level=PRIVATE)
p_hide = mgr7.create_pond("hidden_pond",   OWNER, security_level=HIDDEN)

# Stranger discovers OPEN and PRIVATE but not HIDDEN
discovered = mgr7.discover(STRANGER)
names = [d["name"] for d in discovered]
check("HIDDEN: stranger sees OPEN pond",    "visible_pond"  in names)
check("HIDDEN: stranger sees PRIVATE pond", "private_pond"  in names)
check("HIDDEN: stranger cannot see HIDDEN", "hidden_pond"   not in names)

# Owner always sees their own HIDDEN pond
discovered2 = mgr7.discover(OWNER)
names2 = [d["name"] for d in discovered2]
check("HIDDEN: owner sees own HIDDEN pond", "hidden_pond" in names2)

# Whitelisted identity sees HIDDEN pond
p_hide.grant_access(BOB, label="bob")
discovered3 = mgr7.discover(BOB)
names3 = [d["name"] for d in discovered3]
check("HIDDEN: whitelisted bob sees HIDDEN pond", "hidden_pond" in names3)

# Still hidden to Charlie (not whitelisted)
discovered4 = mgr7.discover(CHARLIE)
names4 = [d["name"] for d in discovered4]
check("HIDDEN: charlie still cannot see HIDDEN pond",
      "hidden_pond" not in names4)

# =============================================================================
print("\n=== Visit log ===\n")

arr8 = UniCellArray(cell_count=500)
arr8.enforce_emission_limits = False
mgr8 = PondManager(arr8)
p_log = mgr8.create_pond("logged_pond", OWNER, security_level=PRIVATE,
                          bridge_count=4)

p_log.grant_access(BOB, label="bob")
p_log.bridges[0].check_access(BOB)       # admitted
p_log.bridges[0].check_access(STRANGER)  # rejected
p_log.bridges[0].check_access(BOB)       # admitted again

check("Bridge log: sequence incremented", p_log.bridge_log.status()["sequence"] == 3)
check("Bridge log: 1 denial recorded",    p_log.bridge_log.denied_count() == 1)
check("Bridge log: has_denials True",     p_log.bridge_log.has_denials())

# Owner reads denied log
log = p_log.get_denied_log(OWNER)
check("Denied log: 1 entry", len(log) == 1)
check("Denied log: entry has timestamp",  "timestamp" in log[0])
check("Denied log: entry not admitted",   not log[0]["admitted"])
check("Denied log: reason REJECTED",      log[0]["reason"] == "REJECTED")

# Non-owner cannot read denied log
perm_err2 = False
try:
    p_log.get_denied_log(BOB)
except PermissionError:
    perm_err2 = True
check("Denied log: non-owner cannot read", perm_err2)

# =============================================================================
print("\n=== Bridge packet counters ===\n")

arr9 = UniCellArray(cell_count=500)
arr9.enforce_emission_limits = False
mgr9 = PondManager(arr9)
p_cnt = mgr9.create_pond("counter_pond", OWNER, security_level=PRIVATE)
p_cnt.grant_access(BOB, label="bob")

# 3 admitted, 2 rejected
for _ in range(3):
    p_cnt.bridges[0].check_access(BOB)
for _ in range(2):
    p_cnt.bridges[0].check_access(STRANGER)

check("Counters: 3 passed",    p_cnt.bridges[0].packets_passed == 3)
check("Counters: 2 rejected",  p_cnt.bridges[0].packets_rejected == 2)
check("Counters: bytes_passed = 12 (3 × 4 bytes)",
      p_cnt.bridges[0].bytes_passed == 12)

# =============================================================================
print("\n=== Resource record ===\n")

arr10 = UniCellArray(cell_count=500)
arr10.enforce_emission_limits = False
mgr10 = PondManager(arr10)
p_rec = mgr10.create_pond("resource_pond", OWNER, bridge_count=3)

rec = p_rec.resource_record()
check("Resource record: pond_id present", "pond_id" in rec)
check("Resource record: name correct", rec["name"] == "resource_pond")
check("Resource record: security_level", rec["security_level"] == OPEN)
check("Resource record: bridge_count = 3", rec["bridge_count"] == 3)
check("Resource record: bridges list length 3", len(rec["bridges"]) == 3)
check("Resource record: free_cells is int", isinstance(rec["free_cells"], int))
check("Resource record: owner truncated", rec["owner_id"].endswith("..."))

# =============================================================================
print("\n=== PondManager status ===\n")

arr11 = UniCellArray(cell_count=1000)
arr11.enforce_emission_limits = False
mgr11 = PondManager(arr11)
mgr11.create_pond("open1",   OWNER, security_level=OPEN)
mgr11.create_pond("open2",   OWNER, security_level=OPEN)
mgr11.create_pond("priv1",   OWNER, security_level=PRIVATE)
mgr11.create_pond("hidden1", OWNER, security_level=HIDDEN)

st = mgr11.status()
check("Manager status: 4 total ponds",   st["total_ponds"]   == 4)
check("Manager status: 2 open ponds",    st["open_ponds"]    == 2)
check("Manager status: 1 private pond",  st["private_ponds"] == 1)
check("Manager status: 1 hidden pond",   st["hidden_ponds"]  == 1)

# Lookup by name
found = mgr11.get_pond_by_name("priv1")
check("Manager: get_pond_by_name works", found is not None and found.name == "priv1")

not_found = mgr11.get_pond_by_name("nonexistent")
check("Manager: get_pond_by_name returns None for missing", not_found is None)

# Duplicate name rejected
dup_err = False
try:
    mgr11.create_pond("open1", OWNER)
except ValueError:
    dup_err = True
check("Manager: duplicate pond name rejected", dup_err)

# =============================================================================
print("\n=== Pond destruction ===\n")

arr12 = UniCellArray(cell_count=500)
arr12.enforce_emission_limits = False
mgr12 = PondManager(arr12)
p_del = mgr12.create_pond("doomed", OWNER)
pid = p_del.pond_id

# Non-owner cannot destroy
ok_bad = mgr12.destroy_pond(pid, BOB)
check("Destroy: non-owner rejected", not ok_bad)
check("Destroy: pond still exists", mgr12.get_pond(pid) is not None)

# Owner destroys
ok_good = mgr12.destroy_pond(pid, OWNER)
check("Destroy: owner can destroy", ok_good)
check("Destroy: pond gone from manager", mgr12.get_pond(pid) is None)

# =============================================================================
print("\n=== Cell pool — request and release ===\n")

arr13 = UniCellArray(cell_count=500)
arr13.enforce_emission_limits = False
mgr13 = PondManager(arr13)
p_pool = mgr13.create_pond("pool_pond", OWNER, security_level=PRIVATE)
p_pool.grant_access(BOB, label="bob")
p_pool.contribute_cells(20)   # pool must be filled before cells can be served

# Rejected identity cannot get cells
cells_bad, reason_bad = p_pool.request_cells(STRANGER, 5)
check("Pool: stranger cannot get cells", cells_bad == [])
check("Pool: reason REJECTED", reason_bad == "REJECTED")

# Admitted identity gets cells
cells_ok, reason_ok = p_pool.request_cells(BOB, 5)
check("Pool: bob gets 5 cells", len(cells_ok) == 5)
check("Pool: reason GRANTED", reason_ok == "GRANTED")
check("Pool: cells are valid addresses", all(isinstance(a, int) for a in cells_ok))

# Release cells
released = p_pool.release_cells(cells_ok, BOB)
check("Pool: 5 cells released", released == 5)

# =============================================================================

# =============================================================================
# Bridge Interface Contract tests (spec v0.1)
# =============================================================================
print("\n=== Bridge Lane Width ===\n")

import hashlib as _hs
def _mid(s): return _hs.sha256(s.encode()).hexdigest()
_OWN = _mid("owner_bridge_tests")

from unicell_array import UniCellArray as _UA
from pond import (PondManager as _PM, OPEN, COMPUTE, STORAGE,
                  DEVICE, TILE_LIBRARY, BOOT, PondBridge as _PB)

# Default lane widths by type (spec §3.3)
_defaults = {COMPUTE:(4,4), STORAGE:(4,2), DEVICE:(2,2),
             TILE_LIBRARY:(1,4), BOOT:(1,1)}

for ptype, (exp_in, exp_out) in _defaults.items():
    _arr = _UA(cell_count=200); _arr.enforce_emission_limits = False
    _mgr = _PM(_arr)
    _p = _mgr.create_pond(f"test_{ptype}", _OWN, pond_type=ptype,
                           bridge_count=2)
    _ib = _p._get_bridge(_PB.INBOUND)
    _ob = _p._get_bridge(_PB.OUTBOUND)
    check(f"Lane default {ptype}: inbound={exp_in}",
          _ib.lane_width == exp_in)
    check(f"Lane default {ptype}: outbound={exp_out}",
          _ob.lane_width == exp_out)

# Explicit lane override
_arr2 = _UA(cell_count=200); _arr2.enforce_emission_limits = False
_mgr2 = _PM(_arr2)
_p2 = _mgr2.create_pond("explicit", _OWN, pond_type=COMPUTE,
                          bridge_count=2,
                          inbound_lanes=8, outbound_lanes=3)
check("Lane override: inbound=8",  _p2._get_bridge(_PB.INBOUND).lane_width  == 8)
check("Lane override: outbound=3", _p2._get_bridge(_PB.OUTBOUND).lane_width == 3)

# MONITOR and LOG always single-cell
_arr3 = _UA(cell_count=200); _arr3.enforce_emission_limits = False
_mgr3 = _PM(_arr3)
_p3 = _mgr3.create_pond("full_bridge", _OWN, pond_type=COMPUTE,
                          bridge_count=4)
check("MONITOR always 1 cell",
      _p3._get_bridge(_PB.MONITOR).lane_width == 1)
check("LOG always 1 cell",
      _p3._get_bridge(_PB.LOG).lane_width    == 1)

# Cell count: COMPUTE 4+4 inbound+outbound + MONITOR + LOG = 10
expected_cells = 4 + 4 + 1 + 1
actual_cells   = sum(b.lane_width for b in _p3.bridges)
check(f"COMPUTE 4-bridge total cells = {expected_cells}",
      actual_cells == expected_cells)

# All lane cells are real UniCells in the array
for bridge in _p3.bridges:
    for addr in bridge.cell_addresses:
        check(f"Lane cell 0x{addr:08X} in array",
              addr in _arr3.cells)

# =============================================================================
print("\n=== Bridge Utilisation and Throttle Detection ===\n")

_arr4 = _UA(cell_count=200); _arr4.enforce_emission_limits = False
_mgr4 = _PM(_arr4)
_p4 = _mgr4.create_pond("throttle_test", _OWN, pond_type=COMPUTE,
                          bridge_count=3,    # includes MONITOR
                          inbound_lanes=2,
                          throttle_threshold=80.0,
                          utilisation_window=5)

_mon = _p4._get_bridge(_PB.MONITOR)
check("MONITOR: initial utilisation = 0",    _mon.utilisation_pct == 0.0)
check("MONITOR: initial not throttled",      not _mon.is_throttled)
check("MONITOR: peak_utilisation = 0",       _mon.peak_utilisation == 0)

# Record low-utilisation cycles (1 emission, capacity = 2 → 50%)
for _ in range(5):
    _mon.record_cycle(1)
check("MONITOR: 50% util not throttled",
      not _mon.is_throttled)
check("MONITOR: utilisation ~50%",
      40 < _mon.utilisation_pct < 60)

# Record high-utilisation cycles (2 emissions, capacity = 2 → 100%)
for _ in range(5):
    _mon.record_cycle(2)
check("MONITOR: 100% util is throttled",
      _mon.is_throttled)
check("MONITOR: peak = 2",
      _mon.peak_utilisation == 2)
check("MONITOR: cycles_throttled > 0",
      _mon.cycles_throttled > 0)

# Throttle appears in resource record
_rec = _p4.resource_record()
check("Resource record: is_throttled field present",
      "is_throttled" in _rec)
check("Resource record: throttled = True",
      _rec["is_throttled"] == True)
check("Resource record: bridge_utilisation list",
      isinstance(_rec["bridge_utilisation"], list))
check("Resource record: total_bridge_cells present",
      "total_bridge_cells" in _rec)
check("Resource record: total_bridge_cells = inbound+outbound+monitor",
      _rec["total_bridge_cells"] == _p4._inbound_lanes + _p4._outbound_lanes + 1)

# After low-utilisation, throttle clears
for _ in range(10):
    _mon.record_cycle(0)
check("MONITOR: throttle clears after low utilisation",
      not _mon.is_throttled)

# =============================================================================
print("\n=== Peripheral Tile Lane Metadata ===\n")

from fp_tiles import TileLibrary as _TL
_lib = _TL()

_peripheral_lanes = {
    "KEYBOARD_HANDLER":  (1, 1),
    "SENSOR_HANDLER":    (2, 1),
    "AUDIO_IN_HANDLER":  (4, 1),
    "AUDIO_OUT_HANDLER": (1, 4),
    "DISPLAY_HANDLER":   (1, 8),
    "NETWORK_HANDLER":   (4, 4),
    "STORAGE_HANDLER":   (4, 2),
}

for name, (exp_in, exp_out) in _peripheral_lanes.items():
    _tile = _lib.get(name)
    check(f"{name}: inbound_lanes={exp_in}",
          _tile.metadata.inbound_lanes  == exp_in)
    check(f"{name}: outbound_lanes={exp_out}",
          _tile.metadata.outbound_lanes == exp_out)
    check(f"{name}: cell_count > 0",
          _tile.metadata.cell_count > 0)
    check(f"{name}: pipeline_depth > 0",
          _tile.metadata.pipeline_depth > 0)

# Pond created from peripheral tile uses tile's lane counts
_arr5 = _UA(cell_count=500); _arr5.enforce_emission_limits = False
_mgr5 = _PM(_arr5)
_display_tile = _lib.get("DISPLAY_HANDLER")
_display_pond = _mgr5.create_pond(
    "display", _OWN, pond_type=DEVICE, bridge_count=2,
    inbound_lanes  = _display_tile.metadata.inbound_lanes,
    outbound_lanes = _display_tile.metadata.outbound_lanes,
)
check("Display Pond: inbound=1 from tile",
      _display_pond._get_bridge(_PB.INBOUND).lane_width  == 1)
check("Display Pond: outbound=8 from tile",
      _display_pond._get_bridge(_PB.OUTBOUND).lane_width == 8)

# =============================================================================
print("\n=== StoragePond Uses STORAGE Lane Defaults ===\n")

import tempfile, os as _os
from pathlib import Path as _P
from uniflex_fs import UniFlex as _UF, FS_NATIVE

with tempfile.TemporaryDirectory() as _td:
    (_P(_td) / "test.txt").write_text("hello")
    _arr6 = _UA(cell_count=500); _arr6.enforce_emission_limits = False
    _ufx  = _UF(_arr6, _OWN)
    _sp   = _ufx.mount(_td, name="storage_test", fs_type=FS_NATIVE)

    check("StoragePond INBOUND lanes = 4",
          _sp._get_bridge(_PB.INBOUND).lane_width  == 4)
    check("StoragePond OUTBOUND lanes = 2",
          _sp._get_bridge(_PB.OUTBOUND).lane_width == 2)
    check("StoragePond total bridge cells = 6",
          sum(b.lane_width for b in _sp.bridges)  == 6)

print(f"\n{'='*55}")
passed = sum(1 for s,_ in results if s == "PASS")
failed = sum(1 for s,_ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
    print("\nPond model validated:")
    print("  - OPEN / PRIVATE / HIDDEN security levels, defaulting to OPEN")
    print("  - Owner-only level changes and whitelist management")
    print("  - 2-4 bridges (INBOUND, OUTBOUND, MONITOR, LOG)")
    print("  - Bridge lane widths: type defaults and explicit override")
    print("  - MONITOR capacity reflects Pond inbound bandwidth")
    print("  - Throttle detection at configured threshold")
    print("  - Throttle visible in resource_record for Cast/Ripple")
    print("  - Permanent, time-limited, single-use grants and visit log")
    print("  - HIDDEN Ponds invisible to non-whitelisted discover()")
    print("  - Peripheral tile lane metadata (7 device stubs)")
    print("  - StoragePond uses STORAGE lane defaults (4 in, 2 out)")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
