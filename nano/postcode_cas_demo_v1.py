"""
postcode_cas_demo_v1.py — points.md #837: the old full-cell `postcode_sort.py` demo (archived,
`old_demo_algorithms.onion`), re-measured on the CURRENT substrate's compare-and-swap primitive.

Alan asked, after finding the old demo in the archive: would the newer core designs make this more
efficient on the current (VIX-generation) substrate? Checked directly, not assumed -- built and RAN a
real compare-and-swap through `llvm_dag_frontend_v1.compile_llvm_via_dag` (the same tested path used
throughout this session's DSP/BRAM work), not reasoned about in the abstract.

THE OLD CAS (`sort.py`'s `build_8bit_cas`, read directly from the archive before comparing against
it). Built entirely from primitive gates -- XNOR each bit pair, a cascaded AND-chain to find the first
differing bit, an OR-tree over 8 decision bits, then a 3-4-cell mux per bit for the swap: ~41 cells for
an 8-BIT compare alone (`postcode_sort.py`'s own docstring gives 711 cells for a full 32-bit
comparator). This is exactly what you would expect from an architecture with no dedicated compare or
add core: every comparison has to be built one NOR-universal gate at a time.

THE CURRENT CAS. A comparison is `icmp` (lowers to `sub` + `cmp_ge`, `#798`) and the swap is `select`'s
already-proven mask-and-merge (`#798`/`#803`) -- whole-32-bit-word operations, not bit-serial gate
cascades. MEASURED here, not estimated: `icmp slt` alone is 13 cells; a full `icmp`+`select` (one
compare, one swap) is 60 cells; TWO independent compiles (min and max, no sharing at all -- the naive,
worst case) together are 120 cells. Even without sharing the comparison between min and max, that is
already roughly 6x fewer cells than the old system's 711 -- a categorical difference (whole-word
operations vs. one gate per cell), not a tuning improvement. Isolating the comparison's own cost (13 of
the 60) suggests a HAND-SHARED version (one comparison feeding two selects) would land near 13 + 2x47 =
107 cells -- a reasoned estimate from the measured pieces, not a separately re-verified construction,
stated as such.

THE WORKED EXAMPLE. The old demo's own `CITIES` dict and `haversine()` function, used UNMODIFIED --
Haversine itself runs in plain Python here exactly as it did in the original (this was never run on the
fabric in either version); only the COMPARISON -- which of two candidate postcodes is nearer the query
point -- runs on the real VM, on the current substrate's own CAS.

HONEST LIMITS. This demonstrates ONE compare-and-swap, verified correct on the real VM across signed-
comparison edge cases (a negative-as-unsigned value, an equal pair) -- not a full N-element sort network
the way the old demo built via `sort.py`'s bitonic network. The current LLVM frontend takes scalar i32
arguments only, so a genuine N-way sort would need real, separate DAG-level construction (chaining many
CAS units with shared placement) that has not been attempted here. The real postcode dataset (~1.2M UK
postcodes, per Alan) is not bundled with this demo -- it uses the same small, real city-coordinate table
the archived original did, as a real, checkable worked example, not a claim of dataset parity.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import llvm_dag_frontend_v1 as F  # noqa: E402

M32 = 0xFFFFFFFF

# ---------------------------------------------------------------------------
# Unmodified from the archived original (old_demo_algorithms.onion/postcode_sort.py)
# ---------------------------------------------------------------------------

CITIES = {
    "london":     (51.5154, -0.1755, "London Paddington"),
    "manchester": (53.4808, -2.2426, "Manchester Piccadilly"),
    "birmingham": (52.4797, -1.9026, "Birmingham New Street"),
    "glasgow":    (55.8617, -4.2583, "Glasgow Central"),
    "edinburgh":  (55.9521, -3.1965, "Edinburgh Waverley"),
    "bristol":    (51.4490, -2.5890, "Bristol Temple Meads"),
    "leeds":      (53.7960, -1.5491, "Leeds City"),
    "cardiff":    (51.4786, -3.1785, "Cardiff Central"),
    "liverpool":  (53.4084, -2.9916, "Liverpool Lime Street"),
    "sheffield":  (53.3781, -1.4620, "Sheffield"),
}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def scale_dist(km: float) -> int:
    """Integer metres -- exact, no approximation, same convention as the original."""
    return int(km * 1000)


# ---------------------------------------------------------------------------
# The current substrate's compare-and-swap: icmp + select, measured, not assumed
# ---------------------------------------------------------------------------

_MIN32 = "define i32 @min32(i32 %a, i32 %b) {\nentry:\n  %lt = icmp slt i32 %a, %b\n  %m = select i1 %lt, i32 %a, i32 %b\n  ret i32 %m\n}\n"
_MAX32 = "define i32 @max32(i32 %a, i32 %b) {\nentry:\n  %lt = icmp slt i32 %a, %b\n  %m = select i1 %lt, i32 %b, i32 %a\n  ret i32 %m\n}\n"
_LT32 = "define i32 @lt32(i32 %a, i32 %b) {\nentry:\n  %lt = icmp slt i32 %a, %b\n  %r = zext i1 %lt to i32\n  ret i32 %r\n}\n"


def build_cas():
    """Compile the current substrate's CAS once; returns (min_result, max_result, lt_only_result)."""
    min_res, d1 = F.compile_llvm_via_dag(_MIN32)
    max_res, d2 = F.compile_llvm_via_dag(_MAX32)
    lt_res, d3 = F.compile_llvm_via_dag(_LT32)
    assert d1 == d2 == d3 == [], (d1, d2, d3)
    return min_res, max_res, lt_res


def cas(min_res, max_res, a_metres: int, b_metres: int) -> tuple:
    """Run the real, compiled CAS on the real VM. Returns (nearer, farther) in metres."""
    lo = F.run_in_vm(min_res, {"a": a_metres & M32, "b": b_metres & M32})
    hi = F.run_in_vm(max_res, {"a": a_metres & M32, "b": b_metres & M32})
    return lo, hi


def report_measurement() -> None:
    min_res, max_res, lt_res = build_cas()
    print("=" * 64)
    print("  Compare-and-swap: old full-cell substrate vs. current substrate")
    print("=" * 64)
    print(f"\n  OLD (bit-serial gates, archived old_demo_algorithms.onion/sort.py):")
    print(f"    ~41 cells for an 8-bit compare alone; 711 cells for a full")
    print(f"    32-bit comparator (postcode_sort.py's own measured figure).")
    print(f"\n  CURRENT (icmp + select, whole-word operations), MEASURED just now:")
    print(f"    icmp slt alone:            {len(lt_res.records):>4d} cells")
    print(f"    icmp + select (min OR max): {len(min_res.records):>4d} cells  ({len(max_res.records)} for max)")
    print(f"    naive combined (both, unshared): {len(min_res.records) + len(max_res.records):>4d} cells")
    print(f"    -> roughly {711 / (len(min_res.records) + len(max_res.records)):.1f}x fewer cells than the old")
    print(f"       system's 711, even with NO sharing of the comparison between min and max.")
    print(f"    A hand-shared version (one compare feeding both selects) is a REASONED estimate")
    print(f"    near {len(lt_res.records) + 2 * (len(min_res.records) - len(lt_res.records))} cells,")
    print(f"    not separately re-verified as its own construction.")


def report_worked_example(city_a: str, city_b: str, query: str) -> None:
    if query not in CITIES or city_a not in CITIES or city_b not in CITIES:
        raise SystemExit(f"unknown city (choices: {', '.join(sorted(CITIES))})")
    qlat, qlon, qname = CITIES[query]
    alat, alon, aname = CITIES[city_a]
    blat, blon, bname = CITIES[city_b]
    a_m = scale_dist(haversine(qlat, qlon, alat, alon))
    b_m = scale_dist(haversine(qlat, qlon, blat, blon))
    min_res, max_res, _ = build_cas()
    nearer_m, farther_m = cas(min_res, max_res, a_m, b_m)
    nearer_name = aname if nearer_m == a_m else bname
    farther_name = bname if nearer_m == a_m else aname
    print("=" * 64)
    print(f"  Which is nearer to {qname}: {aname} or {bname}?")
    print("=" * 64)
    print(f"\n  {aname:<24s} {a_m / 1000:8.1f} km")
    print(f"  {bname:<24s} {b_m / 1000:8.1f} km")
    print(f"\n  Real compare-and-swap, run on the VM (icmp + select):")
    print(f"    nearer:  {nearer_name}  ({nearer_m / 1000:.1f} km)")
    print(f"    farther: {farther_name}  ({farther_m / 1000:.1f} km)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Real compare-and-swap on the current substrate, "
                                                 "vs. the archived full-cell figure, with a real Haversine worked example.")
    parser.add_argument("--a", default="manchester", help="first candidate city (default: manchester)")
    parser.add_argument("--b", default="birmingham", help="second candidate city (default: birmingham)")
    parser.add_argument("--query", default="london", help="query point city (default: london)")
    parser.add_argument("--measure-only", action="store_true", help="only report the cell-count comparison")
    args = parser.parse_args(argv)

    report_measurement()
    print()
    if not args.measure_only:
        report_worked_example(args.a, args.b, args.query)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
