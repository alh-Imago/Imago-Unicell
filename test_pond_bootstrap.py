"""
test_pond_bootstrap.py — Tests the full ICM-to-pond bootstrap sequence.

Verifies spawn_pond_from_icm():
1. Creates pond with Ward and PTT attached
2. Registers named output ports as TYPE_PRIMITIVE PTT entries
3. Registers sentry cluster per primitive entry
4. Loads cell map with ptt= (wires _ptt_ref, patches sentry addresses)
5. Transitions primitive entries to IDLE (ready to receive inputs)
6. Returns a pond that can actually run the program
"""

import os, json
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ['IMAGO_VERBOSE'] = '0'

from pond import PondManager
from unicell_array import UniCellArray
from pond_ptt import (
    TYPE_PRIMITIVE, TYPE_TILE_IN, TYPE_BRIDGE_INBOUND, TYPE_BRIDGE_OUTBOUND,
    STATUS_IDLE, STATUS_ACTIVE, STATUS_NAMES,
    is_ptt_bus_address,
)

results = []

def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    suffix = f" — {detail}" if detail and not condition else ""
    print(f"  [{status}] {label}{suffix}")


# ── Helper ────────────────────────────────────────────────────────────────────

def make_manager(cells=8192):
    array = UniCellArray(cell_count=cells)
    return PondManager(array)


# ── Test 1: not_gate.icm — simplest case ─────────────────────────────────────

print("\n── not_gate.icm ──")

with open('composer/examples/not_gate.icm') as f:
    icm_not = json.load(f)

mgr = make_manager(512)
pond = mgr.spawn_pond_from_icm(icm_not, owner_id='test')

check("Pond created with correct name", pond.name == 'not_gate')
check("Pond has Ward", pond.ward is not None)
check("Pond has PTT", pond._ptt is not None)
check("Pond has controller", hasattr(pond, '_controller') and pond._controller is not None)
check("Pond has region_id", hasattr(pond, '_region_id') and pond._region_id is not None)
check("Input map populated", 'a' in pond._input_map)
check("Output map populated", 'result' in pond._output_map)

# PTT entries: 2 bridges (INBOUND + OUTBOUND) + 1 input (a) + 1 primitive (result)
entries    = pond._ptt._entries
primitives = [e for e in entries.values() if e.entry_type == TYPE_PRIMITIVE]
inputs_e   = [e for e in entries.values() if e.entry_type == TYPE_TILE_IN]
bridges    = [e for e in entries.values() if e.entry_type in (TYPE_BRIDGE_INBOUND, TYPE_BRIDGE_OUTBOUND)]

check("PTT has 1 primitive entry (one output port)", len(primitives) == 1)
check("PTT has 1 input entry (one input port)", len(inputs_e) == 1,
      f"got {len(inputs_e)}")
check("PTT has 2 bridge entries", len(bridges) == 2)
check("Primitive entry is IDLE", primitives[0].status == STATUS_IDLE,
      f"status={STATUS_NAMES.get(primitives[0].status)}")
check("Input entry is IDLE (waiting for user to supply value)",
      inputs_e[0].status == STATUS_IDLE,
      f"status={STATUS_NAMES.get(inputs_e[0].status)}")
check("Input entry label contains port name",
      'not_gate.a' == inputs_e[0].label)
check("Primitive entry label contains program name",
      'not_gate' in primitives[0].label)
check("Primitive sentry address in PTT bus range",
      is_ptt_bus_address(primitives[0].sentry_address))
check("Primitive sentry address distinct from bridge sentries",
      primitives[0].sentry_address not in {b.sentry_address for b in bridges})
check("pond._input_ptt_indices populated",
      hasattr(pond, '_input_ptt_indices') and 'a' in pond._input_ptt_indices)

# All loaded cells have _ptt_ref
ctrl = pond._controller
rid  = pond._region_id
region = ctrl._regions[rid]
ptt_ref_ok = all(
    getattr(ctrl.array.cells.get(addr), '_ptt_ref', None) is pond._ptt
    for addr in region.cell_addresses
    if ctrl.array.cells.get(addr) is not None
)
check("_ptt_ref wired on all cells", ptt_ref_ok)


# ── Test 2: Run the not_gate ──────────────────────────────────────────────────

print("\n── Run not_gate ──")

a_addr      = pond._input_map['a']
result_addr = pond._output_map['result']

r0 = ctrl.run(rid, inputs={a_addr: 0}, capture_addresses=[result_addr])
r1 = ctrl.run(rid, inputs={a_addr: 1}, capture_addresses=[result_addr])

check("not_gate(0) = 1", r0 is not None and r0.get(result_addr) == 1,
      f"got {r0}")
check("not_gate(1) = 0", r1 is not None and r1.get(result_addr) == 0,
      f"got {r1}")


# ── Test 3: adder_int32.icm — multiple outputs, int32 ────────────────────────

print("\n── adder_int32.icm ──")

with open('composer/examples/adder_int32.icm') as f:
    icm_add = json.load(f)

mgr2 = make_manager(8192)
pond2 = mgr2.spawn_pond_from_icm(icm_add, owner_id='test', cell_count=8192)

check("adder pond created", pond2.name == 'adder_int32')
check("adder has 2 inputs", len(pond2._input_map) == 2)
check("adder has 1 output", len(pond2._output_map) == 1)

primitives2 = [e for e in pond2._ptt._entries.values()
               if e.entry_type == TYPE_PRIMITIVE]
inputs2_e   = [e for e in pond2._ptt._entries.values()
               if e.entry_type == TYPE_TILE_IN]
check("adder PTT has 1 primitive entry", len(primitives2) == 1)
check("adder PTT has 2 input entries (a, b)", len(inputs2_e) == 2,
      f"got {len(inputs2_e)}")
check("adder primitive is IDLE", primitives2[0].status == STATUS_IDLE)
check("adder input entries are IDLE", all(e.status == STATUS_IDLE for e in inputs2_e))


# ── Test 4: Verify adder pond structure — int32 run via compile path ──────────
# Note: adder_int32.icm stores only one named output address (the final bit of
# the 32-address Kogge-Stone output chain). Running it end-to-end requires the
# full 32 output bit-addresses from compile_function, not the single PTT address.
# We verify structural correctness here; functional int32 correctness is covered
# by test_compiler_int32.py.

print("\n── adder_int32 structure (int32 functional test in test_compiler_int32.py) ──")

check("adder controller has loaded region",
      pond2._region_id in pond2._controller._regions)
region2 = pond2._controller._regions[pond2._region_id]
check("adder region has 483 cells (Kogge-Stone)",
      len(region2.cell_addresses) == 483,
      f"got {len(region2.cell_addresses)}")
check("adder PTT primitive entry has correct label",
      primitives2[0].label == 'adder_int32.result')


# ── Test 5: Multiple ponds from same manager ──────────────────────────────────

print("\n── Two ponds from same ICM ──")

with open('composer/examples/mux.icm') as f:
    icm_mux = json.load(f)

mgr3 = make_manager(2048)
p1 = mgr3.spawn_pond_from_icm(icm_mux, owner_id='owner1', name='mux_a')
p2 = mgr3.spawn_pond_from_icm(icm_mux, owner_id='owner2', name='mux_b')

check("Two ponds created with distinct pond_ids",
      p1.pond_id != p2.pond_id)
check("Two ponds have distinct PTT objects",
      p1._ptt is not p2._ptt)
check("Two ponds have distinct controllers",
      p1._controller is not p2._controller)

prims1 = [e for e in p1._ptt._entries.values() if e.entry_type == TYPE_PRIMITIVE]
prims2 = [e for e in p2._ptt._entries.values() if e.entry_type == TYPE_PRIMITIVE]
check("Each mux pond has its own primitive PTT entry",
      len(prims1) >= 1 and len(prims2) >= 1)
# Each pond has its own PTT starting from index 0.
# Bridges take indices 0+1, primitive gets index 2 → ptt_bus_address(2).
# Both ponds correctly get the same logical index within their own PTT —
# they are independent objects so no collision occurs.
check("Each pond's primitive has a registered sentry address",
      is_ptt_bus_address(prims1[0].sentry_address) and
      is_ptt_bus_address(prims2[0].sentry_address)
      if prims1 and prims2 else False)
check("Pond PTTs are independent objects (not shared)",
      p1._ptt is not p2._ptt)


# ── Results ───────────────────────────────────────────────────────────────────

print()
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for status, name in results:
        if status == "FAIL":
            print(f"  [FAIL] {name}")
