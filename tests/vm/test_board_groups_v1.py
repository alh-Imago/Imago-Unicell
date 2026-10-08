"""ledger #1025: the two grouped on-board bitstreams cover every board test exactly once and the shipped group descriptions agree."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import board_groups_v1 as g  # noqa: E402
import board_tests_v1 as bt  # noqa: E402


def test_groups_cover_every_test_once():
    names = [n for grp in g.GROUPS.values() for n in grp]
    assert sorted(names) == sorted(t[0] for t in bt.TESTS)
    assert len(names) == len(set(names))


def test_group_json_matches():
    for k, grp in g.GROUPS.items():
        d = json.load(open(os.path.join(ROOT, "fpga", "board_tests", "groups", f"group_{k}.json")))
        assert d["tests"] == grp
        assert d.get("fmax_mhz", 0) >= 27 and d["lut4"] < 20000
        assert all(d["sim_exact_lines"][n] > 0 for n in grp) if "sim_exact_lines" in d else True
