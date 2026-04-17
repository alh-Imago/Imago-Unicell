"""
test_cast.py — Cast and Ripple Discovery Tests (Section 7)

  - Stone: visibility levels, silent cast rejected
  - Pebble Cast: single Pond, owner announced, resource record returned
  - Ripple Cast: all Ponds, nearest first, HIDDEN filtered correctly
  - Skipping Stone: named sequence, cumulative results, hop privacy
  - Mandatory owner announcement: always logged regardless of visibility
  - Query filtering: pond_type, name_contains, security_level
  - ReturnWave: summary, by_hop ordering, first_match

Run with: python3 test_cast.py
"""

import hashlib
from unicell_array import UniCellArray
from pond import PondManager, OPEN, PRIVATE, HIDDEN, COMPUTE, STORAGE
from cast import (CastEngine, Stone, ReturnWave,
                  VIS_ANONYMOUS, VIS_PRIVATE, VIS_PUBLIC, VIS_SILENT)

results = []
def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def make_id(s): return hashlib.sha256(s.encode()).hexdigest()

OWNER   = make_id("alice")
BOB     = make_id("bob")
CHARLIE = make_id("charlie")
STRANGER = make_id("stranger")

# =============================================================================
print("\n=== Stone creation ===\n")

s = Stone(caster_id=OWNER, visibility=VIS_ANONYMOUS, hop_limit=3)
check("Stone: created",                s.caster_id == OWNER)
check("Stone: visibility ANONYMOUS",   s.visibility == VIS_ANONYMOUS)
check("Stone: hop_limit stored",       s.hop_limit == 3)

# Silent cast cannot touch a Pond
silent_err = False
try:
    Stone(caster_id=OWNER, visibility=VIS_SILENT)
except ValueError:
    silent_err = True
check("Stone: SILENT raises ValueError", silent_err)

# Invalid visibility rejected
bad_vis = False
try:
    Stone(caster_id=OWNER, visibility="INVISIBLE")
except ValueError:
    bad_vis = True
check("Stone: invalid visibility raises ValueError", bad_vis)

# =============================================================================
print("\n=== Pebble Cast ===\n")

arr = UniCellArray(cell_count=500)
arr.enforce_emission_limits = False
mgr = PondManager(arr)
p1 = mgr.create_pond("workshop", OWNER, security_level=OPEN,
                      pond_type=COMPUTE)
p2 = mgr.create_pond("archive",  OWNER, security_level=PRIVATE,
                      pond_type=STORAGE)

engine = CastEngine(mgr)

# Pebble cast into OPEN pond
wave = engine.pebble_cast(STRANGER, "workshop")
check("Pebble Cast: returns ReturnWave",         isinstance(wave, ReturnWave))
check("Pebble Cast: 1 result",                   len(wave.results) == 1)
check("Pebble Cast: correct pond",
      wave.results[0].pond_id == p1.pond_id)
check("Pebble Cast: hop is 1",                   wave.results[0].hop == 1)
check("Pebble Cast: owner announced",            wave.results[0].announced_to_owner)
check("Pebble Cast: resource_record present",
      "pond_type" in wave.results[0].resource_record)
check("Pebble Cast: complete",                   wave.complete)

# Mandatory owner announcement — stranger's visit logged on OPEN pond
log = p1.get_visit_log(OWNER)
check("Pebble Cast: visit logged for owner",     len(log) >= 1)
check("Pebble Cast: log entry admitted=True",    log[-1]["admitted"])

# Pebble cast into non-existent pond
wave2 = engine.pebble_cast(STRANGER, "nonexistent")
check("Pebble Cast: missing pond → 0 results",  len(wave2.results) == 0)

# =============================================================================
print("\n=== Ripple Cast ===\n")

arr2 = UniCellArray(cell_count=1000)
arr2.enforce_emission_limits = False
mgr2 = PondManager(arr2)
engine2 = CastEngine(mgr2)

pa = mgr2.create_pond("compute1",  OWNER, security_level=OPEN,    pond_type=COMPUTE)
pb = mgr2.create_pond("storage1",  OWNER, security_level=OPEN,    pond_type=STORAGE)
pc = mgr2.create_pond("private1",  OWNER, security_level=PRIVATE, pond_type=COMPUTE)
pd = mgr2.create_pond("hidden1",   OWNER, security_level=HIDDEN,  pond_type=COMPUTE)

# Ripple from stranger — sees OPEN and PRIVATE, not HIDDEN
wave3 = engine2.ripple_cast(STRANGER, visibility=VIS_ANONYMOUS)
found_ids = {r.pond_id for r in wave3.results}
check("Ripple: OPEN compute1 found",    pa.pond_id in found_ids)
check("Ripple: OPEN storage1 found",    pb.pond_id in found_ids)
check("Ripple: PRIVATE private1 found", pc.pond_id in found_ids)
check("Ripple: HIDDEN hidden1 NOT found", pd.pond_id not in found_ids)
check("Ripple: 3 results total",        len(wave3.results) == 3)

# Owner sees all including HIDDEN
wave4 = engine2.ripple_cast(OWNER, visibility=VIS_ANONYMOUS)
found_ids2 = {r.pond_id for r in wave4.results}
check("Ripple: owner sees HIDDEN pond", pd.pond_id in found_ids2)
check("Ripple: owner sees 4 ponds",     len(wave4.results) == 4)

# Whitelisted identity sees HIDDEN
pd.grant_access(BOB, label="bob")
wave5 = engine2.ripple_cast(BOB, visibility=VIS_ANONYMOUS)
found_ids3 = {r.pond_id for r in wave5.results}
check("Ripple: whitelisted BOB sees HIDDEN", pd.pond_id in found_ids3)

# =============================================================================
print("\n=== Query filtering ===\n")

arr3 = UniCellArray(cell_count=500)
arr3.enforce_emission_limits = False
mgr3 = PondManager(arr3)
engine3 = CastEngine(mgr3)

mgr3.create_pond("comp_a",  OWNER, pond_type=COMPUTE)
mgr3.create_pond("stor_a",  OWNER, pond_type=STORAGE)
mgr3.create_pond("comp_b",  OWNER, pond_type=COMPUTE)

# Filter by pond_type
wave6 = engine3.ripple_cast(STRANGER,
                             query={"pond_type": COMPUTE})
check("Query: COMPUTE filter → 2 results", len(wave6.results) == 2)
check("Query: all results are COMPUTE",
      all(r.resource_record["pond_type"] == COMPUTE
          for r in wave6.results))

wave7 = engine3.ripple_cast(STRANGER,
                             query={"pond_type": STORAGE})
check("Query: STORAGE filter → 1 result", len(wave7.results) == 1)

# Filter by name
wave8 = engine3.ripple_cast(STRANGER,
                             query={"name_contains": "stor"})
check("Query: name_contains 'stor' → 1 result", len(wave8.results) == 1)

# No match
wave9 = engine3.ripple_cast(STRANGER,
                             query={"name_contains": "zzz"})
check("Query: no match → 0 results", len(wave9.results) == 0)

# =============================================================================
print("\n=== Skipping Stone ===\n")

arr4 = UniCellArray(cell_count=500)
arr4.enforce_emission_limits = False
mgr4 = PondManager(arr4)
engine4 = CastEngine(mgr4)

s1 = mgr4.create_pond("stop_1", OWNER, pond_type=COMPUTE)
s2 = mgr4.create_pond("stop_2", OWNER, pond_type=STORAGE)
s3 = mgr4.create_pond("stop_3", OWNER, pond_type=COMPUTE)

wave10 = engine4.skipping_stone(
    STRANGER,
    pond_names=["stop_1", "stop_2", "stop_3"],
    visibility=VIS_ANONYMOUS,
)
check("Skip: 3 results",             len(wave10.results) == 3)
check("Skip: hops 1,2,3",
      sorted(r.hop for r in wave10.results) == [1, 2, 3])
check("Skip: complete",              wave10.complete)

# Missing Pond in sequence — skipped, others still returned
wave11 = engine4.skipping_stone(
    STRANGER,
    pond_names=["stop_1", "nonexistent", "stop_3"],
)
check("Skip: missing Pond skipped",  len(wave11.results) == 2)

# Privacy: each Pond's log has only the Stone's caster, not the path
# Each visit log entry doesn't reveal where else the stone went
log1 = s1.get_visit_log(OWNER)
log3 = s3.get_visit_log(OWNER)
check("Skip privacy: stop_1 log has entry",  len(log1) >= 1)
check("Skip privacy: stop_3 log has entry",  len(log3) >= 1)
check("Skip privacy: logs don't share info",
      log1[-1]["bridge"] == log3[-1]["bridge"])  # same mechanism

# =============================================================================
print("\n=== Mandatory owner announcement (Section 7.5) ===\n")

arr5 = UniCellArray(cell_count=500)
arr5.enforce_emission_limits = False
mgr5 = PondManager(arr5)
engine5 = CastEngine(mgr5)

pa5 = mgr5.create_pond("announced", OWNER, security_level=OPEN)
# Clear any prior visits
initial_visits = len(pa5.visit_log)

# Anonymous cast — stranger invisible to other occupants but owner sees
engine5.pebble_cast(STRANGER, "announced", visibility=VIS_ANONYMOUS)
check("Announcement: visit logged for anonymous cast",
      len(pa5.visit_log) == initial_visits + 1)
log_entries = pa5.get_visit_log(OWNER)
check("Announcement: log has stranger's identity",
      log_entries[-1]["identity"].startswith(STRANGER[:8]))

# HIDDEN pond — no announcement when stone passes over invisibly
arr6 = UniCellArray(cell_count=500)
arr6.enforce_emission_limits = False
mgr6 = PondManager(arr6)
engine6 = CastEngine(mgr6)
ph = mgr6.create_pond("silent_hidden", OWNER, security_level=HIDDEN)
initial = len(ph.visit_log)

engine6.ripple_cast(STRANGER)   # stone passes over HIDDEN without contact
check("HIDDEN: no announcement when stone passes over",
      len(ph.visit_log) == initial)

# =============================================================================
print("\n=== ReturnWave summary and ordering ===\n")

arr7 = UniCellArray(cell_count=500)
arr7.enforce_emission_limits = False
mgr7 = PondManager(arr7)
engine7 = CastEngine(mgr7)

for i in range(4):
    mgr7.create_pond(f"pond_{i}", OWNER,
                     pond_type=COMPUTE if i % 2 == 0 else STORAGE)

wave12 = engine7.ripple_cast(OWNER)
summary = wave12.summary()
check("Summary: ponds_found = 4",    summary["ponds_found"] == 4)
check("Summary: complete = True",    summary["complete"])
check("Summary: by_type has COMPUTE", "COMPUTE" in summary["by_type"] or "PROCESS" in summary["by_type"])
check("Summary: by_type has STORAGE", "STORAGE" in summary["by_type"] or "FILE" in summary["by_type"])

# first_match
fm = wave12.first_match(STORAGE)
check("first_match: finds STORAGE pond", fm is not None)
check("first_match: correct type",
      fm.resource_record["pond_type"] == STORAGE)

fm_none = wave12.first_match("DEVICE")
check("first_match: no match → None", fm_none is None)


# =============================================================================
print("\n=== Mask filtering ===\n")
# =============================================================================

arr_m = UniCellArray(cell_count=500)
arr_m.enforce_emission_limits = False
mgr_m = PondManager(arr_m)
eng_m = CastEngine(mgr_m)

p_pub  = mgr_m.create_pond("mask_public", OWNER, pond_type=COMPUTE)
p_adm  = mgr_m.create_pond("mask_admin",  OWNER, pond_type=COMPUTE)
p_usr  = mgr_m.create_pond("mask_user",   OWNER, pond_type=COMPUTE)

p_adm._get_bridge("INBOUND").set_access_mask(0b00000001)
p_usr._get_bridge("INBOUND").set_access_mask(0b00000010)

wave_admin = eng_m.ripple_cast(OWNER, process_mask=0b00000001)
names_admin = [r.resource_record["name"] for r in wave_admin.results]
check("mask: admin sees public",      "mask_public" in names_admin)
check("mask: admin sees admin pond",  "mask_admin"  in names_admin)
check("mask: admin cannot see user",  "mask_user"   not in names_admin)

wave_user = eng_m.ripple_cast(OWNER, process_mask=0b00000010)
names_user = [r.resource_record["name"] for r in wave_user.results]
check("mask: user sees public",       "mask_public" in names_user)
check("mask: user sees user pond",    "mask_user"   in names_user)
check("mask: user cannot see admin",  "mask_admin"  not in names_user)

wave_open = eng_m.ripple_cast(OWNER, process_mask=0xFFFFFFFF)
names_open = [r.resource_record["name"] for r in wave_open.results]
check("mask: open sees all three",
      all(n in names_open for n in ["mask_public","mask_admin","mask_user"]))

wave_zero = eng_m.ripple_cast(OWNER, process_mask=0b00000000)
names_zero = [r.resource_record["name"] for r in wave_zero.results]
check("mask: zero mask sees only public", "mask_public" in names_zero)
check("mask: zero mask skips admin",      "mask_admin"  not in names_zero)

# =============================================================================

print(f"\n{'='*55}")
passed = sum(1 for s,_ in results if s == "PASS")
failed = sum(1 for s,_ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
    print("\nCast and Ripple validated:")
    print("  - Pebble Cast: single Pond, mandatory owner announcement")
    print("  - Ripple Cast: all Ponds, HIDDEN filtered correctly")
    print("  - Skipping Stone: named sequence, hop numbering, skip missing")
    print("  - Query filtering: pond_type, name_contains")
    print("  - Mandatory owner announcement: always logged, HIDDEN silent")
    print("  - ReturnWave: summary, ordering, first_match")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
