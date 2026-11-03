"""tests/vm/test_hexn_tilegrid_v1.py -- a grid of Hex-N tiles loaded from a UNIT FILE (sub/verilog/hexn_tilegrid_v1.v + tools/hexn_tilegrid_load_v1.py), simulated with iverilog.
Unary-core programs only (the tile has only that core): planned on a base by the existing planner, written to a unit file, loaded onto the grid through ONE config chain, then data words in on the west lane.
Checks: the output WORD equals the planner's reference; the output arrives exactly TWO ticks before the serial VM says, for every program and path length (a fixed bookkeeping offset: the model injects bit 0 at its tick 1 and stamps an output one tick after it is registered; the path timing itself is identical, which needed the tile's core result to go to the faces straight from the core register, tile v2); weights in the unit are never read; a damaged unit, a program with a non-unary core and a pad off the west/east edge are refused. Requires iverilog."""
import copy, json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_bases_v2 as B, hexn_icm_export_v2 as X, hexn_unit_file_v1 as U, hexn_tilegrid_load_v1 as L, hexn_vm_v2 as V

N = B.G.Node9
TASKS = {
    "shl_shr_cp": ([N("m", "shl", ["x"], k=3), N("n", "shr", ["m"], k=2), N("y", "cp", ["n"])], ["x"], ["y"]),
    "shr_shl": ([N("m", "shr", ["x"], k=5), N("y", "shl", ["m"], k=1)], ["x"], ["y"]),
    "five_chain": ([N("a", "cp", ["x"]), N("b", "shl", ["a"], k=1), N("c", "shl", ["b"], k=2), N("d", "shr", ["c"], k=3), N("y", "cp", ["d"])], ["x"], ["y"]),
    "two_streams": ([N("a", "shl", ["x"], k=4), N("b", "shr", ["z"], k=7)], ["x", "z"], ["a", "b"]),
}
M32 = 0xFFFFFFFF


def _unit(name, weights=None):
    t = TASKS[name]; b = B.tailored(t); P = B.fits(b, t)
    icm = X.to_icm(B.program_of(b, P, t), "demo/" + name)
    return t, icm, U.unit_from_icm(icm, weights or {}, "demo")


@pytest.mark.parametrize("name", list(TASKS))
def test_unit_file_onto_tile_grid_matches_reference_and_serial_vm(name):
    t, icm, unit = _unit(name)
    tw = L.tile_words(L.program_of(unit))
    vm = V.SerialVM.load(icm); rnd = random.Random(3)
    for _ in range(2):
        iv = {n: rnd.randrange(1 << 32) for n in t[1]}
        want = B.G.ref9(t[0], iv)
        got = L.rtl_run(tw, iv)["out"]
        cap = vm.run(iv)
        for o in t[2]:
            assert [w for _, w in got[o]] == [w for _, w in cap[o]] == want[o][1], (name, o)
            assert [tk for tk, _ in got[o]] == [tk - 2 for tk, _ in cap[o]], (name, o, got[o], cap[o])


def test_weights_in_the_unit_are_never_read_and_do_not_change_the_result():
    t, icm, unit = _unit("shr_shl", weights={"judge_a": {"w": [1, 2, 3]}})
    assert L.tile_words(L.program_of(unit))["words"] == L.tile_words(L.program_of(_unit("shr_shl")[2]))["words"]
    # the adapter path never touches the weights part: even a mangled weights payload does not stop the program loading as long as the program part is intact
    u2 = copy.deepcopy(unit); u2["weights"] = "not even json objects"
    assert L.program_of(u2)["cells"]


def test_refusals():
    t, icm, unit = _unit("shl_shr_cp")
    bad = copy.deepcopy(unit); bad["program"]["name"] = "tampered"
    with pytest.raises(ValueError, match="refused"): L.program_of(bad)
    # a program with a non-unary core (add) is refused by cell name
    t2 = B.all_tasks()["old/scale_offset"]; b = B.tailored(t2); P = B.fits(b, t2)
    p = X.from_icm(X.to_icm(B.program_of(b, P, t2), "x"))
    with pytest.raises(ValueError, match="unary core"): L.tile_words(p)
    # a pad off the edge is refused
    p = X.from_icm(icm); k = next(iter(p["pads_in"])); p["pads_in"][k] = [1, 2]
    with pytest.raises(ValueError, match="west edge"): L.tile_words(p)


def test_chain_length_is_tiles_times_35():
    t, icm, unit = _unit("shl_shr_cp")
    tw = L.tile_words(L.program_of(unit))
    assert len(tw["words"]) == tw["rows"] * tw["cols"]
    out = L.rtl_run(tw, {"x": 1})
    assert out["chain_clocks"] == len(tw["words"]) * 35
