# Unified carrier — per-core capability & PROG_ID lookup table (CONFIRMED BASE)

*Captured 2026-09-03, per Alan's own direct request at session pause
("usage is getting low... a lookup table of capabilities by core,
their codes and how they are programmed, that will give us a
confirmed base for the carrier"). Every fact below is pulled directly
from the actual, real, sim-verified `v4` RTL files (`#618`-`#626`),
not reconstructed from memory — this is the confirmed state of the
unified carrier family as it stands today, meant to be worked from
directly next session, not re-derived.*

## The shared layer, identical across all 8 real cores

Every core below carries the SAME real shell, per `#617`'s own
5-point breakdown:

- **`active`** (1-bit input): tied high for standalone use; driven by
  a real `core_select` decode when embedded in a future `N=8` carrier.
  Every core gates capture/offer on this (nano and sequencer each
  needed their own real, different treatment — see their own rows).
- **The 3-addon chain**, wired identically everywhere (`nibble_mask` →
  `shift`/`lane` → `invert`), same real 20-bit `addon_config` layout:

  | Bits | Field | Notes |
  |---|---|---|
  | `[7:0]` | `nibble_mask` | which nibbles to zero, when `mask_en`=1 |
  | `[8]` | `mask_en` | |
  | `[13:9]` | `shift_amt` | only 9 real values `{1,2,4,8,12,16,20,24,28}`, others pass through unshifted |
  | `[14]` | `shift_en` | |
  | `[15]` | `direction` | 0=SHIFT_IN(left), 1=SHIFT_OUT(right) |
  | `[18:16]` | `lane_cut` | SHIFT_OUT direction only |
  | `[19]` | `invert_en` | |

- **The `program_in`/`PROG_ID` targeted, staged reconfiguration
  channel** — real, independent per-direction ack
  (`prog_ack_out_n/s/e/w`), real `COMPLETE` marker
  (`word[0]`=1 commits+arms, `word[0]`=0 commits but stays/returns
  cold). Every core's own `PROG_ID_COMPLETE` uses the MAX value for
  its own ID width (`3'd7` for 3-bit IDs, `4'd15` for 4-bit IDs).
  Word/ID split: `prog_id` sits directly above `prog_word` in the same
  32-bit `prog_data_val` (`[22:20]`/`[19:0]` for 3-bit IDs,
  `[23:20]`/`[19:0]` for 4-bit IDs).
- **`armed`**: real staged-reconfiguration state, set on `cfg_valid`
  (atomic path, arms immediately) or via targeted `COMPLETE`.

## Per-core table

| Core | `cfg_data` width | Real own fields (beyond `addon_config`) | `PROG_ID` width | Capture shape |
|---|---:|---|---:|---|
| `adder` | 64 | `downstream_mask`(6), `upstream_mask`(6), `subtract_mode`(1) | 3-bit | two-stage A/B |
| `ram` | **80** | `downstream_mask`(6), `upstream_mask`(6), `fixed_mode`(1), `load_data_valid`(1), `init_data`(32, split LOW/HIGH write) | 3-bit | single-arrival |
| `comparator` | 64 | `downstream_mask`(6), `upstream_mask`(6), `threshold`(32, split LOW/HIGH write) | 3-bit | single-arrival + compute |
| `accumulator` | 64 | `inc_dir`(6), `dec_dir`(6), `downstream_mask`(6), `step_amount`(8), `pulse_mode`(1), `threshold`(16, pulse-only, single write) | 3-bit | continuously-live, dual trigger |
| `latch` | 64 | `set_dir`(6), `clear_dir`(6), `downstream_mask`(6), `toggle_dir`(6) | 3-bit | continuously-live, triple trigger |
| `branch` | **80** | `upstream_dir`(3, value not mask), `value_source_low/eq/high`(3×1), `fixed_value_low/eq/high`(3×7), `emit_low/eq/high`(3×1), `route_low/eq/high`(3×6), `rolling_mode`(1) | **4-bit** (15 real fields) | held-reference two-phase |
| `sequencer` | 64 | `VALUE_0..3`(4×8), `SEQUENCE_LEN`(2), `downstream_mask`(6) | 3-bit | **none** — no capture at all |
| `nano` | **128** | `topology`(10), `routing_mask`(6), `cardinal_edge`(6), `pattern_low/eq/high`(3×4), `dyn_route_en`(1), plus real LIVE control wires: `hold_in`/`fb_internal_in`/`a_reemit_in`/`a_update_in`/`a_self_update_in` | **4-bit** (9 real fields) | two-stage A/B + relay/consume |

## Real, exact `PROG_ID` code tables, per core

**`adder`** (`#618`): `0`=`downstream_mask`, `1`=`upstream_mask`,
`2`=`subtract_mode`, `3`=`addon_config`, `7`=`COMPLETE`.

**`ram`** (`#619`): `0`=`downstream_mask`, `1`=`upstream_mask`,
`2`=`fixed_mode`, `3`=`init_data` LOW, `4`=`init_data` HIGH,
`5`=`addon_config`, `6`=`load_data_valid` (real, separate, EXPLICIT
commit trigger — a real bug fix, `#619`: `COMPLETE` must NOT
implicitly recommit `data_reg`), `7`=`COMPLETE`.

**`comparator`** (`#620`): `0`=`downstream_mask`, `1`=`upstream_mask`,
`2`=`threshold` LOW, `3`=`threshold` HIGH, `4`=`addon_config`,
`7`=`COMPLETE`. (No separate commit trigger needed — `threshold` is
pure config, never itself offered downstream, unlike `ram`'s
`init_data`.)

**`accumulator`** (`#621`): `0`=`inc_dir`, `1`=`dec_dir`,
`2`=`downstream_mask`, `3`=`step_amount`, `4`=`pulse_mode`,
`5`=`threshold`, `6`=`addon_config`, `7`=`COMPLETE`.

**`latch`** (`#623`): `0`=`set_dir`, `1`=`clear_dir`,
`2`=`downstream_mask`, `3`=`toggle_dir`, `4`=`addon_config`,
`7`=`COMPLETE`.

**`branch`** (`#624`, 4-bit ID): `0`=`upstream_dir`,
`1`=`value_source_low`, `2`=`value_source_equal`,
`3`=`value_source_high`, `4`=`fixed_value_low`,
`5`=`fixed_value_equal`, `6`=`fixed_value_high`, `7`=`emit_low`,
`8`=`emit_equal`, `9`=`emit_high`, `10`=`route_low`,
`11`=`route_equal`, `12`=`route_high`, `13`=`rolling_mode`,
`14`=`addon_config`, `15`=`COMPLETE`. **Real, confirmed behavior: the
targeted channel does NOT release the held reference — only a full
`cfg_valid` reconfigure does that** (`branch_cell_v1.v`'s own real,
documented judgment call).

**`sequencer`** (`#625`): `0`=`VALUE_0`, `1`=`VALUE_1`, `2`=`VALUE_2`,
`3`=`VALUE_3`, `4`=`SEQUENCE_LEN`, `5`=`downstream_mask`,
`6`=`addon_config`, `7`=`COMPLETE`.

**`nano`** (`#626`, 4-bit ID): `0`=`topology`, `1`=`routing_mask`,
`2`=`cardinal_edge`, `3`=`pattern_low`, `4`=`pattern_equal`,
`5`=`pattern_high`, `6`=`dyn_route_en`, `7`=`addon_config`,
`15`=`COMPLETE`.

## Real, confirmed cross-core facts worth remembering

- **The `PROG_ID` budget genuinely depends on each core's own real
  field count, not a fixed rule.** `sequencer` (7 fields) and every
  3-bit-ID core fit exactly in 8 slots; `branch` (15 fields) and
  `nano` (9 fields) both needed real widening to 4-bit IDs — the
  project's own two richest, most field-dense cores, confirmed not a
  coincidence.
- **`cfg_data` width genuinely varies per core's own real need.**
  `comparator`/`accumulator`/`latch`/`sequencer` fit the original
  64-bit bus exactly or with margin; `ram`/`branch` needed 80 bits;
  `nano` kept its own already-real 128-bit bus (with ~53 bits of real,
  pre-existing reserved headroom, more than enough for `addon_config`
  without widening at all).
- **A 32-bit-or-wider field always needs a real split LOW/HIGH write**
  (`ram`'s `init_data`, `comparator`'s `threshold`) — a single targeted
  word can't carry more than ~20 bits of real payload alongside its
  own ID. Smaller real fields (`accumulator`'s 16-bit `threshold`) fit
  in one write.
- **`active` needed three genuinely different real treatments**, not
  one uniform rule: one-shot cores (`adder`/`ram`/`comparator`/
  `branch`) only needed to gate the offer side; continuously-live
  cores with external triggers (`accumulator`/`latch`) needed `active`
  to ALSO gate capture, so internal state doesn't silently drift while
  inactive; `sequencer` (no capture at all) needed neither — its
  advance trigger is causally downstream of a successful offer, so
  inactivity blocks it for free; `nano` folded `active` into its own
  pre-existing `effective_freeze` convention rather than importing the
  other cores' separate `effective_armed` pattern.
- **Testbench design for continuously-live cores needs the OPPOSITE
  pattern depending on whether there's a real external trigger.**
  `accumulator`/`latch` (real external inc/dec/set/clear triggers)
  need a free-running auto-consumer, or a precisely-timed single ack
  can drain a stale offer instead of the fresh one. `sequencer` (no
  external trigger at all, purely self-paced by its own ack timing)
  needs the OPPOSITE — precise, manual, single-ack-per-step control,
  or a free-running consumer races ahead of the testbench's own
  checks unpredictably. Confirmed by tracing real failures in both
  directions, not assumed from surface similarity.

## Real, honest scope — what this table does NOT cover

- No real ALM/Fmax numbers for any of the 8 `v4` cores — sim-verified
  functional correctness only. Real Quartus measurement remains the
  standing, separate next step.
- The `N=8` multi-core carrier case (wiring these same 8 cores behind
  one shared `core_select` decode) is not built.
- The command-cell functionality removed from `nano` (`#626`) has no
  real home yet — the parked "9th core" idea.
- `nano`'s own `fb_internal_in`/`a_update_in`/`a_self_update_in`/
  `relay_mismatch` behaviors are cloned unchanged but were not
  individually re-verified in the new `v4` build (real `v1`-level
  tests for each already exist and remain the source of truth for
  those specific behaviors).
