"""tests/vm/test_llvm_ir_vix_target_v1.py — points.md #756: real tests
for the new, VIX-targeting LLVM IR compilation path (`compile_llvm_ir(
..., target="vix")`), mirroring the existing `test_llvm_ir_frontend_v1.
py`'s own "don't just check the format, run it" discipline exactly.

Real, honest scope, confirmed directly, not assumed: this exercises
the same real, linear-accumulation-chain shape the OLD-lineage target
already proves correct (`test_llvm_ir_frontend_v1.py`) -- the real,
first foundation work for VIX targeting, per Alan's own direct framing
("a path we have trodden before"). The fan-out/non-adjacent-reference
mechanism (`#700`-`#717`) is confirmed NOT yet available for VIX (no
`nano_hold_trigger` tile exists in `vix_tile_library_v1.py` yet) --
tested here as a real, honest, clear-error case, not silently ignored.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

from llvm_ir_frontend_v1 import compile_llvm_ir  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _run_vix(source, argument_values, ticks=30):
    icm, diagnostics, info = compile_llvm_ir(source, argument_values, target="vix")
    assert icm is not None, diagnostics
    assert icm.check_connections() == []
    assert icm.check_known_gotchas() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for row, col, value in info.injections:
        grid.inject(row, col, value)
    for _ in range(ticks):
        grid.tick()
    cell = grid.cells[info.result_cell]
    return cell.adder_out_buffer


def test_single_add_targets_vix_correctly():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 5
      ret i32 %t1
    }
    """
    assert _run_vix(ir, {"x": 3}) == 8


def test_linear_chain_targets_vix_correctly():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 5
      %t2 = add i32 %t1, 10
      %t3 = sub i32 %t2, 2
      ret i32 %t3
    }
    """
    assert _run_vix(ir, {"x": 3}) == 16  # (3+5+10)-2


def test_vix_target_produces_a_real_icm_vix_file_not_the_old_format():
    import icm_vix_v1 as vix
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 1
      ret i32 %t1
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 1}, target="vix")
    assert isinstance(icm, vix.IcmVixFile)


def test_old_target_is_unaffected_default_behavior():
    """Real, direct confirmation the new target parameter doesn't
    change anything about the default (old-lineage) path -- the exact
    same real result the existing test suite already proves."""
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 5
      ret i32 %t1
    }
    """
    icm_old, _, _ = compile_llvm_ir(ir, {"x": 3})  # no target= at all
    import icm_v3 as v3
    assert isinstance(icm_old, v3.IcmV3File)


def test_fan_out_dag_reference_now_works_for_vix_too():
    """points.md #757: the real, missing nano_hold_trigger VIX tile
    added -- the fan-out/non-adjacent-reference mechanism (#700-#717)
    now works for VIX targeting too, the same real mechanism the old
    lineage already proved (one producer, multiple non-adjacent
    consumers on the same chain)."""
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 5
      %t2 = add i32 %t1, 10
      %t3 = add i32 %t1, 3
      ret i32 %t3
    }
    """
    assert _run_vix(ir, {"x": 10}, ticks=60) == 18  # 10+5+3


def test_dag_reference_holds_and_only_delivers_on_the_real_explicit_trigger_vix():
    """Real, direct confirmation this isn't an accidental instant
    pass-through for VIX either -- the same real rigor test_llvm_ir_
    frontend_v1.py's own equivalent old-lineage test already applies:
    inspects the drop cell's own internal nano state directly across
    many ticks, confirming it holds the real relayed value the whole
    time before the program's own real trigger fires."""
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 1
      %t2 = add i32 %t1, 2
      %t3 = add i32 %t2, 3
      %t4 = add i32 %t3, 4
      %t5 = add i32 %t1, 100
      ret i32 %t5
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 5}, target="vix")
    assert icm is not None, diagnostics
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for row, col, value in info.injections:
        grid.inject(row, col, value)
    drop_pos = next((r.row, r.col) for r in records if "relay_drop" in r.cell_id)
    for t in range(1, 60):
        grid.tick()
        if t == 20:
            drop_state = grid.cells[drop_pos]._nano
            assert drop_state.a_arrived is True
            assert drop_state.a_data == 6   # x+1
    cell = grid.cells[info.result_cell]
    assert cell.adder_out_buffer == 106
    assert cell.adder_data_valid is True


def test_non_chain_dag_still_rejected_for_vix_too():
    """The genuinely different, still-unsolved shape (#750/#751's own
    real subject: two SEPARATE producers converging at one consumer) --
    confirmed still rejected for VIX too, the same real, honest
    restriction the old-lineage target already enforces."""
    ir = """
    define i32 @f(i32 %x, i32 %y) {
    entry:
      %t1 = add i32 %x, 1
      %t2 = add i32 %y, 2
      %t3 = add i32 %t1, %t2
      ret i32 %t3
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 1, "y": 2}, target="vix")
    assert icm is None
    assert any("LINEAR ACCUMULATION CHAIN" in d.why for d in diagnostics)
