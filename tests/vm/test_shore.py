"""
test_shore.py — Shore Personal Session State Tests (Section 8)

  - Shore creation and status
  - Personal token space
  - Discovery history recording
  - Suppression records: suppress, unsuppress, is_suppressed
  - Wave filtering: suppressed Ponds filtered out, changed ones resurface
  - Suppression thresholds: any / major / never
  - Auto-suppress on record_wave
  - Session management: connect, disconnect, active_sessions
  - ShorePreferences: visibility default, commercial threshold

Run with: python3 test_shore.py
"""

import hashlib, time
from unicell_array import UniCellArray
from pond import PondManager, OPEN, PRIVATE, COMPUTE, STORAGE
from cast import CastEngine, ReturnWave, Stone, VIS_ANONYMOUS, VIS_PUBLIC
from shore import Shore, ShorePreferences, SuppressionRecord, _record_signature

results = []
def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def make_id(s): return hashlib.sha256(s.encode()).hexdigest()
ALICE = make_id("alice")
BOB   = make_id("bob")

# =============================================================================
print("\n=== Shore creation ===\n")

shore = Shore(ALICE)
check("Shore: identity_id stored",       shore.identity_id == ALICE)
check("Shore: tokens is TokenSpace",
      hasattr(shore.tokens, 'register'))
check("Shore: no active sessions",       len(shore.active_sessions) == 0)
check("Shore: no history",               len(shore.history) == 0)
check("Shore: suppressed_count = 0",     shore.suppressed_count == 0)

st = shore.status()
check("Status: identity truncated",      st["identity_id"].endswith("..."))
check("Status: tokens_used = 0",         st["tokens_used"] == 0)
check("Status: active_sessions = 0",     st["active_sessions"] == 0)

# Custom preferences
prefs = ShorePreferences(
    default_visibility   = VIS_PUBLIC,
    commercial_threshold = "any",
    auto_suppress_repeat = False,
    max_history          = 10,
)
shore2 = Shore(BOB, preferences=prefs)
check("Preferences: visibility stored",
      shore2.preferences.default_visibility == VIS_PUBLIC)
check("Preferences: threshold stored",
      shore2.preferences.commercial_threshold == "any")

# =============================================================================
print("\n=== Personal token space ===\n")

from pond import RT_FILE, RT_TILE
tok1 = shore.tokens.register(RT_FILE, 0x1000, "my_document.txt")
tok2 = shore.tokens.register(RT_TILE, 0x2000, "fp32_add")

check("Shore tokens: register file token",  tok1 is not None)
check("Shore tokens: register tile token",  tok2 is not None)
check("Shore tokens: used = 2",             shore.tokens.used == 2)
check("Shore tokens: resolve by label",
      shore.tokens.resolve_by_label("my_document.txt") is not None)
check("Shore tokens: token valid",          tok1.is_valid())

# =============================================================================
print("\n=== Session management ===\n")

session = shore.connect("pond_0001", "workshop")
check("Session: connect returns ActiveSession", session is not None)
check("Session: pond_id stored",    session.pond_id == "pond_0001")
check("Session: pond_name stored",  session.pond_name == "workshop")
check("Session: 1 active session",  len(shore.active_sessions) == 1)
check("Session: get_session works",
      shore.get_session("pond_0001") is session)

session.allocated_cells = [0x1000, 0x1001, 0x1002]
check("Session: cells recorded",    len(session.allocated_cells) == 3)

ok = shore.disconnect("pond_0001")
check("Session: disconnect returns True",  ok)
check("Session: 0 active sessions",       len(shore.active_sessions) == 0)
check("Session: get_session → None",
      shore.get_session("pond_0001") is None)

bad = shore.disconnect("pond_nonexistent")
check("Session: disconnect missing → False", not bad)

# =============================================================================
print("\n=== Discovery history ===\n")

arr = UniCellArray(cell_count=500)
arr.enforce_emission_limits = False
mgr = PondManager(arr)
engine = CastEngine(mgr)

mgr.create_pond("comp1", ALICE, pond_type=COMPUTE)
mgr.create_pond("stor1", ALICE, pond_type=STORAGE)

wave1 = engine.ripple_cast(ALICE)
shore3 = Shore(ALICE)
shore3.record_wave(wave1)

check("History: 1 entry after record_wave", len(shore3.history) == 1)
check("History: entry has ponds_found",
      "ponds_found" in shore3.history[0])
check("History: entry has results list",
      "results" in shore3.history[0])
check("History: entry has cast_time",
      "cast_time" in shore3.history[0])

# Second wave
wave2 = engine.ripple_cast(ALICE)
shore3.record_wave(wave2)
check("History: 2 entries (newest first)", len(shore3.history) == 2)

# Max history enforcement
shore_small = Shore(ALICE, ShorePreferences(max_history=3,
                                            auto_suppress_repeat=False))
for _ in range(5):
    shore_small.record_wave(engine.ripple_cast(ALICE))
check("History: max_history enforced", len(shore_small.history) == 3)

# =============================================================================
print("\n=== Suppression records ===\n")

arr2 = UniCellArray(cell_count=500)
arr2.enforce_emission_limits = False
mgr2 = PondManager(arr2)
engine2 = CastEngine(mgr2)
p1 = mgr2.create_pond("shop_a", ALICE, pond_type=COMPUTE)
p2 = mgr2.create_pond("shop_b", ALICE, pond_type=STORAGE)

shore4 = Shore(ALICE, ShorePreferences(auto_suppress_repeat=False))

wave3 = engine2.ripple_cast(ALICE)
rec   = wave3.results[0].resource_record

# Manual suppress
shore4.suppress(p1.pond_id, rec, threshold="major")
check("Suppress: is_suppressed True",
      shore4.is_suppressed(p1.pond_id))
check("Suppress: count = 1", shore4.suppressed_count == 1)

# Unsuppress
ok2 = shore4.unsuppress(p1.pond_id)
check("Unsuppress: returns True",       ok2)
check("Unsuppress: count = 0",          shore4.suppressed_count == 0)
check("Unsuppress: no longer suppressed",
      not shore4.is_suppressed(p1.pond_id))

bad_un = shore4.unsuppress("pond_nonexistent")
check("Unsuppress: missing → False",    not bad_un)

# =============================================================================
print("\n=== Wave filtering (suppression in action) ===\n")

arr3 = UniCellArray(cell_count=500)
arr3.enforce_emission_limits = False
mgr3 = PondManager(arr3)
engine3 = CastEngine(mgr3)
pa = mgr3.create_pond("cafe_a", ALICE, pond_type=COMPUTE)
pb = mgr3.create_pond("cafe_b", ALICE, pond_type=COMPUTE)

shore5 = Shore(ALICE, ShorePreferences(auto_suppress_repeat=False))

# First ripple — both Ponds surface
wave4 = engine3.ripple_cast(ALICE)
filtered1 = shore5.filter_wave(wave4)
check("Filter: first wave — both surface",  len(filtered1) == 2)

# Suppress cafe_a
shore5.suppress(pa.pond_id,
                wave4.results[0].resource_record,
                threshold="major")

# Second ripple — cafe_a suppressed (record unchanged)
wave5 = engine3.ripple_cast(ALICE)
filtered2 = shore5.filter_wave(wave5)
surfaced_ids = {r.pond_id for r in filtered2}
check("Filter: suppressed cafe_a hidden",   pa.pond_id not in surfaced_ids)
check("Filter: cafe_b still shows",         pb.pond_id in surfaced_ids)
check("Filter: 1 result after suppression", len(filtered2) == 1)

# =============================================================================
print("\n=== Suppression thresholds ===\n")

arr4 = UniCellArray(cell_count=500)
arr4.enforce_emission_limits = False
mgr4 = PondManager(arr4)
engine4 = CastEngine(mgr4)
pc = mgr4.create_pond("venue", ALICE, pond_type=COMPUTE)

shore6 = Shore(ALICE, ShorePreferences(auto_suppress_repeat=False))
wave6 = engine4.ripple_cast(ALICE)
rec6 = wave6.results[0].resource_record
sig6 = _record_signature(rec6)

# threshold "never" — never resurfaces regardless of change
rec6_sup = SuppressionRecord(
    pond_id=pc.pond_id, change_signature=sig6,
    suppressed_at=time.time(), threshold="never"
)
shore6._suppressed[pc.pond_id] = rec6_sup
check("Threshold never: still suppressed same sig",
      shore6.is_suppressed(pc.pond_id, rec6))
# Even with different sig, "never" stays suppressed
changed_rec = dict(rec6)
changed_rec["free_cells"] = 9999
check("Threshold never: still suppressed changed sig",
      shore6.is_suppressed(pc.pond_id, changed_rec))

# threshold "any" — resurfaces on any change
rec6_any = SuppressionRecord(
    pond_id=pc.pond_id, change_signature=sig6,
    suppressed_at=time.time(), threshold="any"
)
shore6._suppressed[pc.pond_id] = rec6_any
check("Threshold any: suppressed same sig",
      shore6.is_suppressed(pc.pond_id, rec6))
check("Threshold any: resurfaces on change",
      not shore6.is_suppressed(pc.pond_id, changed_rec))

# threshold "major" (default) — resurfaces on signature change
sig_changed_rec = _record_signature(changed_rec)
check("Threshold major: different sigs differ",
      sig6 != sig_changed_rec)

# =============================================================================
print("\n=== Auto-suppress on record_wave ===\n")

arr5 = UniCellArray(cell_count=500)
arr5.enforce_emission_limits = False
mgr5 = PondManager(arr5)
engine5 = CastEngine(mgr5)
mgr5.create_pond("auto1", ALICE, pond_type=COMPUTE)
mgr5.create_pond("auto2", ALICE, pond_type=STORAGE)

shore7 = Shore(ALICE, ShorePreferences(auto_suppress_repeat=True))
wave7 = engine5.ripple_cast(ALICE)
check("Auto-suppress: 0 suppressed before record_wave",
      shore7.suppressed_count == 0)

shore7.record_wave(wave7)
check("Auto-suppress: 2 suppressed after record_wave",
      shore7.suppressed_count == 2)

# Second identical wave — filtered out
wave8 = engine5.ripple_cast(ALICE)
filtered3 = shore7.filter_wave(wave8)
check("Auto-suppress: second identical wave → 0 surface", len(filtered3) == 0)

# =============================================================================

print(f"\n{'='*55}")
passed = sum(1 for s,_ in results if s == "PASS")
failed = sum(1 for s,_ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
    print("\nShore validated:")
    print("  - Personal token space, session management")
    print("  - Discovery history with max_history enforcement")
    print("  - Suppress/unsuppress/is_suppressed")
    print("  - Wave filtering: suppressed Ponds hidden, changed ones resurface")
    print("  - Suppression thresholds: any / major / never")
    print("  - Auto-suppress on record_wave")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
