"""
test_shorekeeper.py — ShoreKeeper, HyperShore and thermal Ward tests
"""

import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))

from shorekeeper import ShoreKeeper, HyperShore, ShoreKeeperHeartbeat
from pond import PondManager, OPEN
from pond_types import PROCESS
from unicell_array import UniCellArray
from controller import ImagoController
from ward import Ward

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    results.append(("PASS" if ok else "FAIL", name))
    if not ok:
        print(f"  [FAIL] {name}  got={got!r}  expected={expected!r}")
    else:
        print(f"  [PASS] {name}")


def make_system(n_ponds=2):
    ctrl = ImagoController(cell_count=500)
    arr  = UniCellArray(cell_count=500)
    arr.enforce_emission_limits = False
    mgr  = PondManager(arr)
    ponds = [mgr.create_pond(f"pond_{i}", "owner",
                              security_level=OPEN, pond_type=PROCESS)
             for i in range(n_ponds)]
    return ctrl, arr, mgr, ponds


# =============================================================================
print("\n=== Ward thermal fields ===\n")
# =============================================================================

ctrl, arr, mgr, ponds = make_system(1)
p = ponds[0]
w = p.ward

check("Ward: thermal_load initial = 0",  w.thermal_load == 0.0)
check("Ward: thermal_limit default > 0", w.thermal_limit > 0)
check("Ward: thermal_trend initial = 0", w.thermal_trend == 0.0)
check("Ward: thermal_state = NOMINAL",   w.thermal_state == "NOMINAL")

w.set_thermal_config(limit=10.0, zone="block_5")
check_eq("set_thermal_config: limit",    w.thermal_limit, 10.0)
check_eq("set_thermal_config: zone",     w.thermal_zone,  "block_5")

s = w.thermal_summary()
check("thermal_summary: returns dict",   isinstance(s, dict))
check("thermal_summary: has load",       "load" in s)
check("thermal_summary: has state",      "state" in s)
check("thermal_summary: zone correct",   s["zone"] == "block_5")

# Thermal state thresholds
w2 = Ward(p)
w2.set_thermal_config(limit=1.0)
w2.thermal_load = 0.5;  check_eq("NOMINAL state",  w2.thermal_state, "NOMINAL")
w2.thermal_load = 1.0;  check_eq("THROTTLE state", w2.thermal_state, "THROTTLE")
w2.thermal_load = 1.25; check_eq("FREEZE state",   w2.thermal_state, "FREEZE")
w2.thermal_load = 1.55; check_eq("MIGRATE state",  w2.thermal_state, "MIGRATE")


# =============================================================================
print("\n=== ShoreKeeper: creation and registration ===\n")
# =============================================================================

ctrl, arr, mgr, ponds = make_system(3)
sk = ShoreKeeper("card_0", controller=ctrl, pond_manager=mgr,
                 heartbeat_interval=5)

check_eq("ShoreKeeper: card_id",           sk.card_id, "card_0")
check_eq("ShoreKeeper: initial ponds = 0", sk.pond_count(), 0)

for p in ponds:
    sk.register_pond(p)
check_eq("ShoreKeeper: 3 ponds registered", sk.pond_count(), 3)

for p in ponds:
    check(f"{p.name}: thermal_zone assigned",
          isinstance(p.ward.thermal_zone, str))


# =============================================================================
print("\n=== ShoreKeeper: heartbeat generation ===\n")
# =============================================================================

ctrl, arr, mgr, ponds = make_system(2)
sk = ShoreKeeper("card_1", controller=ctrl, pond_manager=mgr,
                 heartbeat_interval=3)
for p in ponds: sk.register_pond(p)

r1 = sk.tick()
r2 = sk.tick()
check("tick 1: no heartbeat",        r1 is None)
check("tick 2: no heartbeat",        r2 is None)

r3 = sk.tick()
check("tick 3: heartbeat fired",     r3 is not None)
check("heartbeat: correct type",     isinstance(r3, ShoreKeeperHeartbeat))
check_eq("heartbeat: card_id",       r3.card_id, "card_1")
check_eq("heartbeat: tick_count",    r3.tick_count, 3)
check("heartbeat: healthy_ponds > 0",r3.healthy_ponds > 0)
check("heartbeat: no escalations",   len(r3.escalations) == 0)

sk.tick(); sk.tick()
r6 = sk.tick()
check("tick 6: second heartbeat",    r6 is not None)
check("last_heartbeat is latest",    sk.last_heartbeat() is r6)

d = r3.to_dict()
check("to_dict: returns dict",       isinstance(d, dict))
check("to_dict: has card_id",        "card_id" in d)
check("to_dict: has thermal_load",   "thermal_load" in d)


# =============================================================================
print("\n=== ShoreKeeper: card_health ===\n")
# =============================================================================

ctrl, arr, mgr, ponds = make_system(2)
sk = ShoreKeeper("card_2", controller=ctrl, pond_manager=mgr,
                 heartbeat_interval=1)
for p in ponds: sk.register_pond(p)
sk.tick()
health = sk.card_health()

check("card_health: is dict",         isinstance(health, dict))
check("card_health: has healthy",     "healthy_ponds" in health)
check("card_health: has thermal",     "thermal_load" in health)
check("card_health: 2 healthy ponds", health["healthy_ponds"] == 2)


# =============================================================================
print("\n=== HyperShore: multi-card registry ===\n")
# =============================================================================

hs = HyperShore()
check_eq("HyperShore: initial cards = 0", len(hs.cards()), 0)

hs.register_card("card_0")
hs.register_card("card_1")
check_eq("HyperShore: 2 cards registered", len(hs.cards()), 2)

ctrl0, arr0, mgr0, ponds0 = make_system(3)
sk0 = ShoreKeeper("card_0", controller=ctrl0, pond_manager=mgr0,
                  heartbeat_interval=1)
for p in ponds0: sk0.register_pond(p)
sk0.connect_hyper_shore(hs)

ctrl1, arr1, mgr1, ponds1 = make_system(2)
sk1 = ShoreKeeper("card_1", controller=ctrl1, pond_manager=mgr1,
                  heartbeat_interval=1)
for p in ponds1: sk1.register_pond(p)
sk1.connect_hyper_shore(hs)

sk0.tick(); sk1.tick()

gh = hs.global_health()
check("global_health: 2 cards",       gh["cards"] == 2)
check("global_health: 5 healthy",     gh["total_healthy"] >= 5)
check("global_health: card_states",   len(gh["card_states"]) == 2)
check("hottest_card: valid card_id",
      hs.hottest_card() in ["card_0", "card_1"])
check("coolest_card: valid card_id",
      hs.coolest_card() in ["card_0", "card_1"])


# =============================================================================
print("\n=== HyperShore: escalation callback ===\n")
# =============================================================================

escalations = []
hs2 = HyperShore()
hs2.register_card("card_esc")
hs2.on_escalation(lambda hb: escalations.append(hb))

hb_bad = ShoreKeeperHeartbeat(
    card_id="card_esc", timestamp=time.time(), tick_count=1,
    stalled_ponds=1,
    escalations=[{"pond_id": "p1", "state": "STALLED", "reason": "test"}])
hs2.receive_heartbeat(hb_bad)
check("escalation callback fired",   len(escalations) == 1)
check_eq("callback got right card",  escalations[0].card_id, "card_esc")

hb_ok = ShoreKeeperHeartbeat(
    card_id="card_esc", timestamp=time.time(), tick_count=2)
hs2.receive_heartbeat(hb_ok)
check("no callback for clean hb",    len(escalations) == 1)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
