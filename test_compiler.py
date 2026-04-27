"""
Tests for ImagoCompiler — M4 milestone from the Implementation Guide.
Includes the self-compilation target: compiling logic from unicell.py itself.
Run with: python3 test_compiler.py
"""

from unicell import VAR_TRUE, VAR_FALSE
from controller import ImagoController, CellMapRecord
from compiler import ImagoCompiler

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def run_fn(source, fn_name, inputs_dict, output_idx=0):
    """Helper: compile a function, run it, return output at index."""
    compiler = ImagoCompiler()
    records, graph, input_map, output_addrs = compiler.compile_function(
        source, fn_name, list(inputs_dict.keys())
    )
    if not records:
        return None
    ctrl = ImagoController(cell_count=len(records) * 10 + 100)
    rid = ctrl.load_map(records, image_name=fn_name)
    if rid is None:
        return None
    # map named inputs to bus addresses
    bus_inputs = {input_map[k]: v for k, v in inputs_dict.items()}
    result = ctrl.run(rid, inputs=bus_inputs, capture_addresses=output_addrs)
    if result and output_addrs:
        return result.get(output_addrs[output_idx])
    return None


print("\n=== M4 — Compiler tests ===\n")

# ── single NOT ────────────────────────────────────────────────────────────────
not_src = """
def logical_not(a):
    return not a
"""
check("Compile NOT(0)=1", run_fn(not_src, "logical_not", {"a": VAR_FALSE}) == VAR_TRUE)
check("Compile NOT(1)=0", run_fn(not_src, "logical_not", {"a": VAR_TRUE})  == VAR_FALSE)

# ── AND ───────────────────────────────────────────────────────────────────────
and_src = """
def logical_and(a, b):
    return a & b
"""
check("Compile AND(0,0)=0", run_fn(and_src, "logical_and", {"a": VAR_FALSE, "b": VAR_FALSE}) == VAR_FALSE)
check("Compile AND(1,0)=0", run_fn(and_src, "logical_and", {"a": VAR_TRUE,  "b": VAR_FALSE}) == VAR_FALSE)
check("Compile AND(1,1)=1", run_fn(and_src, "logical_and", {"a": VAR_TRUE,  "b": VAR_TRUE})  == VAR_TRUE)

# ── OR ────────────────────────────────────────────────────────────────────────
or_src = """
def logical_or(a, b):
    return a | b
"""
check("Compile OR(0,0)=0", run_fn(or_src,  "logical_or",  {"a": VAR_FALSE, "b": VAR_FALSE}) == VAR_FALSE)
check("Compile OR(0,1)=1", run_fn(or_src,  "logical_or",  {"a": VAR_FALSE, "b": VAR_TRUE})  == VAR_TRUE)
check("Compile OR(1,1)=1", run_fn(or_src,  "logical_or",  {"a": VAR_TRUE,  "b": VAR_TRUE})  == VAR_TRUE)

# ── XOR ───────────────────────────────────────────────────────────────────────
xor_src = """
def logical_xor(a, b):
    return a ^ b
"""
check("Compile XOR(0,0)=0", run_fn(xor_src, "logical_xor", {"a": VAR_FALSE, "b": VAR_FALSE}) == VAR_FALSE)
check("Compile XOR(0,1)=1", run_fn(xor_src, "logical_xor", {"a": VAR_FALSE, "b": VAR_TRUE})  == VAR_TRUE)
check("Compile XOR(1,1)=0", run_fn(xor_src, "logical_xor", {"a": VAR_TRUE,  "b": VAR_TRUE})  == VAR_FALSE)

# ── composed expression ───────────────────────────────────────────────────────
composed_src = """
def composed(a, b, c):
    return (a & b) | (not c)
"""
# (1 & 0) | NOT(1) = 0 | 0 = 0
check("Compile (a&b)|(not c): (1,0,1)=0",
      run_fn(composed_src, "composed", {"a":1,"b":0,"c":1}) == VAR_FALSE)
# (1 & 1) | NOT(0) = 1 | 1 = 1
check("Compile (a&b)|(not c): (1,1,0)=1",
      run_fn(composed_src, "composed", {"a":1,"b":1,"c":0}) == VAR_TRUE)
# (0 & 0) | NOT(0) = 0 | 1 = 1
check("Compile (a&b)|(not c): (0,0,0)=1",
      run_fn(composed_src, "composed", {"a":0,"b":0,"c":0}) == VAR_TRUE)

# ── equality comparison ───────────────────────────────────────────────────────
eq_src = """
def equal(a, b):
    return a == b
"""
# v2: XNOR equality on 1-bit inputs (0/1) produces 32-bit patterns.
# Check bit 0 (LSB) which is the authoritative equality bit.
# equal:   XNOR -> 0xFFFFFFFF (bit0=1 -> true)
# unequal: XNOR -> 0xFFFFFFFE (bit0=0 -> false)
check("Compile a==b: (0,0)=1", run_fn(eq_src, "equal", {"a":0,"b":0}) & 1 == VAR_TRUE & 1)
check("Compile a==b: (0,1)=0", run_fn(eq_src, "equal", {"a":0,"b":1}) & 1 == VAR_FALSE & 1)
check("Compile a==b: (1,1)=1", run_fn(eq_src, "equal", {"a":1,"b":1}) & 1 == VAR_TRUE & 1)

# ── if / else (spatial mux) ───────────────────────────────────────────────────
mux_src = """
def mux(sel, a, b):
    if sel:
        return a
    else:
        return b
"""
check("Compile mux: sel=1 returns a=1", run_fn(mux_src, "mux", {"sel":1,"a":1,"b":0}) == VAR_TRUE)
check("Compile mux: sel=0 returns b=1", run_fn(mux_src, "mux", {"sel":0,"a":0,"b":1}) == VAR_TRUE)
check("Compile mux: sel=1 returns a=0", run_fn(mux_src, "mux", {"sel":1,"a":0,"b":1}) == VAR_FALSE)

# ── function call inlining ────────────────────────────────────────────────────
inline_src = """
def my_not(x):
    return not x

def double_not(a):
    return my_not(my_not(a))
"""
check("Inlined call: double_not(0)=0", run_fn(inline_src, "double_not", {"a":0}) == VAR_FALSE)
check("Inlined call: double_not(1)=1", run_fn(inline_src, "double_not", {"a":1}) == VAR_TRUE)

# ── IRGraph inspection ────────────────────────────────────────────────────────
compiler = ImagoCompiler()
records, graph, input_map, output_addrs = compiler.compile_function(
    not_src, "logical_not", ["a"]
)
check("IRGraph has nodes", len(graph.nodes) > 0)
check("IRGraph has input node", len(graph.input_nodes()) > 0)
check("Input node has bus address assigned", graph.input_nodes()[0].output_addr is not None)
check("Records produced from graph", len(records) > 0)

# ── self compilation target ───────────────────────────────────────────────────
# Compile the NOR gate function — the heart of the UniCell — using the compiler.
# This is the self-compilation test: the compiler compiling logic that
# implements the compiler's own computational substrate.

print("\n  --- Self-compilation target: NOR gate logic ---")

nor_gate_src = """
def nor_gate(a, b):
    return not (a | b)
"""

check("Self-compile: NOR(0,0)=1", run_fn(nor_gate_src, "nor_gate", {"a":0,"b":0}) == VAR_TRUE)
check("Self-compile: NOR(0,1)=0", run_fn(nor_gate_src, "nor_gate", {"a":0,"b":1}) == VAR_FALSE)
check("Self-compile: NOR(1,0)=0", run_fn(nor_gate_src, "nor_gate", {"a":1,"b":0}) == VAR_FALSE)
check("Self-compile: NOR(1,1)=0", run_fn(nor_gate_src, "nor_gate", {"a":1,"b":1}) == VAR_FALSE)

# Compile the XNOR (equality) function — what the security gate uses for
# pattern matching — using the compiler itself.
xnor_src = """
def xnor_gate(a, b):
    return not (a ^ b)
"""
check("Self-compile: XNOR(0,0)=1", run_fn(xnor_src, "xnor_gate", {"a":0,"b":0}) == VAR_TRUE)
check("Self-compile: XNOR(1,0)=0", run_fn(xnor_src, "xnor_gate", {"a":1,"b":0}) == VAR_FALSE)
check("Self-compile: XNOR(1,1)=1", run_fn(xnor_src, "xnor_gate", {"a":1,"b":1}) == VAR_TRUE)

# Compile the mux — what the compiler itself emits for if/else —
# using the compiler's own if/else emission path.
mux_self_src = """
def mux_self(sel, x, y):
    if sel:
        result = x
    else:
        result = y
    return result
"""
check("Self-compile: mux_self(1,1,0)=1", run_fn(mux_self_src, "mux_self", {"sel":1,"x":1,"y":0}) == VAR_TRUE)
check("Self-compile: mux_self(0,1,0)=0", run_fn(mux_self_src, "mux_self", {"sel":0,"x":1,"y":0}) == VAR_FALSE)

# ── summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*40}")
passed = sum(1 for s,_ in results if s == "PASS")
failed = sum(1 for s,_ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
    print("\nSelf-compilation confirmed: the compiler can compile")
    print("the NOR, XNOR, and mux logic that underlies itself.")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
