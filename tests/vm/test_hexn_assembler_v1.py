"""tests/vm/test_hexn_assembler_v1.py -- the Hex-N ASSEMBLER and a FULL END-TO-END RUN in simulation (3 Nov 2026, Alan 10:07). A pattern reference is assembled into a card design (pattern + crossing + UART frame); a unit file is turned into the config image; the design is
driven through its UART like a PC would: identify, wipe, load the program, present PARALLEL words, read back the log of PARALLEL words WITH TICKS. The words must equal the serial VM's, and each tick must equal the VM's tick + 32 (a constant: -2 serial offset, +33 crossing, +1 frame
log; each measured separately). Requires iverilog."""
import json, os, random, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pytest
import test_hexn_pattern_prsq_v1 as T
import hexn_assemble_v1 as A, hexn_card_sim_v1 as S, hexn_icm_export_v3 as X, hexn_unit_file_v1 as U, hexn_vm_v4 as VM, hexn_wrgrid_v19 as G

REF = T.REF
OFFSET = 32


@pytest.fixture(scope="module")
def card():
    d = tempfile.mkdtemp(prefix="asm_")
    rec = A.assemble(REF, d)
    yield d, rec
    shutil.rmtree(d, ignore_errors=True)


def _unit(t, name):
    prog = T._program(t); icm = X.to_icm(prog, "demo/" + name)
    unit = U.unit_from_icm(icm, {}, REF["name"], pattern_id=REF["pattern_id"])
    return icm, unit


def _run(card_dir, unit, t, iv, wipe_first=True):
    program = X.from_icm(unit["program"]); img = A.chain_image(REF, program); rows = program["pads_in"]
    cmds = [("I",)] + ([("W",)] if wipe_first else []) + [("B", img)] + [("D", rows[n][0], iv[n]) for n in t[1]] + [("G", sum(1 << rows[n][0] for n in t[1])), ("wait", 600), ("L",)]
    return S.CardSim(card_dir, 8).run(cmds)


def test_assembly_record_and_files(card):
    d, rec = card
    assert rec["pattern_id_hex"] == REF["pattern_id_hex"] and rec["chain_bits"] == sum(A.P.widths_of(REF)) and rec["rows"] == 7
    for f in ("hexn.cst", "synth.ys", "build.sh", "ASSEMBLY.json", "src/hexn_card_top.v", "src/hexn_pattern_top.v", "src/hexn_frame_v1.v", "src/hexn_tile_pr_v1.v"):
        assert os.path.exists(os.path.join(d, f)), f
    cst = open(os.path.join(d, "hexn.cst")).read()
    assert 'IO_LOC "clk" 4;' in cst and 'IO_LOC "uart_tx" 69;' in cst and 'IO_LOC "uart_rx" 70;' in cst
    assert "32'h%s" % REF["pattern_id_hex"] in open(os.path.join(d, "src/hexn_card_top.v")).read()


def test_assembler_refuses_a_broken_reference():
    bad = json.loads(json.dumps(REF)); bad["work_cells"][0]["type"] = "XX"
    with pytest.raises(ValueError): A.assemble(bad, tempfile.mkdtemp(prefix="asm_bad_"))


def test_unit_checks_against_the_design():
    t = T.TASKS["strict_xyz"]; icm, unit = _unit(t, "chk")
    assert A.check_unit_for(REF, unit) == []
    other = U.unit_from_icm(icm, {}, "J9_7", pattern_id=0x17000001)
    pr = A.check_unit_for(REF, other); assert any("pattern" in p for p in pr)


@pytest.mark.parametrize("name", ["strict_xyz", "weighted", "sequenced_yxz"])
def test_end_to_end_through_the_uart_matches_serial_vm(card, name):
    d, rec = card; t = T.TASKS[name]; icm, unit = _unit(t, name)
    rnd = random.Random(11); iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    r = _run(d, unit, t, iv)
    assert r[0] == dict(pattern_id=REF["pattern_id"], rows=7) and r[1] == b"K" and r[2] == b"K"
    cap = VM.SerialVM.load(icm).run(iv)["p"]
    got = r[-1]
    assert [w for _, w, _ in got] == [w for _, w in cap] and got, (got, cap)
    assert [tk for _, _, tk in got] == [tk + OFFSET for tk, _ in cap]


def test_wipe_then_second_program_gives_a_clean_run(card):
    d, rec = card; t1 = T.TASKS["strict_xyz"]; t2 = T.TASKS["sequenced_yxz"]
    icm1, u1 = _unit(t1, "a"); icm2, u2 = _unit(t2, "b"); rnd = random.Random(2)
    iv1 = {n: rnd.randrange(1 << 32) for n in t1[1]}; iv2 = {n: rnd.randrange(1 << 32) for n in t2[1]}
    p1, p2 = X.from_icm(u1["program"]), X.from_icm(u2["program"])
    cmds = [("W",), ("B", A.chain_image(REF, p1))] + [("D", p1["pads_in"][n][0], iv1[n]) for n in t1[1]] + [("G", sum(1 << p1["pads_in"][n][0] for n in t1[1])), ("wait", 600), ("L",)]
    cmds += [("W",), ("B", A.chain_image(REF, p2))] + [("D", p2["pads_in"][n][0], iv2[n]) for n in t2[1]] + [("G", sum(1 << p2["pads_in"][n][0] for n in t2[1])), ("wait", 600), ("L",)]
    r = S.CardSim(d, 8).run(cmds)
    cap2 = VM.SerialVM.load(icm2).run(iv2)["p"]
    assert [w for _, w, _ in r[-1]] == [w for _, w in cap2] and len(r[-1]) == 3
    assert len([e for e in r if isinstance(e, list)]) == 2 and len(r[[i for i, e in enumerate(r) if isinstance(e, list)][0]]) == 3
