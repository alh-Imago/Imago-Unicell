"""
test_pond_region_scope.py — Region Scope Enforcement Tests

Validates the region_scope field of AccessGrant, which constrains an
identity to a sub-range of the Pond's pool cells.  Tests are written
directly against the Pond and PondBridge model — no external fixtures.

The whitelist acts as a two-stage gate:
  Stage 1 — discovery / cast response (security_level: OPEN/PRIVATE/HIDDEN)
  Stage 2 — bridge admission (_check_identity: owner / whitelist / OPEN)
  Stage 3 — region_scope (request_cells: filters eligible pool cells)

These tests cover Stage 3 and its interaction with Stages 1 and 2.

Bugs fixed in this session:
  1. request_cells called contribute_cells() for each request, allocating
     fresh array cells whose addresses were always beyond the scope range.
     Fixed: serve from existing _pool_cells, filter by scope before allocation.
  2. free_cells returned total array free space, not Pond pool size.
     Fixed: return len(_pool_cells).
  3. release_cells removed cells from the pool instead of adding them back.
     Fixed: append unreturned addresses to _pool_cells.

Run with: python3 test_pond_region_scope.py
"""

from unicell_array import UniCellArray
from pond import (Pond, PondManager, PondBridge, AccessGrant,
                  OPEN, PRIVATE, HIDDEN, COMPUTE)

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

def make_pond(cells=100, security=PRIVATE, bridges=2) -> tuple:
    """Helper: create a fresh array and Pond, return (pond, pool_addresses)."""
    arr = UniCellArray(cells)
    p = Pond("test_pond", arr, "owner_id_xxxxxxxx",
             security_level=security, bridge_count=bridges)
    p.contribute_cells(30)
    return p, list(p._pool_cells)


# =============================================================================
print("\n=== free_cells — pool-based count ===\n")

p, pool = make_pond()
check_eq("free_cells equals pool size on fresh pond", p.free_cells, 30)

p.grant_access("alice_xxxxxxxxxxxx")
addrs, _ = p.request_cells("alice_xxxxxxxxxxxx", 5)
check_eq("free_cells decreases after request", p.free_cells, 25)

p.release_cells(addrs, "alice_xxxxxxxxxxxx")
check_eq("free_cells restores after release", p.free_cells, 30)


# =============================================================================
print("\n=== release_cells — returns cells to pool ===\n")

p2, pool2 = make_pond()
p2.grant_access("bob_xxxxxxxxxxxx")
taken, _ = p2.request_cells("bob_xxxxxxxxxxxx", 4)
check_eq("pool shrinks after request", p2.free_cells, 26)

released = p2.release_cells(taken, "bob_xxxxxxxxxxxx")
check_eq("released count matches returned", released, 4)
check_eq("pool restored after release", p2.free_cells, 30)

# Released cells must actually be back in the pool
check("released cells re-appear in pool",
      all(a in p2._pool_cells for a in taken))

# Releasing cells not in pool (double-release prevention)
released2 = p2.release_cells(taken, "bob_xxxxxxxxxxxx")
check_eq("double-release returns 0 (already in pool)", released2, 0)
check_eq("pool unchanged after double-release", p2.free_cells, 30)


# =============================================================================
print("\n=== region_scope — basic enforcement ===\n")

p3, pool3 = make_pond()
# Scope: middle 10 of the 30 pool cells (indices 10..19)
lo = pool3[10]; hi = pool3[19]
p3.grant_access("carol_xxxxxxxxxxx", region_scope=(lo, hi))

addrs3, reason3 = p3.request_cells("carol_xxxxxxxxxxx", 5)
check_eq("scoped request: reason is GRANTED", reason3, "GRANTED")
check_eq("scoped request: correct count returned", len(addrs3), 5)
check("scoped request: all returned addresses within scope",
      all(lo <= a <= hi for a in addrs3))
check("scoped request: no addresses outside scope returned",
      not any(a < lo or a > hi for a in addrs3))


# =============================================================================
print("\n=== region_scope — insufficient cells within scope ===\n")

p4, pool4 = make_pond()
lo4 = pool4[0]; hi4 = pool4[2]   # only 3 cells in scope
p4.grant_access("dave_xxxxxxxxxxxx", region_scope=(lo4, hi4))

addrs4, reason4 = p4.request_cells("dave_xxxxxxxxxxxx", 5)   # more than in scope
check_eq("request exceeds scope: INSUFFICIENT_CELLS", reason4, "INSUFFICIENT_CELLS")
check_eq("request exceeds scope: no cells returned", len(addrs4), 0)
check_eq("pool unchanged after scope rejection", p4.free_cells, 30)


# =============================================================================
print("\n=== region_scope — exact fit ===\n")

p5, pool5 = make_pond()
lo5 = pool5[0]; hi5 = pool5[2]   # exactly 3 cells in scope
p5.grant_access("eve_xxxxxxxxxxxxx", region_scope=(lo5, hi5))

addrs5, reason5 = p5.request_cells("eve_xxxxxxxxxxxxx", 3)
check_eq("exact fit: GRANTED", reason5, "GRANTED")
check_eq("exact fit: 3 cells returned", len(addrs5), 3)

# Now scope is exhausted — second request fails
addrs5b, reason5b = p5.request_cells("eve_xxxxxxxxxxxxx", 1)
check_eq("scope exhausted: INSUFFICIENT_CELLS", reason5b, "INSUFFICIENT_CELLS")


# =============================================================================
print("\n=== region_scope — release returns cells to scope ===\n")

p6, pool6 = make_pond()
lo6 = pool6[0]; hi6 = pool6[4]   # 5 cells in scope
p6.grant_access("frank_xxxxxxxxxx", region_scope=(lo6, hi6))

taken6, _ = p6.request_cells("frank_xxxxxxxxxx", 5)
check_eq("took all scoped cells", len(taken6), 5)

# Release 2 back
p6.release_cells(taken6[:2], "frank_xxxxxxxxxx")

# Should now be able to request those 2 again
retaken, reason6 = p6.request_cells("frank_xxxxxxxxxx", 2)
check_eq("re-request after release: GRANTED", reason6, "GRANTED")
check_eq("re-request: 2 cells returned", len(retaken), 2)
check("re-requested cells are within scope",
      all(lo6 <= a <= hi6 for a in retaken))


# =============================================================================
print("\n=== region_scope — does not affect unscoped identity ===\n")

p7, pool7 = make_pond()
lo7 = pool7[0]; hi7 = pool7[4]   # small scope
p7.grant_access("grace_xxxxxxxxxx", region_scope=(lo7, hi7))
p7.grant_access("henry_xxxxxxxxxx")   # no scope — full pool access

# Henry requests cells that include addresses outside grace's scope
addrs7h, reason7h = p7.request_cells("henry_xxxxxxxxxx", 10)
check_eq("unscoped identity: GRANTED", reason7h, "GRANTED")
check_eq("unscoped identity: gets correct count", len(addrs7h), 10)
# Henry may receive cells outside grace's range
check("unscoped can receive cells outside any scope",
      any(a < lo7 or a > hi7 for a in addrs7h))


# =============================================================================
print("\n=== region_scope — interacts with PRIVATE security level ===\n")

p8, pool8 = make_pond(security=PRIVATE)
lo8 = pool8[0]; hi8 = pool8[9]
p8.grant_access("ida_xxxxxxxxxxxxx", region_scope=(lo8, hi8))

# Unlisted identity cannot get cells even if scope would allow
addrs8_unl, reason8_unl = p8.request_cells("unknown_xxxxxxxx", 3)
check_eq("unlisted identity rejected before scope check", reason8_unl, "REJECTED")
check_eq("unlisted identity: no cells returned", len(addrs8_unl), 0)

# Owner is always admitted with full access
addrs8_own, reason8_own = p8.request_cells("owner_id_xxxxxxxx", 3)
check_eq("owner: GRANTED despite PRIVATE", reason8_own, "GRANTED")
check_eq("owner: gets requested count", len(addrs8_own), 3)


# =============================================================================
print("\n=== region_scope — combined with single_use grant ===\n")

p9, pool9 = make_pond()
lo9 = pool9[0]; hi9 = pool9[9]
p9.grant_access("jack_xxxxxxxxxxx",
                region_scope=(lo9, hi9),
                single_use=True)

# First request succeeds and consumes the grant
addrs9, reason9 = p9.request_cells("jack_xxxxxxxxxxx", 2)
check_eq("single-use + scope: GRANTED on first use", reason9, "GRANTED")
check("single-use + scope: cells within scope",
      all(lo9 <= a <= hi9 for a in addrs9))

# Grant is now gone — second request rejected
addrs9b, reason9b = p9.request_cells("jack_xxxxxxxxxxx", 1)
check_eq("single-use + scope: REJECTED after consumption", reason9b, "REJECTED")
check("single-use grant removed from whitelist",
      "jack_xxxxxxxxxxx" not in p9._whitelist)


# =============================================================================
print("\n=== region_scope — combined with expiry ===\n")

import time as _time

p10, pool10 = make_pond()
lo10 = pool10[0]; hi10 = pool10[9]
# Grant that expired in the past
p10.grant_access("kate_xxxxxxxxxxx",
                 region_scope=(lo10, hi10),
                 expires_at=_time.time() - 1.0)

addrs10, reason10 = p10.request_cells("kate_xxxxxxxxxxx", 2)
check_eq("expired + scope: EXPIRED (not INSUFFICIENT_CELLS)", reason10, "EXPIRED")
check_eq("expired grant: no cells returned", len(addrs10), 0)


# =============================================================================
print("\n=== region_scope — HIDDEN Pond: scope only visible to whitelisted ===\n")

arr11 = UniCellArray(200)
p11 = Pond("hidden_pond", arr11, "owner11_xxxxxxxx",
           security_level=HIDDEN, bridge_count=3)
p11.contribute_cells(20)
lo11 = p11._pool_cells[0]; hi11 = p11._pool_cells[4]
p11.grant_access("lena_xxxxxxxxxxx", region_scope=(lo11, hi11))

mgr = PondManager(arr11)
mgr._ponds[p11.pond_id] = p11

# Unknown identity: cannot see HIDDEN pond in discover
visible_unknown = mgr.discover("stranger_xxxxxxx")
hidden_ids = [r["pond_id"] for r in visible_unknown]
check("HIDDEN pond invisible to non-whitelisted", p11.pond_id not in hidden_ids)

# Lena (whitelisted): can see it, and gets scoped cells
visible_lena = mgr.discover("lena_xxxxxxxxxxx")
lena_ids = [r["pond_id"] for r in visible_lena]
check("HIDDEN pond visible to scoped identity", p11.pond_id in lena_ids)

addrs11, reason11 = p11.request_cells("lena_xxxxxxxxxxx", 3)
check_eq("HIDDEN + scoped: GRANTED", reason11, "GRANTED")
check("HIDDEN + scoped: cells within scope",
      all(lo11 <= a <= hi11 for a in addrs11))


# =============================================================================
print("\n=== region_scope — visit log records scope outcomes ===\n")

p12, pool12 = make_pond(bridges=4)   # MONITOR + LOG present
lo12 = pool12[0]; hi12 = pool12[2]   # 3 cells in scope
p12.grant_access("mia_xxxxxxxxxxxxx", region_scope=(lo12, hi12))

p12.request_cells("mia_xxxxxxxxxxxxx", 2)     # GRANTED
p12.request_cells("mia_xxxxxxxxxxxxx", 5)     # INSUFFICIENT_CELLS (scope empty+count>2)

log = p12.get_visit_log("owner_id_xxxxxxxx")
admitted_entries = [e for e in log if e["admitted"]]
check("visit log has admitted entries", len(admitted_entries) >= 1)
check("visit log has at least one INBOUND entry",
      any(e["bridge"] == "INBOUND" for e in log))


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
