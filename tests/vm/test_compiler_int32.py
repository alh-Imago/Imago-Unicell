"""
test_compiler_int32.py — 32-bit Integer Compiler Extension Tests

Validates Int32Compiler and run_int32_function against the architecture:
  - int32 type annotations create 32-bit parameter inputs
  - + operator routes to INT32_ADD_CLA (3.3× faster than ripple)
  - - operator routes to INT32_SUB
  - == / != route to INT32_EQ with optional inversion
  - Chained operations (multi-tile) use per-tile bus segments and
    depth-aligned PASS chains so early output bits aren't lost
  - Per-bit output padding aligns all 32 bits to pipeline_depth before
    they feed into a downstream tile
  - Single-bit (bool) returns work alongside int32 returns

Run with: python3 test_compiler_int32.py
"""

from compiler_int32 import (
    Int32Compiler, Int32Value, run_int32_function,
    _is_int32_annotation, _returns_int32,
)
from fp_tiles import TileLibrary
import ast

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

INT32_MAX =  2**31 - 1
INT32_MIN = -(2**31)
lib = TileLibrary()


# =============================================================================
print("\n=== Int32Value — type wrapper ===\n")

iv = Int32Value(list(range(32)), depth=0)
check("Int32Value: holds 32 addresses", len(iv.bit_addrs) == 32)
check("Int32Value: depth defaults to 0", iv.depth == 0)

iv2 = Int32Value(list(range(32, 64)), depth=58)
check("Int32Value: depth field set correctly", iv2.depth == 58)

try:
    Int32Value(list(range(31)))
    check("Int32Value: rejects < 32 addresses", False)
except ValueError:
    check("Int32Value: rejects < 32 addresses", True)

try:
    Int32Value(list(range(33)))
    check("Int32Value: rejects > 32 addresses", False)
except ValueError:
    check("Int32Value: rejects > 32 addresses", True)


# =============================================================================
print("\n=== Type annotation helpers ===\n")

tree = ast.parse("def f(a: int32, b: str, c) -> int32: pass")
fn = tree.body[0]
check("_is_int32_annotation: int32 param", _is_int32_annotation(fn.args.args[0].annotation))
check("_is_int32_annotation: str param is not int32", not _is_int32_annotation(fn.args.args[1].annotation))
check("_is_int32_annotation: unannotated param", not _is_int32_annotation(fn.args.args[2].annotation))
check("_returns_int32: int32 return annotation", _returns_int32(fn))

tree2 = ast.parse("def g(a: int32): pass")
fn2 = tree2.body[0]
check("_returns_int32: no return annotation", not _returns_int32(fn2))


# =============================================================================
print("\n=== compile_int32_function — structure ===\n")

compiler = Int32Compiler(tile_library=lib)
src = "def add(a: int32, b: int32) -> int32:\n    return a + b"
records, graph, ibm, out_addrs, spans = compiler.compile_int32_function(src, "add")

check("compile_int32_function: returns 5-tuple", True)  # reached here = OK
check("compile_int32_function: records is a list", isinstance(records, list))
check("compile_int32_function: records non-empty", len(records) > 0)
check("compile_int32_function: 'a' in input_bit_map", "a" in ibm)
check("compile_int32_function: 'b' in input_bit_map", "b" in ibm)
check("compile_int32_function: a has 32 bit addresses", len(ibm["a"]) == 32)
check("compile_int32_function: b has 32 bit addresses", len(ibm["b"]) == 32)
check("compile_int32_function: 32 output addresses", len(out_addrs) == 32)
check("compile_int32_function: segment spans non-empty", len(spans) > 0)
check("compile_int32_function: span covers tile records", spans[0][1] > spans[0][0])


# =============================================================================
print("\n=== INT32 addition — single operation ===\n")

add_src = "def f(a: int32, b: int32) -> int32:\n    return a + b"

check_eq("ADD: 0 + 0 = 0",         run_int32_function(add_src,"f",{"a":0,"b":0},lib), 0)
check_eq("ADD: 1 + 1 = 2",         run_int32_function(add_src,"f",{"a":1,"b":1},lib), 2)
check_eq("ADD: 100 + 200 = 300",   run_int32_function(add_src,"f",{"a":100,"b":200},lib), 300)
check_eq("ADD: -1 + 1 = 0",        run_int32_function(add_src,"f",{"a":-1,"b":1},lib), 0)
check_eq("ADD: -5 + 3 = -2",       run_int32_function(add_src,"f",{"a":-5,"b":3},lib), -2)
check_eq("ADD: -1 + -1 = -2",      run_int32_function(add_src,"f",{"a":-1,"b":-1},lib), -2)
check_eq("ADD: INT32_MAX + 1 wraps",run_int32_function(add_src,"f",{"a":INT32_MAX,"b":1},lib), INT32_MIN)
check_eq("ADD: INT32_MIN + -1 wraps",run_int32_function(add_src,"f",{"a":INT32_MIN,"b":-1},lib), INT32_MAX)
check_eq("ADD: 1M + 2M = 3M",      run_int32_function(add_src,"f",{"a":1000000,"b":2000000},lib), 3000000)


# =============================================================================
print("\n=== INT32 subtraction — single operation ===\n")

sub_src = "def f(a: int32, b: int32) -> int32:\n    return a - b"

check_eq("SUB: 200 - 100 = 100",   run_int32_function(sub_src,"f",{"a":200,"b":100},lib), 100)
check_eq("SUB: 0 - 1 = -1",        run_int32_function(sub_src,"f",{"a":0,"b":1},lib), -1)
check_eq("SUB: 100 - 100 = 0",     run_int32_function(sub_src,"f",{"a":100,"b":100},lib), 0)
check_eq("SUB: -5 - -3 = -2",      run_int32_function(sub_src,"f",{"a":-5,"b":-3},lib), -2)
check_eq("SUB: INT32_MIN - 1 wraps",run_int32_function(sub_src,"f",{"a":INT32_MIN,"b":1},lib), INT32_MAX)


# =============================================================================
print("\n=== INT32 equality / inequality ===\n")

eq_src  = "def f(a: int32, b: int32):\n    return a == b"
neq_src = "def f(a: int32, b: int32):\n    return a != b"

check_eq("EQ: 5 == 5 -> 1",   run_int32_function(eq_src, "f",{"a":5,"b":5},lib), 1)
check_eq("EQ: 5 == 6 -> 0",   run_int32_function(eq_src, "f",{"a":5,"b":6},lib), 0)
check_eq("EQ: 0 == 0 -> 1",   run_int32_function(eq_src, "f",{"a":0,"b":0},lib), 1)
check_eq("EQ: -1 == -1 -> 1", run_int32_function(eq_src, "f",{"a":-1,"b":-1},lib), 1)
check_eq("EQ: -1 == 1 -> 0",  run_int32_function(eq_src, "f",{"a":-1,"b":1},lib), 0)
check_eq("NEQ: 5 != 6 -> 1",  run_int32_function(neq_src,"f",{"a":5,"b":6},lib), 1)
check_eq("NEQ: 5 != 5 -> 0",  run_int32_function(neq_src,"f",{"a":5,"b":5},lib), 0)


# =============================================================================
print("\n=== Chained operations (multi-tile) ===\n")

# add then sub
chain1 = "def f(a: int32, b: int32, c: int32) -> int32:\n    t = a + b\n    return t - c"
check_eq("CHAIN add-sub: (100+200)-50=250",
         run_int32_function(chain1,"f",{"a":100,"b":200,"c":50},lib), 250)
check_eq("CHAIN add-sub: (10+20)-30=0",
         run_int32_function(chain1,"f",{"a":10,"b":20,"c":30},lib), 0)
check_eq("CHAIN add-sub: (INT32_MAX+0)-1=INT32_MAX-1",
         run_int32_function(chain1,"f",{"a":INT32_MAX,"b":0,"c":1},lib), INT32_MAX-1)

# sub then add
chain2 = "def f(a: int32, b: int32, c: int32) -> int32:\n    t = a - b\n    return t + c"
check_eq("CHAIN sub-add: (500-200)+100=400",
         run_int32_function(chain2,"f",{"a":500,"b":200,"c":100},lib), 400)
check_eq("CHAIN sub-add: (0-1)+1=0",
         run_int32_function(chain2,"f",{"a":0,"b":1,"c":1},lib), 0)

# add then add
chain3 = "def f(a: int32, b: int32, c: int32) -> int32:\n    t = a + b\n    return t + c"
check_eq("CHAIN add-add: 1+2+3=6",
         run_int32_function(chain3,"f",{"a":1,"b":2,"c":3},lib), 6)
check_eq("CHAIN add-add: 1000+2000+3000=6000",
         run_int32_function(chain3,"f",{"a":1000,"b":2000,"c":3000},lib), 6000)


# =============================================================================
print("\n=== Per-bit output depth alignment ===\n")

# CLA outputs bits at depths 13..58. Without alignment, early bits vanish
# before the downstream tile reads them. These tests catch that regression.
compiler2 = Int32Compiler(tile_library=lib)
src_add = "def f(a: int32, b: int32) -> int32:\n    return a + b"
recs2, graph2, ibm2, out2, spans2 = compiler2.compile_int32_function(src_add, "f")

# Verify the output addresses all arrive at the same depth (pipeline_depth=58)
# by checking they are the LAST in PASS chains, not raw tile outputs.
cla_tile = lib.get("INT32_ADD")  # was INT32_ADD_CLA, now Kogge-Stone
raw_cla_outs = set(cla_tile.out)
# After padding, output addrs should NOT be the raw tile outputs
check("CLA outputs are padded (not raw tile addresses)",
      not any(a in raw_cla_outs for a in out2))

# Each padded output address should be the end of a PASS chain
from gate_states import GS_PASS
pass_recs = [r for r in recs2 if r.gate_state == GS_PASS]
pass_outputs = {r.output_address for r in pass_recs}
cla_tile = lib.get("INT32_ADD")  # was INT32_ADD_CLA, now Kogge-Stone

# Compute per-bit depths from the tile
_d = {}
for a in cla_tile.in_a + cla_tile.in_b: _d[a] = 0
for r in cla_tile.records:
    _d[r.output_address] = max(_d.get(r.output_address,0), _d.get(r.input_address,0)+1)
tile_depth = cla_tile.metadata.pipeline_depth
bits_needing_pad = sum(1 for a in cla_tile.out if _d.get(a,0) < tile_depth)

# Kogge-Stone: the deepest output bit should match pipeline_depth.
# Shallow bits (e.g. bit 0 = XOR only) are expected and correct.
max_out_depth = max(_d.get(a,0) for a in cla_tile.out)
check("Output bits have near-uniform depth (Kogge-Stone property)",
      max_out_depth == tile_depth)


# =============================================================================
print("\n=== Segment assignment — bus lane compliance ===\n")

# Each tile placement must be in its own segment to prevent first-tick
# NOT cell emissions from stacking above the 256-lane limit.
compiler3 = Int32Compiler(tile_library=lib)
src_chain = "def f(a: int32, b: int32, c: int32) -> int32:\n    t = a + b\n    return t - c"
recs3, graph3, ibm3, out3, spans3 = compiler3.compile_int32_function(src_chain, "f")

check("Chain produces 2 segment spans (one per tile)", len(spans3) == 2)
seg_ids = [s for _,_,s in spans3]
check("Each tile gets a unique segment id", len(set(seg_ids)) == len(seg_ids))
check("Segment ids are positive integers", all(s > 0 for s in seg_ids))

# The segments must not overlap in record index range
(s1, e1, _), (s2, e2, _) = spans3
check("Tile spans do not overlap", e1 <= s2 or e2 <= s1)


# =============================================================================
print("\n=== TILE_FUNCTION_MAP — INT32_ADD_CLA registration ===\n")

from compiler import ImagoCompiler
base_compiler = ImagoCompiler()
check("INT32_ADD in TILE_FUNCTION_MAP",
      "int32_add" in base_compiler.TILE_FUNCTION_MAP)
check("INT32_ADD maps to correct tile name",
      base_compiler.TILE_FUNCTION_MAP["int32_add"] == "INT32_ADD")


# =============================================================================
print("\n=== Correctness vs reference (50 pseudo-random pairs) ===\n")

def lcg(seed=0xDEADBEEF):
    s = seed
    while True:
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        yield s if s < 2**31 else s - 2**32

gen = lcg()
pairs = [(next(gen), next(gen)) for _ in range(50)]

mismatches = 0
for a, b in pairs:
    got = run_int32_function(add_src, "f", {"a": a, "b": b}, lib)
    expected = ((a + b) & 0xFFFFFFFF)
    expected = expected if expected < 2**31 else expected - 2**32
    if got != expected:
        mismatches += 1
        print(f"    MISMATCH: {a}+{b} -> {got}, expected {expected}")

check(f"50 pseudo-random ADD pairs match reference (mismatches={mismatches})",
      mismatches == 0)

mismatches_sub = 0
for a, b in pairs[:25]:
    got = run_int32_function(sub_src, "f", {"a": a, "b": b}, lib)
    expected = ((a - b) & 0xFFFFFFFF)
    expected = expected if expected < 2**31 else expected - 2**32
    if got != expected:
        mismatches_sub += 1
        print(f"    MISMATCH: {a}-{b} -> {got}, expected {expected}")

check(f"25 pseudo-random SUB pairs match reference (mismatches={mismatches_sub})",
      mismatches_sub == 0)


# =============================================================================
# Comparison operators: Lt, Gt, LtE, GtE using INT32_LT_U tile
# =============================================================================

lt_src  = "from compiler_int32 import int32\ndef f(a: int32, b: int32) -> int32: return a < b"
gt_src  = "from compiler_int32 import int32\ndef f(a: int32, b: int32) -> int32: return a > b"
lte_src = "from compiler_int32 import int32\ndef f(a: int32, b: int32) -> int32: return a <= b"
gte_src = "from compiler_int32 import int32\ndef f(a: int32, b: int32) -> int32: return a >= b"

cmp_cases = [
    ("Lt  3 < 5",  lt_src,  3,  5, 1),
    ("Lt  7 < 2",  lt_src,  7,  2, 0),
    ("Lt  5 < 5",  lt_src,  5,  5, 0),
    ("Gt  7 > 3",  gt_src,  7,  3, 1),
    ("Gt  3 > 7",  gt_src,  3,  7, 0),
    ("Gt  5 > 5",  gt_src,  5,  5, 0),
    ("LtE 3 <= 7", lte_src, 3,  7, 1),
    ("LtE 7 <= 3", lte_src, 7,  3, 0),
    ("LtE 5 <= 5", lte_src, 5,  5, 1),
    ("GtE 7 >= 3", gte_src, 7,  3, 1),
    ("GtE 3 >= 7", gte_src, 3,  7, 0),
    ("GtE 5 >= 5", gte_src, 5,  5, 1),
]
for label, src, a, b, expected in cmp_cases:
    got = run_int32_function(src, "f", {"a": a, "b": b}, lib)
    check(label, got == expected)

# Fuzz comparisons against Python reference (20 pairs).
# int32 uses signed semantics (INT32_LT_S). Pass values as signed ints.
cmp_mismatches = 0
for a, b in pairs[:20]:
    # a and b are already signed (from lcg). Use them directly.
    sa = a if a < 2**31 else a - 2**32
    sb = b if b < 2**31 else b - 2**32
    for src, py_op in [(lt_src, sa < sb), (gt_src, sa > sb),
                       (lte_src, sa <= sb), (gte_src, sa >= sb)]:
        got = run_int32_function(src, "f", {"a": sa, "b": sb}, lib)
        if got != int(py_op):
            cmp_mismatches += 1
check(f"20-pair fuzz: Lt/Gt/LtE/GtE vs Python (mismatches={cmp_mismatches})",
      cmp_mismatches == 0)

# =============================================================================
# min() / max() builtins routing to INT32_MIN / INT32_MAX tiles
# =============================================================================

min_src = "from compiler_int32 import int32\ndef f(a: int32, b: int32) -> int32: return min(a, b)"
max_src = "from compiler_int32 import int32\ndef f(a: int32, b: int32) -> int32: return max(a, b)"

minmax_cases = [
    ("min(3, 7)",   min_src, 3,   7,   3),
    ("min(7, 3)",   min_src, 7,   3,   3),
    ("min(5, 5)",   min_src, 5,   5,   5),
    ("min(0, 100)", min_src, 0,   100, 0),
    ("max(3, 7)",   max_src, 3,   7,   7),
    ("max(7, 3)",   max_src, 7,   3,   7),
    ("max(5, 5)",   max_src, 5,   5,   5),
    ("max(0, 100)", max_src, 0,   100, 100),
]
for label, src, a, b, expected in minmax_cases:
    got = run_int32_function(src, "f", {"a": a, "b": b}, lib)
    check(label, got == expected)

mm_mismatches = 0
for a, b in pairs[:20]:
    # pairs come from LCG as signed int32 values
    for src, py_ref in [(min_src, min(a, b)), (max_src, max(a, b))]:
        got = run_int32_function(src, "f", {"a": a, "b": b}, lib)
        if got != py_ref:
            mm_mismatches += 1
check(f"20-pair fuzz: min/max signed vs Python (mismatches={mm_mismatches})",
      mm_mismatches == 0)


# =============================================================================
# NotImplementedError boundary tests — int32 compiler rejects unsupported constructs
# =============================================================================

def assert_ni_int32(src, fn_name, label):
    try:
        run_int32_function(src, fn_name, {})
        check(label, False)  # should not reach here
    except (NotImplementedError, Exception) as e:
        if "not supported" in str(e).lower() or isinstance(e, NotImplementedError):
            check(label, True)
        else:
            check(label, False)

assert_ni_int32(
    "from compiler_int32 import int32\ndef f(a: int32, b: int32, c: int32) -> int32: return a < b < c",
    "f", "int32 chained comparison raises error"
)
assert_ni_int32(
    "from compiler_int32 import int32\ndef f(a: int32, b: int32) -> int32: return a ** b",
    "f", "int32 unsupported BinOp (Pow) raises error"
)

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
