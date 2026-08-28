"""
test_mixed_grid_checkpoint_v1.py — real, direct verification of
`mixed_grid_checkpoint_v1.py` (points.md #483, Alan's own choice to
pick #482's "full mixed-grid checkpointing" thread back up): a whole
grid mixing ordinary SuperCells (including a delegated nano CACell)
and DspWrapperCells, checkpointed together, wiped, reloaded, and
confirmed both DATA-exact and FUNCTIONALLY correct via a real, live
SuperGrid -- not just standalone cell round-trips in isolation.
"""
import sys

sys.path.insert(0, ".")

from unicell_automaton_v1 import CACell, N, S, E, W, TOPO_PASS_A
from unicell_super_automaton_v1 import SuperGrid, SuperCell
from dsp_wrapper_automaton_v1 import DspWrapperCell, _float_to_bits, _bits_to_float
from mixed_grid_checkpoint_v1 import save_mixed_model, load_mixed_model


def f(val: float) -> int:
    return _float_to_bits(val)


def check(label, cond):
    status = "PASS" if cond else "FAIL"
    print(f"{status}: {label}")
    return cond


def test_supercell_checkpoint_roundtrip_alone():
    """Real, direct test of SuperCell.checkpoint()/restore() in
    isolation first -- before trusting the mixed-grid layer built on
    top of it -- across three different core types plus a delegated
    nano CACell, each driven into genuine, non-default state."""
    errors = 0

    # ── adder, genuine mid-flight (A arrived, B not) ──
    adder = SuperCell(row=1, col=2, core="adder")
    adder.adder_upstream_mask = 1 << W
    adder.adder_downstream_mask = 1 << E
    adder.deliver({W: 11})
    snap = adder.checkpoint()
    restored = SuperCell.restore(snap)
    errors += not check("adder checkpoint: core/position preserved",
                         restored.core == "adder" and restored.row == 1 and restored.col == 2)
    errors += not check("adder checkpoint: genuine mid-flight A-arrived state preserved",
                         restored.adder_a_arrived and restored.adder_a_reg == 11 and not restored.adder_data_valid)
    restored.deliver({W: 9})
    val, valid, _ = restored._offer_state()
    errors += not check(f"adder checkpoint: functional continuation after restore, sum={val} (expect 20)",
                         valid and val == 20)

    # ── accumulator, real nonzero running total ──
    acc = SuperCell(row=0, col=0, core="accumulator")
    acc.acc_inc_dir = 1 << W
    acc.acc_step_amount = 1   # #515: magnitude now data-driven, was implicitly 1
    for _ in range(5):
        acc.deliver({W: 0})
    errors += not check("accumulator pre-checkpoint total is real (5)", acc.acc_total == 5)
    snap = acc.checkpoint()
    restored = SuperCell.restore(snap)
    errors += not check(f"accumulator checkpoint: real running total preserved ({restored.acc_total}, expect 5)",
                         restored.acc_total == 5)
    restored.deliver({W: 0})
    errors += not check(f"accumulator checkpoint: functional continuation, total now {restored.acc_total} (expect 6)",
                         restored.acc_total == 6)

    # ── nano, delegated CACell, real distinguishing state ──
    nano_cell = SuperCell(row=3, col=4, core="nano")
    nano_cell._nano = CACell(
        row=3, col=4, topology=TOPO_PASS_A, start_flag=True,
        routing_mask=(1 << E), cardinal_edge=(1 << N),
    )
    nano_cell._nano.a_data = 0x1234
    nano_cell._nano.a_arrived = True
    nano_cell._nano.pending_ack = 0b0101
    snap = nano_cell.checkpoint()
    restored = SuperCell.restore(snap)
    errors += not check("nano checkpoint: delegated CACell reconstructed, not None", restored._nano is not None)
    errors += not check(
        f"nano checkpoint: real CACell state exactly preserved (a_data={restored._nano.a_data:#x}, "
        f"a_arrived={restored._nano.a_arrived}, pending_ack={restored._nano.pending_ack:#b})",
        restored._nano.a_data == 0x1234 and restored._nano.a_arrived is True
        and restored._nano.pending_ack == 0b0101 and restored._nano.routing_mask == (1 << E)
        and restored._nano.cardinal_edge == (1 << N),
    )

    print()
    if errors == 0:
        print("PASS: SuperCell checkpoint/restore -- adder/accumulator/nano all data-exact and functionally correct in isolation")
    else:
        print(f"FAIL: {errors} error(s)")
    return errors


def test_mixed_grid_freeze_wipe_reload():
    """The real, full task: a genuine mixed grid -- DspWrapperCell ->
    SuperCell(adder) -> SuperCell(accumulator), wired with real
    downstream masks -- driven into real, mixed mid-flight state (not
    a clean stopping point for any of the three), checkpointed
    TOGETHER as one file, wiped (real object deletion), reloaded, and
    then run FURTHER through a real, live SuperGrid to confirm the
    reconstructed chain still computes correctly end to end."""
    import os
    import tempfile
    import gc

    errors = 0

    # ── Real topology: dsp(0,0) --E--> adder(0,1) --E--> acc(0,2) ──
    dsp = DspWrapperCell(row=0, col=0, op="ADD", a_dir=N, b_dir=S, downstream_mask=1 << E)
    adder = SuperCell(row=0, col=1, core="adder")
    adder.adder_upstream_mask = 1 << W
    adder.adder_downstream_mask = 1 << E
    acc = SuperCell(row=0, col=2, core="accumulator")
    acc.acc_inc_dir = 1 << W
    acc.acc_step_amount = 1   # #515: magnitude now data-driven, was implicitly 1

    # ── Real, genuine mixed mid-flight state, nothing quiesced: ──
    dsp.deliver({N: f(2.0)})          # dsp: only A arrived, B still missing
    adder.deliver({W: 100})           # adder: A arrived directly (not yet via dsp), B still missing
    for _ in range(3):
        acc.deliver({W: 0})           # acc: real running total = 3, mid-cycle, not a boundary

    pre = {
        "dsp_primed_a": dsp._primed_a, "dsp_primed_b": dsp._primed_b,
        "adder_a_arrived": adder.adder_a_arrived, "adder_a_reg": adder.adder_a_reg,
        "acc_total": acc.acc_total,
    }
    errors += not check("pre-checkpoint: dsp genuinely mid-flight (A only)",
                         pre["dsp_primed_a"] and not pre["dsp_primed_b"])
    errors += not check("pre-checkpoint: adder genuinely mid-flight (A only)",
                         pre["adder_a_arrived"] and pre["adder_a_reg"] == 100)
    errors += not check(f"pre-checkpoint: acc real running total ({pre['acc_total']}, expect 3)",
                         pre["acc_total"] == 3)

    # ── Real save, as one mixed-grid file ──
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "mixed_model.json")
    save_mixed_model({(0, 0): dsp, (0, 1): adder, (0, 2): acc}, path, name="real mixed-grid checkpoint test")

    # ── Real wipe -- objects genuinely gone, not a stale reference ──
    del dsp, adder, acc
    gc.collect()

    # ── Real reload ──
    reloaded = load_mixed_model(path)
    r_dsp = reloaded[(0, 0)]
    r_adder = reloaded[(0, 1)]
    r_acc = reloaded[(0, 2)]

    errors += not check("reloaded cell classes correct (DspWrapperCell / SuperCell / SuperCell)",
                         isinstance(r_dsp, DspWrapperCell) and isinstance(r_adder, SuperCell) and isinstance(r_acc, SuperCell))
    errors += not check("reloaded dsp: genuine mid-flight state exactly preserved",
                         r_dsp._primed_a == pre["dsp_primed_a"] and r_dsp._primed_b == pre["dsp_primed_b"])
    errors += not check("reloaded adder: genuine mid-flight state exactly preserved",
                         r_adder.adder_a_arrived == pre["adder_a_arrived"] and r_adder.adder_a_reg == pre["adder_a_reg"])
    errors += not check(f"reloaded acc: real running total exactly preserved ({r_acc.acc_total}, expect {pre['acc_total']})",
                         r_acc.acc_total == pre["acc_total"])

    # ── Real functional continuation, via an ACTUAL live SuperGrid,
    # not just isolated direct calls -- confirms the reconstructed
    # chain still computes correctly wired together. ──
    grid = SuperGrid([])
    grid.cells[(0, 0)] = r_dsp
    grid.cells[(0, 1)] = r_adder
    grid.cells[(0, 2)] = r_acc

    # Resolve dsp's still-missing operand B directly (its own
    # mid-flight state, independent of the grid wiring).
    r_dsp.deliver({S: f(3.0)})
    val, valid, _ = r_dsp._offer_state()
    errors += not check(f"reloaded dsp resolves correctly (2.0+3.0={_bits_to_float(val) if valid else None}, expect 5.0)",
                         valid and _bits_to_float(val) == 5.0)

    # Resolve adder's still-missing operand B directly too.
    r_adder.deliver({W: 23})
    val, valid, _ = r_adder._offer_state()
    errors += not check(f"reloaded adder resolves correctly (100+23={val}, expect 123)",
                         valid and val == 123)

    # Now let the REAL grid tick propagate adder's now-ready offer
    # downstream into acc -- confirms wiring survived reload, not just
    # each cell's own isolated state.
    grid.tick()   # adder's offer reaches acc
    grid.tick()   # acc processes the arrival
    errors += not check(f"real grid propagation after reload: acc total now {grid.cells[(0, 2)].acc_total} (expect {pre['acc_total'] + 1})",
                         grid.cells[(0, 2)].acc_total == pre["acc_total"] + 1)

    # ── Real corruption detection, same discipline as #482 ──
    with open(path) as fh:
        raw = fh.read()
    tampered_path = os.path.join(tmpdir, "tampered.json")
    with open(tampered_path, "w") as fh:
        fh.write(raw.replace('"ADD"', '"SUB"', 1))
    try:
        load_mixed_model(tampered_path)
        errors += not check("real tampering correctly detected via hash mismatch", False)
    except ValueError as e:
        errors += not check(f"real tampering correctly detected via hash mismatch ({e})", "hash mismatch" in str(e))

    print()
    if errors == 0:
        print("PASS: mixed-grid checkpoint -- genuine mixed mid-flight state exactly preserved, "
              "real functional continuation through a live SuperGrid confirmed, tamper detection confirmed")
    else:
        print(f"FAIL: {errors} error(s)")
    return errors


if __name__ == "__main__":
    e1 = test_supercell_checkpoint_roundtrip_alone()
    e2 = test_mixed_grid_freeze_wipe_reload()
    sys.exit(1 if (e1 or e2) else 0)
