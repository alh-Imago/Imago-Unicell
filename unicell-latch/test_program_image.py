"""
test_program_image.py — ProgramImage named ranges and manifest tests

Tests:
  - ProgramImage.from_compiler(): builds from compiler output
  - Named range classification (INPUT/OUTPUT/LOOP/ACCUMULATOR)
  - Manifest structure (HEADER/MODELS/NAMED RANGES/SCRIPTS)
  - run() via CPU controller — correct results
  - run() loop programs — tick auto-injected
  - Serialise to_dict() / from_dict() round-trip
  - Named range lookup by name
  - GPU load: vram_offsets assigned
  - describe() and repr()
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from program_image import ProgramImage, NamedRange, RangeKind
from compiler import ImagoCompiler
from fp_tiles import TileLibrary

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


lib = TileLibrary()

def compile_fn(src, fn_name, args):
    c = ImagoCompiler(tile_library=lib)
    return c.compile_function(src, fn_name, args)


# =============================================================================
print("\n=== NamedRange ===\n")
# =============================================================================

r = NamedRange("my_input", 0x1000, width=32, kind=RangeKind.INPUT,
               description="Test input")
check_eq("NamedRange: name",        r.name, "my_input")
check_eq("NamedRange: bus_address", r.bus_address, 0x1000)
check_eq("NamedRange: width",       r.width, 32)
check_eq("NamedRange: kind",        r.kind, RangeKind.INPUT)

d = r.to_dict()
r2 = NamedRange.from_dict(d)
check_eq("NamedRange: round-trip name",    r2.name,        r.name)
check_eq("NamedRange: round-trip addr",    r2.bus_address, r.bus_address)
check_eq("NamedRange: round-trip kind",    r2.kind,        r.kind)


# =============================================================================
print("\n=== ProgramImage.from_compiler() ===\n")
# =============================================================================

records, graph, imap, oa = compile_fn(
    'def f(a, b):\n    return a & b', 'f', ['a', 'b'])

img = ProgramImage.from_compiler(
    name        = "and_test",
    records     = records,
    input_map   = imap,
    output_addrs= oa,
    models      = ["INT32_AND"],
    arg_names   = ['a', 'b'],
)

check("from_compiler: creates ProgramImage",  img is not None)
check_eq("from_compiler: name",               img.name, "and_test")
check("from_compiler: has records",           len(img.records) > 0)
check("from_compiler: has ranges",            len(img.ranges) > 0)
check_eq("from_compiler: models",             img.models, ["INT32_AND"])
check("from_compiler: os_name = Claudette",   img.os_name == "Claudette")
check("from_compiler: os_version = 1.3",      img.os_version == "1.3")


# =============================================================================
print("\n=== Named range classification ===\n")
# =============================================================================

check("inputs: a present",      any(r.name == 'a' for r in img.inputs()))
check("inputs: b present",      any(r.name == 'b' for r in img.inputs()))
check("outputs: output present", any(r.name == 'output' for r in img.outputs()))
check("inputs: kind = INPUT",
      all(r.kind == RangeKind.INPUT for r in img.inputs()))
check("outputs: kind = OUTPUT",
      all(r.kind == RangeKind.OUTPUT for r in img.outputs()))

# Output range has bit_addresses
out_range = img.range("output")
check("output range: has bit_addresses",  len(out_range.bit_addresses) > 0)
check_eq("output range: width = 1",       out_range.width, 1)  # single result


# =============================================================================
print("\n=== Manifest structure ===\n")
# =============================================================================

m = img.manifest()
check("manifest: has MANIFEST HEADER",   "MANIFEST HEADER" in m)
check("manifest: has MODELS NEEDED",     "MODELS NEEDED" in m)
check("manifest: has NAMED RANGES",      "NAMED RANGES" in m)
check("manifest: has PROGRAM SCRIPTS",   "PROGRAM SCRIPTS" in m)

header = m["MANIFEST HEADER"]
check("manifest header: has program_id", "program_id" in header)
check("manifest header: has name",       header["name"] == "and_test")
check("manifest header: has os",         "Claudette" in header["os"])
check("manifest header: has cell_count", header["cell_count"] > 0)

named = m["NAMED RANGES"]
check("named ranges: a present",         "a" in named)
check("named ranges: b present",         "b" in named)
check("named ranges: output present",    "output" in named)
check("named ranges: a is INPUT",        named["a"]["kind"] == RangeKind.INPUT)
check("named ranges: output is OUTPUT",  named["output"]["kind"] == RangeKind.OUTPUT)


# =============================================================================
print("\n=== Range lookup ===\n")
# =============================================================================

r_a = img.range("a")
check("range('a'): found",           r_a is not None)
check_eq("range('a'): kind",         r_a.kind, RangeKind.INPUT)
check("range('a'): has bus_address", r_a.bus_address > 0)

r_missing = img.range("does_not_exist")
check("range(missing): None",        r_missing is None)

addr_a = img.input_address("a")
check("input_address('a'): not None", addr_a is not None)
check_eq("input_address('a'): == range addr", addr_a, r_a.bus_address)


# =============================================================================
print("\n=== run() via CPU controller ===\n")
# =============================================================================

result_11 = img.run(inputs={"a": 1, "b": 1})
check_eq("run AND(1,1): output = 1", result_11.get("output"), 1)

result_10 = img.run(inputs={"a": 1, "b": 0})
check_eq("run AND(1,0): output = 0", result_10.get("output"), 0)

result_00 = img.run(inputs={"a": 0, "b": 0})
check_eq("run AND(0,0): output = 0", result_00.get("output"), 0)


# =============================================================================
print("\n=== run() loop program ===\n")
# =============================================================================

records2, graph2, imap2, oa2 = compile_fn(
    'def f():\n    for i in range(4):\n        pass\n    return i', 'f', [])

img2 = ProgramImage.from_compiler("loop_test", records2, imap2, oa2)

check("loop: loop controls present",  len(img2.loop_controls()) > 0)
check("loop: tick auto-injected",
      any(r.kind == RangeKind.LOOP_TICK for r in img2.loop_controls()))

result_loop = img2.run()  # no inputs needed — tick auto-injected
check("loop: run() completes",        result_loop is not None)


# =============================================================================
print("\n=== Serialise / from_dict round-trip ===\n")
# =============================================================================

d = img.to_dict()
check("to_dict: returns dict",        isinstance(d, dict))
check("to_dict: has program_id",      "program_id" in d)
check("to_dict: has name",            d["name"] == "and_test")
check("to_dict: has models",          "models" in d)
check("to_dict: has ranges",          len(d["ranges"]) > 0)
check("to_dict: has records",         len(d["records"]) > 0)

img_r = ProgramImage.from_dict(d)
check("from_dict: creates image",     img_r is not None)
check_eq("from_dict: name",           img_r.name, img.name)
check_eq("from_dict: program_id",     img_r.program_id, img.program_id)
check_eq("from_dict: range count",    len(img_r.ranges), len(img.ranges))

result_r = img_r.run(inputs={"a": 1, "b": 1})
check_eq("from_dict: run correct",    result_r.get("output"), 1)


# =============================================================================
print("\n=== GPU load: vram_offsets assigned ===\n")
# =============================================================================

from gpu_array import GPUArrayBackend

backend = GPUArrayBackend(cell_count=len(img.records) + 100)
img.load_to_gpu(backend)

for r in img.ranges:
    check(f"vram_offset set for '{r.name}'", r.vram_offset >= 0)


# =============================================================================
print("\n=== describe() and repr() ===\n")
# =============================================================================

desc = img.describe()
check("describe: contains name",     "and_test" in desc)
check("describe: contains cells",    "cells" in desc)
check("describe: contains inputs",   "inputs" in desc)
check("describe: contains outputs",  "outputs" in desc)

check("repr: same as describe",      repr(img) == img.describe())


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
