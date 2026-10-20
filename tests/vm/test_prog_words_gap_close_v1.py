"""Ledger #1305: the VM's word-programming tables for the adder's second output (ids 4, 5) and for mul, div, priority and merge (and command, whose table was already in the carrier module).
Guard: every PROG_ID the standard RTL declares for these cores is in the VM table, no more and no less. Behaviour: a blank cell programmed by words ends up with the same fields as a cell
built from a record with that configuration."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperCell  # noqa: E402


def test_every_rtl_id_is_in_the_vm_table_for_all_twelve_cores():
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "prog_table_vs_rtl_v2.py"), "--json"], capture_output=True, text=True, check=True).stdout
    res = json.loads(out)
    assert set(res) == {"adder", "ram", "comparator", "accumulator", "latch", "sequencer", "branch", "mul", "div", "priority", "merge", "command"}
    assert {c: (r["rtl_only"], r["vm_only"]) for c, r in res.items() if r["rtl_only"] or r["vm_only"]} == {}


def _rec(core, cfg):
    return v3.IcmV3Record(cell_id="c", row=0, col=0, core=core, core_config=cfg, addon_config={})


def _fields(cell, names):
    return {n: getattr(cell, n) for n in names}


def test_adder_second_output_by_words_matches_a_record_built_cell():
    ref = SuperCell.from_record(_rec("adder", {"downstream_mask": ["e"], "second_output": 1, "second_downstream_mask": ["s"]}))
    cell = SuperCell.from_record(_rec("adder", {}))
    assert not cell.adder_carry_mode and cell.second_mask == 0
    cell.program_word(4, 1)
    cell.program_word(5, ref.second_mask)
    assert cell.adder_carry_mode is True and cell.second_mask == ref.second_mask != 0
    cell.program_word(4, 0xFFFE)                       # only bit 0 counts (prog_word[0])
    assert cell.adder_carry_mode is False
    cell.program_word(5, 0xFFFF)                       # only 6 bits count (prog_word[5:0])
    assert cell.second_mask == 0x3F


def test_mul_div_by_words_match_record_built_cells():
    refm = SuperCell.from_record(_rec("mul", {"downstream_mask": ["e"], "upstream_mask": ["w"], "second_output": 1, "second_downstream_mask": ["n"]}))
    m = SuperCell.from_record(_rec("mul", {}))
    for pid, val in ((0, refm.mul_downstream_mask), (1, refm.mul_upstream_mask), (2, 1), (4, refm.second_mask), (7, 1)):
        m.program_word(pid, val)
    names = ["mul_downstream_mask", "mul_upstream_mask", "mul_wide_mode", "second_mask"]
    assert _fields(m, names) == _fields(refm, names) and m.program_done
    refd = SuperCell.from_record(_rec("div", {"downstream_mask": ["e"], "upstream_mask": ["w"], "second_output": 1, "remainder_primary": 1, "second_downstream_mask": ["n"]}))
    d = SuperCell.from_record(_rec("div", {}))
    for pid, val in ((0, refd.div_downstream_mask), (1, refd.div_upstream_mask), (2, 1), (4, 1), (5, refd.second_mask), (7, 1)):
        d.program_word(pid, val)
    names = ["div_downstream_mask", "div_upstream_mask", "div_remainder_primary", "div_second_output", "second_mask"]
    assert _fields(d, names) == _fields(refd, names) and d.program_done


def test_priority_ranks_one_word_and_credits_cleared():
    ref = SuperCell.from_record(_rec("priority", {"upstream_mask": ["n", "s"], "downstream_mask": ["e"], "priority_rank_n": 3, "priority_rank_s": 1, "priority_rank_e": 2, "priority_rank_w": 0, "scheduling_mode": 1}))
    c = SuperCell.from_record(_rec("priority", {}))
    c.pri_credit_n, c.pri_credit_w = 5, 7                                            # stale credits
    c.program_word(0, ref.pri_upstream_mask)                                         # the RTL's id 0 is the UPSTREAM mask (id 1 is downstream)
    c.program_word(1, ref.pri_downstream_mask)
    c.program_word(2, 3 | (1 << 2) | (2 << 4) | (0 << 6) | (1 << 8))                # {sched[8], w, e, s, n}
    names = ["pri_upstream_mask", "pri_downstream_mask", "pri_rank_n", "pri_rank_s", "pri_rank_e", "pri_rank_w", "pri_scheduling_mode"]
    assert _fields(c, names) == _fields(ref, names)
    assert (c.pri_credit_n, c.pri_credit_s, c.pri_credit_e, c.pri_credit_w) == (0, 0, 0, 0)
    c.program_word(2, 0x1FF & ~(1 << 8))
    assert c.pri_scheduling_mode == 0 and c.pri_rank_n == 3 and c.pri_rank_w == 3


def test_merge_mode_and_addon_id_five():
    ref = SuperCell.from_record(_rec("merge", {"upstream_mask": ["n", "s"], "downstream_mask": ["e"], "mode": 3}))
    c = SuperCell.from_record(_rec("merge", {}))
    c.program_word(0, ref.mrg_downstream_mask)
    c.program_word(1, ref.mrg_upstream_mask)
    c.program_word(2, 3)
    c.program_word(5, 0x12345)                                                       # merge's addon_config is id 5; id 3 is not a merge id and does nothing
    c.program_word(3, 0xFFFFF)
    assert _fields(c, ["mrg_downstream_mask", "mrg_upstream_mask", "mrg_mode"]) == _fields(ref, ["mrg_downstream_mask", "mrg_upstream_mask", "mrg_mode"])
    assert c.addon_config == 0x12345


def test_program_in_is_now_allowed_for_these_cores_and_a_fake_core_still_raises():
    for core in ("mul", "div", "priority", "merge"):
        c = SuperCell.from_record(_rec(core, {}))
        c.program_in = True
        assert c.program_in is True
    c = SuperCell.from_record(_rec("adder", {}))
    c.core = "not_a_real_core"
    try:
        c.program_in = True
    except ValueError as e:
        assert "no PROG_ID table" in str(e)
    else:
        raise AssertionError("expected ValueError")
