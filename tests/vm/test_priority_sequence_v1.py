"""tests/vm/test_priority_sequence_v1.py -- ledger #1018: the priority core's third mode, the SEQUENCED CHANNEL (Alan's #772), recorded in the ICM and carried to the flex RTL.
A sequenced priority takes ONLY the face whose turn it is, in a fixed cyclic order; any other arrival waits for ever if need be (head-of-line blocking, by design). Checked here:
the turn order round-trips through the ICM file; the VM reads it from the file (no side channel) and behaves as the RTL; the generated flex design takes turns in the recorded order,
waits for a late due face, stops when a due face runs dry, repeats a face that has several turns; the file's refusals (no order recorded, a due face nobody feeds, the sub family);
a sequenced priority in front of a two-operand cell becomes direct wiring with the TURN deciding operand A / B; a defective core is caught. Requires iverilog."""
import json
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_priority_flex_v1 import ROOT, build, cli, ram, run_level, design  # noqa: E402,F401
from icm_v3 import IcmV3File, IcmV3Record, pack_core_config, unpack_core_config  # noqa: E402

DIR = {"n": 0, "s": 1, "e": 2, "w": 3}


def seq_design(order, sources=("n", "w"), up=None):
    """Sequenced priority P at (1,1); sources N and W feed it (entries E1, E2, and E3 below on S); output east to an exit ram."""
    recs = design(2, (0, 0, 0), sources)
    p = [r for r in recs if r.cell_id == "P"][0]
    p.core_config["upstream_mask"] = list(up if up is not None else sources)
    p.core_config["sequence_len"] = len(order)
    for k, f in enumerate(order):
        p.core_config[f"sequence_{k}"] = DIR[f]
    return recs


def test_turn_order_round_trips_through_the_icm_file():
    c = {"upstream_mask": ["n", "e", "w"], "downstream_mask": ["s"], "scheduling_mode": 2, "sequence_len": 4,
         "sequence_0": 3, "sequence_1": 0, "sequence_2": 2, "sequence_3": 0}
    back = unpack_core_config("priority", pack_core_config("priority", c))
    for k, v in c.items():
        assert back[k] == v, (k, back[k], v)
    tmp = tempfile.mkdtemp()
    f = os.path.join(tmp, "x.icm")
    IcmV3File(name="x", records=seq_design(("w", "n", "w"))).save(f)
    p = [r for r in IcmV3File.load(f).records if r.cell_id == "P"][0]
    assert p.core_config["scheduling_mode"] == 2 and p.core_config["sequence_len"] == 3
    assert [p.core_config[f"sequence_{k}"] for k in range(3)] == [3, 0, 3]


def test_the_vm_reads_the_order_from_the_file_and_takes_turns():
    sys.path.insert(0, os.path.join(ROOT, "nano"))
    from unicell_super_automaton_v1 import SuperGrid
    recs = seq_design(("w", "n"))
    g = SuperGrid(recs)
    cell = g.cells[(1, 1)]
    assert cell.pri_scheduling_mode == 2 and cell.pri_seq_order == (3, 0)        # (W, N), straight from the saved configuration
    # an old file (mode 2, nothing recorded) has an empty order, which never captures (as before)
    old = design(2, (0, 0, 0), ("n", "w"))
    assert SuperGrid(old).cells[(1, 1)].pri_seq_order == ()


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
class TestRtl:
    def gen(self, name, recs, *extra):
        tmp = tempfile.mkdtemp()
        d, r = build(tmp, name, recs, *extra)
        assert r.returncode == 0, r.stderr[-800:] + r.stdout[-800:]
        return d

    def test_alternates_in_the_recorded_order_whoever_is_early(self):
        d = self.gen("seq_nw", seq_design(("n", "w")))
        S = {"E1": [1000 + j for j in range(8)], "E2": [2000 + j for j in range(8)]}
        for mode, seed in (("plain", 1), ("stall", 2), ("skewfirst", 3), ("skewlast", 4)):      # skew: either source slow, so either is early
            _, got = run_level(d, S, mode, seed=seed, settle=200, cycles=12000)
            exp = [v for pair in zip(S["E1"], S["E2"]) for v in pair]
            assert got["O"] == exp, (mode, got["O"])

    def test_the_other_order_is_not_the_same_result(self):
        d = self.gen("seq_wn", seq_design(("w", "n")))
        S = {"E1": [1000 + j for j in range(6)], "E2": [2000 + j for j in range(6)]}
        _, got = run_level(d, S, "plain", settle=200, cycles=8000)
        assert got["O"] == [v for pair in zip(S["E2"], S["E1"]) for v in pair], got["O"]

    def test_a_face_with_two_turns(self):
        d = self.gen("seq_nnw", seq_design(("n", "n", "w")))
        S = {"E1": [1000 + j for j in range(8)], "E2": [2000 + j for j in range(4)]}
        _, got = run_level(d, S, "stall", seed=5, settle=300, cycles=12000)
        assert got["O"] == [1000, 1001, 2000, 1002, 1003, 2001, 1004, 1005, 2002, 1006, 1007, 2003], got["O"]

    def test_stops_where_the_due_face_has_nothing_more(self):
        """Head-of-line blocking is the point: north has 5 items, west only 3 -- after n3 the west's turn never comes, so n4 waits for ever and the output ends at seven items."""
        d = self.gen("seq_hol", seq_design(("n", "w")))
        S = {"E1": [1000 + j for j in range(5)], "E2": [2000 + j for j in range(3)]}
        _, got = run_level(d, S, "plain", settle=300, cycles=4000)
        assert got["O"] == [1000, 2000, 1001, 2001, 1002, 2002, 1003], got["O"]

    def test_three_sources_one_turn_each_cyclic(self):
        d = self.gen("seq_s3", seq_design(("s", "w", "n"), ("n", "w", "s")))
        S = {"E1": [1000 + j for j in range(4)], "E2": [2000 + j for j in range(4)], "E3": [3000 + j for j in range(4)]}
        _, got = run_level(d, S, "stall", seed=7, settle=300, cycles=12000)
        exp = [v for k in range(4) for v in (S["E3"][k], S["E2"][k], S["E1"][k])]
        assert got["O"] == exp, got["O"]

    def test_configuration_word_and_a_defective_core_is_caught(self):
        d = self.gen("seq_bite", seq_design(("n", "w")))
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        top = open(os.path.join(d, rec["top"] + ".v")).read()
        inst = [l for l in top.splitlines() if "priority_cell_v4sa #" in l]
        # mask n+w = 0x9; sequenced bit 13 = 0x2000; len 2 at [16:14] = 0x8000; turn0 n=0, turn1 w=3 at [20:19] = 0x180000
        assert len(inst) == 1 and "cfg_data(32'h0018A009)" in inst[0] and "sequenced channel nw" in inst[0], inst
        S = {"E1": [1000 + j for j in range(6)], "E2": [2000 + j for j in range(6)]}
        _, good = run_level(d, S, "plain", settle=200, cycles=8000)
        f = os.path.join(d, "priority_cell_v4sa.v")
        src = open(f).read()
        for old, new in (("if (sequenced) seq_idx <=", "if (1'b0) seq_idx <="),            # the turn never advances
                         ("wire cand_n = valid_in_n && upstream_mask[0] && (!sequenced || due_n);", "wire cand_n = valid_in_n && upstream_mask[0];")):   # every face a candidate
            assert old in src
            open(f, "w").write(src.replace(old, new))
            _, bad = run_level(d, S, "plain", settle=200, cycles=8000)
            assert bad["O"] != good["O"], old
        open(f, "w").write(src)


def test_refusals_have_reasons():
    tmp = tempfile.mkdtemp()
    d, r = build(tmp, "sq_none", design(2, (0, 0, 0), ("n", "w")))                       # no order recorded
    assert r.returncode != 0 and "turn order" in (r.stderr + r.stdout)
    recs = seq_design(("n", "s"), ("n", "w"), up=("n", "w", "s"))                         # due face S: allowed by the mask, but nothing feeds it
    d, r = build(tmp, "sq_nosrc", recs)
    assert r.returncode != 0 and "no source connected" in (r.stderr + r.stdout)
    recs = seq_design(("n", "e"), ("n", "w"))                                             # due face E is not in the upstream mask
    d, r = build(tmp, "sq_mask", recs)
    assert r.returncode != 0 and "turn order" in (r.stderr + r.stdout)
    icm = os.path.join(tmp, "sq_sub.icm")
    IcmV3File(name="x", records=seq_design(("n", "w"))).save(icm)
    r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_sub"))
    assert r.returncode != 0 and "priority" in (r.stderr + r.stdout)


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_a_sequenced_priority_before_a_two_operand_cell_is_wiring_and_the_turn_picks_operand_a():
    """P (sequenced W then N) -> subtractor: the VM subtracts (first-taken) - (second-taken) = W - N. As direct wiring the turn, not arrival, decides: A is turn 0's face."""
    recs = [
        IcmV3Record(cell_id="P", row=1, col=1, core="priority", core_config={"upstream_mask": ["n", "w"], "downstream_mask": ["e"], "scheduling_mode": 2,
                                                                              "sequence_len": 2, "sequence_0": 3, "sequence_1": 0,
                                                                              "priority_rank_n": 0, "priority_rank_s": 0, "priority_rank_e": 0, "priority_rank_w": 0}),
        IcmV3Record(cell_id="D", row=1, col=2, core="adder", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"], "subtract_mode": 1}),
        ram("O", 1, 3, ["w"], ["e"]),
        ram("E1", 0, 1, [], ["s"]),
        ram("E2", 1, 0, [], ["e"]),
    ]
    tmp = tempfile.mkdtemp()
    d, r = build(tmp, "sq_sub", recs)
    assert r.returncode == 0, r.stderr[-800:] + r.stdout[-800:]
    rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
    assert rec.get("eliminated_priority_cells") == ["P"], rec.get("eliminated_priority_cells")
    n = [50, 60, 70, 80]
    w = [1000, 2000, 3000, 4000]
    # run both orders of arrival: the answer is W - N either way
    for mode, seed in (("plain", 1), ("skewfirst", 2), ("skewlast", 3), ("stall", 4)):
        _, got = run_level(d, {"E1": n, "E2": w}, mode, seed=seed, settle=300, cycles=12000)
        assert got["O"] == [(b - a) & 0xFFFFFFFF for a, b in zip(n, w)], (mode, got["O"])
