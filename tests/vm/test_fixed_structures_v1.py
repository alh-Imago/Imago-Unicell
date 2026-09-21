"""tests/vm/test_fixed_structures_v1.py — points.md #807: the BRAM/DSP fixed structures (dispatch tree,
gather tree, sentinel at a chain's head and tail), checked against the project's own HARDWARE-PROVEN values
(`tb_mux_tree2_v1.v` #271 and `tb_combiner_tree2_v1.v` #272) and the RTL decode (`mux_cell_v1.v`).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import fixed_structures_v1 as FS  # noqa: E402
import llvm_dag_frontend_v1 as F  # noqa: E402

M = 0xFFFFFFFF


# ---- the depth rule: 3 usable faces per node, at most 3 levels ------------------------------------------

def test_levels_grow_with_the_number_of_feeds_ceil_log3():
    expect = {1: 0, 2: 1, 3: 1, 4: 2, 5: 2, 9: 2, 10: 3, 27: 3}
    for n, lv in expect.items():
        assert FS.levels_for(n) == lv, n
    for n in range(2, 28):
        assert FS.levels_for(n) == max(1, math.ceil(math.log(n, 3) - 1e-9)), n


def test_more_than_27_feeds_is_refused_with_the_reason():
    with pytest.raises(FS.TreeError, match="2-bit level count"):
        FS.levels_for(28)
    with pytest.raises(FS.TreeError):
        FS.build_tree(28)
    with pytest.raises(FS.TreeError):
        FS.levels_for(0)


def test_a_node_has_three_usable_faces_so_a_tree_is_needed_beyond_three_feeds():
    assert FS.FACES_PER_NODE == 3
    assert FS.build_tree(3).node_count == 1 and FS.build_tree(3).levels == 1
    assert FS.build_tree(4).node_count == 2


def test_node_counts_follow_each_child_consuming_one_face_and_adding_three():
    """k nodes give 2k+1 faces (each non-root node consumes one parent face), so ceil((n-1)/2) nodes."""
    for n in range(3, 28):
        assert FS.build_tree(n).node_count == math.ceil((n - 1) / 2), n
    assert FS.build_tree(27).node_count == 13 and FS.build_tree(9).node_count == 4


def test_built_tree_depth_matches_the_rule_and_every_destination_is_reachable():
    for n in range(1, 28):
        t = FS.build_tree(n)
        assert t.levels == FS.levels_for(n), n
        assert sorted(t.paths) == list(range(n))
        assert len({tuple(p) for p in t.paths.values()}) == n                  # distinct paths


# ---- hardware-proven ground truth ----------------------------------------------------------------------

def test_the_five_destination_tree_is_exactly_the_proven_271_topology():
    t = FS.build_tree(5)
    assert t.node_count == 2 and t.levels == 2
    root, child = t.nodes
    assert root.slots == [("leaf", 0), ("leaf", 1), ("node", 1)]               # N leaf1, S leaf2, E -> CHILD
    assert child.slots == [("leaf", 2), ("leaf", 3), ("leaf", 4)]              # N leaf3, S leaf4, E leaf5
    assert FS.DEFAULT_SLOT_FACES == {0: "n", 1: "s", 2: "e"}                   # CFG_ROOT = {E, S, N, upstream W}


def test_dispatch_routing_bytes_equal_the_ones_the_mux_tree_testbench_writes():
    """tb_mux_tree2_v1.v (#271): leaf1 {01,00}, leaf2 {01,01}, leaf3 {10,00,10}, leaf4 {10,01,10}, leaf5 {10,10,10}."""
    t = FS.build_tree(5)
    assert [FS.dispatch_id(t, d) for d in range(5)] == [0x40, 0x50, 0x88, 0x98, 0xA8]


def test_gather_stamps_equal_the_ones_the_combiner_tree_testbench_expects():
    """tb_combiner_tree2_v1.v (#272): chainA {01,00,00,00}, chainB {01,01,00,00}, chainC {10,00,10,00}, chainD {10,01,10,00}."""
    t = FS.build_tree(5)
    assert [FS.gather_stamp(t, d) for d in range(4)] == [0x40, 0x50, 0x88, 0x98]


def test_the_write_side_rule_and_the_read_side_rule_agree_for_every_destination():
    """Two independent implementations (increment-and-restamp vs indexed-by-count) must give the same byte."""
    for n in range(1, 28):
        t = FS.build_tree(n)
        for d in range(n):
            assert FS.gather_stamp(t, d) == FS.dispatch_id(t, d), (n, d)


def test_walking_the_tree_as_the_rtl_does_reaches_every_destination():
    for n in range(1, 28):
        t = FS.build_tree(n)
        for d in range(n):
            assert FS.mux_decode(t, FS.dispatch_id(t, d)) == d, (n, d)


def test_routing_bytes_are_unique_and_fit_the_8_bit_field():
    for n in (5, 9, 27):
        t = FS.build_tree(n)
        ids = [FS.dispatch_id(t, d) for d in range(n)]
        assert len(set(ids)) == n and all(0 <= i <= 0xFF for i in ids)


# ---- what the RTL treats as invalid --------------------------------------------------------------------

def test_slot_code_11_count_zero_and_over_long_routes_are_refused():
    t = FS.build_tree(5)
    with pytest.raises(FS.TreeError, match="11"):
        FS.mux_decode(t, (1 << 6) | (3 << 4))                     # count 1, slot1 = 11
    with pytest.raises(FS.TreeError, match="count 0"):
        FS.mux_decode(t, 0x00)                                    # count 0 at a real node
    with pytest.raises(FS.TreeError, match="more levels"):
        FS.mux_decode(t, (2 << 6) | (0 << 2) | (0 << 4))          # count 2 but the root's face 0 is already a leaf
    with pytest.raises(FS.TreeError, match="unused"):
        FS.mux_decode(FS.build_tree(4), 0xA8)                     # child face 2 is unused in a 4-feed tree


def test_a_single_feed_needs_no_tree_at_all():
    t = FS.build_tree(1)
    assert t.node_count == 0 and FS.dispatch_id(t, 0) == 0 and FS.mux_decode(t, 0) == 0


# ---- the set-piece library ------------------------------------------------------------------------------

def test_set_piece_library_records_the_fixed_interface_and_where_it_must_sit():
    sp = FS.SET_PIECES
    assert sp["mux"].usable_faces == 3 and sp["combiner"].usable_faces == 3
    assert sp["bram_controller"].site_kind == "bram" and sp["splitter"].site_kind == "bram"
    assert all(sp[k].site_kind == "dsp" for k in ("dsp_add", "dsp_arith", "dsp_compare"))
    assert not sp["sentinel"].grid_cell and not sp["addr_counter"].grid_cell      # connection logic, no grid position
    assert sp["mux"].grid_cell and sp["bram_controller"].rtl_module == "bram_controller_v1"


def test_dsp_ops_map_only_the_six_the_wrapper_actually_has():
    import dsp_wrapper_automaton_v1 as D
    assert set(FS.DSP_OPS.values()) == set(D.ALL_OPS) == {"ADD", "SUB", "MUL", "GE", "LE", "NEQ"}
    assert FS.dsp_op_for("mul") == "MUL" and FS.dsp_op_for("icmp", "sge") == "GE"
    assert FS.dsp_op_for("icmp", "slt") is None and FS.dsp_op_for("xor") is None     # stays in logic


def test_the_sentinel_attaches_feeds_at_the_head_and_collect_at_the_tail_of_a_compiled_chain():
    res, _ = F.compile_llvm_via_dag("define i32 @f(i32 %x, i32 %y) {\nentry:\n  %a = add i32 %x, %y\n  ret i32 %a\n}\n")
    spec = FS.sentinel_for(res, chain_length=4)
    assert spec.chain_length == 4 and len(spec.feed_at) == 2 and spec.collect_at == res.result_cell


# ---- streaming through BRAM -> dispatch -> chains -> gather -> BRAM ------------------------------------

ADD7 = "define i32 @f(i32 %x) {\nentry:\n  %a = add i32 %x, 7\n  ret i32 %a\n}\n"


@pytest.mark.parametrize("chains", [1, 2, 3, 5, 9])
def test_streaming_through_the_trees_returns_correct_stamped_results(chains):
    res, d = F.compile_llvm_via_dag(ADD7)
    assert d == []
    inputs = [{"x": v} for v in (0, 1, 100, M, 12345, 7, 42, 9, 1000, 5, 2, 8)]
    out = FS.run_stream(res, inputs, chains)
    assert out.sentinels_safe, out.sentinel_errors
    assert out.levels == FS.levels_for(chains) and out.dispatch_nodes == out.gather_nodes
    tree = FS.build_tree(chains)
    for i, (dest, stamp, value) in enumerate(out.outputs):
        assert dest == i % chains                                        # steered where the byte said
        assert stamp == FS.dispatch_id(tree, dest)                       # stamped with where it came from
        assert value == (inputs[i]["x"] + 7) & M                         # and the chain computed the right thing
        assert out.bram_out.read(i) == (stamp << 32) | value


def test_streaming_to_an_explicit_destination_order():
    res, _ = F.compile_llvm_via_dag(ADD7)
    out = FS.run_stream(res, [{"x": 1}, {"x": 2}, {"x": 3}, {"x": 4}], 5, destinations=[4, 0, 3, 3])
    assert [o[0] for o in out.outputs] == [4, 0, 3, 3] and out.sentinels_safe


def test_the_sentinel_latches_overflow_when_feeds_outrun_collects():
    """The sentinel's job at the head of a chain: too many arrivals in flight is an error, not silence."""
    s = FS.Sentinel(chain_length=1, out_frozen=False)
    s.step(True, False, False, False)
    assert not s.err_flag
    s.step(True, False, False, False)                                    # diff = 2 >= 2 x chain_length
    assert s.err_overflow and s.err_flag


def test_the_sentinel_latches_underflow_when_a_collect_has_no_matching_feed():
    s = FS.Sentinel(chain_length=1, out_frozen=False)
    s.step(False, True, False, False)                                    # a result left that never arrived
    assert s.err_negative and s.err_flag


def test_a_chain_that_never_drained_is_reported_not_safe():
    res, _ = F.compile_llvm_via_dag(ADD7)
    calls = []

    def leaky(r, args):
        calls.append(args)
        return 0
    out = FS.run_stream(res, [{"x": 1}], 1, run_chain=leaky)
    assert out.sentinels_safe                                            # fed and collected: balanced
    s = FS.Sentinel(chain_length=1, out_frozen=False)
    s.step(True, False, False, False)                                    # fed, never collected
    s.step(False, False, True, False)
    assert not s.safe_to_intervene


def test_plan_stream_sizes_the_deployment_by_the_number_of_feeds():
    res, _ = F.compile_llvm_via_dag(ADD7)
    p5, p9, p27 = (FS.plan_stream(res, n) for n in (5, 9, 27))
    assert (p5.levels, p9.levels, p27.levels) == (2, 2, 3)
    assert (p5.dispatch_nodes, p9.dispatch_nodes, p27.dispatch_nodes) == (2, 4, 13)
    assert p5.grid_cells == 5 * p5.chain_cells + 2 * 2 + 2
    assert p5.sentinels == 5 and p5.bram_sites == 2 and "LOWER BOUND" in p5.notes[0]
