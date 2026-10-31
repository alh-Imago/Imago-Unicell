# Store v7: look-back as a setting (plan, 31 Oct 2026)

Status: PLAN only. Nothing in this file is built. Clone path: `rtl/hexn_store_v6.v` stays untouched; v7 would be a new file.

Alan, 31 Oct 02:26/02:27: the look-back should be a value set at the start of the design. Reading taken of the 02:27 words ("and no value is 3"): **the working value to start with is 3**, the same as layer 2 today. If you meant something else, say so.

## The two numbers

| | Name | Set when | What it costs | Value |
|---|---|---|---|---|
| Maximum | `LMAX` | when the design is built | history registers, key width, number of lookup levels | 8 (proposal, see the 06:20 row: 7 was best where information sat one routine back) |
| Working value | `lookback` | at start-up, a register like `n_prom` | nothing (the lookup starts at this level and works down) | **3** |

Rule: `lookback` may be 1 to `LMAX`; a value above `LMAX` is held at `LMAX`.

## What changes from v6 (read from the v5/v6 code)

1. History: `h0, h1, h2` (three event registers) become a shift register of `LMAX` events; `hn` counts up to `LMAX` (now 0 to 3).
2. Level counter `lj` (2 bits) widens to `clog2(LMAX+1)`; the token tag `{len[1:0], e2, e1, e0}` becomes `{len, e(LMAX-1)..e0}`, so `TW = clog2(LMAX+1) + LMAX*EVB` (v5: 14 bits at 4-bit events; at LMAX 8: 36). The candidate key grows by the same amount.
3. Hash: the three-mix XOR fold of a 32-bit value cannot hold 8 events of 4 bits plus a length; it needs to be a fold over `LMAX*EVB + length` bits (a wider shift/XOR fold, or two folds). The probe order stays.
4. Per-level result registers (`an1..an3, tot1..3, bs1..3, be1..3, bv/bq/bw1..3`) are the main logic cost if copied per level. Instead keep ONE set that is overwritten whenever a longer level has entries (the selected level is the longest one with entries), plus one set for the goal read (`glvl`), so the register count does not grow with `LMAX`. This is the one design change that matters for size.
5. The loop bound: `if (lj == 3 || hn <= lj)` becomes `if (lj == lookback || hn <= lj)`.
6. Eviction (v6) is unchanged; the index scan time does not depend on the look-back. The number of evictions per command can reach `lookback` (one per level).
7. Lookup time grows with the number of levels: each level costs about `3 + 3*(1 + R)` clocks per heap row of its context; at the working value 3 it equals today's.
8. The host interface gets one new setting (`lookback`) beside `n_prom`, `w_win`, `vshift`, `glvl`; `glvl` keeps its meaning (the longest level the goal read may use).

## Check plan (when built)

- Same-answers test: v7 with `LMAX = 3`, `lookback = 3` must equal v6 on every command (the existing `tools/hexn_store_v6_check_v1.py` stream).
- Look-back test: `lookback = 3` on an `LMAX = 8` build must equal the `LMAX = 3` build; `lookback` 1 to 8 must follow a Python reference (the bit-true model `tools/hexn_store_v5.py` extended to a variable length).
- Size: yosys counts for `LMAX` 3, 6, 8 against v6, same method as the 04:10 row.

## Risks and open points

- Whether layer 3 uses this store as it is: layer 3's context elements are SNAPSHOTS (one key per sensor), not single 4-bit events. The size study (`tools/hexn_layer3_size_v1.py`) suggests a snapshot-ID table (store v5's idea of tokenising known values) so each element is a small ID; the width figures above assume that. Not designed.
- The model's best look-back changed with the world (3 in the steady one, 7 in the announced-flip one); the working value 3 is the safe start, not a result for every case.
- Mask choice (which sensors are in a context) multiplies the number of contexts; the cap of the table is the bound (05:10 row).
