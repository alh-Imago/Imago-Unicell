# Kogge-Stone 32-bit Adder — UniCell Mapping

Captured 2026-05-18. Reference for INT32 two-arrival implementation.

## Architecture

Parallel-prefix adder (Kogge-Stone). Minimises depth at cost of cell count.

```
G[i] = A[i] & B[i]          (generate)
P[i] = A[i] ^ B[i]          (propagate)
C[i+1] = G[i] | (P[i] & C[i])  (carry)
```

Prefix network reduces carry depth from 32 to 5 levels.

## Cell types

AND, OR, XOR — all 32-bit wide, all two-arrival.

## Stage 0 — P[i] and G[i]

64 UniCells (32 XOR + 32 AND). Packet schedule per bit i:

```
Send A[i] → XOR_i         (first arrival, stored in a_data)
Send B[i] → XOR_i fires   (second arrival, triggers) → P[i]

Send A[i] → AND_i         (first arrival, stored)
Send B[i] → AND_i fires   (second arrival, triggers) → G[i]
```

**KEY POINT**: A and B both go to the SAME cell's input_address, sequentially.
No relay cells. No separate B address. The cell holds A and waits for B.

Depth: 2 cycles per bit (all bits in parallel).

## Stages 1-5 — Prefix Tree

Each stage doubles span. Each prefix node computes G' and P':

```
G' = G_hi | (P_hi & G_lo)
P' = P_hi & P_lo
```

Maps to 3 UniCells per node:
- AND1: P_hi & G_lo
- OR1:  G_hi | AND1  → G'
- AND2: P_hi & P_lo  → P'

Packet schedule for G' computation:
```
Cycle k:   send P_hi → AND1        (first arrival)
Cycle k+1: send G_lo → AND1 fires  (second arrival)
Cycle k+2: send G_hi → OR1         (first arrival)
Cycle k+3: send AND1_out → OR1 fires → G'  (second arrival)
```

Packet schedule for P':
```
Cycle k:   send P_hi → AND2        (first arrival)
Cycle k+1: send P_lo → AND2 fires → P'  (second arrival)
```

Depth per stage: 4 cycles. Total prefix: 5 × 4 = 20 cycles.

## Final Stage — SUM[i]

32 XOR cells. Packet schedule:
```
Send P[i] → XOR_sum_i         (first arrival)
Send C[i] → XOR_sum_i fires   (second arrival) → SUM[i]
```

## Totals

| Stage      | Cycles |
|------------|--------|
| P/G gen    | 2      |
| Prefix × 5 | 20     |
| Final sum  | 2      |
| **Total**  | **24** |

| Function         | Cells |
|-----------------|-------|
| P[i] XOR × 32  | 32    |
| G[i] AND × 32  | 32    |
| Prefix (3 × 31 × 5) | 465 |
| Final XOR × 32 | 32    |
| **Total**       | **561** |

## Implementation note for fp_tiles / run_int32_function

The packet schedule above shows A and B arrive at the SAME input_address.
The correct implementation:

1. Tile placer: when placing a binary op tile, merge in_b addresses to in_a
   addresses — OR — keep them separate and have run_int32_function inject
   A first then B at the same address.

2. No relay cells needed for internal chain cells. Upstream cells fire
   naturally and their outputs arrive sequentially at downstream cells.

3. run_int32_function must inject in this order:
   - A bits at shared_addr[i] (first arrivals, stored)
   - B bits at shared_addr[i] (second arrivals, trigger)

4. _pending_inputs re-injection in controller.run() should NOT re-inject
   binary op shared addresses (would cause spurious second A firing).

## Brent-Kung alternative

Brent-Kung has 9 prefix levels vs KS's 5, giving ~30-35 cycles vs ~24.
More cells saved but worse depth. For depth-first design, KS is preferred.
