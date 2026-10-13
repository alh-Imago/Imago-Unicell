"""Ledger #1159: a saved mid-flight state moves between the card (state file) and the VM (FlexGrid) for the LaTeX design, both ways.
Real-card image -> VM runs on to the model's answers; simulated-card images cut at many points (join about to fire, divider 9..32 steps from done) -> VM; VM state -> state file -> simulated card;
a VM state the card cannot express is refused with the reason. Needs iverilog for the simulated-card parts (fails, never skips, without it)."""
import json, os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for d_ in ("tools", "nano"):
    sys.path.insert(0, os.path.join(ROOT, d_))
import pytest, scan_image_v1 as si, vm_state_bridge_v1 as vb  # noqa: E402
K = os.path.join(ROOT, "fpga", "board_tests_scan_latex")
REAL = json.load(open(os.path.join(K, "images", "real_card_cut_3_3_0.state.json")))


def _model(z, n, step):
    out = []
    for _ in range(n):
        z = step(z); out.append(z)
    return out


def test_real_card_state_runs_on_in_the_vm_to_the_models_answers():
    d, notes, drv, outs = vb.run_on(REAL, 8)
    assert outs == _model(REAL["closing"]["word"], 8, eval("lambda z: " + d["step"])) and drv.steps == REAL["closing"]["steps"] + 8


def test_vm_state_file_round_trips_and_is_refused_when_the_card_cannot_hold_it():
    d, sm, r, g, pos, drv, _ = vb.vm_run()
    drv.step()
    st = None
    for _ in range(80):                         # find a tick where the VM state is expressible
        if drv.pending_feed is not None and drv._feed(drv.pending_feed):
            drv.pending_feed = None
        try:
            st = vb.vm_to_state(g, pos, drv, sm, d); break
        except ValueError as e:
            assert "cannot be handed to the card" in str(e)
            g.tick()
    assert st is not None and st["closing"]["steps"] == 1
    raw = si.unpack(st, sm); assert len(bytes.fromhex(raw["image"])) == 256 and raw["layout"] == st["layout"]
    # a VM caught with one operand arrived in the multiplier cannot be written to the card
    d, sm, r, g, pos, drv, _ = vb.vm_run()
    drv.pending_feed = None
    for p in r.result.arg_injections["v_z"][:1]:
        g.cells[p].ram_data_reg, g.cells[p].ram_data_valid = 7, True
    for _ in range(6):
        g.tick()
    with pytest.raises(ValueError) as e:
        vb.vm_to_state(g, pos, drv, sm, d)
    assert "cannot be handed to the card" in str(e.value)


def test_simulated_card_cuts_into_the_vm_and_vm_state_into_the_simulated_card():
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        pytest.fail("iverilog missing: this test must not pass by skipping")
    import board_scan_v1 as v1, board_scan_v2 as b2, scan_host_v2 as h
    from scan_flow_check_v2 import step_fn, Z0
    work = tempfile.mkdtemp()
    try:
        top, files, g, meta = b2.build_files(work, 8, 3000)
        sm = json.load(open(os.path.join(g, "SCAN_MAP.json"))); layout = b2.layout_id(sm)
        c = v1.SimCard(cpb=8, tmo=3000, built=(top, files, g)); card = h.Card(c, design=meta["name"], log=lambda *a: None)
        card.reset(); c.idle(1500)
        seen_join = seen_div = False
        for (k1, lag) in [(3, 2), (4, 12), (5, 30), (5, 40)]:
            card.reset(); c.idle(1500)
            card.configure(2, k1, 0, lag); card.load(Z0); card.wait_stopped()
            ses, img = card.capture_verified()
            st = si.pack(dict(ses=ses, image=img.hex(), cut=[k1, lag, 0], design=meta["name"], layout=layout), sm, meta["formula"])
            d, notes, drv, outs = vb.run_on(st, 5)
            assert outs == _model(st["closing"]["word"], 5, step_fn), (k1, lag)
            seen_join |= any("fired" in n for n in notes); seen_div |= any("finished by the divider" in n for n in notes)
        assert seen_div
        # VM -> state file -> simulated card
        d, sm2, r, gr, pos, drv, _ = vb.vm_run()
        for _ in range(3):
            drv.step()
        drv._feed(drv.pending_feed); drv.pending_feed = None
        for _ in range(10):
            gr.tick()
        st = vb.vm_to_state(gr, pos, drv, sm2, d)
        raw = si.unpack(st, sm)
        tr = h.parse_trailer(bytes.fromhex(raw["image"]))
        card.reset(); c.idle(1500)
        card.configure(2, 4, 3, 0); card.restore(raw["ses"], bytes.fromhex(raw["image"])); card.go()
        q = card.wait_stopped(steps=tr["steps"] + 4)
        assert q["word"] == _model(Z0, q["steps"], step_fn)[-1] and q["held_valid"]
        c.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)
