import json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_bases_v2 as B, hexn_wrgrid_v11 as G, hexn_icm_export_v2 as X, hexn_vm_v2 as V
import pytest

ALL = B.all_tasks()
NAMES = ("old/scale_offset", "old/diff_abs", "new/merge_two", "new/prio3", "new/branch_route", "new/seq_add")


def _file(nm, tmp_path):
    t = ALL[nm]; b = B.tailored(t); P = B.fits(b, t)
    p = str(tmp_path / (nm.replace("/", "_") + ".json"))
    json.dump(X.to_icm(B.program_of(b, P, t), nm), open(p, "w"))
    return t, p


@pytest.mark.parametrize("nm", NAMES)
def test_vm_runs_from_the_file_alone(nm, tmp_path):
    t, p = _file(nm, tmp_path)
    vm = V.SerialVM.load(p)                                          # nothing but the file: no planner, no Base
    rnd = random.Random(11)
    for _ in range(4):
        iv = {n: rnd.randrange(1 << 20) for n in t[1]}
        cap = vm.run(iv); ref = G.ref9(t[0], iv)
        for o in t[2]:
            got = [w for _, w in cap[o]]; ordd, want = ref[o]
            assert (got == want) if ordd else (sorted(got) == sorted(want))


def test_vm_refuses_missing_input_damaged_file_and_wrong_kind(tmp_path):
    t, p = _file("old/scale_offset", tmp_path)
    vm = V.SerialVM.load(p)
    with pytest.raises(ValueError): vm.run({})
    d = json.load(open(p)); d["records"][0]["row"] += 1
    with pytest.raises(ValueError): V.SerialVM.load(d)                # hash
    prog = X.from_icm(json.load(open(p))); k = next(iter(prog["cells"])); prog["cells"][k]["kind"] = "prio"
    with pytest.raises(AssertionError): V.SerialVM(prog).run({n: 1 for n in t[1]})
