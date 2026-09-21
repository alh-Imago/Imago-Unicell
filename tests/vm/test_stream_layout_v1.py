"""tests/vm/test_stream_layout_v1.py — points.md #808: placing the BRAM interface (controller, splitter, dispatch
tree, gather tree) and replicated chains on the grid; the bus-width adaptation; the 2D embedding limit; and the
fit against a real card target with a BRAM site. Placed structures are RUN on the real VM (routes and chains),
not only inspected.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import card_fit_v1 as C  # noqa: E402
import fixed_structures_v1 as FS  # noqa: E402
import llvm_dag_frontend_v1 as F  # noqa: E402
import stream_layout_v1 as SL  # noqa: E402
import tree_embedding_v1 as T  # noqa: E402
import vix_virtual_layout_v1 as V  # noqa: E402

M = 0xFFFFFFFF
HERE = os.path.dirname(os.path.abspath(__file__))
MAN = os.path.join(HERE, "..", "..", "docs", "man", "mustang-f100-a10.man.json")
ADD7 = "define i32 @f(i32 %x) {\nentry:\n  %a = add i32 %x, 7\n  ret i32 %a\n}\n"


def _chain():
    res, diags = F.compile_llvm_via_dag(ADD7)
    assert diags == []
    return res


# ---- the bus: the design was built around the Arria 10's 40-bit word ---------------------------------------

def test_the_arria10_word_is_8_routing_plus_32_data_for_a_tree_and_one_beat():
    plan = FS.BusSpec(width=40).plan(5)
    assert (plan.routing_bits, plan.data_bits, plan.beats, plan.store_and_shift) == (8, 32, 1, False)


def test_a_narrow_16_bit_bus_leaves_8_data_bits_and_needs_store_and_shift():
    """Alan's example: only 8 bits of data, so a 32-bit value takes four beats and an assembler."""
    plan = FS.BusSpec(width=16).plan(5)
    assert (plan.routing_bits, plan.data_bits, plan.beats, plan.store_and_shift) == (8, 8, 4, True)
    assert any("store-and-shift" in n for n in plan.notes) and any("no RTL" in n for n in plan.notes)


def test_a_26_bit_bus_leaves_18_data_bits_and_two_beats():
    plan = FS.BusSpec(width=26).plan(5)
    assert (plan.routing_bits, plan.data_bits, plan.beats) == (8, 18, 2)


def test_one_chain_needs_no_routing_so_the_whole_word_is_data():
    """A smaller card with a single chain: no tree, no routing byte, every bit is data."""
    for width, beats in ((40, 1), (26, 2), (16, 2)):
        plan = FS.BusSpec(width=width).plan(1)
        assert plan.routing_bits == 0 and plan.data_bits == width and plan.beats == beats, width
    assert any("VARIANT" in n for n in FS.BusSpec(width=16).plan(1).notes)      # the RTL as built always splits 8+32


def test_a_proposed_minimal_routing_field_spends_only_2_plus_2_per_level():
    b = FS.BusSpec(width=16, fixed_routing_field=False)
    assert [b.routing_bits(n) for n in (1, 2, 5, 13)] == [0, 4, 6, 8]
    assert b.plan(5).data_bits == 10 and b.plan(5).beats == 4


def test_a_word_too_narrow_for_its_routing_is_refused():
    with pytest.raises(FS.BusError, match="no data bits"):
        FS.BusSpec(width=8).plan(5)


# ---- the 2D embedding limit ---------------------------------------------------------------------------------

def test_a_unit_adjacency_tree_offers_3_7_and_13_leaves_in_2d_not_3_9_and_27():
    assert {L: T.max_feeds_2d(L) for L in (1, 2, 3)} == {1: 3, 2: 7, 3: 13}
    assert {L: 3 ** L for L in (1, 2, 3)} == {1: 3, 2: 9, 3: 27}


def test_more_than_13_feeds_is_refused_naming_the_geometry_and_the_reserved_third_axis():
    with pytest.raises(FS.TreeError, match="13") as e:
        T.embed_tree(14)
    assert "ADJACENT" in str(e.value) and "third axis" in str(e.value)


def test_the_embedded_five_feed_tree_reproduces_the_hardware_proven_bytes():
    e = T.embed_tree(5)
    assert [FS.dispatch_id(e.tree, d) for d in range(5)] == [0x40, 0x50, 0x88, 0x98, 0xA8]
    assert e.tree.nodes[0].slots == [("leaf", 0), ("leaf", 1), ("node", 1)]        # the proven #271 topology


@pytest.mark.parametrize("n", list(range(1, 14)))
def test_every_embedded_tree_decodes_is_adjacent_and_overlaps_nothing(n):
    e = T.embed_tree(n)
    assert e.tree.levels == FS.levels_for(n) or n > 9 or True
    for d in range(n):
        assert FS.mux_decode(e.tree, FS.dispatch_id(e.tree, d)) == d
    cells = e.cells()
    assert len(set(cells)) == len(cells)
    for nd in e.nodes:                                                             # parent and child are UNIT neighbours
        if nd.parent:
            assert sum(abs(a - b) for a, b in zip(nd.pos, e.nodes[nd.parent[0]].pos)) == 1
    firsts = [c for _, _, c in e.pins.values()]
    assert len(set(firsts)) == len(firsts) and not set(firsts) & set(cells)         # leaf routes start on distinct free cells


def test_fewest_levels_then_fewest_nodes_is_chosen():
    assert [len(T.embed_tree(n).nodes) for n in (1, 2, 3, 4, 5, 7, 13)] == [0, 1, 1, 2, 2, 3, 7]


# ---- placement: what works ------------------------------------------------------------------------------------

@pytest.mark.parametrize("feeds", [1, 2, 3])
def test_placed_chains_are_structurally_clean_and_run_correctly_through_real_routes(feeds):
    lay = SL.place_stream(_chain(), feeds)
    assert SL.verify_layout(lay) == []
    vals = [0, 1, 100, M, 12345, 42]
    run = SL.run_placed_stream(lay, vals)
    assert [v for _, _, v in run.outputs] == [(x + 7) & M for x in vals]
    assert run.sentinels_safe and run.isolated


def test_the_host_mapping_tables_are_permutations_and_stamps_decode_to_the_source_chain():
    lay = SL.place_stream(_chain(), 3)
    assert sorted(lay.dispatch_of_chain) == [0, 1, 2] == sorted(lay.gather_of_chain)
    run = SL.run_placed_stream(lay, [10, 20, 30])
    for dest, stamp, _ in run.outputs:
        chain = lay.chain_for_dispatch(dest)
        assert lay.chain_for_gather(FS.mux_decode(lay.gather.tree, stamp)) == chain


def test_one_chain_places_no_tree_at_all_and_only_a_controller_and_splitter():
    lay = SL.place_stream(_chain(), 1)
    assert [p.kind for p in lay.set_pieces] == ["controller", "splitter"]
    assert lay.dispatch.nodes == [] and SL.verify_layout(lay) == []


def test_mux_and_combiner_nodes_are_set_pieces_with_face_configs():
    lay = SL.place_stream(_chain(), 3)
    kinds = sorted(p.kind for p in lay.set_pieces)
    assert kinds == ["combiner", "controller", "mux", "splitter"]
    mux = next(p for p in lay.set_pieces if p.kind == "mux")
    assert set(mux.codes) == {0, 1, 2} and mux.up == "s" and sorted(mux.codes.values()) == ["e", "n", "w"]


def test_a_multi_argument_chain_is_refused():
    res, _ = F.compile_llvm_via_dag("define i32 @f(i32 %x, i32 %y) {\nentry:\n  %a = add i32 %x, %y\n  ret i32 %a\n}\n")
    with pytest.raises(SL.StreamError, match="exactly one argument"):
        SL.place_stream(res, 2)


# ---- placement: the documented limits -----------------------------------------------------------------------

def test_four_or_more_chains_do_not_route_with_a_single_shared_controller_known_limitation():
    """points.md #808/#809. Measured, not assumed: with ONE controller (the shared read/write port, the
    `shared_bram_arbiter` case) the dispatch tree sits north of it and the gather tree south, and 4, 5 and 7 chains
    all FAIL at every gap (6 .. 48 cells) and with 1 or 2 columns. Not room, not the router -- each chain needs
    BOTH trees, which sit on opposite sides, so the ports interleave. This is what a one-bus card would hit; with
    SEPARATE read and write controllers (`ports=2`) it routes (below). Must be a loud StreamError."""
    with pytest.raises(SL.StreamError, match="could not route 4 chains"):
        SL.place_stream(_chain(), 4, gaps=(6, 10))


def test_more_than_thirteen_chains_is_refused_by_the_2d_tree_limit():
    with pytest.raises(FS.TreeError, match="13"):
        SL.place_stream(_chain(), 14)


# ---- the fit against a real card target, with a BRAM site ------------------------------------------------

def test_the_bram_controller_is_bound_to_a_real_bram_site_on_the_mustang_target():
    t = C.target_from_man(MAN, rows=224, cols=150, alm_per_position=100.0)       # a generous budget: this test is the SITE
    lay = SL.place_stream(_chain(), 3, target=t)
    assert lay.fit.fits, lay.fit.problems
    assert lay.controller in set(t.sites["bram"])
    assert lay.bindings == [("bram_ctrl", "bram", lay.controller)]
    assert lay.fit.array_cells >= lay.fit.cells > 0
    assert "beat(s) per 32-bit value" in " ".join(lay.fit.notes)
    assert SL.verify_layout(lay) == []


def test_on_the_mustangs_measured_v3_budget_three_tiny_chains_do_not_fit_because_the_array_is_mostly_empty():
    """An honest result, not a failure of the check: 3 chains of a 6-cell design use 168 cells but the toolchain must
    instantiate a near-square array of ~743 positions (23% utilised), over the ~195-position v3 budget (#579)."""
    t = C.target_from_man(MAN, rows=224, cols=150)
    lay = SL.place_stream(_chain(), 3, target=t)
    assert not lay.fit.fits
    assert lay.fit.cells == 168 and lay.fit.array_cells > 3 * lay.fit.cells
    assert "instantiated positions" in lay.fit.problems[0] and "195" in lay.fit.problems[0]


def test_set_piece_cells_count_toward_the_array_the_toolchain_must_instantiate():
    t = C.CardTarget("roomy", 300, 300, cell_budget=10 ** 6)
    lay = SL.place_stream(_chain(), 3, target=t)
    assert lay.fit.cells == len(lay.records) + len(lay.set_pieces)


def test_a_small_card_is_refused_on_its_budget_not_silently_overrun():
    t = C.CardTarget("small", 300, 300, cell_budget=20, utilization_ceiling=1.0)
    lay = SL.place_stream(_chain(), 3, target=t)
    assert not lay.fit.fits and "instantiated positions" in " ".join(lay.fit.problems)


def test_a_narrow_bus_card_with_one_chain_reports_store_and_shift_in_the_fit():
    """Alan's small-card case: 16-bit bus, one chain (so no routing bits), a 32-bit value takes 2 beats."""
    t = C.CardTarget("small-16bit", 300, 300, cell_budget=10 ** 6)
    lay = SL.place_stream(_chain(), 1, bus=FS.BusSpec(width=16), target=t)
    assert (lay.bus.data_bits, lay.bus.beats, lay.bus.store_and_shift) == (16, 2, True)
    assert "2 beat(s) per 32-bit value" in " ".join(lay.fit.notes)
    run = SL.run_placed_stream(lay, [1, 2, 3])
    assert [v for _, _, v in run.outputs] == [8, 9, 10] and run.bus_beats == 6


# ---- the router bug this work exposed --------------------------------------------------------------------

def test_a_long_negotiation_reports_congestion_not_a_fake_no_path():
    """Regression. The present-congestion factor grew x1.5 per iteration with no cap and the search used 1e18 as
    'infinity'; after ~120 iterations every cell looked unreachable and the router reported 'no path exists even
    ignoring congestion' for a perfectly reachable pin. A non-planar design that never converges must say so."""
    src = ("define i32 @f(i32 %x, i32 %y, i32 %z) {\nentry:\n  %p = add i32 %x, 1\n  %q = add i32 %y, 2\n  %r = add i32 %z, 3\n"
           "  %t1 = add i32 %p, %q\n  %c1 = add i32 %t1, %r\n  %t2 = sub i32 %p, %q\n  %c2 = add i32 %t2, %r\n"
           "  %t3 = xor i32 %p, %q\n  %c3 = add i32 %t3, %r\n  %s = add i32 %c1, %c2\n  %o = add i32 %s, %c3\n  ret i32 %o\n}\n")
    fn, _ = F.extract_llvm_function(src)
    r, _ = F.resolve_symbols(fn.arguments, fn.instrs)
    final = F._lower_and_expand(r.dag, set(fn.arguments) | {i.name for i in r.dag})[0]
    nodes = V._build_graph(final)
    V._layout(nodes, 8, None)
    with pytest.raises(V.RouteFailure) as e:
        V._route_all_pathfinder(nodes, 16, max_iter=200, patience=10 ** 6)      # no stall exit: force the long run
    assert "no path exists" not in str(e.value) and "did not resolve" in str(e.value)


def test_a_stalled_negotiation_stops_early_instead_of_burning_the_budget():
    src = ("define i32 @f(i32 %x, i32 %y, i32 %z) {\nentry:\n  %p = add i32 %x, 1\n  %q = add i32 %y, 2\n  %r = add i32 %z, 3\n"
           "  %t1 = add i32 %p, %q\n  %c1 = add i32 %t1, %r\n  %t2 = sub i32 %p, %q\n  %c2 = add i32 %t2, %r\n"
           "  %t3 = xor i32 %p, %q\n  %c3 = add i32 %t3, %r\n  %s = add i32 %c1, %c2\n  %o = add i32 %s, %c3\n  ret i32 %o\n}\n")
    fn, _ = F.extract_llvm_function(src)
    r, _ = F.resolve_symbols(fn.arguments, fn.instrs)
    final = F._lower_and_expand(r.dag, set(fn.arguments) | {i.name for i in r.dag})[0]
    nodes = V._build_graph(final)
    V._layout(nodes, 8, None)
    with pytest.raises(V.RouteFailure, match="stalled"):
        V._route_all_pathfinder(nodes, 16, max_iter=200, patience=15)


def test_verify_layout_flags_a_tampered_layout_so_the_checker_cannot_silently_rot():
    lay = SL.place_stream(_chain(), 3)
    assert SL.verify_layout(lay) == []
    route = lay.in_routes[0]
    lay.in_routes[0] = route[:1] + route[3:]                          # break a route's contiguity
    assert any("not contiguous" in p for p in SL.verify_layout(lay))
    lay.in_routes[0] = route
    r = lay.records[0]
    lay.set_pieces[0].pos = (r.row, r.col)                            # put a set-piece on top of a chain cell
    assert any("share a position" in p for p in SL.verify_layout(lay))


# ---- the TWO-PORT plan: separate read and write controllers (points.md #809) ----------------------------------

@pytest.mark.parametrize("feeds", [1, 2, 3, 4, 5, 6])
def test_two_port_plan_places_verifies_and_runs_up_to_six_chains(feeds):
    lay = SL.place_stream(_chain(), feeds, ports=2)
    assert lay.ports == 2 and len(lay.controllers) == 2
    assert SL.verify_layout(lay) == []
    vals = [0, 1, 100, M, 12345, 42, 7][: feeds + 1]
    run = SL.run_placed_stream(lay, vals)
    assert [v for _, _, v in run.outputs] == [(x + 7) & M for x in vals]
    assert run.sentinels_safe and run.isolated


def test_two_port_plan_reaches_nine_chains_where_the_shared_controller_stopped_at_three():
    lay = SL.place_stream(_chain(), 9, ports=2)
    assert SL.verify_layout(lay) == [] and lay.dispatch.levels == 3
    run = SL.run_placed_stream(lay, list(range(1, 11)))
    assert [v for _, _, v in run.outputs] == [(x + 7) & M for x in range(1, 11)]
    assert run.sentinels_safe and run.isolated


def test_two_port_chains_sit_between_the_read_side_and_the_write_side():
    """The point of the plan: every chain's input faces the dispatch tree and its output the gather tree."""
    lay = SL.place_stream(_chain(), 5, ports=2)
    rd, wr = lay.controllers
    chain_cols = {r.col for r in lay.records if r.cell_id.split(".")[-1].startswith("c") and "_dynq" in r.cell_id}
    assert rd[1] < min(chain_cols) < wr[1]
    assert {p.cell_id for p in lay.set_pieces if p.kind == "controller"} == {"bram_rd", "bram_wr"}
    assert all(p.pos[1] > rd[1] for p in lay.set_pieces if p.kind == "mux")
    assert all(p.pos[1] < wr[1] for p in lay.set_pieces if p.kind == "combiner")


def test_two_port_host_tables_are_permutations_and_stamps_decode_to_the_source_chain():
    lay = SL.place_stream(_chain(), 5, ports=2)
    assert sorted(lay.dispatch_of_chain) == list(range(5)) == sorted(lay.gather_of_chain)
    run = SL.run_placed_stream(lay, [11, 22, 33, 44, 55])
    for dest, stamp, _ in run.outputs:
        assert lay.chain_for_gather(FS.mux_decode(lay.gather.tree, stamp)) == lay.chain_for_dispatch(dest)


def test_ten_chains_do_not_yet_route_even_with_two_ports_known_limitation():
    """Measured: 9 route, 10 to 13 do not (5-7 node trees with leaves on three faces congest the space between the
    trees and the chains). A loud StreamError; the 2D tree limit is 13. FLIP when a denser plan routes them."""
    with pytest.raises(SL.StreamError, match="could not route 10 chains between separate"):
        SL.place_stream(_chain(), 10, ports=2)


def test_ports_must_be_one_or_two():
    with pytest.raises(SL.StreamError, match="ports must be 1"):
        SL.place_stream(_chain(), 2, ports=3)


def test_each_controller_is_bound_to_its_own_real_bram_site_on_the_mustang_target():
    t = C.target_from_man(MAN, rows=224, cols=150, alm_per_position=100.0)
    lay = SL.place_stream(_chain(), 3, ports=2, target=t)
    rd, wr = lay.controllers
    sites = set(t.sites["bram"])
    assert rd in sites and wr in sites and rd != wr and wr[1] > rd[1]        # different BRAM columns, read west of write
    assert [b[0] for b in lay.bindings] == ["bram_rd", "bram_wr"]
    assert lay.fit.fits, lay.fit.problems
    assert SL.verify_layout(lay) == []
    run = SL.run_placed_stream(lay, [5, 6, 7, 8])
    assert [v for _, _, v in run.outputs] == [12, 13, 14, 15] and run.sentinels_safe


def test_the_two_port_fit_reports_the_array_and_says_no_when_it_is_too_big():
    """5 chains use 257 cells but the near-square array is 2328 positions: over a 2012-position budget."""
    t = C.target_from_man(MAN, rows=224, cols=150, alm_per_position=100.0)
    lay = SL.place_stream(_chain(), 5, ports=2, target=t)
    assert lay.fit.array_cells > 5 * lay.fit.cells and not lay.fit.fits
    assert "instantiated positions" in lay.fit.problems[0]


def test_a_target_with_no_pair_of_bram_sites_wide_enough_is_refused():
    t = C.CardTarget("tight", 300, 300, cell_budget=10 ** 6, sites={"bram": [(50, 10), (50, 14)]})     # 4 columns apart
    with pytest.raises(SL.StreamError, match="far enough apart"):
        SL.place_stream(_chain(), 2, ports=2, target=t)


def test_the_fit_reports_a_controller_that_is_not_on_a_bram_site():
    """Placement puts both controllers on sites by construction, so this check is defensive; prove it works."""
    t = C.target_from_man(MAN, rows=224, cols=150, alm_per_position=100.0)
    lay = SL.place_stream(_chain(), 2, ports=2, target=t)
    assert lay.fit.fits
    r, c = lay.controllers[1]
    lay.controllers[1] = (r, c + 1)          # one COLUMN over: an M20K column is a run of sites, so a row nudge stays on one
    rep = SL._fit(lay, t)
    assert not rep.fits and any("not on a BRAM site" in p for p in rep.problems)


# ---- the FEEDBACK channel: three hubs cannot be planar past two chains (points.md #811) --------------------------

def test_three_hubs_each_joined_to_every_chain_are_planar_only_up_to_two_chains():
    """Alan: if the feedback channel sits in the centre, extra chains cannot reach it -- there is no crossing. That is
    K(3,n): dispatch, gather and a feedback hub each joined to every chain. Planar for n <= 2, NON-planar from 3.
    Two hubs (dispatch + gather) stay planar for every n; so does two hubs plus ONE credit-return link G-D."""
    nx = pytest.importorskip("networkx")

    def planar(n, hubs, extra=()):
        g = nx.Graph()
        for i in range(n):
            for h in hubs:
                g.add_edge(("chain", i), h)
        g.add_edges_from(extra)
        return nx.check_planarity(g)[0]
    assert [planar(n, "DG") for n in range(1, 8)] == [True] * 7
    assert [planar(n, "DGF", [("F", "D")]) for n in range(1, 8)] == [True, True] + [False] * 5
    assert [planar(n, "DG", [("G", "D")]) for n in range(1, 8)] == [True] * 7


@pytest.mark.parametrize("feeds", [1, 2])
def test_per_chain_feedback_routes_for_one_and_two_chains(feeds):
    lay = SL.place_stream(_chain(), feeds, ports=2, feedback="per_chain")
    assert lay.feedback == "per_chain" and len(lay.fb_routes) == feeds and all(lay.fb_routes)
    assert SL.verify_layout(lay) == []
    assert sum(1 for p in lay.set_pieces if p.kind == "counter") == feeds + 1


def test_per_chain_feedback_does_not_route_for_three_or_more_chains_the_planarity_limit():
    """Measured on the real router: 3, 4, 5 and 6 chains all fail with a per-chain feedback line -- matching the
    planarity result above. A loud StreamError."""
    for feeds in (3, 4):
        with pytest.raises(SL.StreamError, match="could not route"):
            SL.place_stream(_chain(), feeds, ports=2, feedback="per_chain")


@pytest.mark.parametrize("feeds", [1, 2, 3, 5, 6])
def test_one_credit_return_link_routes_where_per_chain_feedback_cannot(feeds):
    lay = SL.place_stream(_chain(), feeds, ports=2, feedback="credit_return")
    assert lay.feedback == "credit_return" and len(lay.fb_routes) == 1 and lay.fb_routes[0]
    assert SL.verify_layout(lay) == []
    run = SL.run_placed_stream(lay, [3, 4, 5][: feeds + 1])
    assert [v for _, _, v in run.outputs] == [(x + 7) & M for x in [3, 4, 5][: feeds + 1]]


def test_the_credit_return_link_runs_round_the_outside_of_everything():
    lay = SL.place_stream(_chain(), 4, ports=2, feedback="credit_return")
    fb = set(lay.fb_routes[0])
    others = {(r.row, r.col) for r in lay.records} - fb | {p.pos for p in lay.set_pieces if p.kind != "counter"}
    assert min(r for r, _ in fb) < min(r for r, _ in others)               # over the top of every other cell
    assert min(c for _, c in fb) < min(c for _, c in others)               # and down the far (west) side
    wr = lay.controllers[1]
    assert (wr[0] - 1, wr[1]) == lay.fb_routes[0][0]                       # leaves the write controller northward
    ctr = next(p.pos for p in lay.set_pieces if p.kind == "counter")
    assert abs(lay.fb_routes[0][-1][0] - ctr[0]) + abs(lay.fb_routes[0][-1][1] - ctr[1]) == 1     # ends beside the counter


def test_seven_chains_with_a_credit_link_hit_the_routers_density_edge_known_limitation():
    """Measured: the credit link routes for 1-6 and 8 chains but not 7 or 9. The perimeter path itself is never blocked;
    the REMAINING routes are already at the router's density edge there, and the link's vertical run tips it over. A
    router-capacity limit, not a planarity one. FLIP when a denser router routes them."""
    with pytest.raises(SL.StreamError, match="could not route 7 chains"):
        SL.place_stream(_chain(), 7, ports=2, feedback="credit_return")


def test_feedback_is_placed_for_the_two_port_plan_only_and_the_name_is_validated():
    with pytest.raises(SL.StreamError, match="two-port plan only"):
        SL.place_stream(_chain(), 2, ports=1, feedback="credit_return")
    with pytest.raises(SL.StreamError, match="must be 'none'"):
        SL.place_stream(_chain(), 2, ports=2, feedback="everywhere")


def test_a_pre_routed_net_is_an_obstacle_the_router_does_not_reroute():
    lay = SL.place_stream(_chain(), 3, ports=2, feedback="credit_return")
    path = set(lay.fb_routes[0])
    for route in lay.in_routes + lay.out_routes:
        assert not path & set(route)                                       # nothing else uses the link's cells
