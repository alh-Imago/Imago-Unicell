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
from dsp_wrapper_automaton_v1 import DspWrapperCell, compute_real_result, _float_to_bits, _bits_to_float, save_model, load_model
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


def test_watchdog():
    errors = 0

    # ── Real test: disabled by default (threshold=None), never trips ──
    cell = DspWrapperCell(row=0, col=0, op="ADD", a_dir=N, b_dir=S, downstream_mask=1 << 2)
    result = False
    for _ in range(1000):
        result = cell.watchdog_tick()
    errors += not check("watchdog disabled by default: never trips even after 1000 ticks", result == False)

    # ── Real test: trips at EXACTLY the configured tick count, real
    # sustained inactivity, nothing else happening. ──
    cell = DspWrapperCell(row=0, col=0, op="ADD", a_dir=N, b_dir=S, downstream_mask=1 << 2)
    cell.configure_watchdog(10)
    tripped_at = None
    for i in range(1, 21):
        if cell.watchdog_tick():
            tripped_at = i
            break
    errors += not check(f"real watchdog trips at exactly tick {tripped_at} (expect 10)", tripped_at == 10)

    # ── Real test: genuine partial progress (one operand arriving, no
    # full pair) resets the count -- matches #459's own real "patient,
    # don't false-trip on real progress" requirement, same as the RTL. ──
    cell = DspWrapperCell(row=0, col=0, op="ADD", a_dir=N, b_dir=S, downstream_mask=1 << 2)
    cell.configure_watchdog(10)
    for _ in range(6):
        cell.watchdog_tick()   # 6 ticks of real inactivity, not yet tripped
    cell.deliver({N: f(1.0)})   # real partial progress -- only A, never B
    for _ in range(6):
        cell.watchdog_tick()   # 6 MORE ticks -- if reset worked, still not tripped
    errors += not check("real partial progress (one operand) correctly resets the watchdog", not cell.watchdog_timeout)

    # ── Real test: normal operation (both operands arrive, real result
    # drained) never trips a reasonably-set watchdog. ──
    cell = DspWrapperCell(row=0, col=0, op="ADD", a_dir=N, b_dir=S, downstream_mask=1 << 2)
    cell.configure_watchdog(10)
    cell.deliver({N: f(1.0), S: f(2.0)})
    cell.watchdog_tick()
    cell.clear_valid_on_drain()
    for _ in range(5):
        cell.watchdog_tick()
    errors += not check("real, normal operation never false-trips a reasonably-set watchdog", not cell.watchdog_timeout)

    # ── Real test: reconfiguring the SAME instance to a DIFFERENT
    # threshold works correctly -- the real point of it being
    # programmable, not hardcoded (#464's own real design goal). ──
    cell = DspWrapperCell(row=0, col=0, op="ADD", a_dir=N, b_dir=S, downstream_mask=1 << 2)
    cell.configure_watchdog(5)
    for _ in range(5):
        cell.watchdog_tick()
    errors += not check("first real threshold (5) trips correctly", cell.watchdog_timeout)
    cell.configure_watchdog(15)   # real reconfiguration, same instance
    tripped_at = None
    for i in range(1, 21):
        if cell.watchdog_tick():
            tripped_at = i
            break
    errors += not check(f"SAME instance reconfigured to a DIFFERENT threshold (15), real trip at tick {tripped_at} (expect 15)", tripped_at == 15)

    print()
    if errors == 0:
        print("PASS: DspWrapperCell watchdog -- disabled-by-default, exact real tick timing, partial-progress reset, no false-trips, and genuine reconfigurability all confirmed")
    else:
        print(f"FAIL: {errors} error(s)")
    return errors


def test_model_freeze_save_wipe_reload():
    """Real model: two DspWrapperCells, built via direct Python calls
    (no ICM/DSL involved -- that's separate, future compiler work,
    #478). Run it into a genuine MID-FLIGHT state -- not a clean,
    quiescent snapshot -- then freeze/save, wipe (real object
    deletion, not just a stale reference), reload, and confirm the
    reloaded model is functionally identical, not just a data match."""
    import os
    import tempfile

    errors = 0

    # ── Build the real model ──
    add_cell = DspWrapperCell(row=0, col=0, op="ADD", a_dir=N, b_dir=S, downstream_mask=1 << E)
    mul_cell = DspWrapperCell(row=0, col=1, op="MUL", a_dir=W, b_dir=N, downstream_mask=1 << E)
    add_cell.configure_watchdog(50)
    mul_cell.configure_watchdog(50)

    # ── Real, genuine mid-flight state: add_cell has ONE operand
    # captured, not both -- a real, in-progress, unresolved state, not
    # a clean stopping point. mul_cell HOLDS an undrained result. Both
    # watchdogs have real, nonzero counts. ──
    add_cell.deliver({N: f(3.5)})              # only A arrived
    mul_cell.deliver({W: f(4.0), N: f(5.0)})    # both arrived, real result held = 20.0
    for _ in range(7):
        add_cell.watchdog_tick()
        mul_cell.watchdog_tick()

    pre_wipe_state = {
        "add_primed_a": add_cell._primed_a, "add_primed_b": add_cell._primed_b,
        "add_latched_a": add_cell._latched_a, "add_result_valid": add_cell._result_valid,
        "add_wd_count": add_cell.watchdog_count,
        "mul_result": mul_cell._result, "mul_result_valid": mul_cell._result_valid,
        "mul_wd_count": mul_cell.watchdog_count,
    }
    errors += not check("real pre-freeze state: add_cell genuinely mid-flight (A primed, B not)",
                         pre_wipe_state["add_primed_a"] and not pre_wipe_state["add_primed_b"])
    errors += not check(f"real pre-freeze state: mul_cell holds real result={_bits_to_float(pre_wipe_state['mul_result'])} (expect 20.0)",
                         pre_wipe_state["mul_result_valid"] and _bits_to_float(pre_wipe_state["mul_result"]) == 20.0)

    # ── Real freeze and save ──
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "test_model.json")
    save_model({(0, 0): add_cell, (0, 1): mul_cell}, path, name="real freeze/wipe/reload test model")

    # ── Real wipe -- actually delete the Python objects, not just let
    # a stale reference linger. ──
    del add_cell, mul_cell
    import gc
    gc.collect()

    # ── Real reload ──
    reloaded = load_model(path)
    r_add = reloaded[(0, 0)]
    r_mul = reloaded[(0, 1)]

    errors += not check("reloaded add_cell: config matches (op/a_dir/b_dir/downstream_mask)",
                         r_add.op == "ADD" and r_add.a_dir == N and r_add.b_dir == S and r_add.downstream_mask == (1 << E))
    errors += not check("reloaded add_cell: genuine mid-flight state EXACTLY preserved (A primed, B not)",
                         r_add._primed_a == pre_wipe_state["add_primed_a"] and
                         r_add._primed_b == pre_wipe_state["add_primed_b"] and
                         r_add._latched_a == pre_wipe_state["add_latched_a"])
    errors += not check(f"reloaded add_cell: real watchdog count preserved ({r_add.watchdog_count}, expect {pre_wipe_state['add_wd_count']})",
                         r_add.watchdog_count == pre_wipe_state["add_wd_count"])
    errors += not check(f"reloaded mul_cell: real held result preserved ({_bits_to_float(r_mul._result)}, expect 20.0)",
                         r_mul._result_valid == pre_wipe_state["mul_result_valid"] and
                         _bits_to_float(r_mul._result) == _bits_to_float(pre_wipe_state["mul_result"]))

    # ── Real functional continuation -- not just a data match. Feed
    # add_cell's missing operand B and confirm it correctly resolves
    # using the operand A that survived the freeze/wipe/reload. ──
    r_add.deliver({S: f(1.5)})
    val, valid, _ = r_add._offer_state()
    errors += not check(f"reloaded add_cell correctly resolves after its missing operand arrives: {_bits_to_float(val) if valid else None} (expect 5.0 = 3.5+1.5)",
                         valid and _bits_to_float(val) == 5.0)

    # ── Real corruption detection -- tamper with the saved file,
    # confirm load_model() catches it, matching IcmV3File's own real
    # discipline. ──
    with open(path) as fh:
        raw = fh.read()
    tampered_path = os.path.join(tmpdir, "tampered.json")
    with open(tampered_path, "w") as fh:
        fh.write(raw.replace("\"ADD\"", "\"SUB\"", 1))
    try:
        load_model(tampered_path)
        errors += not check("real tampering correctly detected via hash mismatch", False)
    except ValueError as e:
        errors += not check(f"real tampering correctly detected via hash mismatch ({e})", "hash mismatch" in str(e))

    print()
    if errors == 0:
        print("PASS: real model freeze/save/wipe/reload -- genuine mid-flight state exactly preserved, functional continuation confirmed, real tamper detection confirmed")
    else:
        print(f"FAIL: {errors} error(s)")
    return errors


if __name__ == "__main__":
    import sys as _sys
    e1 = main()
    e2 = test_watchdog()
    e3 = test_model_freeze_save_wipe_reload()
    _sys.exit(1 if (e1 or e2 or e3) else 0)
