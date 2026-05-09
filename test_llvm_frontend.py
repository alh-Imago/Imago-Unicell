"""
test_llvm_frontend.py — LLVM IR Frontend tests
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from llvm_frontend import (
    LLVMFrontend, parse_ll, validate_ll, describe_support,
    SUPPORTED_ARITH, SUPPORTED_ICMP, FUTURE_ARITH,
)

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


# ── Test fixtures ─────────────────────────────────────────────────────────────

LL_ADD = '''
define i32 @add(i32 %a, i32 %b) {
entry:
  %r = add i32 %a, %b
  ret i32 %r
}
'''

LL_ALL_ARITH = '''
define i32 @arith(i32 %a, i32 %b) {
entry:
  %x0 = add i32 %a, %b
  %x1 = sub i32 %a, %b
  %x2 = and i32 %a, %b
  %x3 = or  i32 %a, %b
  %x4 = xor i32 %a, %b
  ret i32 %x0
}
'''

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

LL_WHILE = '''
define i32 @countdown(i32 %n) {
entry:
  br label %loop
loop:
  %i = phi i32 [ %n, %entry ], [ %i_next, %loop ]
  %cmp = icmp sgt i32 %i, 0
  %i_next = sub i32 %i, 1
  br i1 %cmp, label %loop, label %exit
exit:
  ret i32 %i
}
'''

LL_ICMP_ALL = '''
define i1 @cmp(i32 %a, i32 %b) {
entry:
  %eq  = icmp eq  i32 %a, %b
  %ne  = icmp ne  i32 %a, %b
  %slt = icmp slt i32 %a, %b
  %sgt = icmp sgt i32 %a, %b
  %sle = icmp sle i32 %a, %b
  %sge = icmp sge i32 %a, %b
  ret i1 %eq
}
'''

LL_REJECTED_GEP = '''
define i32 @bad(i32* %p) {
entry:
  %x = getelementptr i32, i32* %p, i32 1
  ret i32 0
}
'''

LL_REJECTED_FLOAT = '''
define float @badf(float %a) {
entry:
  %r = fadd float %a, 1.0
  ret float %r
}
'''

LL_REJECTED_I64 = '''
define i64 @bad64(i64 %a, i64 %b) {
entry:
  %r = add i64 %a, %b
  ret i64 %r
}
'''

LL_REJECTED_CALL = '''
define i32 @badcall(i32 %a) {
entry:
  %r = call i32 @some_extern_fn(i32 %a)
  ret i32 %r
}
declare i32 @some_extern_fn(i32)
'''

LL_PERMITTED_INTRINSIC = '''
define i32 @popcount(i32 %a) {
entry:
  %r = call i32 @llvm.ctpop.i32(i32 %a)
  ret i32 %r
}
declare i32 @llvm.ctpop.i32(i32)
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

LL_MULTI_FN = '''
define i32 @fn1(i32 %a) {
entry:
  ret i32 %a
}
define i32 @fn2(i32 %a, i32 %b) {
entry:
  %r = add i32 %a, %b
  ret i32 %r
}
'''


# =============================================================================
print("\n=== Frontend creation ===\n")
# =============================================================================

fe = LLVMFrontend()
check("LLVMFrontend: creates", fe is not None)
check("describe_support: returns string", len(describe_support()) > 100)


# =============================================================================
print("\n=== Simple function parse ===\n")
# =============================================================================

r = parse_ll(LL_ADD)
check("add: ok",                r.ok)
check_eq("add: 1 function",     len(r.functions), 1)
fn = r.functions[0]
check_eq("add: name",           fn.name, "add")
check_eq("add: args",           fn.arg_names, ['a', 'b'])
check_eq("add: 1 block",        len(fn.blocks), 1)
check_eq("add: entry block",    fn.entry_block, "entry")

block = fn.blocks[0]
check_eq("add: 2 instructions", len(block.instructions), 2)

add_instr = block.instructions[0]
check_eq("add instr: opcode",      add_instr.opcode, "add")
check_eq("add instr: result",      add_instr.result, "r")
check_eq("add instr: tile",        add_instr.maps_to_tile, "INT32_ADD")  # Kogge-Stone
check_eq("add instr: 2 operands",  len(add_instr.operands), 2)
check_eq("add instr: op0 name",    add_instr.operands[0].name, "a")
check_eq("add instr: op1 name",    add_instr.operands[1].name, "b")

ret_instr = block.instructions[1]
check_eq("ret instr: opcode",      ret_instr.opcode, "ret")


# =============================================================================
print("\n=== All arithmetic opcodes ===\n")
# =============================================================================

r2 = parse_ll(LL_ALL_ARITH)
check("arith: ok",              r2.ok)
fn2 = r2.functions[0]
block2 = fn2.blocks[0]
opcodes = [i.opcode for i in block2.instructions]
tiles   = [i.maps_to_tile for i in block2.instructions if i.maps_to_tile]

for op, tile in SUPPORTED_ARITH.items():
    check(f"arith: {op} → {tile}",
          tile in tiles)


# =============================================================================
print("\n=== if/else with phi (max function) ===\n")
# =============================================================================

r3 = parse_ll(LL_MAX)
check("max: ok",                r3.ok)
fn3 = r3.functions[0]
check_eq("max: 4 blocks",       len(fn3.blocks), 4)

# CFG structure
entry = fn3.block("entry")
check("max: entry has 2 succs", len(entry.successors) == 2)
check("max: if.true in succs",  "if.true" in entry.successors)
check("max: if.false in succs", "if.false" in entry.successors)

merge = fn3.block("merge")
check("max: merge has 2 preds", len(merge.predecessors) == 2)

# phi instruction
phi_instrs = [i for i in merge.instructions if i.opcode == "phi"]
check("max: 1 phi in merge",    len(phi_instrs) == 1)
phi = phi_instrs[0]
check_eq("max: phi result",     phi.result, "result")
check_eq("max: phi 2 values",   len(phi.phi_values), 2)

phi_blocks = [bl for _, bl in phi.phi_values]
check("max: phi from if.true",  "if.true"  in phi_blocks)
check("max: phi from if.false", "if.false" in phi_blocks)

# icmp
icmp_instrs = [i for i in entry.instructions if i.opcode == "icmp"]
check("max: icmp sgt",          icmp_instrs[0].predicate == "sgt")

# conditional br
br_instrs = [i for i in entry.instructions if i.opcode == "br"]
check("max: conditional br",    br_instrs[0].is_conditional)
check_eq("max: true label",     br_instrs[0].true_label, "if.true")
check_eq("max: false label",    br_instrs[0].false_label, "if.false")


# =============================================================================
print("\n=== While loop with back-edge phi ===\n")
# =============================================================================

r4 = parse_ll(LL_WHILE)
check("while: ok",               r4.ok)
fn4 = r4.functions[0]
loop_block = fn4.block("loop")
check("while: loop block exists",loop_block is not None)

phi_w = [i for i in loop_block.instructions if i.opcode == "phi"]
check("while: phi in loop",      len(phi_w) >= 1)
# Back edge: one value comes from entry, one from loop
phi_blocks_w = [bl for _, bl in phi_w[0].phi_values]
check("while: phi from entry",   "entry" in phi_blocks_w)
check("while: phi back-edge",    "loop"  in phi_blocks_w)


# =============================================================================
print("\n=== All icmp predicates ===\n")
# =============================================================================

r5 = parse_ll(LL_ICMP_ALL)
check("icmp all: ok", r5.ok)
fn5 = r5.functions[0]
block5 = fn5.blocks[0]
icmps = [i for i in block5.instructions if i.opcode == "icmp"]
preds = [i.predicate for i in icmps]
for pred in ["eq", "ne", "slt", "sgt", "sle", "sge"]:
    check(f"icmp {pred}: parsed",  pred in preds)
    matching = [i for i in icmps if i.predicate == pred]
    check(f"icmp {pred}: has tile", bool(matching[0].maps_to_tile if matching else False))


# =============================================================================
print("\n=== Rejected instructions ===\n")
# =============================================================================

r_gep = parse_ll(LL_REJECTED_GEP)
check("reject getelementptr: has errors", not r_gep.ok)
check("reject getelementptr: correct msg",
      any("pointer arithmetic" in e for e in r_gep.errors))

r_i64 = parse_ll(LL_REJECTED_I64)
check("reject i64: has errors",           not r_i64.ok)
check("reject i64: correct msg",
      any("i64" in e for e in r_i64.errors))

r_call = parse_ll(LL_REJECTED_CALL)
check("reject extern call: has errors",   not r_call.ok)
check("reject extern call: correct msg",
      any("some_extern_fn" in e for e in r_call.errors))


# =============================================================================
print("\n=== Permitted intrinsic call ===\n")
# =============================================================================

r_intr = parse_ll(LL_PERMITTED_INTRINSIC)
check("intrinsic ctpop: ok",         r_intr.ok)
fn_intr = r_intr.functions[0]
calls = [i for b in fn_intr.blocks
         for i in b.instructions if i.opcode == "call"]
check("intrinsic: call parsed",      len(calls) == 1)
check_eq("intrinsic: callee",        calls[0].callee, "llvm.ctpop.i32")


# =============================================================================
print("\n=== alloca / load / store ===\n")
# =============================================================================

r_alloca = parse_ll(LL_ALLOCA)
check("alloca: ok",                  r_alloca.ok)
fn_a = r_alloca.functions[0]
block_a = fn_a.blocks[0]
ops = [i.opcode for i in block_a.instructions]
check("alloca: alloca present",      "alloca" in ops)
check("alloca: store present",       "store"  in ops)
check("alloca: load present",        "load"   in ops)

alloca_instr = [i for i in block_a.instructions if i.opcode == "alloca"][0]
check_eq("alloca: alloc_type",       alloca_instr.alloc_type, "i32")


# =============================================================================
print("\n=== Multi-function module ===\n")
# =============================================================================

r_multi = parse_ll(LL_MULTI_FN)
check("multi: ok",                   r_multi.ok)
check_eq("multi: 2 functions",       len(r_multi.functions), 2)
names = [f.name for f in r_multi.functions]
check("multi: fn1 present",          "fn1" in names)
check("multi: fn2 present",          "fn2" in names)


# =============================================================================
print("\n=== validate_ll convenience function ===\n")
# =============================================================================

errors = validate_ll(LL_ADD)
check("validate: valid source → no errors", len(errors) == 0)

errors2 = validate_ll(LL_REJECTED_GEP)
check("validate: invalid source → errors",  len(errors2) > 0)


# =============================================================================
print("\n=== block() lookup ===\n")
# =============================================================================

r_b = parse_ll(LL_MAX)
fn_b = r_b.functions[0]
check("block lookup: found",      fn_b.block("entry") is not None)
check("block lookup: missing",    fn_b.block("nonexistent") is None)


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
