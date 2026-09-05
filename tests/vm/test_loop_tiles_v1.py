"""
test_loop_tiles_v1.py — points.md #652: the real tile-library
counterpart to `#649`'s own confirmed-working hand-built VM loop-ring.
Proves the exact same #638/#649 topology (LOOPVAR --south--> LOOP_CTRL
--east--> ADDER --north--> RAM_RELAY --west--> LOOPVAR) works entirely
through the STANDARD tile-library pipeline (`super_tile_library.place()`
-> `IcmV3Record` -> `SuperGrid`) -- the same pipeline `compile_program_
ir()`/the LLVM frontend actually consumes -- not hand-built CACell/
SuperCell instances.

Depends on three real fixes made in this same entry, not assumed
already correct:
1. `icm_v3.py`'s nano field table extended with `dynamic_route_en`/
   `pattern_low`/`pattern_equal`/`pattern_high` (confirmed these
   already exist on `unicell_stripped_v1.v` since #49/#51).
2. `TilePort.field` generalized to accept MULTIPLE field names, not
   just one -- `nano_loop_ctrl`'s own `continue_out`/`exit_out` ports
   each set their own dedicated comparator-pattern field AND contribute
   their chosen direction into the shared `routing_mask`, a field
   genuinely DERIVED from two different ports' own independent choices.
2. A real, PRE-EXISTING bug found and fixed in `SuperCell.from_record()`:
   `routing_mask`/`cardinal_edge` were never wrapped in the same `dm()`
   list-to-bitmask normalization every other core's own dir-fields
   already use -- confirmed directly by testing (a tile-placed record
   with `routing_mask=['e']` silently left the CACell holding the raw
   list, not a packed int) before fixing. Never caught before because
   nothing had placed a nano tile through the library and loaded it
   via `SuperGrid`/`from_record()` in the same real path until now.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from super_tile_library_v1 import super_tile_library, place
from unicell_super_automaton_v1 import SuperGrid

results = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")


# =============================================================================
print("=== #638/#649's own real 4-cell bounded loop ring, built entirely through the tile library ===")
# =============================================================================
lv_tile = super_tile_library.get("nano_loop_var")
lc_tile = super_tile_library.get("nano_loop_ctrl")
adder_tile = super_tile_library.get("adder")
ram_tile = super_tile_library.get("ram_flowing")

rec_loopvar = place(lv_tile, 0, 0, {"out": "s"}, cell_id="LOOPVAR")
rec_loop_ctrl = place(lc_tile, 1, 0, {"continue_out": "e", "exit_out": "s"},
                       params={"pattern_low": ["s"]}, cell_id="LOOP_CTRL")
rec_adder = place(adder_tile, 1, 1, {"in_a": "w", "in_b": "s", "out": "n"}, cell_id="ADDER")
rec_ram = place(ram_tile, 0, 1, {"in": "s", "out": "w"}, cell_id="RAM_RELAY")

# Real, confirmed-correct config, matching #638/#649's own hand-verified
# values exactly: routing_mask=6 (E|S), pattern_high=4 (E), pattern_
# equal=pattern_low=2 (S), hold_in=True, dynamic_route_en=True.
grid = SuperGrid([rec_loopvar, rec_loop_ctrl, rec_adder, rec_ram])
loopvar_ca = grid.cells[(0, 0)]._nano
loop_ctrl_ca = grid.cells[(1, 0)]._nano
adder = grid.cells[(1, 1)]
ram_relay = grid.cells[(0, 1)]

check("real tile-built LOOPVAR: hold_in=True, routing_mask=2 (S)",
      loopvar_ca.hold_in is True and loopvar_ca.routing_mask == 2)
check("real tile-built LOOP_CTRL: dynamic_route_en=True, routing_mask=6 (E|S)",
      loop_ctrl_ca.dynamic_route_en is True and loop_ctrl_ca.routing_mask == 6)
check("real tile-built LOOP_CTRL: pattern_high=4 (E), pattern_equal=pattern_low=2 (S)",
      loop_ctrl_ca.pattern_high == 4 and loop_ctrl_ca.pattern_equal == 2 and loop_ctrl_ca.pattern_low == 2)

# Real entry-seed: two arrivals (capture + can_fire), matching #636/#649's
# own established real pattern.
grid.inject(0, 0, 0)
grid.run_to_quiescence()
grid.inject(0, 0, 0xDEADBEEF)
grid.run_to_quiescence()
check("entry-seed: LOOPVAR.a_data=0", loopvar_ca.a_data == 0)
check("entry-seed: LOOP_CTRL has real pending A (i=0) from LOOPVAR's own offer", loop_ctrl_ca.a_arrived)

N_BOUND = 3


def do_round(n_bound):
    grid.inject(1, 0, n_bound)
    grid.run_to_quiescence()

    if not (adder.adder_a_arrived and not loop_ctrl_ca.a_arrived):
        return False

    loopvar_ca.a_update_in = True
    grid.inject(1, 1, 1)   # real constant B=1, standing in for a not-yet-built source
    grid.run_to_quiescence()
    loopvar_ca.a_update_in = False

    loopvar_ca.a_reemit_in = True
    grid.inject(0, 0, 0xFFFFFFFF)   # real "second arrival" trigger, ignored value
    grid.run_to_quiescence()
    loopvar_ca.a_reemit_in = False

    return True


cont = do_round(N_BOUND)
check("round 1: continued (0<3)", cont)
check("round 1: LOOPVAR.a_data=1 via the real tile-library-built ring", loopvar_ca.a_data == 1)

cont = do_round(N_BOUND)
check("round 2: continued (1<3)", cont)
check("round 2: LOOPVAR.a_data=2 via the real tile-library-built ring", loopvar_ca.a_data == 2)

cont = do_round(N_BOUND)
check("round 3: continued (2<3)", cont)
check("round 3: LOOPVAR.a_data=3 via the real tile-library-built ring", loopvar_ca.a_data == 3)

cont = do_round(N_BOUND)
check("round 4: real exit (3==3)", not cont)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
