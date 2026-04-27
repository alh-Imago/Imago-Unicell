"""
test_llvm_ir_mapper.py — LLVM IR mapper tests
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from llvm_ir_mapper import LLVMIRMapper, compile_ll
from llvm_frontend import parse_ll
from program_image import RangeKind

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


LL_ADD  = 'define i32 @add(i32 %a, i32 %b) {\nentry:\n  %r = add i32 %a, %b\n  ret i32 %r\n}'
LL_AND  = 'define i32 @band(i32 %a, i32 %b) {\nentry:\n  %r = and i32 %a, %b\n  ret i32 %r\n}'
LL_OR   = 'define i32 @bor(i32 %a, i32 %b)  {\nentry:\n  %r = or  i32 %a, %b\n  ret i32 %r\n}'
LL_XOR  = 'define i32 @bxor(i32 %a, i32 %b) {\nentry:\n  %r = xor i32 %a, %b\n  ret i32 %r\n}'
LL_SUB  = 'define i32 @sub(i32 %a, i32 %b)  {\nentry:\n  %r = sub i32 %a, %b\n  ret i32 %r\n}'

LL_MAX = '''
define i32 @max(i32 %a, i32 %b) {
entry:
  %cmp = icmp sgt i32 %a, %b
  br i1 %cmp, label %if.true, label %if.false
if.true:
  br label %merge
if.false:
  br label %merge
merge:
  %result = phi i32 [ %a, %if.true ], [ %b, %if.false ]
  ret i32 %result
}
'''

LL_EQ = '''
define i1 @eq(i32 %a, i32 %b) {
entry:
  %r = icmp eq i32 %a, %b
  ret i1 %r
}
'''

LL_LOOP = '''
define i32 @countdown(i32 %n) {
entry:
  br label %loop
loop:
  %i = phi i32 [ %n, %entry ], [ %i_next, %loop ]
  %i_next = sub i32 %i, 1
  %cmp = icmp sgt i32 %i, 0
  br i1 %cmp, label %loop, label %exit
exit:
  ret i32 %i
}
'''

LL_MULTI = '''
define i32 @fn1(i32 %x) {
entry:
  %r = and i32 %x, 255
  ret i32 %r
}
define i32 @fn2(i32 %a, i32 %b) {
entry:
  %r = or i32 %a, %b
  ret i32 %r
}
'''

LL_ALLOCA = '''
define i32 @with_alloca(i32 %a) {
entry:
  %slot = alloca i32
  store i32 %a, i32* %slot
  %val = load i32, i32* %slot
  ret i32 %val
}
'''


# =============================================================================
print("\n=== compile_ll: basic arithmetic ===\n")
# =============================================================================

for src, fn_name, expected_tile in [
    (LL_ADD,  "add",  "INT32_ADD_CLA"),
    (LL_AND,  "band", "INT32_AND"),
    (LL_OR,   "bor",  "INT32_OR"),
    (LL_XOR,  "bxor", "INT32_XOR"),
    (LL_SUB,  "sub",  "INT32_SUB"),
]:
    imgs, errors = compile_ll(src)
    check(f"{fn_name}: no errors",           len(errors) == 0)
    check(f"{fn_name}: 1 image",             len(imgs) == 1)
    if imgs:
        img = imgs[0]
        check_eq(f"{fn_name}: name",         img.name, fn_name)
        check(f"{fn_name}: has records",     len(img.records) > 0)
        check(f"{fn_name}: 2 inputs",        len(img.inputs()) == 2)
        check(f"{fn_name}: 1 output",        len(img.outputs()) == 1)
        check(f"{fn_name}: tile = {expected_tile}",
              expected_tile in img.models)
        check(f"{fn_name}: a is INPUT",
              any(r.name == 'a' for r in img.inputs()))
        check(f"{fn_name}: b is INPUT",
              any(r.name == 'b' for r in img.inputs()))
        out = img.range("output")
        check(f"{fn_name}: output range exists", out is not None)


# =============================================================================
print("\n=== compile_ll: icmp ===\n")
# =============================================================================

imgs_eq, errs_eq = compile_ll(LL_EQ)
check("icmp eq: no errors",          len(errs_eq) == 0)
if imgs_eq:
    img_eq = imgs_eq[0]
    check("icmp eq: INT32_EQ in models", "INT32_EQ" in img_eq.models)
    check("icmp eq: has output",         len(img_eq.outputs()) == 1)

# icmp sgt via INT32_SUB sign bit
imgs_max, errs_max = compile_ll(LL_MAX)
check("max/icmp sgt: no errors",     len(errs_max) == 0)
if imgs_max:
    check("max: INT32_SUB in models", "INT32_SUB" in imgs_max[0].models)


# =============================================================================
print("\n=== compile_ll: phi node ===\n")
# =============================================================================

imgs_max, _ = compile_ll(LL_MAX)
if imgs_max:
    img = imgs_max[0]
    check("max: phi → accumulator",
          len(img.accumulators()) >= 1)
    phi_range = next((r for r in img.accumulators()
                      if "result" in r.name), None)
    check("max: phi_result accumulator",   phi_range is not None)
    if phi_range:
        check_eq("max: phi kind",          phi_range.kind, RangeKind.ACCUMULATOR)


# =============================================================================
print("\n=== compile_ll: while loop ===\n")
# =============================================================================

imgs_loop, errs_loop = compile_ll(LL_LOOP)
check("loop: no errors",             len(errs_loop) == 0)
if imgs_loop:
    img_l = imgs_loop[0]
    check_eq("loop: name",           img_l.name, "countdown")
    check("loop: phi_i accumulator",
          any("phi_i" in r.name for r in img_l.accumulators()))
    check("loop: INT32_SUB in models", "INT32_SUB" in img_l.models)
    check("loop: 1 input (n)",        len(img_l.inputs()) == 1)
    check_eq("loop: input name",      img_l.inputs()[0].name, "n")


# =============================================================================
print("\n=== compile_ll: multiple functions ===\n")
# =============================================================================

imgs_m, errs_m = compile_ll(LL_MULTI)
check("multi: no errors",            len(errs_m) == 0)
check_eq("multi: 2 images",          len(imgs_m), 2)
if len(imgs_m) == 2:
    names = {img.name for img in imgs_m}
    check("multi: fn1 present",      "fn1" in names)
    check("multi: fn2 present",      "fn2" in names)


# =============================================================================
print("\n=== compile_ll: alloca / load / store ===\n")
# =============================================================================

imgs_a, errs_a = compile_ll(LL_ALLOCA)
check("alloca: no errors",           len(errs_a) == 0)
if imgs_a:
    check("alloca: has records",     len(imgs_a[0].records) > 0)
    check("alloca: 1 input",         len(imgs_a[0].inputs()) == 1)


# =============================================================================
print("\n=== ProgramImage structure from mapper ===\n")
# =============================================================================

imgs_add, _ = compile_ll(LL_ADD)
img = imgs_add[0]

check("img: has program_id",         bool(img.program_id))
check("img: os_name = Claudette",    img.os_name == "Claudette")
check("img: os_version = 1.3",       img.os_version == "1.3")

m = img.manifest()
check("manifest: MANIFEST HEADER",  "MANIFEST HEADER" in m)
check("manifest: MODELS NEEDED",    "MODELS NEEDED" in m)
check("manifest: NAMED RANGES",     "NAMED RANGES" in m)
check("manifest: a in ranges",      "a" in m["NAMED RANGES"])
check("manifest: b in ranges",      "b" in m["NAMED RANGES"])
check("manifest: output in ranges", "output" in m["NAMED RANGES"])


# =============================================================================
print("\n=== LLVMIRMapper direct API ===\n")
# =============================================================================

fe_result = parse_ll(LL_AND)
check("direct: parse ok",            fe_result.ok)
if fe_result.ok:
    mapper = LLVMIRMapper()
    img_d = mapper.lower(fe_result.functions[0])
    check("direct: lower ok",        img_d is not None)
    check("direct: INT32_AND",       "INT32_AND" in img_d.models)
    check("direct: has inputs",      len(img_d.inputs()) == 2)


# =============================================================================
print("\n=== compile_ll error handling ===\n")
# =============================================================================

# Bad LLVM IR
imgs_bad, errs_bad = compile_ll("this is not valid llvm ir")
check("bad IR: errors returned",     len(errs_bad) > 0)
check("bad IR: no images",           len(imgs_bad) == 0)


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
