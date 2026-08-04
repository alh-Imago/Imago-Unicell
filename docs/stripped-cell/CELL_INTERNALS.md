# Stripped/nano cell — Internal Structure & Register Model

**Ground truth: `fpga/verilog/unicell_stripped_v1.v`. Built 2026-08-04 by
reading the file directly, start to finish — this is the cell's FIRST
standalone documentation; before this it existed only as `points.md`
#88 onward and the RTL's own header comments. If this doc and the
Verilog disagree, the Verilog wins — re-verify against it, don't trust
this doc's numbers blind, the same discipline the project applies
everywhere else.**

For what this cell shares with the FULL cell (gate computation,
`cmd_latch` field alignment, the firing/freeze principles), see
`../shared/SYSTEM_MECHANICS.md` — not repeated here. This document
covers what's specific to THIS cell: its own mechanisms, its own field
usage, its own port list.

## Why this cell exists

Per `points.md` #107's fork: the FULL cell (`unicell64_v3.v`) uses an
addressed, shared wired-OR bus — powerful, but the shared bus is the
reason behind its measured 25-cell/zone practical cap. The stripped
cell asks a narrower question: what if a cell has NO address, NO shared
bus, and talks only to its four immediate cardinal neighbors over
dedicated point-to-point wires? `input_address`, `output_address`,
`auth_mask`, `config_match`, and the whole address-matched command-bus
decode are, per the RTL's own header, "DELIBERATELY ABSENT, NOT MERELY
DISABLED" — not a cut corner, a different design.

This is the ACTIVE line as of 2026-08-01, and the one currently proven
on real Arria 10 silicon.

## Boot-time configuration — two genuinely different paths

- **`cfg_valid`/`cfg_data`** — a plain synchronous load, no address
  match (there's no bus to match against). One cycle, the whole 128-bit
  `cmd_latch` at once. This is the atomic path: **arms immediately**
  (see Armed, below) since there's no partial-state ambiguity in a
  single-cycle full commit. A stand-in for eventual `loader_fsm_v3.v`
  integration — not yet wired to it.
- **`program_in`/the ID-tagged incremental path** — the real, actively
  used mechanism (see Programming, below). Genuinely different: several
  separate word-writes over time, and does NOT auto-arm.

## `cmd_latch` — 128 bits, actual current field usage

| Bits | Name | Notes |
|---|---|---|
| `[9:0]` | `topology` | shared with FULL cell, see `SYSTEM_MECHANICS.md` |
| `[10]` | `is_command_cell` | config-driven, permanent re-emit-on-trigger (see Command-emit, below) |
| `[13]` | `ready_bit` | this cell's own dynamic readiness (see Ready/ack, below) |
| `[69:64]` | `routing_mask` | shared slot, output-side openness |
| `[75:70]` (only `[73:70]` wired) | `cardinal_edge` | shared slot, but REINTERPRETED per-INCOMING direction here (consume vs. relay) — the FULL cell uses it per-outgoing. Real difference, not a typo. |
| `[79:76]` | `pattern_low` | shared slot (low 4 of 6), wanted directions when comparator=LOW |
| `[85:82]` | `pattern_equal` | shared slot (low 4 of 6), ...EQUAL |
| `[91:88]` | `pattern_high` | shared slot (low 4 of 6), ...HIGH |
| `[94]` | `dynamic_route_en` | shared slot |
| `[127:96]` | `out_buffer` | the offered-output value, separate from `data_reg` (working register) |

Bits `[12:11]`, `[63:14]` (minus the slots above), `[95]` are presently
free/unclaimed — reserved deliberately for the still-deferred cardinal
COMMAND channel (a `points.md` #84 idea, not built).

**`armed` is NOT a `cmd_latch` bit** — it's a separate, standalone `reg`
(see Armed, below). Easy to assume otherwise since everything else
control-related lives in the latch; checked directly, it doesn't.

## The two-arrival firing model, as actually wired here

- `input_val` = A = `data_reg` if already captured, else the fresh
  arrival.
- `second_val` = B = the internal-feedback source if `internal_fb_active`,
  else the fresh arrival if this is the first capture, else `data_reg`.
- `capture_now`: first arrival, stores into `data_reg`, sets `a_arrived`.
- `can_fire`: second arrival with `a_arrived` already set — runs the
  gate computation, offers the result on `out_buffer`.
- No address matching anywhere in this path — arrival is just
  `arrived_n/s/e/w` going high, a genuine per-direction wire, not a bus
  event.

**Multi-direction arrivals in the SAME cycle OR-combine** (`points.md`
#153) — `arrived_val` is the OR of every direction that arrived this
cycle, recreating the FULL cell's free wired-OR N-way combine on
dedicated wires that have nothing to contend over. A real protective
case exists for when this shouldn't happen — see Relay/consume
mismatch, below.

## Relay vs. consume — per-INCOMING-direction, not per-outgoing

`cardinal_edge` bit `x` = 0 means direction `x`'s arrivals are CONSUMED
(normal two-arrival participation). Bit `x` = 1 means RELAYED (pure
pass-through straight to `out_buffer`, never touches `data_reg` or the
gate computation at all). This is the cell acting as a conduit for one
direction while genuinely computing on another.

**Relay/consume mismatch protection (`points.md` #154):** if directions
arriving the SAME cycle disagree on classification (one relay-tagged,
one consume-tagged), that's a genuine error by construction (a
well-formed compiled model never has this — the compiler's job is
ensuring relay/consume timing is deliberate). `relay_mismatch` sets
`error_frozen`, a real internal protective latch distinct from
`freeze_in` — auto-clears on the next successful reprogram's `COMPLETE`
marker. The offending cycle's own OR-combine still completes (can't be
undone), but the cell is frozen going forward until reprogrammed.

## Hold / memory mechanisms

- **`hold_in`** — the ONLY change: `a_arrived`'s normal auto-clear-on-fire
  becomes conditional on `!hold_in`. Held, the same first-arrival value
  keeps comparing against every new second-arrival — a live,
  continuously-updating comparator with zero host round-trip per
  comparison.
- **`fb_internal_in`** — while `hold_in && fb_internal_in`, `second_val`
  is drawn from THIS cell's own `out_buffer` instead of an external
  arrival, recomputing every cycle. Genuinely separate mechanism from
  external cardinal feedback (closes a real self-loop deadlock found in
  `tb_stripped_v1_feedback.v` — forcing internal recurrence through the
  ack mechanism built for two independent cells doesn't work).
- **`a_reemit_in`** — while held, an arriving trigger (value ignored)
  pushes the held `data_reg` to `out_buffer` UNPROCESSED, no gate
  computation. Distinct from `relay_fire` (which pushes the ARRIVING
  value, ignoring A).
- **`a_update_in`** — while held, an arriving value REPLACES `data_reg`
  directly — the genuine write/update path.
- **`a_self_update_in`** — while `internal_fb_active`, decides where the
  computed result goes: low (default) = oscillates in `out_buffer`, A
  stays fixed; high = the result REPLACES `data_reg` directly, a
  genuine self-adjusting accumulator.
- **`is_command_cell`** (`cmd_latch[10]`) — config-time, permanent
  version of `a_reemit_in`: once set, no external control wire needed at
  all. Mirrors the FULL cell's own `COMMAND_EMIT` precedent, same bit
  position.

## Branch / routing (comparator-driven)

Ported from the FULL cell's `pattern_low`/`pattern_equal`/`pattern_high`
+ `dynamic_route_en`. `cmp_gt`/`cmp_lt` compare `second_val` against
`input_val` (genuine arithmetic magnitude comparison, unrelated to the
NOR-gate topology computation). The comparison result selects which
4-bit pattern becomes `effective_routing` — `dynamic_route_en=0` (the
default) preserves the plain static `routing_mask` behavior exactly;
`1` makes routing genuinely data-dependent, per-fire.

## Programming — variable-length, ID-tagged, NOT the FULL cell's model

Each word: `{don't-care[31:19], 3-bit ID[18:16], 16-bit data[15:0]}`.
While `program_in` is held, ANY arrival on ANY direction (same N>S>E>W
priority as everywhere else) is redirected here instead of the normal
two-arrival gate — genuinely suspending ordinary operation, top
priority, no possibility of colliding with a normal fire the same
cycle. Each word independently targets ONE field:

| ID | Field |
|---|---|
| 0 | `topology` |
| 1 | `routing_mask` (low 4 bits) |
| 2 | `cardinal_edge` (low 4 bits) |
| 3 | `pattern_low` |
| 4 | `pattern_equal` |
| 5 | `pattern_high` |
| 6 | `dynamic_route_en` |
| 7 | `COMPLETE` (reserved marker) |

No word-count state — a reprogram touching only one field sends exactly
one field-write plus `COMPLETE`, not a fixed-size overwrite ("a scalpel,
not a hammer"). Rides on its OWN dedicated cardinal wires
(`prog_data_in_*`/`prog_arrived_in_*`/`prog_ack_out_*`), separate from
ordinary `data_in_*` — sharing them was tried and measured more
expensive (`points.md` #131).

## Armed — a real gate, added `points.md` #156

A standalone `reg`, NOT a `cmd_latch` bit. Mirrors the FULL cell's
`start_flag`/`CMD_RELEASE` concept and its "armed = opcode LSB"
convention, but scoped specifically to the incremental programming path
above:

- `rst` → `armed = 0`.
- `cfg_valid` (atomic load) → `armed = 1` immediately — no partial-state
  ambiguity to gate against.
- `PROG_ID_COMPLETE` → `armed = prog_word[0]` directly. `COMPLETE` with
  data LSB=1 commits AND arms; LSB=0 commits but stays (or returns to)
  cold. Lets a command cell pause mid-reprogram, apply more field
  writes, then re-arm.
- `effective_freeze = freeze_in || error_frozen || !armed` — a
  disarmed cell is fully paused, same as a frozen one. `ready_out` also
  requires `ready_bit && armed` — a disarmed cell reports NOT ready to
  its neighbors too, so nobody routes into it before it's armed.

## Ready / ack / backpressure — NOT present on the FULL cell at all

Checked directly (`SYSTEM_MECHANICS.md` §5): grepped `unicell64_v3.v`
for `ready`/`pending_ack`, no match. This whole mechanism is
STRIPPED-cell-only.

- `pending_ack` (6 bits, `points.md` #89/#90): a fire-time snapshot of
  which directions were ACTUALLY targeted this fire.
  `next_ready = hold_in || (next_pending_ack == 0)` — this cell's own
  `ready_bit` only recovers once every targeted direction has
  genuinely acked.
- `fire_x` is a LEVEL held by `pending_ack[x]`, not a one-shot pulse —
  a receiver that was busy keeps seeing the offer every cycle until it
  can accept it, not just a single missable window.
- `ack_out_x` fires only when this cell genuinely CONSUMES the arrival
  this cycle (captures it fresh, or accepts it as the firing trigger
  AND actually fires). If this cell is doubly full, no ack goes out —
  the delivery stays unconsumed, and the sender's own `pending_ack`
  never clears either. **This is the mechanism the freeze-cascade proof
  (`points.md` #91/#92/#152/#155) rides on** — no separate
  zone-targeting RTL needed, freezing any cell backs up everything
  upstream of it for free.
- `targets_all_ready`: a fire only commits once every targeted
  direction's neighbor shows ready — one shared `out_buffer`, one
  ready bit, wait-for-all (not per-direction partial hold — Alan's
  explicit choice, `points.md` #88).

## Port list, by category

- **Boot config:** `cfg_valid`, `cfg_data[127:0]`
- **Cardinal data:** `data_in_*`/`arrived_*` (in), `data_out_*`/`fire_*`
  (out) — one point-to-point link per direction (N/S/E/W)
- **Ready:** `ready_out` (broadcast, unconditional), `ready_in_*`
- **Ack:** `ack_out_*`, `ack_in_*`
- **Command cardinal bus:** `cmd_in_*`/`cmd_out_*` — ports exist,
  RESERVED, tied to `32'h0` / unconnected. Not implemented in this
  draft.
- **Control lines (live external wires):** `freeze_in`, `hold_in`,
  `fb_internal_in`, `a_reemit_in`, `a_update_in`, `a_self_update_in` —
  in every grid-scale build so far, these are driven by
  `cell_wrapper_v2`'s persistent `SET_CTRL`/`CLR_CTRL` latches, not
  raw testbench wires.
- **Programming:** `program_in`, `program_done` (out), the dedicated
  `prog_data_in_*`/`prog_arrived_in_*`/`prog_ack_out_*` cardinal set.

## Companion modules (not part of this file, but always paired with it)

- **`cell_wrapper_v2.v`** — the host/JTAG-facing path. 5 opcodes:
  `PROGRAM`, `COLLECT`, `SET_CTRL`, `CLR_CTRL`, `DIAG`. Holds the 6
  persistent control-line latches. See its own header for the full
  opcode contract.
- **`cell_command_v1.v`** — the minimal command-cell companion:
  trigger → hold `program_in` → release on `program_done`. A handful of
  real lines, deliberately separate from a stripped cell instance, not
  a mode flag on one.

## Real bugs found and fixed on this cell, worth knowing before touching it

- `a_reemit_active` never actually required `a_arrived` — a latent bug
  in the original design, only exposed once `is_command_cell`'s
  config-driven mode removed the external sequencing that had silently
  masked it (`points.md` #144).
- The 750-cell-scale command walker (`points.md` #150/#151/#155) sent a
  hardcoded `routing_mask=0` for whatever cell it currently targeted —
  harmless for area/Fmax measurement, genuinely corrupting for any
  functional test. Fixed by giving the walker its own row/col tracking
  so it recomputes each cell's correct value instead.
- Two separate `always` blocks both driving `cmd_latch` simulated fine
  in Icarus but is illegal for synthesis ("multiple constant drivers") —
  caught by Quartus, not by sim (`points.md` #96). Merged into one
  process.

## Real silicon/Quartus numbers so far (see `points.md` for full detail)

| Build | ALMs | ALM/cell | Fmax |
|---|---|---|---|
| 25-cell baseline | 145 | 5.8 | 261.44 MHz |
| + wrapper (full parity) | +264 | 10.6 | 190.22 MHz |
| + command-cell (corrected) | +163 | 6.5 | 174.64 MHz |
| + both (complete redesign) | 293 | 11.72 | 192.75 MHz |
| 50-cell zone | 813 | 16.26 | 171.29 MHz |
| 750-cell zone | 12,295 | 16.39 | not yet re-measured with #151/#155/#156 combined |

500-cell (20×25) fallback zone built and sim-verified in reserve
(`points.md` #157), not yet needed.
