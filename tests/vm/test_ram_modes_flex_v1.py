"""tests/vm/test_ram_modes_flex_v1.py -- ledger #1021: the ram cell's three behaviours in generated flex designs (generator -> Verilog -> iverilog):
  CONSTANT  fixed mode, no source: offered continuously, ignores the in-port (unchanged; its own tests are elsewhere);
  ONE-SHOT  flowing mode (the ordinary ram); with load_data_valid its configured word is offered ONCE at start, then it is empty (the VM's behaviour, checked against the VM);
  HOLD      fixed mode WITH a source: the words arriving replace the stored value, offered continuously and never drained; starts empty, or holding a given value.
Also the refusals (sub family, a hold with two sources). Requires iverilog."""
import json
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_priority_flex_v1 import ROOT, build, cli, ram, run_level  # noqa: E402
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")


def adder(cid, r, c, up, down, **kw):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="adder", core_config={"upstream_mask": up, "downstream_mask": down, "subtract_mode": 0}, **kw)


def oneshot_design(init=100):
    """K: a one-shot preloaded ram (offers `init` once); E -> R (relay, so K is the EARLIER operand) -> adder A -> O."""
    return [ram("K", 0, 1, [], ["s"], init_data=init, load_data_valid=1) if False else
            IcmV3Record(cell_id="K", row=0, col=1, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["s"], "init_data": init, "load_data_valid": 1}),
            ram("E", 0, 0, [], ["s"]), ram("R", 1, 0, ["n"], ["e"]), adder("A", 1, 1, ["n", "w"], ["e"]), ram("O", 1, 2, ["w"], ["e"])]


def hold_design(preload=None):
    """W -> H (a HOLD ram) -> adder A <- X (the stream); A -> O. H is the later operand (two hops), X the earlier."""
    h = IcmV3Record(cell_id="H", row=1, col=1, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"], "fixed_mode": 1},
                    preload_value=preload)
    return [ram("W", 1, 0, [], ["e"]), h, ram("X", 0, 2, [], ["s"]), adder("A", 1, 2, ["w", "n"], ["e"]), ram("O", 1, 3, ["w"], ["e"])]


def hold_exit_design(preload=None, ldv=0):
    """W -> H, H is the design's output: its value as seen by the host, cycle by cycle."""
    cfg = {"upstream_mask": ["w"], "downstream_mask": [], "fixed_mode": 1}
    if ldv:
        cfg["load_data_valid"] = 1
        cfg["init_data"] = ldv
    return [ram("W", 0, 0, [], ["e"]), IcmV3Record(cell_id="H", row=0, col=1, core="ram", core_config=cfg, preload_value=preload)]


def gen(name, recs, *extra):
    tmp = tempfile.mkdtemp()
    d, r = build(tmp, name, recs, *extra)
    assert r.returncode == 0, r.stderr[-900:] + r.stdout[-900:]
    return d


def runs(levels, skip=0):
    """The distinct consecutive values of a per-cycle level list, ignoring the leading idle zeros."""
    out = []
    for v in levels:
        if not out and v == skip:
            continue
        if not out or out[-1] != v:
            out.append(v)
    return out


# ---------------------------------------------------------------- one-shot
def test_oneshot_preload_is_offered_once_and_then_the_cell_is_empty():
    d = gen("rm_one", oneshot_design(100))
    _, got = run_level(d, {"E": [10, 20, 30]}, "plain", settle=200, cycles=2000)
    assert got["O"] == [110], got                     # only the FIRST item sees the preload; the rest wait for ever (the VM's single-shot behaviour)


def test_oneshot_first_item_equals_the_vm():
    sys.path.insert(0, os.path.join(ROOT, "nano"))
    from unicell_super_automaton_v1 import SuperGrid
    recs = oneshot_design(100)
    g = SuperGrid(recs)
    cell = g.cells[(0, 0)]
    cell.ram_data_reg, cell.ram_data_valid = 10, True
    out = g.cells[(1, 2)]
    v = None
    for _ in range(60):
        g.tick()
        if out.ram_data_valid:
            v = out.ram_data_reg
            break
    assert v == 110


def test_oneshot_without_load_data_valid_is_just_a_normal_entry():
    recs = oneshot_design(100)
    k = [r for r in recs if r.cell_id == "K"][0]
    k.core_config["load_data_valid"] = 0              # no preload offer: K is an ordinary host entry
    d = gen("rm_entry", recs)
    _, got = run_level(d, {"E": [10, 20], "K": [100, 200]}, "plain", settle=200, cycles=3000)
    assert sorted(got["O"]) == [110, 220], got


# ---------------------------------------------------------------- hold
def test_hold_value_is_offered_again_and_again():
    d = gen("rm_hold", hold_design())
    for mode, seed in (("plain", 1), ("stall", 2), ("skewlast", 3)):
        _, got = run_level(d, {"W": [7], "X": [1, 2, 3, 4, 5, 6]}, mode, seed=seed, settle=300, cycles=8000)
        assert got["O"] == [8, 9, 10, 11, 12, 13], (mode, got["O"])        # 7 was written once, used six times, never drained


def test_hold_starting_value_without_any_write():
    d = gen("rm_holdpre", hold_design(preload=5))
    _, got = run_level(d, {"W": [], "X": [1, 2, 3, 4]}, "stall", seed=4, settle=300, cycles=8000)
    assert got["O"] == [6, 7, 8, 9], got["O"]


def test_hold_empty_until_written_and_each_write_replaces_it():
    d = gen("rm_holdexit", hold_exit_design())
    levels, _ = run_level(d, {"W": [7, 20, 33]}, "plain", settle=60, cycles=400)
    assert runs(levels["H"]) == [7, 20, 33], runs(levels["H"])
    assert levels["H"][-1] == 33                                              # and the last value stays held
    d = gen("rm_holdexit_ldv", hold_exit_design(ldv=55))
    levels, _ = run_level(d, {"W": [9]}, "plain", settle=60, cycles=400)
    assert runs(levels["H"])[-2:] == [55, 9] or runs(levels["H"]) == [55, 9], runs(levels["H"])   # load_data_valid: it starts holding 55, then the write replaces it


def test_hold_valid_only_once_a_value_exists():
    """A consumer must never see a value before one has been written: the adder's output stays empty until W is written."""
    d = gen("rm_holdwait", hold_design())
    _, got = run_level(d, {"W": [], "X": [1, 2, 3]}, "plain", settle=200, cycles=1500)
    assert got["O"] == [], got["O"]


def test_the_generated_instances_carry_the_parameters():
    d = gen("rm_params", hold_design(preload=5))
    top = open(os.path.join(d, json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"] + ".v")).read()
    h = [l for l in top.splitlines() if "ram_cell_v4sa" in l and ".HOLD(1)" in l]
    assert len(h) == 1 and ".OFFER_PRELOAD(1)" in h[0] and "HOLD" in h[0] and "holding 5 at start" in h[0], h
    d = gen("rm_params1", oneshot_design(100))
    top = open(os.path.join(d, json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"] + ".v")).read()
    k = [l for l in top.splitlines() if ".OFFER_PRELOAD(1)" in l]
    assert len(k) == 1 and ".HOLD(1)" not in k[0] and "offering 100 once" in k[0], k


def test_a_defective_ram_is_caught_by_these_designs():
    d = gen("rm_bite", hold_design())
    S = {"W": [7], "X": [1, 2, 3]}
    _, good = run_level(d, S, "plain", settle=200, cycles=3000)
    f = os.path.join(d, "ram_cell_v4sa.v")
    src = open(f).read()
    old = "else if (HOLD != 0 && valid_in) begin"
    assert old in src
    open(f, "w").write(src.replace(old, "else if (1'b0) begin"))              # writes never replace the value
    _, bad = run_level(d, S, "plain", settle=200, cycles=3000)
    assert bad["O"] != good["O"]
    open(f, "w").write(src)


# ---------------------------------------------------------------- refusals
def test_refusals_have_reasons():
    tmp = tempfile.mkdtemp()
    for name, recs, needle in (("hold on sub", hold_design(), "HOLD"), ("one-shot on sub", oneshot_design(), "ONE-SHOT")):
        icm = os.path.join(tmp, name.replace(" ", "_") + ".icm")
        IcmV3File(name="x", records=recs).save(icm)
        r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_" + name.replace(" ", "_")))
        assert r.returncode != 0 and needle in (r.stderr + r.stdout) and "flex family only" in (r.stderr + r.stdout), (name, r.stderr[-400:])
    recs = hold_design()
    recs.append(ram("W2", 2, 1, [], ["n"]))                                  # a second source into H
    recs[1].core_config["upstream_mask"] = ["w", "s"]
    d, r = build(tmp, "rm_two", recs)
    assert r.returncode != 0 and "exactly one source" in (r.stderr + r.stdout)
