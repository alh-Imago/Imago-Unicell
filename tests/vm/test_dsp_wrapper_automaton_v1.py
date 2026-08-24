"""
test_dsp_wrapper_automaton_v1.py — real, direct verification of
DspWrapperCell (points.md #479's own first real VM-side piece):
genuine IEEE-754 correctness, real two-port capture (both arrival
orders), the real offer/drain/re-arm protocol, and real integration
into a live SuperGrid alongside ordinary SuperCells.
"""
import struct
import sys

sys.path.insert(0, ".")

from unicell_automaton_v1 import N, S, E, W
from dsp_wrapper_automaton_v1 import DspWrapperCell, compute_real_result, _float_to_bits, _bits_to_float
from unicell_super_automaton_v1 import SuperGrid, SuperCell


def f(val: float) -> int:
    return _float_to_bits(val)


def check(label, cond):
    status = "PASS" if cond else "FAIL"
    print(f"{status}: {label}")
    return cond


def main():
    errors = 0

    # ── Real test 1: genuine IEEE-754 correctness, not a placeholder ──
    result = compute_real_result("ADD", f(2.5), f(1.25))
    errors += not check(f"real ADD: 2.5+1.25={_bits_to_float(result)} (expect 3.75)", _bits_to_float(result) == 3.75)

    result = compute_real_result("SUB", f(10.0), f(3.0))
    errors += not check(f"real SUB: 10.0-3.0={_bits_to_float(result)} (expect 7.0)", _bits_to_float(result) == 7.0)

    result = compute_real_result("MUL", f(6.0), f(7.0))
    errors += not check(f"real MUL: 6.0*7.0={_bits_to_float(result)} (expect 42.0)", _bits_to_float(result) == 42.0)

    result = compute_real_result("GE", f(5.0), f(3.0))
    errors += not check(f"real GE: 5.0>=3.0 -> {result} (expect 1)", result == 1)
    result = compute_real_result("GE", f(1.0), f(3.0))
    errors += not check(f"real GE: 1.0>=3.0 -> {result} (expect 0)", result == 0)

    # ── Real test 2: direct DspWrapperCell, operand A arrives first ──
    cell = DspWrapperCell(row=0, col=0, op="ADD", a_dir=N, b_dir=S, downstream_mask=1 << 2)
    cell.deliver({N: f(1.5)})
    val, valid, _ = cell._offer_state()
    errors += not check("A-first: not valid until B arrives", not valid)
    cell.deliver({S: f(2.5)})
    val, valid, dmask = cell._offer_state()
    errors += not check(f"A-first: real result={_bits_to_float(val)} (expect 4.0), valid={valid}",
                         valid and _bits_to_float(val) == 4.0)

    # ── Real test 3: re-arm after drain, opposite arrival order ──
    cell.pending_ack = 0  # simulate a real drain
    cell.clear_valid_on_drain()
    val, valid, _ = cell._offer_state()
    errors += not check("re-armed: not valid immediately after drain", not valid)
    cell.deliver({S: f(10.0)})   # B arrives first this time
    cell.deliver({N: f(5.0)})    # then A
    val, valid, _ = cell._offer_state()
    errors += not check(f"B-first: real result={_bits_to_float(val)} (expect 15.0), valid={valid}",
                         valid and _bits_to_float(val) == 15.0)

    # ── Real test 4: full integration into a live SuperGrid alongside
    # an ordinary SuperCell, using the SAME tick() loop unmodified. ──
    grid = SuperGrid([])
    dsp = DspWrapperCell(row=0, col=0, op="MUL", a_dir=N, b_dir=S, downstream_mask=1 << 2)  # offers East
    ram = SuperCell(row=0, col=1, core="ram")
    ram.ram_upstream_mask = 1 << 3   # listens West (where the DSP wrapper's East output arrives)
    ram.ram_downstream_mask = 0
    grid.cells[(0, 0)] = dsp
    grid.cells[(0, 1)] = ram

    grid.inject(0, 0, f(3.0))          # arrives with no direction -- goes to `injected`, not a/b path
    # DspWrapperCell doesn't handle `injected` (real RTL has no such
    # path either -- only real cardinal a/b arrivals) -- confirm it's a
    # safe no-op, not a crash.
    grid.tick()
    val, valid, _ = dsp._offer_state()
    errors += not check("DspWrapperCell safely ignores injected (no a/b direction), doesn't crash or false-fire", not valid)

    grid._pending.clear()
    grid._pending[(0, 0)] = [(None, N, f(4.0)), (None, S, f(5.0))]
    grid.tick()   # DSP wrapper captures both operands and offers, in the same tick
    grid.tick()   # RAM cell receives the now-pending offer -- matches every other single-shot core's own real, same two-tick shape
    val, valid, _ = ram._offer_state()
    errors += not check(f"real grid integration: DSP wrapper (MUL) -> RAM cell, real result={_bits_to_float(val) if valid else None} (expect 20.0)",
                         valid and _bits_to_float(val) == 20.0)

    print()
    if errors == 0:
        print("PASS: DspWrapperCell -- real IEEE-754 correctness, both arrival orders, re-arm, and full real SuperGrid integration all confirmed")
    else:
        print(f"FAIL: {errors} error(s)")
    return errors


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(1 if main() else 0)
