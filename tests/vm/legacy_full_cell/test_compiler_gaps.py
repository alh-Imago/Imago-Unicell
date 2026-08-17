"""
test_compiler_gaps.py — Tests for known compiler bugs and gaps.

These tests document known failures and missing coverage.
Some are expected to fail until the underlying bug is fixed.
Each test is clearly marked with its status.

Known failures documented here:
- MUX selector bug: if/else always returns false branch
- Depth padding: shallow+deep operand pair correctness
- Multi-param ordering: both params must contribute correctly
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from compiler_int32 import Int32Compiler, run_int32_function
from fp_tiles import TileLibrary

results = []

def check(name, condition, expected_fail=False):
    status = "PASS" if condition else "FAIL"
    if expected_fail and not condition:
        status = "KNOWN_FAIL"
    elif expected_fail and condition:
        status = "FIXED"  # bug was fixed — update this test
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected, expected_fail=False):
    ok = (got == expected)
    status = "PASS" if ok else "FAIL"
    if expected_fail and not ok:
        status = "KNOWN_FAIL"
    elif expected_fail and ok:
        status = "FIXED"
    results.append((status, name))
    if not ok:
        print(f"  [{status}] {name}  got={got!r}  expected={expected!r}")
    else:
        print(f"  [{status}] {name}")

lib = TileLibrary()

def run(src, **kwargs):
    return run_int32_function(src, 'f', kwargs, lib)

def run_safe(src, expected_fail=False, **kwargs):
    """Run a function, returning None if it crashes."""
    try:
        return run_int32_function(src, 'f', kwargs, lib)
    except Exception:
        if expected_fail:
            return None
        raise



# ── Test 1: MUX selector bug ──────────────────────────────────────────────────
# Root cause: IR graph node output_addr not in tile placer address space.
# PASS selector always sees 0, false branch always fires.
# See docs/CODEBASE_AUDIT.md issue #1.

print("\n=== MUX selector bug (KNOWN FAIL until fixed) ===\n")

src_mux1 = """
def f(x: int32) -> int32:
    if x > 0:
        return 10
    else:
        return 20
"""

r = run(src_mux1, x=5)
check_eq("if x>0: x=5 should return 10", r, 10, expected_fail=True)

r = run(src_mux1, x=-5)
check_eq("if x>0: x=-5 should return 20", r, 20)

r = run(src_mux1, x=0)
check_eq("if x>0: x=0 should return 20", r, 20)

src_mux2 = """
def f(x: int32) -> int32:
    if x < 0:
        return 100
    else:
        return 0
"""

# x < 0 also crashes due to sign_or node missing output_addr — known bug
r = run_safe(src_mux2, expected_fail=True, x=-1)
check("if x<0: compiles without crash", r is not None, expected_fail=True)
if r is not None:
    check_eq("if x<0: x=-1 should return 100", r, 100, expected_fail=True)

r = run_safe(src_mux2, expected_fail=True, x=1)
if r is not None:
    check_eq("if x<0: x=1 should return 0", r, 0)

src_mux3 = """
def f(x: int32) -> int32:
    if x == 0:
        return 999
    else:
        return 1
"""

r = run_safe(src_mux3, expected_fail=True, x=0)
check("if x==0: compiles without crash", r is not None, expected_fail=True)
if r is not None:
    check_eq("if x==0: x=0 should return 999", r, 999, expected_fail=True)

r = run_safe(src_mux3, expected_fail=True, x=5)
if r is not None:
    check_eq("if x==0: x=5 should return 1", r, 1)


# ── Test 2: Depth padding correctness ─────────────────────────────────────────
# When two int32 values of different pipeline depths are combined,
# the shallower one is padded to match the deeper one.
# Bug: padding used bare GS_PASS (fixed 2026-06-04) — this test
# verifies the fix holds and catches any regression.

print("\n=== Depth padding correctness ===\n")

def to_int32(v):
    """Convert to signed int32 — matches run_int32_function return type."""
    v = v & 0xFFFFFFFF
    if v >= 0x80000000:
        v -= 0x100000000
    return v

# ADD uses KS tree (depth ~10). A constant has depth 0.
# The constant side must be padded to match ADD depth.
src_pad1 = """
def f(x: int32, y: int32) -> int32:
    return x + y
"""

for a, b in [(0, 0), (1, 1), (100, 200), (0x7FFFFFFF, 1),
             (-1, 1), (-100, 50), (1000, -2000)]:
    expected = to_int32(a + b)
    r = run(src_pad1, x=a, y=b)
    check_eq(f"ADD({a}, {b})", r, expected)

# Constant + variable — constant side gets padded
src_pad2 = """
def f(x: int32) -> int32:
    return x + 42
"""

for v in [0, 1, -1, 100, -100, 0x7FFFFFD5]:
    expected = to_int32(v + 42)
    r = run(src_pad2, x=v)
    check_eq(f"x+42 with x={v}", r, expected)


# ── Test 3: Multi-param ordering ──────────────────────────────────────────────
# In functions with multiple int32 params, the first param is excluded
# from re-injection. Workaround: put non-passthrough param first.
# This test verifies both params contribute correctly to the result
# and catches any regression in the ordering workaround.
# See PLAN.md issue #6.

print("\n=== Multi-param ordering ===\n")

src_mp1 = """
def f(x: int32, y: int32) -> int32:
    return x + y
"""

# Both params must contribute — swap order and verify same result
pairs = [(3, 7), (100, 200), (-5, 5), (0, 1000), (0x7FFF, 0x8000)]
for a, b in pairs:
    expected = (a + b) & 0xFFFFFFFF
    r = run(src_mp1, x=a, y=b)
    check_eq(f"f({a},{b}) = {a}+{b}", r, expected)

# Verify y actually contributes — if first param is ignored,
# f(0, 5) and f(0, 10) would give same wrong result
r5  = run(src_mp1, x=0, y=5)
r10 = run(src_mp1, x=0, y=10)
check("y=5 and y=10 give different results (y contributes)", r5 != r10)
check_eq("f(0, 5) = 5", r5, 5)
check_eq("f(0, 10) = 10", r10, 10)

# Verify x actually contributes
rx5  = run(src_mp1, x=5,  y=0)
rx10 = run(src_mp1, x=10, y=0)
check("x=5 and x=10 give different results (x contributes)", rx5 != rx10)
check_eq("f(5, 0) = 5", rx5, 5)
check_eq("f(10, 0) = 10", rx10, 10)

# Subtraction — non-commutative, verifies both params in correct position
src_mp2 = """
def f(x: int32, y: int32) -> int32:
    return x - y
"""

for a, b in [(10, 3), (100, 1), (0, 5), (5, 5)]:
    expected = to_int32(a - b)
    r = run(src_mp2, x=a, y=b)
    check_eq(f"f({a},{b}) = {a}-{b}", r, expected)

# ── Comparison random fuzz ────────────────────────────────────────────────────
# Zero-comparison fast path — verify correctness across a range of values.

print("\n=== Comparison fuzz ===\n")

import random
random.seed(42)

test_vals = [0, 1, -1, 2, -2, 100, -100,
             0x7FFFFFFF, -0x80000000, 0x7FFFFFFE, -0x7FFFFFFF]
test_vals += [random.randint(-2**31, 2**31-1) for _ in range(20)]

ops = [
    ("x > 0",  lambda x: 1 if x > 0 else 0,
     "def f(x: int32) -> int32: return 1 if x > 0 else 0"),
    ("x < 0",  lambda x: 1 if x < 0 else 0,
     "def f(x: int32) -> int32: return 1 if x < 0 else 0"),
    ("x == 0", lambda x: 1 if x == 0 else 0,
     "def f(x: int32) -> int32: return 1 if x == 0 else 0"),
    ("x != 0", lambda x: 1 if x != 0 else 0,
     "def f(x: int32) -> int32: return 1 if x != 0 else 0"),
    ("x >= 0", lambda x: 1 if x >= 0 else 0,
     "def f(x: int32) -> int32: return 1 if x >= 0 else 0"),
    ("x <= 0", lambda x: 1 if x <= 0 else 0,
     "def f(x: int32) -> int32: return 1 if x <= 0 else 0"),
]

for op_name, py_fn, src in ops:
    mismatches = 0
    for v in test_vals:
        expected = py_fn(v)
        got = run(src, x=v)
        if got != expected:
            mismatches += 1
    check(f"{op_name}: {len(test_vals)} values, {mismatches} mismatches",
          mismatches == 0)


# ── Summary ───────────────────────────────────────────────────────────────────
print("\n=== Results ===\n")
passed      = sum(1 for s, _ in results if s == "PASS")
failed      = sum(1 for s, _ in results if s == "FAIL")
known_fails = sum(1 for s, _ in results if s == "KNOWN_FAIL")
fixed       = sum(1 for s, _ in results if s == "FIXED")

print(f"Results: {passed} passed, {failed} failed, "
      f"{known_fails} known_fail, {fixed} newly_fixed "
      f"out of {len(results)} tests")

if fixed:
    print("\n*** NEWLY FIXED bugs detected — update expected_fail flags ***")

if failed:
    print("\nUnexpected failures — investigate before committing.")
    sys.exit(1)
else:
    print("\nAll unexpected failures: 0")
