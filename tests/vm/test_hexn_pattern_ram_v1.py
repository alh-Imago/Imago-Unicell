"""tests/vm/test_hexn_pattern_ram_v1.py -- patterns with RAM routing cells (hexn_ramhold_v1) and the planner's HOLDS, 3 Nov 2026 (Alan 09:50 'apply the ram side'). Generator v6, verify v12, ICM export v3, serial VM v4, planner v18 + bases v10 (RAM cell 171).
A task is planned on a pattern with RAM cells; where the planner uses a hold to ALIGN a two-input core (no FIFO), the hold travels through the program, the ICM v3 file, the unit file and the serial VM, and the RTL must give the same words at the usual -2 offset.
Also: the old export / VM (v2 / v3) silently lose the hold. Requires iverilog."""
import json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_pattern_ref_v8 as R, hexn_pattern_designer_v8 as D, hexn_bases_v10 as B, hexn_pattern_gen_v6 as P, hexn_pattern_verify_v12 as V
import hexn_icm_export_v3 as X, hexn_icm_export_v2 as X2, hexn_unit_file_v1 as U, hexn_vm_v4 as VM, hexn_vm_v3 as VM3, hexn_wrgrid_v18 as G

N = G.Node9
REC = {"lead2": {"n": 7, "counts": {"UN": 2, "AL": 5}, "ram": "lead2"}, "every4": {"n": 7, "counts": {"UN": 2, "AL": 5}, "ram": "every4"}}
TASKS = {
    "scale_offset": ([N("m", "shl", ["x"], k=3), N("y", "add", ["m", "z"])], ["x", "z"], ["y"]),
    "shift_chain_add": ([N("a", "shl", ["x"], k=1), N("b", "shl", ["a"], k=2), N("y", "add", ["b", "z"])], ["x", "z"], ["y"]),
    "shr_shl_xor": ([N("m", "shr", ["x"], k=2), N("n", "shl", ["m"], k=1), N("y", "xor", ["n", "z"])], ["x", "z"], ["y"]),
}
CASES = [("lead2", "scale_offset"), ("lead2", "shift_chain_add"), ("lead2", "shr_shl_xor"), ("every4", "shift_chain_add"), ("every4", "shr_shl_xor")]


def _setup(pat, name):
    rec = REC[pat]; t = TASKS[name]; base = D.make_base(rec); plan = B.fits(base, t); assert plan, (pat, name)
    ref, _ = R.reference(rec, {})
    return rec, t, ref, V.program_for(base, plan)


def test_ram_pattern_generates_hold_cells():
    ref, _ = R.reference(REC["lead2"], {})
    assert not R.check_reference(ref) and len(ref["ram_cells"]) == 14
    top = P.generate(ref)
    assert top.count("hexn_ramhold_v1 #") == 14 and sum(P.widths_of(ref)) == 14 * 22 + 2 * 35 + 7 * 25 + (ref["rows"] * ref["cols"] - 14 - 9) * 12


@pytest.mark.parametrize("pat,name", CASES)
def test_hold_program_matches_reference_and_serial_vm(pat, name):
    rec, t, ref, prog = _setup(pat, name)
    assert prog["holds"], "this task is meant to use a hold"
    assert all(2 <= h["dly"] <= 96 for h in prog["holds"].values())
    assert "aligned" in {c["mode"] for c in prog["cells"].values()}
    icm = X.to_icm(prog, "demo/" + name); unit = U.unit_from_icm(icm, {}, ref["name"], pattern_id=ref["pattern_id"])
    program = X.from_icm(U.unicell_view(unit)[0])
    assert program["holds"] == prog["holds"]
    vm = VM.SerialVM.load(icm)
    for seed in (3, 4):
        rnd = random.Random(seed); iv = {n: rnd.randrange(1 << 32) for n in t[1]}
        got = V.sim_run(ref, program, iv, extra_clocks=200)
        want = G.ref9(t[0], iv); cap = vm.run(iv)
        for o in t[2]:
            assert [w for _, w in got["out"][o]] == [w for _, w in cap[o]] == want[o][1], (pat, name, seed)
            assert [tk for tk, _ in got["out"][o]] == [tk - 2 for tk, _ in cap[o]], (pat, name, seed)


def test_old_export_and_vm_lose_the_hold():
    """the bug this version fixes, kept as a record: v2 export / v3 VM have no holds, so the VM output differs from the reference"""
    rec, t, ref, prog = _setup("lead2", "scale_offset")
    icm2 = X2.to_icm(prog, "demo/old")
    assert "holds" not in X2.from_icm(icm2)
    rnd = random.Random(3); iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    cap = VM3.SerialVM.load(icm2).run(iv); want = G.ref9(t[0], iv)
    assert [w for _, w in cap["y"]] != want["y"][1]


def test_second_hold_in_a_cell_and_hold_on_bare_cell_are_refused():
    rec, t, ref, prog = _setup("lead2", "scale_offset")
    bad = json.loads(json.dumps(prog)); bad["holds"]["0,0"] = dict(out="E", dly=5)           # (0,0) is a work-free routing cell in the pattern but not a RAM column: bare cell
    program = X.from_icm(X.to_icm(bad, "demo/bad"))
    with pytest.raises(ValueError, match="bare routing cell"): P.load_words(ref, program)
    worse = json.loads(json.dumps(prog)); k = next(iter(worse["holds"])); worse["holds"][k]["dly"] = 200
    with pytest.raises(ValueError, match="out of range"): X.to_icm(worse, "demo/worse")


@pytest.mark.parametrize("pat", ["lead2", "every4"])
def test_committed_pnr_records_verify_the_ram_references(pat):
    reg = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/registry.json")))
    ref, _ = R.reference(REC[pat] if False else dict(REC[pat], counts={"UN": 2, "AL": 7}), reg)
    n = "%s_%s" % (ref["name"], ref["pattern_id_hex"])
    rec = json.load(open(os.path.join(ROOT, "docs/hex-n/data/pnr/%s.pnr.json" % n)))
    fil = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/%s.json" % n)))
    assert fil["content_hash"] == ref["content_hash"] and V.verified(fil, rec) and abs(rec["deviation_pct"]) <= 10 and rec["fmax_mhz"] >= 27


def test_ram_cost_in_bases_v10():
    assert B.RAM_COST == 171
