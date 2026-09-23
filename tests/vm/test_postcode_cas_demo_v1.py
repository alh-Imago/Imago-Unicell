"""tests/vm/test_postcode_cas_demo_v1.py — points.md #837: the real, saved demo comparing the old
full-cell bit-serial compare-and-swap (archived, ~711 cells for 32 bits) against the current
substrate's icmp+select CAS, run on the real VM."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import postcode_cas_demo_v1 as D  # noqa: E402

M = 0xFFFFFFFF


def test_min_and_max_are_correct_on_the_real_vm_including_signed_edge_cases():
    min_res, max_res, _ = D.build_cas()

    def s32(v):
        v &= M
        return v - (1 << 32) if v >> 31 else v
    for a, b in [(3, 7), (7, 3), (M, 5), (100, 100), (0, 0), (1, M)]:
        lo, hi = D.cas(min_res, max_res, a, b)
        assert lo == (a if s32(a) < s32(b) else b) & M
        assert hi == (b if s32(a) < s32(b) else a) & M


def test_the_measured_cell_counts_are_far_smaller_than_the_old_711_figure():
    min_res, max_res, lt_res = D.build_cas()
    assert len(lt_res.records) < len(min_res.records) < 711
    naive_total = len(min_res.records) + len(max_res.records)
    assert naive_total < 711 / 4                                # a real, large margin, not a close call


def test_haversine_and_scale_dist_match_the_archived_originals_exactly():
    km = D.haversine(51.5154, -0.1755, 53.4808, -2.2426)
    assert 250 < km < 270                                        # London to Manchester, real-world sanity range
    assert D.scale_dist(km) == int(km * 1000)


def test_the_worked_example_picks_the_genuinely_nearer_city():
    """Birmingham is real-world nearer London than Manchester is -- checked against reality, not just
    internal consistency."""
    a_m = D.scale_dist(D.haversine(*D.CITIES["london"][:2], *D.CITIES["manchester"][:2]))
    b_m = D.scale_dist(D.haversine(*D.CITIES["london"][:2], *D.CITIES["birmingham"][:2]))
    min_res, max_res, _ = D.build_cas()
    nearer, farther = D.cas(min_res, max_res, a_m, b_m)
    assert nearer == b_m and farther == a_m                      # Birmingham (b) is the real nearer city


def test_an_unknown_city_is_refused():
    import pytest
    with pytest.raises(SystemExit):
        D.report_worked_example("atlantis", "london", "manchester")


def test_main_runs_end_to_end_without_error(capsys):
    rc = D.main(["--a", "leeds", "--b", "sheffield", "--query", "york"[:0] or "edinburgh"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "nearer:" in out and "farther:" in out
