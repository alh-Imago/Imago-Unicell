"""tests/vm/test_flex_grid_merge_v1.py -- FlexGrid step 5: the flex MERGE (relay behind merge_cell_v4sa) in both modes, checked against the REAL GENERATED RTL (ledger #969).

The std VM ORs same-tick arrivals into one value. The flex family puts a merge CORE in front of a multi-source input: ARBITRATE grants one source at a time (round-robin, A first), JOIN-OR waits for
every source and ORs them. FlexGrid(records, merge_mode=...) mirrors the generator's --merge-mode spec. Each design is generated with project_assemble_v1 (-s flex), run in iverilog with the same
streamed items, and the sequence of values reaching the exit is compared with FlexGrid's. Requires iverilog and FAILS without it.
"""
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flex_rtl_harness_v1 as h  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
import unicell_super_automaton_v1 as vm  # noqa: E402

ram = h.ram

TWO = [ram("X", 0, 1, [], ["s"]), ram("Y", 1, 0, [], ["e"]), ram("M", 1, 1, ["n", "w"], ["e"]), ram("E", 1, 2, ["w"], [])]
THREE = [ram("X", 0, 1, [], ["s"]), ram("Y", 1, 0, [], ["e"]), ram("Z", 2, 1, [], ["n"]), ram("M", 1, 1, ["n", "w", "s"], ["e"]), ram("E", 1, 2, ["w"], [])]


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fgmerge_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def rtl_sequence(tmp, name, recs, streams, merge_mode):
    d, r = h.build(tmp, name, recs) if merge_mode == "arbitrate" else (os.path.join(tmp, "g_" + name), None)
    if merge_mode != "arbitrate":
        icm = os.path.join(tmp, name + ".icm")
        h.IcmV3File(name=name, records=recs).save(icm)
        r = h.cli("-s", "flex", "--icm", icm, "--output", d, "--merge-mode", merge_mode)
    assert r.returncode == 0, r.stderr[:300]
    _, got = h.run_level(d, streams, "plain", 5, settle=200)
    return got["E"]


def vm_sequence(recs, streams, merge_mode, ticks=400, width=32):
    """Drive the entry rams with the streams (a new item whenever an entry is empty) and record, then consume, whatever reaches the exit E (the host's read)."""
    g = fg.FlexGrid(recs, width=width, merge_mode=merge_mode)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    todo = {k: list(v) for k, v in streams.items()}
    seen = []
    e = g.cells[pos["E"]]
    for _ in range(ticks):
        for k, vals in todo.items():
            c = g.cells[pos[k]]
            if vals and not c.ram_data_valid and not any(ev for ev in g._pending.get(pos[k], [])):
                g.inject(*pos[k], vals.pop(0))
        g.tick()
        if e.ram_data_valid:
            seen.append(e.ram_data_reg)
            e.ram_data_valid = False
    return seen


XS = [0x1000 + k for k in range(8)]
YS = [0x2000 + k for k in range(8)]


def test_arbitrate_two_items_in_the_same_cycle_are_sequenced_not_fused(tmp):
    streams = {"X": [0x00F0], "Y": [0x0F00]}
    rtl = rtl_sequence(tmp, "two", TWO, streams, "arbitrate")
    mine = vm_sequence(TWO, streams, "arbitrate")
    std = vm_sequence(TWO, streams, "arbitrate", ) if False else None
    assert sorted(rtl) == [0x00F0, 0x0F00], rtl
    assert mine == rtl, f"FlexGrid {mine} vs RTL {rtl}"


def test_the_std_vm_fuses_that_same_pair_and_flexgrid_does_not():
    g = vm.SuperGrid(TWO)
    pos = {r.cell_id: (r.row, r.col) for r in TWO}
    for _ in range(4):
        g.tick()
    g.inject(*pos["X"], 0x00F0)
    g.inject(*pos["Y"], 0x0F00)
    seen = []
    e = g.cells[pos["E"]]
    for _ in range(30):
        g.tick()
        if e.ram_data_valid:
            seen.append(e.ram_data_reg)
            e.ram_data_valid = False
    assert seen == [0x0FF0]
    assert vm_sequence(TWO, {"X": [0x00F0], "Y": [0x0F00]}, "arbitrate") != [0x0FF0]


def test_arbitrate_streams_every_item_once_uncorrupted_in_each_sources_own_order(tmp):
    rtl = rtl_sequence(tmp, "two_s", TWO, {"X": XS, "Y": YS}, "arbitrate")
    mine = vm_sequence(TWO, {"X": XS, "Y": YS}, "arbitrate")
    assert sorted(mine) == sorted(XS + YS) and [v for v in mine if v in XS] == XS and [v for v in mine if v in YS] == YS
    assert sorted(rtl) == sorted(XS + YS)
    # both sources are served within the first few items (round-robin, no starvation), as in the RTL
    assert any(v in XS for v in mine[:4]) and any(v in YS for v in mine[:4])


def test_join_or_pairs_are_ORed_in_order_and_equal_the_rtl_exactly(tmp):
    xs = [0x00F0F000 + k for k in range(8)]
    ys = [(0x0000F00F << (k % 3)) & 0xFFFFFFFF for k in range(8)]
    rtl = rtl_sequence(tmp, "two_j", TWO, {"X": xs, "Y": ys}, "join-or")
    mine = vm_sequence(TWO, {"X": xs, "Y": ys}, "join-or")
    assert rtl == [a | b for a, b in zip(xs, ys)]
    assert mine == rtl


def test_join_or_a_lone_item_waits_and_is_never_fused_with_a_later_one(tmp):
    rtl = rtl_sequence(tmp, "two_w", TWO, {"X": XS, "Y": YS[:5]}, "join-or")
    mine = vm_sequence(TWO, {"X": XS, "Y": YS[:5]}, "join-or")
    assert rtl == [a | b for a, b in zip(XS[:5], YS[:5])]
    assert mine == rtl


def test_join_or_of_three_sources_waits_for_all_three(tmp):
    xs, ys, zs = [0x1, 0x2, 0x4], [0x10, 0x20, 0x40], [0x100, 0x200, 0x400]
    rtl = rtl_sequence(tmp, "three_j", THREE, {"X": xs, "Y": ys, "Z": zs}, "join-or")
    mine = vm_sequence(THREE, {"X": xs, "Y": ys, "Z": zs}, "join-or")
    assert rtl == [0x111, 0x222, 0x444]
    assert mine == rtl


def test_arbitrate_of_three_sources_is_refused_because_its_grant_order_is_not_mirrored():
    with pytest.raises(ValueError, match="tree"):
        fg.FlexGrid(THREE, merge_mode="arbitrate")
    fg.FlexGrid(THREE, merge_mode="join-or")


def test_merge_mode_spec_per_consumer_and_unknown_modes():
    fg.FlexGrid(TWO, merge_mode="M=join-or,arbitrate")
    with pytest.raises(Exception):
        fg.FlexGrid(TWO, merge_mode="bogus")


def test_the_comparison_bites_a_join_or_mirror_that_does_not_wait(tmp, monkeypatch):
    xs, ys = XS, YS[:5]
    rtl = rtl_sequence(tmp, "two_m", TWO, {"X": xs, "Y": ys}, "join-or")
    # a mirror that falls back to the std relay (ORs whatever arrives, never waits) must disagree with the RTL
    monkeypatch.setattr(fg, "_FLEX_HANDLERS", {})
    assert vm_sequence(TWO, {"X": xs, "Y": ys}, "join-or") != rtl


def test_the_whole_cordic_in_flexgrid_equals_the_generated_flex_rtl_for_12_angles(tmp):
    """The hand-built CORDIC (36 cells: 4 branches, 4 merges, 8 adders, 12 constants) with one item in flight: FlexGrid's z_output equals the real generated flex RTL's, angle by angle, and the repo's
    independent anchor (z0 = 50000 -> -404) holds."""
    from hierarchical_icm_prototype_loader import load_hierarchical, flatten
    path = os.path.join(h.ROOT, "nano", "examples", "cordic_z_convergence.icm-hier.json")
    d = os.path.join(tmp, "cordic")
    r = h.cli("-s", "flex", "--icm", path, "--output", d)
    assert r.returncode == 0, r.stderr[:300]
    records, _ = flatten(load_hierarchical(path))
    ic = next(x for x in records if x.io_name == "z_input")
    oc = next(x for x in records if x.io_name == "z_output")
    s32 = lambda v: (v & 0xFFFFFFFF) - (1 << 32) if v & 0x80000000 else v & 0xFFFFFFFF

    def flex_z(z0):
        g = fg.FlexGrid(records)
        for _ in range(6):
            g.tick()
        g.inject(ic.row, ic.col, z0 & 0xFFFFFFFF)
        for _ in range(200):
            g.tick()
            o = g.cells[(oc.row, oc.col)]
            if o.ram_data_valid:
                return s32(o.ram_data_reg)
        return None

    angles = (50000, -50000, 0, 1, -1, 100, -100, 12345, -12345, 90000, -90000, 200000)
    _, got = h.run_level(d, {"z_input": [z & 0xFFFFFFFF for z in angles]}, "plain", 1, settle=300, cycles=12000, serial=True)
    rtl = [s32(v) for v in got["z_output"]]
    mine = [flex_z(z) for z in angles]
    assert mine == rtl, f"FlexGrid {mine} vs RTL {rtl}"
    assert mine[0] == -404
