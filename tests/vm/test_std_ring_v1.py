"""Ledger #1116: ring control on the standard line (VM SuperGrid): counter + branch + join-gate IN the ring. Stops after exactly N laps, values equal the model, quiet, release = one more lap."""
import os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from nano import looped_cordic_v1 as L
from nano.unicell_super_automaton_v1 import SuperGrid


def _run(n):
    g, recs = L.new_grid(SuperGrid, join=True, ring_laps=n)
    seen = L.run_steps(g, n + 4, max_ticks=(n + 4) * 60)
    return g, recs, seen


@pytest.mark.parametrize("n", [5, 6, 9])
def test_stops_after_exactly_n_laps_with_model_values(n):
    g, recs, seen = _run(n)
    assert len(seen) == n
    m = L.model(n + 2)
    assert [v for _, v in seen] == m[:n]
    for _ in range(400):
        g.tick()
    assert L.run_steps(g, 2, max_ticks=300) == []
    assert g.cells[(6, 8)].ram_data_valid


@pytest.mark.parametrize("n", [5, 8])
def test_each_release_gives_one_more_lap(n):
    g, recs, seen = _run(n)
    rel = next(r for r in recs if r.io_name == "ring_release")
    got = [v for _, v in seen]
    for _ in range(3):
        for _ in range(300):
            g.tick()
        g.inject(rel.row, rel.col, 0)
        more = L.run_steps(g, 3, max_ticks=500)
        assert len(more) == 1
        got += [v for _, v in more]
    assert got == L.model(len(got))[:len(got)]


def test_small_n_refused():
    with pytest.raises(ValueError):
        L.build_doc(L.DRIFT, False, True, False, ring_laps=L.MIN_RING_LAPS - 1)


# ---- the same ring on the VIXeN carrier grid (RTL) ----
import shutil, tempfile
sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "..", "tools")]
needs_iverilog = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
KEEP = ("ram", "adder", "branch", "accum")


def _rtl(n, clocks, extra=()):
    import carrier_grid_v3 as G
    recs = L.build_records(join=True, ring_laps=n)
    inp = next(r for r in recs if r.io_name == "z_input")
    rel = next(r for r in recs if r.io_name == "ring_release")
    tap = next(r.cell_id for r in recs if r.cell_id.endswith("fb19"))
    loads = [(40, inp.cell_id, L.Z0)] + [(t, rel.cell_id, 0) for t in extra]
    return [v for _, v in G.simulate(recs, tap, clocks, loads=loads, workdir=tempfile.mkdtemp(), keep=KEEP)]


@needs_iverilog
@pytest.mark.parametrize("n", [5, 6, 9])
def test_carrier_rtl_stops_after_exactly_n_laps(n):
    assert _rtl(n, 2500) == L.model(n)[:n]


@needs_iverilog
def test_carrier_rtl_release_gives_one_lap_each_time():
    got = _rtl(6, 4000, extra=(2200, 3200))
    assert got == L.model(8)[:8]
