"""tests/vm/test_card_fit_v1.py — points.md #804: does a compiled design FIT a bounded card, with
resource-bound ops PINNED onto the card's fixed sites (DSP, BRAM)? Every positive test also runs the
fabric through the real VM against an independent Python model.

Synthetic targets exercise the mechanism; one test reads the REAL Mustang-F100-A10 MAN file (DSP/M20K
columns read by Alan from Chip Planner) to check the die->grid mapping and the budget arithmetic.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import card_fit_v1 as C  # noqa: E402
import llvm_dag_frontend_v1 as F  # noqa: E402

M = 0xFFFFFFFF
HERE = os.path.dirname(os.path.abspath(__file__))
MAN = os.path.join(HERE, "..", "..", "docs", "man", "mustang-f100-a10.man.json")


def _ir(body, args="i32 %x"):
    return f"define i32 @f({args}) {{\nentry:\n{body}\n}}\n"


def _compile(src, **kw):
    res, diags = F.compile_llvm_via_dag(src, **kw)
    assert diags == [], [d.problem for d in diags]
    return res


TWO_MULS = _ir("  %a = mul i32 %x, 3\n  %b = mul i32 %y, 5\n  %r = add i32 %a, %b\n  ret i32 %r", "i32 %x, i32 %y")


def _two_muls_ok(res):
    for x, y in ((1, 2), (10, 20), (M, 3), (0, 0)):
        assert F.run_in_vm(res, {"x": x, "y": y}) == (x * 3 + y * 5) & M, (x, y)


def test_max_cells_is_the_budget_times_the_utilisation_ceiling():
    t = C.CardTarget("t", 10, 10, cell_budget=1000, utilization_ceiling=0.8)
    assert t.max_cells == 800


# ---- fixed sites: resource-bound ops are PINNED --------------------------------------------------

def test_multiplies_are_pinned_onto_dsp_sites_and_results_stay_correct():
    sites = [(5, 5), (5, 25), (30, 5)]
    tgt = C.CardTarget("synthetic", 60, 60, cell_budget=1000, sites={"dsp": sites})
    res = _compile(TWO_MULS, target=tgt)
    assert res.fit.fits and res.placer == "routed"
    assert len(res.fit.bindings) == 2
    assert res.positions["a"] in sites and res.positions["b"] in sites
    assert res.positions["a"] != res.positions["b"]                      # distinct sites
    assert {b[0] for b in res.fit.bindings} == {"a", "b"} and {b[1] for b in res.fit.bindings} == {"dsp"}
    _two_muls_ok(res)


def test_the_op_core_cell_sits_exactly_on_the_site():
    tgt = C.CardTarget("synthetic", 60, 60, cell_budget=1000, sites={"dsp": [(20, 20)]})
    res = _compile(_ir("  %a = mul i32 %x, 7\n  ret i32 %a"), target=tgt)
    assert res.positions["a"] == (20, 20)
    assert res.result_cell == (20, 20)
    for x in (0, 3, M):
        assert F.run_in_vm(res, {"x": x}) == (x * 7) & M


def test_more_multiplies_than_sites_fall_back_to_logic_and_are_reported():
    src = _ir("  %a = mul i32 %x, 3\n  %b = mul i32 %a, 5\n  %c = mul i32 %b, 7\n  ret i32 %c")
    tgt = C.CardTarget("one-dsp", 80, 80, cell_budget=2000, sites={"dsp": [(10, 10)]})
    res = _compile(src, target=tgt)
    assert len(res.fit.bindings) == 1
    assert len(res.fit.fallbacks) == 2 and all("no free dsp site" in f for f in res.fit.fallbacks)
    assert res.fit.sites_used == {"dsp": 1} and res.fit.sites_available == {"dsp": 1}
    for x in (0, 2, 9, M):
        assert F.run_in_vm(res, {"x": x}) == (x * 105) & M


def test_a_card_with_no_dsp_sites_binds_nothing_and_reports_no_fallback():
    tgt = C.CardTarget("no-dsp", 80, 80, cell_budget=2000)
    res = _compile(TWO_MULS, target=tgt)
    assert res.fit.bindings == [] and res.fit.fallbacks == []
    _two_muls_ok(res)


def test_bram_sites_are_modelled_and_counted_but_no_op_consumes_one_yet():
    tgt = C.CardTarget("with-bram", 60, 60, cell_budget=1000, sites={"bram": [(3, 3), (3, 9)]})
    res = _compile(_ir("  %a = add i32 %x, 1\n  ret i32 %a"), target=tgt)
    assert res.fit.sites_available == {"bram": 2} and res.fit.sites_used == {}


# ---- extent: FOLD to fit a bounded grid ----------------------------------------------------------

LONG_CHAIN = _ir("\n".join(
    [f"  %v{i} = {op} i32 {'%x' if i == 0 else f'%v{i-1}'}, {k}"
     for i, (op, k) in enumerate([("add", 3), ("xor", 5), ("add", 7), ("shl", 1), ("xor", 9), ("add", 11),
                                  ("lshr", 1), ("add", 13), ("xor", 3), ("add", 1)])]) + "\n  ret i32 %v9")


def _chain_ref(x):
    v = (x + 3) & M
    v ^= 5
    v = (v + 7) & M
    v = (v << 1) & M
    v ^= 9
    v = (v + 11) & M
    v >>= 1
    v = (v + 13) & M
    v ^= 3
    return (v + 1) & M


def _extent(res):
    rows = [r.row for r in res.records]
    cols = [r.col for r in res.records]
    return max(rows) - min(rows) + 1, max(cols) - min(cols) + 1


def test_a_design_wider_than_the_grid_is_folded_to_fit_and_stays_correct():
    flat = _compile(LONG_CHAIN, placer="routed")
    fh, fw = _extent(flat)
    # MEASURED: this 29-column chain folds down to 19 columns (7 columns/band), and refuses at 14
    tgt = C.CardTarget("narrow", rows=fh * 4, cols=(fw * 2) // 3, cell_budget=5000)
    res = _compile(LONG_CHAIN, target=tgt)
    assert res.fit.fits and res.fit.fold_width is not None
    assert _extent(res)[1] <= tgt.cols < fw
    assert all(0 <= r.row < tgt.rows and 0 <= r.col < tgt.cols for r in res.records)      # routes included
    for x in (0, 1, 100, 0x7FFFFFFF, M):
        assert F.run_in_vm(res, {"x": x}) == _chain_ref(x), hex(x)


def test_folding_has_a_floor_below_which_the_design_is_refused_precisely():
    flat = _compile(LONG_CHAIN, placer="routed")
    fh, fw = _extent(flat)
    res, diags = F.compile_llvm_via_dag(LONG_CHAIN, target=C.CardTarget("too-narrow", fh * 4, fw // 2, 5000))
    assert res is None and diags[0].stage == "fit" and "no layout" in diags[0].problem


def test_a_grid_that_already_holds_the_flat_layout_is_not_folded_needlessly():
    tgt = C.CardTarget("roomy", rows=400, cols=400, cell_budget=5000)
    res = _compile(LONG_CHAIN, target=tgt)
    assert res.fit.fits and res.fit.fold_width is None


def test_a_grid_too_small_for_any_fold_is_a_precise_fit_refusal():
    tgt = C.CardTarget("tiny", rows=6, cols=6, cell_budget=5000)
    res, diags = F.compile_llvm_via_dag(LONG_CHAIN, target=tgt)
    assert res is None and diags[0].stage == "fit"
    assert "no layout" in diags[0].problem and "6x6" in diags[0].problem


# ---- budget --------------------------------------------------------------------------------------

def test_the_operation_cells_alone_exceeding_the_budget_is_refused_before_any_routing():
    tgt = C.CardTarget("small-budget", rows=500, cols=500, cell_budget=10, utilization_ceiling=1.0)
    res, diags = F.compile_llvm_via_dag(LONG_CHAIN, target=tgt)
    assert res is None and diags[0].stage == "fit"
    assert "ALONE" in diags[0].problem and "budget of 10" in diags[0].problem


def test_routes_count_toward_the_budget():
    """Each op fits, but the routes push the total over: a specific, reported reason."""
    roomy = C.CardTarget("roomy", 400, 400, cell_budget=5000)
    n = len(_compile(LONG_CHAIN, target=roomy).records)
    ops_alone = C._node_cell_count(F._lower_and_expand(
        F.resolve_symbols(*(lambda fn: (fn.arguments, fn.instrs))(F.extract_llvm_function(LONG_CHAIN)[0]))[0].dag,
        {"x"} | {f"v{i}" for i in range(10)})[0])
    assert ops_alone < n
    tight = C.CardTarget("tight", 400, 400, cell_budget=n - 1, utilization_ceiling=1.0)
    res, diags = F.compile_llvm_via_dag(LONG_CHAIN, target=tight)
    assert res is None and "exceeds the budget" in diags[0].problem or "ALONE" in diags[0].problem


def test_check_fit_reports_budget_and_extent_of_an_already_compiled_design():
    res = _compile(TWO_MULS, placer="growth")
    big = C.CardTarget("big", 5000, 5000, cell_budget=10 ** 6)
    small = C.CardTarget("small", 5000, 5000, cell_budget=10, utilization_ceiling=1.0)
    assert C.check_fit(res.records, big).fits
    rep = C.check_fit(res.records, small)
    assert not rep.fits and "exceeds the budget" in rep.problems[0]


# ---- the REAL Mustang-F100-A10 MAN file ----------------------------------------------------------

def _man():
    with open(MAN) as f:
        return json.load(f)


def test_the_real_man_file_gives_the_real_dsp_and_bram_columns():
    t = C.target_from_man(MAN, rows=224, cols=150)
    man = _man()["device"]
    assert {c for _, c in t.sites["dsp"]} == {col["x"] for col in man["dsp"]["columns"]}
    rows96 = [r for r, c in t.sites["dsp"] if c == 96]
    assert (min(rows96), max(rows96)) == (1, 167)                      # the truncated column: y 1..167
    assert t.cell_budget == int(251680 // 1030.52) == 244            # super_v3, MEASURED (#579)
    assert (100, 52) in t.sites["bram"] and (165, 52) not in t.sites["bram"]     # x=52 is broken into 3 segments
    assert any("PARAMETER" in p for p in t.provenance)
    assert any("MEASURED" in p for p in t.provenance)


def test_the_die_to_grid_mapping_is_a_parameter_not_an_assumption():
    a = C.target_from_man(MAN, rows=224, cols=150)
    b = C.target_from_man(MAN, rows=112, cols=75, pitch=(2, 2))
    assert {c for _, c in b.sites["dsp"]} == {col["x"] // 2 for col in _man()["device"]["dsp"]["columns"]}
    assert a.sites["dsp"] != b.sites["dsp"]


def test_compiling_against_the_real_mustang_target_pins_a_multiply_on_a_real_site():
    t = C.target_from_man(MAN, rows=224, cols=150)
    res = _compile(_ir("  %a = mul i32 %x, 9\n  %b = add i32 %a, 1\n  ret i32 %b"), target=t)
    assert res.fit.fits
    assert res.positions["a"] in set(t.sites["dsp"])
    for x in (0, 7, M):
        assert F.run_in_vm(res, {"x": x}) == (x * 9 + 1) & M


def test_the_default_path_has_no_fit_report():
    assert _compile(_ir("  %a = add i32 %x, 1\n  ret i32 %a")).fit is None


def test_the_layout_is_rejected_before_any_routing_when_it_cannot_fit_the_grid():
    """The grid is enforced three times -- here, in the router's search box, and in the final
    `check_fit(absolute=True)`. This is the earliest, cheapest one: it must fire on its own."""
    import vix_virtual_layout_v1 as V
    fn, _ = F.extract_llvm_function(LONG_CHAIN)
    r, _ = F.resolve_symbols(fn.arguments, fn.instrs)
    final, _, _ = F._lower_and_expand(r.dag, {"x"} | {f"v{i}" for i in range(10)})
    nodes = V._build_graph(final)
    V._layout(nodes, 4, None)
    with pytest.raises(V.RouteFailure, match="does not fit a 5x5 grid"):
        V._fit_positions(nodes, (5, 5), None)
    nodes = V._build_graph(final)
    V._layout(nodes, 4, None)
    V._fit_positions(nodes, (400, 400), None)          # a big enough grid is fine
    assert min(p[0] for n in nodes for p in n.cells()) >= 0


def test_a_bound_op_with_no_site_of_its_kind_fails_loudly():
    import vix_virtual_layout_v1 as V
    fn, _ = F.extract_llvm_function(TWO_MULS)
    r, _ = F.resolve_symbols(fn.arguments, fn.instrs)
    final, _, _ = F._lower_and_expand(r.dag, {"x", "y", "a", "b", "r"})
    bound, _ = C.bind_resources(final, C.CardTarget("t", 50, 50, 1000, sites={"dsp": [(5, 5), (5, 20)]}))
    with pytest.raises(V.RouteFailure, match="needs a 'dsp' site"):
        V.compile_dag_routed(bound, bounds=(50, 50), sites={"bram": [(1, 1)]}, attempts=1, spacings=(4,))


# ---- units: the budget is INSTANTIATED positions at a MEASURED cost (points.md #806) -------------------

def _brute_array(points):
    import project_assemble_v1 as pa
    n = len(points)
    while True:
        rows, cols = pa.grid_dims(n)
        if points <= set(pa.cell_positions(n, rows, cols)):
            return n
        n += 1


class _Rec:
    def __init__(self, r, c):
        self.row, self.col = r, c


@pytest.mark.parametrize("pts", [
    {(r, c) for r in range(3) for c in range(3)},          # a full block
    {(0, c) for c in range(10)},                            # a single wide row: the generator pays for a near-square array
    {(r, 0) for r in range(7)},
    {(0, 0), (4, 0), (4, 6)},                               # sparse
    {(0, 0)},
])
def test_array_cells_matches_the_assemblers_own_grid_functions_by_brute_force(pts):
    recs = [_Rec(r + 5, c + 9) for r, c in pts]              # translated: the array starts at the design's origin
    assert C.array_cells(recs) == _brute_array(pts)
    assert C.array_cells(recs, "rect") == (max(r for r, _ in pts) + 1) * (max(c for _, c in pts) + 1)


def test_a_wide_flat_layout_costs_far_more_positions_than_the_cells_it_uses():
    """The reason area efficiency matters: the toolchain instantiates a dense NEAR-SQUARE array, so a
    1x10 row of 10 cells must pay for 91 positions."""
    recs = [_Rec(0, c) for c in range(10)]
    assert C.array_cells(recs) == 91 and len(recs) == 10


def test_the_report_shows_used_cells_and_instantiated_positions_and_utilisation():
    res = _compile(TWO_MULS, target=C.CardTarget("t", 200, 200, cell_budget=10 ** 6))
    assert res.fit.array_cells >= res.fit.cells > 0
    assert "instantiated positions" in res.fit.format() and "utilised" in res.fit.format()


def test_a_sparse_design_is_refused_on_its_ARRAY_not_on_the_cells_it_uses():
    big = C.CardTarget("plenty", 300, 300, cell_budget=10 ** 6)
    res = _compile(LONG_CHAIN, target=big)
    used, arr = res.fit.cells, res.fit.array_cells
    assert arr > used
    tight = C.CardTarget("tight", 300, 300, cell_budget=used + 5, utilization_ceiling=1.0)   # fits by USED cells
    r2, diags = F.compile_llvm_via_dag(LONG_CHAIN, target=tight)
    assert r2 is None and "instantiated positions" in diags[0].problem


def test_measured_shell_costs_are_the_only_presets_and_the_vix_carrier_is_not_guessed():
    assert C.ALM_PER_POSITION == {"nano": 102.8, "super_v3": 1030.52, "super_v4": 1307.42}
    v3 = C.target_from_man(MAN, rows=224, cols=150)
    v4 = C.target_from_man(MAN, rows=224, cols=150, shell="super_v4")
    assert (v3.cell_budget, v4.cell_budget) == (244, 192)
    with pytest.raises(ValueError, match="no MEASURED ALM cost"):
        C.target_from_man(MAN, rows=224, cols=150, shell="vix")
    assert C.target_from_man(MAN, rows=224, cols=150, shell="vix", alm_per_position=2000.0).cell_budget == 125
