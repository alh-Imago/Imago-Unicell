# fp32 (MIF split-float) pipeline -> cells, and where the second output ports are used

Ledger #982 (Alan, 2026-10-06: "map those and test"). Companion test: `tests/vm/test_fp32_stage_map_cells_v1.py` (real generated RTL in iverilog == FlexGrid == the Python models).
Python models: `nano/fp32_boundary_v1.py`, `fp32_add_v1.py`, `fp32_mul_v1.py`, `fp32_compare_v1.py`, `fp32_min_max_v1.py`. Cells are flex (v4sa) cells; the ICM flags are `second_output` (+ optional `second_downstream_mask`).

Status words: **PROVEN HERE** = a design of real cells run in RTL and the VM by the companion test; **EARLIER** = a mechanism proven in a prior ledger entry (named), not re-run here; **MODEL ONLY** = exists as a Python model, no cell design yet; **NO CELL** = the function has no cell that does it today.

## Operand convention for 32-bit cells
Significands are LEFT-ALIGNED in the word (sig << 8). A 32-bit cell then sees the 24-bit significand's own carries: the adder's carry out of bit 31 is the significand overflow, and the multiplier's 64-bit product is P48 << 16, so the HIGH word's top bit is the product's bit 47. (At a 24-bit cell width the same holds without shifting; FlexGrid at W24 shows it in `test_flex_grid_mif_fit_v1.py`, #978.)

## Stage map

| # | Stage (model function) | Cells | Second port? | Status |
|---|---|---|---|---|
| 1 | UNPACK sign+exponent (`extract_sign_exp`) | relay `ram` with the shift add-on (shift right 23) | no | **PROVEN HERE** (RTL == VM == model, random floats + 0, 1.0, -2.5, all-ones); mechanism EARLIER #697/#839 |
| 2 | UNPACK mantissa (`extract_mantissa`) | `ram` relays with mask / shift add-ons (the double mask-shift) | no | EARLIER #697/#839 |
| 3 | restore implicit 1 (`restore_implicit_one`) | OR of a constant (merge / adder with a constant) | no | MODEL ONLY |
| 4 | exponent difference, pick the larger (add path) | `adder` (subtract_mode) + `comparator` / `branch` | the subtract's carry (NOT-borrow) is the "which is larger" bit, available as a second word | MODEL ONLY |
| 5 | ALIGN: shift the smaller significand right by the exponent difference (`_align_wide`) | the shift add-on takes a CONSTANT amount | -- | **NO CELL for a data-dependent shift** (options: a branch tree choosing among constant-shift paths, or a sequencer-driven shift-by-1 loop; neither built) |
| 6 | significand ADD / SUB (24-bit) | `adder` | **carry word = the overflow = normalise trigger** | **PROVEN HERE** (add: sum word to `SUM`, carry word straight into the exponent adder) |
| 7 | NORMALISE, add overflow: shift right 1, exponent + 1 | exponent `adder` (exp + carry); the shift-right-1 is the shift add-on | uses the carry from #6, routed with `second_downstream_mask` to a different consumer than the sum | exponent bump **PROVEN HERE**; the conditional shift of the sum is NOT built (needs the carry to choose a path: `branch` on the carry word) |
| 8 | NORMALISE, subtract: left-shift to the leading 1 | -- | -- | **NO CELL** (leading-zero detect + data-dependent left shift) |
| 9 | significand MUL (24 x 24 -> 48) | `mul` (or `mul_dsp`) | **high word = bits 24..47 (or P48>>16 at 32 bits)**; the low word carries the guard/sticky bits | both words **PROVEN HERE** (`LO`, `HIX` equal the 64-bit product's halves) |
| 10 | exponent add (a_exp + b_exp - 127) | `adder` x2 (the 127 as a constant `ram`) | no | MODEL ONLY (the test feeds the exponent sum in) |
| 11 | NORMALISE, mul: product bit 47 -> exponent + 1, choose shift 24 / 23 | high word -> shift add-on (bit 31 -> 0/1) -> exponent `adder` | high word fanned out by a `ram` (to the exit and to the bit extractor) | exponent bump **PROVEN HERE**; the choice of shift for the significand is NOT built (same "branch on the bit" as #7) |
| 12 | GUARD / STICKY (`guard`, `sticky`) | guard: mask / shift add-on on the low word; sticky: `comparator` (!= 0) on the discarded bits | no | EARLIER #846 (the G/R/S split mechanism, built as a placed grid); sticky reduction NOT built |
| 13 | ROUND to nearest even (`round_to_nearest_even`) | `adder` (+1) chosen by guard / sticky / lsb through a `branch` | no | MODEL ONLY |
| 14 | rounding overflow (sig reaches 2^24): shift right 1, exponent + 1 | `adder` carry again (a second use of the carry word) | **second_output** on the +1 adder | MODEL ONLY |
| 15 | strip the implicit 1, PACK (`pack`) | mask add-on; shift-left add-on; OR-merge of the two non-overlapping fields | no | EARLIER #839/#692-#696 |
| 16 | COMPARE / MIN / MAX (`fp32_compare`, `fp32_min`) | order key (mask/xor add-ons) -> `comparator` gives the 0/1 result; the SELECT is a `branch` (emit in1 / in2 per outcome) | no (comparator stays result-only, #978 ruling) | MODEL ONLY |

## What the second ports buy in this pipeline
* **Add path:** the carry word replaces a separate "is bit 24 set" detector. It goes straight to the exponent adder (#7) and, later, to rounding overflow (#14). Without `second_downstream_mask` the carry would have had to share the sum's consumer.
* **Mul path:** the high word is the significand (#9) and its top bit is the normalise test (#11): one multiplier cell, two ports, no 64-bit product wire and no second multiplier (the sequential `mul_cell_v5` of #853 is not needed on flex).
* **Cost:** the port is built only on cells whose ICM flag is set (default off). At the card's 18-bit width adder +4 LUT4, LUT multiplier roughly 2x, DSP multiplier 5 -> 8 LUT4 (sweep data, `docs/measurements/flex_width_sweep_975/`).
* **Not needed:** compare/min/max, pack/unpack, guard/sticky -- the second ports do not touch them.

## What is still missing for a full fp32 add or multiply on cells (honest list)
1. A way to shift by a DATA value (stage 5 align, stage 8 left-normalise, the shift-choice of #7 and #11). The add-ons shift by a configured constant.
2. Leading-zero detection (stage 8).
3. The conditional path selection (a `branch` on the carry / normalise bit steering the sum word to the shift-by-1 or shift-by-0 path) -- the pieces exist, the design is not built.
4. Sticky reduction and the round-to-nearest-even select (stages 12-13).
5. The generator is a 32-bit build: the 24-bit cells (the card's natural significand width) are covered by the VM test (#978) and the cost sweep, not by a functional RTL bench.
