"""
test_conditional_pond.py — CONDITIONAL pond type and Ward dissolve contract

Tests:
  - CONDITIONAL, SHOREKEEPER, HYPERSHORE pond types registered
  - Ward.set_dissolve_contract() and evaluate_dissolve()
  - All dissolve condition types: TIME, RETURN, COMPLETE, EXTERNAL, COMPOUND
  - All dissolve actions: DISSOLVE, FREEZE, CHECKPOINT
  - One-shot firing (no double-trigger)
  - Ward.tick() increments internal counter for TIME conditions
  - Invalid action raises ValueError
  - Compound ANY and ALL logic
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from pond_types import (
    registry,
    CONDITIONAL, SHOREKEEPER, HYPERSHORE,
    DISSOLVE_TIME, DISSOLVE_RETURN, DISSOLVE_COMPLETE,
    DISSOLVE_EXTERNAL, DISSOLVE_COMPOUND,
    ACTION_DISSOLVE, ACTION_FREEZE, ACTION_CHECKPOINT,
)
from pond import PondManager, OPEN
from unicell_array import UniCellArray
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


def make_pond(name="test", pond_type=CONDITIONAL):
    arr = UniCellArray(cell_count=200)
    arr.enforce_emission_limits = False
    mgr = PondManager(arr)
    p = mgr.create_pond(name, "owner", security_level=OPEN, pond_type=pond_type)
    return p

def make_ward(pond_type=CONDITIONAL):
    p = make_pond(pond_type=pond_type)
    return Ward(p), p


# =============================================================================
print("\n=== New pond types registered ===\n")
# =============================================================================

for t in [CONDITIONAL, SHOREKEEPER, HYPERSHORE]:
    spec = registry.get(t)
    check(f"{t}: registered", spec is not None)
    check(f"{t}: has description", bool(spec.description if spec else ""))

check("SHOREKEEPER: permanent_anchor = True",
      registry.get(SHOREKEEPER).permanent_anchor)
check("HYPERSHORE: permanent_anchor = True",
      registry.get(HYPERSHORE).permanent_anchor)
check("CONDITIONAL: permanent_anchor = False",
      not registry.get(CONDITIONAL).permanent_anchor)

check("SHOREKEEPER: security = HIDDEN",
      registry.get(SHOREKEEPER).security == "HIDDEN")
check("HYPERSHORE: security = HIDDEN",
      registry.get(HYPERSHORE).security == "HIDDEN")


# =============================================================================
print("\n=== CONDITIONAL pond creation ===\n")
# =============================================================================

p = make_pond(pond_type=CONDITIONAL)
check("CONDITIONAL: pond creates OK",  p is not None)
check_eq("CONDITIONAL: pond_type",     p.pond_type, CONDITIONAL)
check("CONDITIONAL: has bridges",      len(p.bridges) >= 2)


# =============================================================================
print("\n=== Ward.set_dissolve_contract() ===\n")
# =============================================================================

w, p = make_ward()
w.set_dissolve_contract({'type': DISSOLVE_TIME, 'ticks': 5}, ACTION_DISSOLVE)
check("set_dissolve_contract: condition stored",
      w._dissolve_condition is not None)
check_eq("set_dissolve_contract: action stored",
         w._dissolve_action, ACTION_DISSOLVE)
check("set_dissolve_contract: not yet triggered",
      not w._dissolve_triggered)

# Invalid action raises ValueError
try:
    w2, _ = make_ward()
    w2.set_dissolve_contract({'type': DISSOLVE_TIME, 'ticks': 1}, "EXPLODE")
    check("invalid action raises ValueError", False)
except ValueError:
    check("invalid action raises ValueError", True)


# =============================================================================
print("\n=== TIME condition ===\n")
# =============================================================================

w, p = make_ward()
w.set_dissolve_contract({'type': DISSOLVE_TIME, 'ticks': 3}, ACTION_DISSOLVE)

# Ticks 1-2: not yet
w.tick(0); r1 = w.evaluate_dissolve()
w.tick(0); r2 = w.evaluate_dissolve()
check("TIME(3): not triggered at tick 1",  r1 is None)
check("TIME(3): not triggered at tick 2",  r2 is None)

# Tick 3: fires
w.tick(0); r3 = w.evaluate_dissolve()
check_eq("TIME(3): fires at tick 3",        r3, ACTION_DISSOLVE)

# Tick 4: one-shot — does not fire again
w.tick(0); r4 = w.evaluate_dissolve()
check("TIME(3): one-shot — no re-fire",     r4 is None)

# TIME(0): fires immediately
w_zero, _ = make_ward()
w_zero.set_dissolve_contract({'type': DISSOLVE_TIME, 'ticks': 0}, ACTION_DISSOLVE)
r_zero = w_zero.evaluate_dissolve()
check_eq("TIME(0): fires immediately",      r_zero, ACTION_DISSOLVE)


# =============================================================================
print("\n=== RETURN condition ===\n")
# =============================================================================

w, _ = make_ward()
w.set_dissolve_contract(
    {'type': DISSOLVE_RETURN, 'process_id': 'proc_1', 'value': 42},
    ACTION_FREEZE)

r_wrong = w.evaluate_dissolve({'return_values': {'proc_1': 99}})
check("RETURN: wrong value — no fire",      r_wrong is None)

r_missing = w.evaluate_dissolve({'return_values': {}})
check("RETURN: missing process — no fire",  r_missing is None)

r_correct = w.evaluate_dissolve({'return_values': {'proc_1': 42}})
check_eq("RETURN: correct value fires",     r_correct, ACTION_FREEZE)

r_again = w.evaluate_dissolve({'return_values': {'proc_1': 42}})
check("RETURN: one-shot",                   r_again is None)


# =============================================================================
print("\n=== COMPLETE condition ===\n")
# =============================================================================

w, _ = make_ward()
w.set_dissolve_contract(
    {'type': DISSOLVE_COMPLETE, 'process_id': 'proc_2'},
    ACTION_CHECKPOINT)

r_run = w.evaluate_dissolve({'process_states': {'proc_2': 'RUNNING'}})
check("COMPLETE: RUNNING — no fire",        r_run is None)

r_done = w.evaluate_dissolve({'process_states': {'proc_2': 'COMPLETE'}})
check_eq("COMPLETE: COMPLETE fires",        r_done, ACTION_CHECKPOINT)


# =============================================================================
print("\n=== EXTERNAL condition ===\n")
# =============================================================================

w, _ = make_ward()
w.set_dissolve_contract(
    {'type': DISSOLVE_EXTERNAL, 'session_id': 'sess_abc'},
    ACTION_DISSOLVE)

r_alive = w.evaluate_dissolve({'active_sessions': {'sess_abc', 'sess_xyz'}})
check("EXTERNAL: session alive — no fire",  r_alive is None)

r_gone = w.evaluate_dissolve({'active_sessions': {'sess_xyz'}})
check_eq("EXTERNAL: session gone fires",    r_gone, ACTION_DISSOLVE)

# Empty sessions set — session gone
w2, _ = make_ward()
w2.set_dissolve_contract(
    {'type': DISSOLVE_EXTERNAL, 'session_id': 'sess_abc'},
    ACTION_DISSOLVE)
r_empty = w2.evaluate_dissolve({'active_sessions': set()})
check_eq("EXTERNAL: empty sessions fires",  r_empty, ACTION_DISSOLVE)


# =============================================================================
print("\n=== COMPOUND ANY condition ===\n")
# =============================================================================

w, _ = make_ward()
w.set_dissolve_contract({
    'type': DISSOLVE_COMPOUND,
    'op': 'ANY',
    'conditions': [
        {'type': DISSOLVE_COMPLETE, 'process_id': 'p1'},
        {'type': DISSOLVE_EXTERNAL, 'session_id': 's1'},
    ]
}, ACTION_FREEZE)

# Neither met
r_none = w.evaluate_dissolve({
    'process_states': {'p1': 'RUNNING'},
    'active_sessions': {'s1'}
})
check("COMPOUND ANY: none met — no fire",   r_none is None)

# One met (session gone)
r_one = w.evaluate_dissolve({
    'process_states': {'p1': 'RUNNING'},
    'active_sessions': set()
})
check_eq("COMPOUND ANY: one met fires",     r_one, ACTION_FREEZE)


# =============================================================================
print("\n=== COMPOUND ALL condition ===\n")
# =============================================================================

w, _ = make_ward()
w.set_dissolve_contract({
    'type': DISSOLVE_COMPOUND,
    'op': 'ALL',
    'conditions': [
        {'type': DISSOLVE_TIME, 'ticks': 2},
        {'type': DISSOLVE_COMPLETE, 'process_id': 'p2'},
    ]
}, ACTION_CHECKPOINT)

# Time met, process not complete
w.tick(0); w.tick(0)
r_partial = w.evaluate_dissolve({'process_states': {'p2': 'RUNNING'}})
check("COMPOUND ALL: partial — no fire",    r_partial is None)

# Both met
r_both = w.evaluate_dissolve({'process_states': {'p2': 'COMPLETE'}})
check_eq("COMPOUND ALL: both met fires",    r_both, ACTION_CHECKPOINT)

# One-shot
r_again = w.evaluate_dissolve({'process_states': {'p2': 'COMPLETE'}})
check("COMPOUND ALL: one-shot",             r_again is None)


# =============================================================================
print("\n=== All three actions work ===\n")
# =============================================================================

for action in [ACTION_DISSOLVE, ACTION_FREEZE, ACTION_CHECKPOINT]:
    w_a, _ = make_ward()
    w_a.set_dissolve_contract({'type': DISSOLVE_TIME, 'ticks': 1}, action)
    w_a.tick(0)
    result = w_a.evaluate_dissolve()
    check_eq(f"action {action}: returned correctly", result, action)


# =============================================================================
print("\n=== Ward without contract — evaluate_dissolve returns None ===\n")
# =============================================================================

w_no, _ = make_ward()
check("no contract: evaluate_dissolve = None",
      w_no.evaluate_dissolve() is None)


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
