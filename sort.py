"""
sort.py — Parallel Sorting Networks on the Imago UniCell VM

Two implementations:

1. BIT SORT (1-bit values, n up to 256)
   Each compare-and-swap: AND (min) + OR (max) = 2 cells
   n=64:  300 comparators = 600 cells,  depth 21
   n=128: 784 comparators = 1,568 cells, depth 28  
   n=256: 2,048 comparators = 4,096 cells, depth 36
   Input: n bit-values (0 or 1)
   Output: all 1s at top, all 0s at bottom (population sort)

2. BYTE SORT (8-bit unsigned values, n up to 32)
   Each compare-and-swap: 8-bit cascaded comparator + 2×8-bit MUX
   ~41 cells per comparator
   n=16: 80 comparators = 3,280 cells, depth 10 stages
   n=32: 240 comparators = 9,840 cells, depth 15 stages
   Input: n byte values (0-255)
   Output: sorted ascending

Both use a bitonic sorting network — all comparators within a stage
fire simultaneously. The sorted result emerges in log²(n) parallel stages.

Usage:
    python3 sort.py --mode bits --n 64
    python3 sort.py --mode bits --n 256
    python3 sort.py --mode bytes --n 16 --data 57,12,140,125,114,71,52,44
    python3 sort.py --mode bytes --n 32 --random
    python3 sort.py --benchmark
"""

import argparse, random, time
import imago_log
imago_log.set_level(imago_log.SILENT)

from gate_states import (GS_AND_V2, GS_OR_V2, GS_XOR_V2, GS_NAND_V2,
                         GS_XNOR_V2, GS_NOT, GS_PASS, GS_SYNC_WAIT,
                         GS_OUT_POSEDGE)
from controller import ImagoController, CellMapRecord


# ── Gate primitives ───────────────────────────────────────────────────────────

def AND(a, b, out):
    return [CellMapRecord(GS_AND_V2|GS_SYNC_WAIT|GS_OUT_POSEDGE,
                          a, out, input_b_address=b)]

def OR(a, b, out):
    return [CellMapRecord(GS_OR_V2|GS_SYNC_WAIT|GS_OUT_POSEDGE,
                          a, out, input_b_address=b)]

def XOR(a, b, out):
    return [CellMapRecord(GS_XOR_V2|GS_SYNC_WAIT|GS_OUT_POSEDGE,
                          a, out, input_b_address=b)]

def XNOR(a, b, out):
    return [CellMapRecord(GS_XNOR_V2|GS_SYNC_WAIT|GS_OUT_POSEDGE,
                          a, out, input_b_address=b)]

def NOT(a, out):
    return [CellMapRecord(GS_NOT|GS_OUT_POSEDGE, a, out)]

def PASS(a, out):
    return [CellMapRecord(GS_PASS|GS_OUT_POSEDGE, a, out)]




# ── 32-bit integer bitonic sort ───────────────────────────────────────────────

def build_int32_sort(n):
    """
    Build a bitonic sort network for n unsigned 32-bit integers.

    Each compare-and-swap is built fresh using the Kogge-Stone subtractor:
      lt    = NOT(carry_out of (a + NOT(b) + 1))  = a < b unsigned
      min_i = (a[i] AND lt) OR (b[i] AND NOT lt)
      max_i = (b[i] AND lt) OR (a[i] AND NOT lt)

    No relay cells — tile inputs are wired directly to element/layer slots.

    Cell count: ~775 cells per comparator (KS subtractor + MUX trees)
    n=4:  6 comparators  ~4,650 cells
    n=8:  24 comparators ~18,600 cells
    n=16: 80 comparators ~62,000 cells

    Returns (records, input_addrs, output_addrs, carry_in_addrs)
    input_addrs[i] = [addr_bit0, ..., addr_bit31] for element i
    carry_in_addrs: must all be pre-loaded to 1 before running
    """
    from fp_tiles import TileAddressAllocator, NORBuilder, _build_int32_add_ks

    stages = bitonic_network(n)
    total_stages = len(stages)
    BASE = 0x10000
    SLOT = 32  # addresses per element per layer

    def slot_addr(elem, layer, bit):
        return BASE + (elem * (total_stages + 2) + layer) * SLOT + bit

    input_addrs  = [[slot_addr(i, 0,            b) for b in range(32)] for i in range(n)]
    output_addrs = [[slot_addr(i, total_stages, b) for b in range(32)] for i in range(n)]

    all_records  = []
    carry_ins    = []
    int_base     = BASE + n * (total_stages + 2) * SLOT + 0x1000
    ptr          = [int_base]

    def fresh_alloc(count):
        addr = ptr[0]; ptr[0] += count + 16; return addr

    for stage_idx, stage in enumerate(stages):
        paired = set()
        for (lo, hi) in stage:
            lo_in  = [slot_addr(lo, stage_idx,     b) for b in range(32)]
            hi_in  = [slot_addr(hi, stage_idx,     b) for b in range(32)]
            lo_out = [slot_addr(lo, stage_idx + 1, b) for b in range(32)]
            hi_out = [slot_addr(hi, stage_idx + 1, b) for b in range(32)]

            alloc = TileAddressAllocator(fresh_alloc(800))
            bld   = NORBuilder(alloc)
            for a in lo_in + hi_in:
                bld.depth_map[a] = 0
            ci = alloc.alloc()
            bld.depth_map[ci] = 0
            carry_ins.append(ci)

            nhi = [bld.NOT(hi_in[i]) for i in range(32)]
            ks_bld, _sum, carry_out = _build_int32_add_ks(alloc, lo_in, nhi, ci)
            bld.records.extend(ks_bld.records)
            bld.depth_map.update(ks_bld.depth_map)

            lt  = bld.NOT(carry_out)
            nlt = bld.NOT(lt)
            for b in range(32):
                mn = bld.OR2(bld.AND2(lo_in[b], lt),  bld.AND2(hi_in[b], nlt))
                mx = bld.OR2(bld.AND2(hi_in[b], lt),  bld.AND2(lo_in[b], nlt))
                if mn != lo_out[b]:
                    bld.records.append(
                        CellMapRecord(GS_PASS | GS_OUT_POSEDGE, mn, lo_out[b]))
                if mx != hi_out[b]:
                    bld.records.append(
                        CellMapRecord(GS_PASS | GS_OUT_POSEDGE, mx, hi_out[b]))

            all_records.extend(bld.records)
            paired.add(lo); paired.add(hi)

        # Pass-through for unpaired elements
        for i in range(n):
            if i not in paired:
                for b in range(32):
                    all_records.append(CellMapRecord(
                        GS_PASS | GS_OUT_POSEDGE,
                        slot_addr(i, stage_idx,     b),
                        slot_addr(i, stage_idx + 1, b)))

    return all_records, input_addrs, output_addrs, carry_ins


def run_int32_sort(n=8, values=None, verbose=True):
    """Sort n unsigned 32-bit integers using a bitonic network."""
    if values is None:
        rng = random.Random(42)
        values = [rng.randint(0, 2**32 - 1) for _ in range(n)]
    assert len(values) == n

    if verbose:
        print(f"\nINT32 sort: n={n}")
        print(f"  Input:  {values}")

    t_build = time.time()
    records, in_addrs, out_addrs, carry_ins = build_int32_sort(n)
    build_ms = (time.time() - t_build) * 1000

    stages = bitonic_network(n)
    comps  = sum(len(s) for s in stages)
    cells_per = len(records) // comps if comps else 0

    if verbose:
        print(f"  Network: {len(stages)} stages, {comps} comparators")
        print(f"  Cells:   {len(records):,} total (~{cells_per} per comparator)")

    ctrl = ImagoController(cell_count=len(records) + 10000)
    ctrl.array._segments[0].lane_count = len(records) * 3

    known = {ci: 1 for ci in carry_ins}
    for i, val in enumerate(values):
        for b in range(32):
            known[in_addrs[i][b]] = (val >> b) & 1

    t_run = time.time()
    flat_out = [out_addrs[i][b] for i in range(n) for b in range(32)]
    rid = ctrl.load_map(records, f"int32_sort_{n}", known_values=known)
    result = ctrl.run(rid, inputs={}, capture_addresses=flat_out,
                      max_cycles=len(records) * 5)
    run_ms = (time.time() - t_run) * 1000

    if not result:
        if verbose: print("  FAILED: no result")
        return None, False, run_ms

    output = [sum(result.get(out_addrs[i][b], 0) << b for b in range(32))
              for i in range(n)]
    expected = sorted(values)
    ok = output == expected

    if verbose:
        print(f"  Output: {output}")
        print(f"  Result: {'✓ CORRECT' if ok else '✗ WRONG'}")
        print(f"  Build:  {build_ms:.0f}ms  Run: {run_ms:.0f}ms")

    return output, ok, run_ms

# ── Bitonic network generator ─────────────────────────────────────────────────

def bitonic_network(n):
    """Return list of stages; each stage is list of (lo_idx, hi_idx) pairs.
    In each pair: lo_idx should hold the smaller value (min), hi the larger."""
    stages = []
    k = 2
    while k <= n:
        j = k // 2
        while j >= 1:
            stage = []
            for i in range(n):
                l = i ^ j
                if l > i:
                    if (i & k) == 0:
                        stage.append((i, l))
                    else:
                        stage.append((l, i))
            stages.append(stage)
            j //= 2
        k *= 2
    return stages


# ── 1-bit bitonic sort ────────────────────────────────────────────────────────

STRIDE_BIT = 4   # address slots per element in bit sort

def bit_sort_addr(i, layer, total_layers):
    """Bus address for bit sort element i in layer."""
    # Each element has STRIDE_BIT addresses: one per pipeline layer
    return 0x10000 + i * STRIDE_BIT * total_layers + layer * STRIDE_BIT

def build_bit_sort(n):
    """
    Build a bitonic sort network for n 1-bit values.
    Returns (records, input_addrs, output_addrs, known_values_template)
    """
    stages = bitonic_network(n)
    total_stages = len(stages)

    # Address scheme: element i at layer L → addr = base + i*stride + L
    BASE = 0x10000
    STRIDE = total_stages + 2

    def addr(i, layer):
        return BASE + i * STRIDE + layer

    # Layer 0 = input addresses (pre-injected)
    input_addrs  = [addr(i, 0) for i in range(n)]
    output_addrs = [addr(i, total_stages) for i in range(n)]

    records = []
    # For each stage, build the compare-and-swap cells
    # Elements not in a comparator pair need PASS cells to advance their layer
    for stage_idx, stage in enumerate(stages):
        in_layer  = stage_idx
        out_layer = stage_idx + 1
        paired = set()
        for (lo, hi) in stage:
            # min(a,b) = a AND b → goes to lo's next layer
            records += AND(addr(lo, in_layer), addr(hi, in_layer),
                          addr(lo, out_layer))
            # max(a,b) = a OR b → goes to hi's next layer
            records += OR(addr(lo, in_layer), addr(hi, in_layer),
                         addr(hi, out_layer))
            paired.add(lo); paired.add(hi)
        # Pass-through for unpaired elements
        for i in range(n):
            if i not in paired:
                records += PASS(addr(i, in_layer), addr(i, out_layer))

    return records, input_addrs, output_addrs


def run_bit_sort(n=64, values=None, verbose=True):
    """Sort n bits using a bitonic network."""
    if values is None:
        rng = random.Random(42)
        values = [rng.randint(0, 1) for _ in range(n)]

    assert len(values) == n
    assert all(v in (0, 1) for v in values)

    if verbose:
        print(f"\nBit sort: n={n}")
        print(f"  Input:  {''.join(str(v) for v in values)}")

    records, in_addrs, out_addrs = build_bit_sort(n)

    if verbose:
        stages = bitonic_network(n)
        comps = sum(len(s) for s in stages)
        print(f"  Network: {len(stages)} stages, {comps} comparators, "
              f"{len(records)} cells")

    ctrl = ImagoController(cell_count=len(records) + 1000)
    ctrl.array._segments[0].lane_count = len(records) * 3

    known = {in_addrs[i]: values[i] for i in range(n)}
    t0 = time.time()
    rid = ctrl.load_map(records, f"bit_sort_{n}", known_values=known)
    result = ctrl.run(rid, inputs={}, capture_addresses=out_addrs,
                      max_cycles=len(records) * 5)
    elapsed = (time.time() - t0) * 1000

    if result is None:
        print("  FAILED: no result")
        return None

    output = [result.get(a, 0) for a in out_addrs]
    expected = sorted(values)
    ok = output == expected

    if verbose:
        print(f"  Output: {''.join(str(v) for v in output)}")
        print(f"  Result: {'✓ CORRECT' if ok else '✗ WRONG'}")
        print(f"  Time:   {elapsed:.0f}ms")

    return output, ok, elapsed


# ── 8-bit compare-and-swap ────────────────────────────────────────────────────

def build_8bit_cas(a_addrs, b_addrs, min_addrs, max_addrs, tmp_base):
    """
    8-bit compare-and-swap: given two 8-bit values A and B (each 8 bus addresses),
    output min(A,B) and max(A,B).

    Uses cascaded priority comparator from MSB down:
      - XNOR(a[i],b[i]): 1 if equal at bit i
      - Equal mask: AND of all higher XNOR bits (bits above i are equal)
      - Deciding bit: AND(equal_mask, XOR(a[i],b[i]))
    
    a_less = OR of all: AND(equal_above_i, a[i]=0, b[i]=1)
           = 1 if A < B
    
    min = MUX(a_less, A, B): if a<b then A else B
    max = MUX(a_less, B, A): if a<b then B else A
    
    8-bit MUX: 3 cells per bit (NOT(sel), AND(a,sel), AND(b,not_sel), OR → 4 cells)
    Actually: mux(sel,a,b) = (a AND sel) OR (b AND NOT sel) = 3-4 cells per bit
    
    ~41 cells total.
    Returns list of CellMapRecords.
    """
    recs = []
    t = tmp_base

    # Step 1: XNOR each bit pair (equal at this position)
    xnor_addrs = []
    for bit in range(8):
        xnor_addrs.append(t)
        recs += XNOR(a_addrs[bit], b_addrs[bit], t)
        t += 1

    # Step 2: cascaded equal mask (AND of all XNOR from MSB down)
    # eq_mask[7] = 1 (bits 7+ all equal — trivially, no bits above)
    # eq_mask[6] = XNOR[7]
    # eq_mask[5] = AND(XNOR[7], XNOR[6])
    # etc.
    eq_mask = [0] * 8
    eq_mask[7] = -1  # sentinel: bit 7 has no "above" bits, mask=1 always

    # For MSB, deciding factor is just XNOR and the bit value
    # a < b at bit 7: a[7]=0 AND b[7]=1 AND nothing above
    # We'll compute a_less directly:
    # a_less = OR over bits 7..0 of: (equal above bit i) AND (NOT a[i]) AND b[i]

    # Equal above bit 7: always 1 (no bits above)
    # Deciding at bit 7: NOT(a[7]) AND b[7]
    decide = []  # decide[i] = "a < b decided at bit i"

    # Bit 7 (MSB): no mask needed
    na7 = t; recs += NOT(a_addrs[7], na7); t += 1
    d7  = t; recs += AND(na7, b_addrs[7], d7); t += 1
    decide.append(d7)

    # Running equal mask: starts as XNOR[7]
    running_eq = xnor_addrs[7]

    for bit in range(6, -1, -1):
        # Deciding at this bit requires all higher bits to be equal
        # AND(running_eq, NOT(a[bit]), b[bit])
        na  = t; recs += NOT(a_addrs[bit], na); t += 1
        nb  = t; recs += AND(na, b_addrs[bit], nb); t += 1
        d   = t; recs += AND(running_eq, nb, d); t += 1
        decide.append(d)
        t += 1  # gap

        # Update running_eq = AND(running_eq, XNOR[bit])
        if bit > 0:
            new_eq = t; recs += AND(running_eq, xnor_addrs[bit], new_eq); t += 1
            running_eq = new_eq

    # a_less = OR of all decide[] 
    # Build OR tree of 8 elements
    def or_tree(addrs, base_t):
        if len(addrs) == 1:
            return addrs[0], base_t
        mid = len(addrs) // 2
        left,  base_t = or_tree(addrs[:mid], base_t)
        right, base_t = or_tree(addrs[mid:], base_t)
        out = base_t
        nonlocal recs
        recs += OR(left, right, out)
        return out, base_t + 1

    a_less, t = or_tree(decide, t)

    # min/max using 8-bit MUX
    # min(A,B): if a_less then A else B  (for each bit)
    # max(A,B): if a_less then B else A
    not_al = t; recs += NOT(a_less, not_al); t += 1

    for bit in range(8):
        # min bit: (a[bit] AND a_less) OR (b[bit] AND NOT a_less)
        ta = t; recs += AND(a_addrs[bit], a_less, ta); t += 1
        tb = t; recs += AND(b_addrs[bit], not_al, tb); t += 1
        recs += OR(ta, tb, min_addrs[bit]); t += 1

        # max bit: (b[bit] AND a_less) OR (a[bit] AND NOT a_less)
        tc = t; recs += AND(b_addrs[bit], a_less, tc); t += 1
        td = t; recs += AND(a_addrs[bit], not_al, td); t += 1
        recs += OR(tc, td, max_addrs[bit]); t += 1

    return recs, t


def build_byte_sort(n):
    """
    Build a bitonic sort for n 8-bit unsigned values.
    Each value uses 8 bus addresses (one per bit).
    Returns (records, input_addrs, output_addrs)
    where input_addrs[i] = list of 8 addresses for value i (bit 0 first)
    """
    stages = bitonic_network(n)
    total_stages = len(stages)

    # Address layout: value i, bit b, layer l
    # addr = BASE + i * (8 * (total_stages+1)) + b * (total_stages+1) + l
    BASE  = 0x20000
    L     = total_stages + 1  # layers per bit
    VSTRIDE = 8 * L           # addresses per value

    def addr(i, bit, layer):
        return BASE + i * VSTRIDE + bit * L + layer

    input_addrs  = [[addr(i, b, 0)            for b in range(8)] for i in range(n)]
    output_addrs = [[addr(i, b, total_stages) for b in range(8)] for i in range(n)]

    records = []
    # Temporaries: place after all value/layer addresses
    tmp_base = BASE + n * VSTRIDE

    for stage_idx, stage in enumerate(stages):
        in_l  = stage_idx
        out_l = stage_idx + 1
        paired = set()

        for (lo, hi) in stage:
            lo_in  = [addr(lo, b, in_l)  for b in range(8)]
            hi_in  = [addr(hi, b, in_l)  for b in range(8)]
            lo_out = [addr(lo, b, out_l) for b in range(8)]
            hi_out = [addr(hi, b, out_l) for b in range(8)]
            new_recs, tmp_base = build_8bit_cas(lo_in, hi_in, lo_out, hi_out, tmp_base)
            records.extend(new_recs)
            paired.add(lo); paired.add(hi)

        # Pass-through for unpaired elements
        for i in range(n):
            if i not in paired:
                for b in range(8):
                    records += PASS(addr(i, b, in_l), addr(i, b, out_l))

    return records, input_addrs, output_addrs


def run_byte_sort(n=16, values=None, verbose=True):
    """Sort n unsigned bytes using a bitonic network."""
    if values is None:
        rng = random.Random(42)
        values = [rng.randint(0, 255) for _ in range(n)]

    assert len(values) == n

    if verbose:
        print(f"\nByte sort: n={n}")
        print(f"  Input:  {values}")

    records, in_addrs, out_addrs = build_byte_sort(n)

    stages = bitonic_network(n)
    comps = sum(len(s) for s in stages)
    cells_per_comp = len(records) // comps if comps else 0
    if verbose:
        print(f"  Network: {len(stages)} stages, {comps} comparators")
        print(f"  Cells:   {len(records):,} total (~{cells_per_comp} per comparator)")

    ctrl = ImagoController(cell_count=len(records) + 10000)
    ctrl.array._segments[0].lane_count = len(records) * 3

    # Pre-inject all input values as known_values (bit by bit)
    known = {}
    for i, val in enumerate(values):
        for b in range(8):
            known[in_addrs[i][b]] = (val >> b) & 1

    t0 = time.time()
    rid = ctrl.load_map(records, f"byte_sort_{n}", known_values=known)
    flat_out = [out_addrs[i][b] for i in range(n) for b in range(8)]
    result = ctrl.run(rid, inputs={}, capture_addresses=flat_out,
                      max_cycles=len(records) * 5)
    elapsed = (time.time() - t0) * 1000

    if result is None:
        print("  FAILED: no result")
        return None

    output = []
    for i in range(n):
        val = sum(result.get(out_addrs[i][b], 0) << b for b in range(8))
        output.append(val)

    expected = sorted(values)
    ok = output == expected

    if verbose:
        print(f"  Output: {output}")
        print(f"  Result: {'✓ CORRECT' if ok else '✗ WRONG'}")
        if not ok:
            print(f"  Expect: {expected}")
        print(f"  Time:   {elapsed:.0f}ms")

    return output, ok, elapsed


# ── Benchmark ─────────────────────────────────────────────────────────────────

def benchmark():
    print("=== UniCell Sorting Network Benchmark ===\n")
    rng = random.Random(99)

    print("── 1-bit Bitonic Sort ──")
    for n in [16, 32, 64, 128]:
        vals = [rng.randint(0,1) for _ in range(n)]
        _, ok, ms = run_bit_sort(n, vals, verbose=False)
        stages = bitonic_network(n)
        comps = sum(len(s) for s in stages)
        from sort import build_bit_sort
        recs,_,_ = build_bit_sort(n)
        print(f"  n={n:4d}: {len(recs):5d} cells, {len(stages):2d} stages, "
              f"{comps:4d} comps — {'✓' if ok else '✗'}  {ms:.0f}ms")

    print("\n── 8-bit Byte Sort ──")
    for n in [8, 16, 32]:
        vals = [rng.randint(0,255) for _ in range(n)]
        _, ok, ms = run_byte_sort(n, vals, verbose=False)
        stages = bitonic_network(n)
        comps = sum(len(s) for s in stages)
        recs,_,_ = build_byte_sort(n)
        print(f"  n={n:4d}: {len(recs):6,d} cells, {len(stages):2d} stages, "
              f"{comps:4d} comps — {'✓' if ok else '✗'}  {ms:.0f}ms")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Parallel sorting networks on UniCell VM")
    p.add_argument("--mode", choices=["bits","bytes","int32","benchmark"], default="bits")
    p.add_argument("--n",    type=int, default=32)
    p.add_argument("--data", type=str, default=None,
                   help="Comma-separated input values")
    p.add_argument("--random", action="store_true", dest="rand")
    p.add_argument("--seed",  type=int, default=42)
    args = p.parse_args()

    if args.mode == "benchmark":
        benchmark()
    elif args.mode == "int32":
        vals = None
        if args.data:
            vals = [int(x) for x in args.data.split(",")]
        elif args.rand or vals is None:
            rng = random.Random(args.seed)
            vals = [rng.randint(0, 2**32 - 1) for _ in range(args.n)]
        run_int32_sort(args.n, vals[:args.n])
    elif args.mode == "bits":
        vals = None
        if args.data:
            vals = [int(x) for x in args.data.split(",")]
        elif args.rand or vals is None:
            rng = random.Random(args.seed)
            vals = [rng.randint(0,1) for _ in range(args.n)]
        run_bit_sort(args.n, vals[:args.n])
    else:
        vals = None
        if args.data:
            vals = [int(x) for x in args.data.split(",")]
        elif args.rand or vals is None:
            rng = random.Random(args.seed)
            vals = [rng.randint(0,255) for _ in range(args.n)]
        run_byte_sort(args.n, vals[:args.n])
