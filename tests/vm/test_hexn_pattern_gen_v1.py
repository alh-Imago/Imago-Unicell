"""tests/vm/test_hexn_pattern_gen_v1.py -- the pattern generator and its verification (tools/hexn_pattern_gen_v1.py, hexn_pattern_verify_v1.py), 3 Nov 2026.
A unary pattern (7 x 7, 9 UN tiles + 40 bare routing cells) is generated from its REFERENCE FILE; programs planned on it are written as unit files and loaded onto the generated RTL through the mixed-width chain; output words must equal the planner's
reference and the serial VM's, at the fixed 2-tick offset. Also: unsupported work types / RAM cells are refused by name; the verification record is tied to the reference's ID and hash. Requires iverilog (place and route is in test_hexn_pattern_pnr_v1.py)."""
import copy, json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_pattern_ref_v2 as R, hexn_pattern_designer_v2 as D, hexn_bases_v4 as B4, hexn_pattern_gen_v1 as P, hexn_pattern_verify_v1 as V
import hexn_icm_export_v2 as X, hexn_unit_file_v1 as U, hexn_vm_v2 as VM, hexn_wrgrid_v13 as G

N = G.Node9
RECIPE = {"n": 7, "counts": {"UN": 9}, "ram": "none"}
TASKS = {
    "shl_shr_cp": ([N("m", "shl", ["x"], k=3), N("n", "shr", ["m"], k=2), N("y", "cp", ["n"])], ["x"], ["y"]),
    "five_chain": ([N("a", "cp", ["x"]), N("b", "shl", ["a"], k=1), N("c", "shl", ["b"], k=2), N("d", "shr", ["c"], k=3), N("y", "cp", ["d"])], ["x"], ["y"]),
    "two_streams": ([N("a", "shl", ["x"], k=4), N("b", "shr", ["z"], k=7)], ["x", "z"], ["a", "b"]),
}
REF, _ = R.reference(RECIPE, {})


def _program(name):
    t = TASKS[name]; base = D.make_base(RECIPE); plan = B4.fits(base, t); assert plan, name
    return t, V.program_for(base, plan)


def test_reference_and_generated_top():
    assert not R.check_reference(REF) and REF["counts"] == {"work": 9, "ram": 0, "routing": 40}
    top = P.generate(REF)
    assert top.count("hexn_tile_v2 #") == 9 and top.count("hexn_rcore_flag_v2 #") == 40 and REF["pattern_id_hex"] in top
    assert sum(P.widths_of(REF)) == 9 * 35 + 40 * 12


def test_unsupported_types_and_ram_are_refused_by_name():
    ref, _ = R.reference({"n": 7, "counts": {"JN": 3, "UN": 1}, "ram": "none"}, {})
    with pytest.raises(ValueError, match="AL|JN"): P.generate(ref)
    ref, _ = R.reference({"n": 7, "counts": {"UN": 9}, "ram": "lead2"}, {})
    with pytest.raises(ValueError, match="RAM"): P.generate(ref)


@pytest.mark.parametrize("name", list(TASKS))
def test_program_on_generated_pattern_matches_reference_and_serial_vm(name):
    t, prog = _program(name)
    icm = X.to_icm(prog, "demo/" + name); unit = U.unit_from_icm(icm, {}, REF["name"], pattern_id=REF["pattern_id"])
    program = X.from_icm(U.unicell_view(unit)[0])
    vm = VM.SerialVM.load(icm); rnd = random.Random(4)
    iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    got = V.sim_run(REF, program, iv)
    want = G.ref9(t[0], iv); cap = vm.run(iv)
    assert got["chain_bits"] == 9 * 35 + 40 * 12
    for o in t[2]:
        assert [w for _, w in got["out"][o]] == [w for _, w in cap[o]] == want[o][1]
        assert [tk for tk, _ in got["out"][o]] == [tk - 2 for tk, _ in cap[o]]


def test_work_cell_on_a_bare_routing_position_is_refused():
    t, prog = _program("shl_shr_cp")
    prog = copy.deepcopy(prog); k = next(iter(prog["cells"])); c = prog["cells"].pop(k); r, col = map(int, k.split(",")); prog["cells"]["%d,%d" % (r, col + 1)] = c
    with pytest.raises(ValueError, match="bare routing cell|tile has only"): P.load_words(REF, X.from_icm(X.to_icm(prog, "bad")))


def test_verification_record_is_tied_to_the_reference():
    rec = dict(format="hexn-pnr-v1", pattern_id=REF["pattern_id"], content_hash=REF["content_hash"], verdict="PASS")
    assert V.verified(REF, rec)
    assert not V.verified(REF, dict(rec, verdict="FAIL"))
    assert not V.verified(REF, dict(rec, pattern_id=REF["pattern_id"] + 1))
    other, _ = R.reference({"n": 9, "counts": {"UN": 16}, "ram": "none"}, {})
    assert not V.verified(other, rec)
    tampered = dict(REF, rows=9)
    assert not V.verified(tampered, rec)
