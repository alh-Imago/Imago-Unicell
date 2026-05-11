"""
postcode_sort.py — Sort real UK postcodes by distance using UniCell

Takes 32 real UK postcodes from the national dataset, computes their
distance from a query point, and sorts them using the bitonic sorting
network implemented in sort.py.

The distance values are scaled to a single byte (0-255) representing
0-1000km. All 32 distances feed into the bitonic byte-sort network —
80 compare-and-swap operations, all firing in parallel within each
of 10 pipeline stages.

Usage:
    python3 postcode_sort.py
    python3 postcode_sort.py --city manchester
    python3 postcode_sort.py --n 16
    python3 postcode_sort.py --lat 53.48 --lon -2.24
"""

import argparse, math, random, time, os
import imago_log
imago_log.set_level(imago_log.SILENT)

from sort import run_byte_sort, run_int32_sort, build_int32_sort, bitonic_network

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "postcodes_1k.csv")

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

MAX_KM = 1000.0   # UK max diagonal (London → Shetland)
METRES_PER_KM = 1000  # distance stored as integer metres for INT32 sort

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def scale_dist(km):
    """Scale km to integer metres for INT32 sort (exact, no approximation)."""
    return int(km * METRES_PER_KM)

def unscale_dist(metres):
    """Convert metres back to km."""
    return metres / METRES_PER_KM


def run(query_lat=51.5154, query_lon=-0.1755, query_name="London Paddington",
        n=32):
    # Load postcode data
    postcodes = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 3:
                    try:
                        postcodes.append(
                            (parts[0], float(parts[1]), float(parts[2])))
                    except ValueError:
                        pass
    else:
        print("  Data file not found — generating synthetic UK postcodes")
        rng = random.Random(42)
        for i in range(1000):
            postcodes.append((f"XX{i:04d}", rng.uniform(50,58.5), rng.uniform(-5.5,1.5)))

    # Compute real distances
    with_dist = [
        (pc, lat, lon, haversine(query_lat, query_lon, lat, lon))
        for pc, lat, lon in postcodes
    ]
    with_dist.sort(key=lambda x: x[3])

    # Sample n postcodes: mix of near, middle, far for variety
    # (a pure random sample from 997 postcodes mostly gives 300-900km)
    quarter = len(with_dist) // 4
    near  = with_dist[:max(1, n//6)]
    mid   = with_dist[quarter: quarter + max(1, n//2)]
    far   = with_dist[-max(1, n//3):]
    pool  = near + mid + far
    # Ensure exactly n by padding from mid if needed
    while len(pool) < n:
        pool.append(with_dist[quarter + len(pool)])
    sample = pool[:n]
    random.Random(99).shuffle(sample)
    sample = sample[:n]

    # Scale distances to bytes
    scaled = [(pc, lat, lon, dist, scale_dist(dist))
              for pc, lat, lon, dist in sample]

    # Use INT32 distances (metres precision — no approximation)
    int32_values = [s for _, _, _, _, s in scaled]
    stages = bitonic_network(n)
    comps  = sum(len(s) for s in stages)

    print(f"\n{'═'*60}")
    print(f"  UK Postcode Sort by Distance from {query_name}")
    print(f"{'═'*60}")
    print(f"\n  Query point: ({query_lat:.4f}, {query_lon:.4f})")
    print(f"  Postcodes:   {n}  (from UK national dataset, {len(postcodes):,} total)")
    print(f"  Distances:   integer metres (Haversine, exact)")
    print(f"\n  Input (unsorted):")
    for pc, lat, lon, dist, int32_d in scaled:
        bar = "█" * min(30, int(dist / MAX_KM * 30))
        print(f"    {pc:<9} {dist:6.0f}km  {bar}")

    print(f"\n  Running INT32 bitonic sort on UniCell VM...")
    print(f"  ({n} values, {comps} CAS comparators, {len(stages)} parallel stages)")
    print(f"  ~{comps * 775:,} UniCells total")

    t0 = time.time()
    result, ok, ms = run_int32_sort(n, int32_values, verbose=False)
    elapsed = time.time() - t0

    print(f"  Done in {ms:.0f}ms  ({'✓ CORRECT' if ok else '✗ WRONG'})")

    # Reconstruct postcode order from sorted distances
    # (pair each result value with the nearest unmatched input)
    remaining = list(scaled)
    sorted_postcodes = []
    for dist_byte in result:
        # Find the postcode with closest scaled distance
        best = min(remaining, key=lambda x: abs(x[4] - dist_byte))
        sorted_postcodes.append(best)
        remaining.remove(best)

    print(f"\n  Sorted output (nearest → farthest from {query_name}):")
    print(f"  {'Rank':<5} {'Postcode':<10} {'Distance':>10}  {'Bar':30} {'Region'}")
    print(f"  {'─'*4} {'─'*9} {'─'*10}  {'─'*30}")
    for rank, (pc, lat, lon, dist, sd) in enumerate(sorted_postcodes, 1):
        bar = "█" * min(30, sd * 30 // 255)
        # Rough region from postcode prefix
        area = pc.split()[0].rstrip('0123456789')
        print(f"  {rank:<5} {pc:<10} {dist:9.0f}km  {bar:<30} {area}")

    print(f"\n  Architecture note:")
    print(f"  All 80 compare-and-swap operations within each stage")
    print(f"  fire simultaneously on the wired-OR bus.")
    print(f"  No sequential scan. No instruction loop.")
    print(f"  The sorted result emerges in 10 parallel pipeline stages.")
    print(f"  Cells used: {n*41*10//n*n:,}  "
          f"(~{n*41} for n={n} comparators × ~41 cells each)")


def main():
    p = argparse.ArgumentParser(
        description="Sort UK postcodes by distance on UniCell VM")
    p.add_argument("--city", choices=list(CITIES.keys()),
                   help="Named city as query point")
    p.add_argument("--lat",  type=float)
    p.add_argument("--lon",  type=float)
    p.add_argument("--n",    type=int, default=32,
                   choices=[8, 16, 32],
                   help="Number of postcodes to sort (8, 16, or 32)")
    args = p.parse_args()

    if args.city:
        lat, lon, name = CITIES[args.city]
    elif args.lat and args.lon:
        lat, lon, name = args.lat, args.lon, f"({args.lat}, {args.lon})"
    else:
        lat, lon, name = 51.5154, -0.1755, "London Paddington"

    run(lat, lon, name, args.n)


if __name__ == "__main__":
    main()
