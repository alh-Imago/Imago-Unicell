# The super carrier shell — Internal Structure & Register Model

**Ground truth: `fpga/verilog/unicell_super_v1.v` (the original 6-core
shell), `unicell_super_v2.v` (adds the sequencer, #421/#422), and
`unicell_super_v3.v` (adds branch cell, #542) — three real, separate
files, never modified in place once proven, each cloned from the last
per this project's own standing discipline. Originally built 2026-08-16
by reading `unicell_super_v1.v` directly, start to finish; updated
2026-08-30 (points.md #543) to cover v2/v3 and every real field this
session added to the original 6 cores. If this doc and the Verilog
disagree, the Verilog wins, the same discipline `CELL_INTERNALS.md`
already established for the nano cell.**

For the nano/stripped cell's own internal structure (`unicell_stripped_
v1.v`, standalone, no super shell), see `CELL_INTERNALS.md` — not
repeated here. This document covers what's specific to the super
carrier shell: a genuinely different cell built ON TOP OF the same
cardinal-wiring philosophy, not a variant of the nano cell itself.

## Why this cell exists

Per `points.md` #324's own milestone: every cell generation before this
one committed to exactly one core type at synthesis time. The super
carrier shell asks a different question — what if a single physical
shell held ALL the real cores simultaneously, with the ACTIVE one
chosen by a runtime config write, not a recompile? Every core is
ALWAYS physically instantiated and clocked in every bitstream; only
the SELECTED core ever sees genuine `arrived_*`/`cfg_valid` activity —
confirmed directly against the RTL, not assumed.

**Three real shell versions now exist, each a real, separate build
target, never a modification of a proven one:**
- **v1** — the original 6 real cores (nano, RAM, adder, accumulator,
  comparator, latch). Real measured cost (post-#515/#521/#522's own
  field extensions): 233 ALM, `clk_div` 129.48 MHz real SDC-constrained
  Fmax (`points.md` #524/#525).
- **v2** — adds the sequencer (`SEL_SEQ=6`, `points.md` #421/#422).
  Real measured cost: 305 ALM, `clk_div` 99.57 MHz (`points.md` #526).
- **v3** — adds branch cell (`SEL_BRANCH=7`, `points.md` #542), closing
  the "real VM, no RTL slot" half of the asymmetry `#519` first named
  (the sequencer's own mirror-image gap -- real RTL, no VM dispatch --
  remains open). Sim-verified (`tb_unicell_super_v3.v`, 12/12, including
  a substantive real branch cell test through `core_select` routing),
  not yet Quartus/silicon-confirmed as an 8-core shell.

## `SUPER_LATCH[79:0]` — the whole config surface, one register

Verified two independent ways this session, not just read from the
RTL's own comment: bit-for-bit against `tb_unicell_super_v1.v`'s own
proven test vectors (iverilog-compiled and run against the real RTL),
AND mechanically re-extracted straight from the RTL's own comments via
`nano/root_definition_extractor_v1.py`, cross-checked against the
hand-typed table in `nano/icm_v3.py` with zero mismatches
(`points.md` #355).

| Bits | Field | Width |
|---|---|---|
| `[4:0]` | `core_select` | 5 |
| `[46:5]` | `core_config` | 42 (union, reinterpreted per core) |
| `[66:47]` | `addon_config` | 20 |
| `[79:67]` | reserved | 13 |

`core_select` values 0-5 are the original 6 real cores below, `6` is
the sequencer (v2 only), `7` is branch cell (v3 only) -- **8-31 remain
real, deliberate reserved headroom**, per a genuine requirement Alan
stated the day before the session that built this shell (`points.md`
#317: "must stay genuinely extensible... without a field-map
reshuffle") -- not leftover space. The RTL's own output mux treats an
unassigned value as inert (all outputs zero), not X.

Loaded by a plain synchronous register write: `if (cfg_valid)
super_latch <= cfg_data`. No address match, no partial-state ambiguity
-- the same atomic, single-cycle commit discipline `CELL_INTERNALS.md`
already documents for the nano cell's own `cmd_latch`.

## The 8 real cores (6 in v1, +1 sequencer in v2, +1 branch in v3), each one's own real `core_config[N:0]` field map

Every table below was read directly from that core's own `.v` file
header. The original 6 were re-confirmed via mechanical extraction
(`points.md` #355/#356); this session's own extensions (accumulator,
adder, latch, nano's exposed ports) and the two new cores were
verified the same way, plus a real, independent hand cross-check
(`nano/validate_icm_v3_against_rtl_v1.py`, passing, `points.md` #543)
-- not transcribed once and trusted.

**nano** (`core_select=0`) -- only a REDUCED SUBSET of nano's own
standalone `cmd_latch` fields reaches it here, confirmed by comparing
the two field maps directly and finding them genuinely different, not
assumed the same:
| Field | Bits | Note |
|---|---|---|
| `topology` | `[9:0]` | same NOR-tree selection as standalone nano |
| `ready` | `[10]` | this cell's readiness |
| `routing_mask` | `[16:11]` | which directions this cell's fire targets |
| `cardinal_edge` | `[22:17]` | per-incoming-direction relay/consume |
| `hold_in` | `[23]` | real port, exposed `points.md` #522, VM-wired #543 |
| `fb_internal_in` | `[24]` | real port, exposed #522, VM-wired #543 |
| `a_reemit_in` | `[25]` | real port, exposed #522, VM-wired #543 |
| `a_update_in` | `[26]` | real port, exposed #522, VM-wired #543 |
| `a_self_update_in` | `[27]` | real port, exposed #522, VM-wired #543 |

**Real, honest structural note on the 5 new fields above:** unlike
every other field in this document, these are real PORTS on
`unicell_stripped_v1.v` (not part of nano's own `cfg_data` structure)
-- wired individually via `core_config` bits in the shell RTL,
physically separated from nano's own field-map comment block by ~150
lines. `root_definition_extractor_v1.py` genuinely cannot see them
(confirmed, not assumed) -- `nano/root_definition.json`'s own
`nano_within_super` entry has these 5 added MANUALLY, with an explicit
warning that regenerating without `--check` wipes them. This exposes
the CAPABILITY -- it does NOT make these lightweight-runtime-
toggleable; changing them still requires a full reconfigure (a real,
deliberately-scoped limitation, not solved yet).

`is_command_cell`/`cmd_in`/`cmd_out` remain tied to inactive defaults
here -- genuinely still out of scope for this shell. **The programming
channel itself is real, not tied off any more (`points.md` #390):**
`program_in`/`prog_data_in_n/s/e/w`/`prog_arrived_in_n/s/e/w`/
`program_done` are real, top-level shell ports, gated to reach nano
via the same `sel_active_nano` convention this file already uses for
`arrived_*`.

**RAM** (`core_select=1`) -- full 42 bits used, unchanged this session
(confirmed genuinely full, no headroom, `points.md` #521's own survey):
| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |
| `fixed_mode` | `[8]` |
| `load_data_valid` | `[9]` |
| `init_data` | `[41:10]` (32-bit) |

**adder** (`core_select=2`) -- 9 of 42 bits used (was 8); `in_a`/`in_b`
share ONE field (whichever configured direction's arrival lands first
becomes A, the second B -- direction alone doesn't decide the role):
| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |
| `subtract_mode` | `[8]` | 0=A+B (unchanged), 1=A-B, real RTL #521 |

Reuses `adder_v1.v`'s own already-present `cin`/`cout` ports (invert B,
`cin=1`) -- zero new arithmetic hardware. Real silicon confirmed
correct (`points.md` #539), including a genuine borrow case.

**accumulator** (`core_select=3`) -- 37 of 42 bits used (was 12),
continuously-live in static mode, single-shot pulse behavior in pulse
mode:
| Field | Bits |
|---|---|
| `inc_dir` | `[3:0]` |
| `dec_dir` | `[7:4]` |
| `downstream_mask` | `[11:8]` |
| `step_amount` | `[19:12]` | magnitude, was hardcoded +-1, real RTL #515 |
| `pulse_mode` | `[20]` | 0=static/continuous (unchanged), 1=reset-after-fire pulse |
| `threshold` | `[36:21]` | pulse_mode only -- crossing resets total to 0 |

**Real, deliberate semantic in pulse mode:** crossing threshold
changes what's offered ENTIRELY, not alongside the continuous total --
only the discrete crossing pulse is ever offered, and the internal
total hard-resets to 0 in the same event (discarding any overshoot).
Real silicon confirmed correct, including genuine repeat (a second
independent crossing correctly fires again) and negative-direction
crossings (`points.md` #515`/`#537`).

**comparator** (`core_select=4`) -- stateless, single-arrival,
unchanged this session:
| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |
| `threshold` | `[39:8]` (32-bit, signed) |

**Real, settled architectural note (`points.md` #507/#508):** the
branch cell (below), used in static mode, fully SUBSUMES this core's
own function -- kept anyway, deliberately, per this project's own
standing "never remove a proven design, even when superseded" rule.
Comparator is cheaper and simpler for the one common case (a plain
threshold check) where branch cell's own richer per-outcome machinery
is unused overhead.

**latch** (`core_select=5`) -- 16 of 42 bits used (was 12),
continuously-live:
| Field | Bits |
|---|---|
| `set_dir` | `[3:0]` |
| `clear_dir` | `[7:4]` |
| `downstream_mask` | `[11:8]` |
| `toggle_dir` | `[15:12]` | real RTL #522, flips instead of forcing |

**Real priority chain when multiple triggers arrive the same cycle:
`CLEAR > SET > TOGGLE`** -- the two idempotent/deterministic operations
win over the state-dependent one, extending `#279`/`#284`'s own
"explicit host action wins" rule. Real silicon confirmed correct,
including the full 3-way priority chain, not just pairwise
(`points.md` #522`/`#541).

**sequencer** (`core_select=6`, v2/v3 only) -- 38 of 42 bits used,
real distinct territory none of the other cores cover: cycles through
a short, fixed, host-configured value list. **Real, genuinely
different protocol from every other core here, confirmed directly
before relying on it (`points.md` #542):** capture (`arrived_X`) plays
NO role at all -- it self-advances purely on its own ack-drain cycle.
| Field | Bits |
|---|---|
| `VALUE_0` | `[7:0]` |
| `VALUE_1` | `[15:8]` |
| `VALUE_2` | `[23:16]` |
| `VALUE_3` | `[31:24]` |
| `SEQUENCE_LEN` | `[33:32]` | how many of the 4 values are real (1-4) |
| `downstream_mask` | `[37:34]` |

**Real, honest gap, unchanged from earlier sessions:** has real RTL
(since v2) but zero VM dispatch in `nano/unicell_super_automaton_v1.py`
-- the mirror-image of branch cell's own former situation (real VM, no
RTL), not yet closed.

**branch** (`core_select=7`, v3 only) -- 42 of 42 bits used, zero
spare, the richest real core in this shell:
| Field | Bits |
|---|---|
| `upstream_dir` | `[1:0]` | single fixed direction (0=N/1=S/2=E/3=W), not a mask |
| `value_source_low/equal/high` | `[2]/[3]/[4]` | 0=relay the compared value, 1=fixed |
| `fixed_value_low/equal/high` | `[11:5]/[18:12]/[25:19]` | 7 bits each |
| `emit_low/equal/high` | `[26]/[27]/[28]` | 0=genuinely SUPPRESS this outcome |
| `route_low/equal/high` | `[32:29]/[36:33]/[40:37]` | real one-hot(s) fan-out masks |
| `rolling_mode` | `[41]` | 0=fixed reference (static), 1=reference updates each compare |

**Real mechanism:** the reference is HELD, set by the first real
arrival on `upstream_dir` (not a config-time constant like
comparator's threshold) -- every later arrival is classified LOW/
EQUAL/HIGH against it and independently routed or genuinely suppressed.
Real silicon confirmed correct standalone (`points.md` #530) and
through `core_select` routing in the real v3 shell (`points.md` #542`'s
own `tb_unicell_super_v3.v`) -- held-reference capture, per-outcome
routing, and genuine suppression all proven, not just simulated.

All `*_mask`/`*_dir` fields share one one-hot convention, confirmed
identical across every core that has one: **bit0=N, bit1=S, bit2=E,
bit3=W** (`ram_cell_v1.v`'s own comment states this explicitly).
`upstream_dir` (branch cell only) is the one real exception -- a
single fixed 2-bit direction CODE, not a one-hot mask.

## `addon_config[19:0]` -- identical across every core

The addon chain sits on the periphery, applied to whichever core is
selected, in this fixed order: nibble_mask -> shift_lane -> invert
(`unicell_super_v1.v` lines 337-349's own real instantiation order).

| Field | Bits |
|---|---|
| `nibble_mask` | `[7:0]` |
| `mask_en` | `[8]` |
| `shift_amt` | `[13:9]` |
| `shift_en` | `[14]` |
| `direction` | `[15]` |
| `lane_cut` | `[18:16]` |
| `invert_en` | `[19]` |

**Real, honest gap:** unlike every field table above, `addon_config`
is NOT wired through the RTL's "field map" comment convention at all --
it's set via direct module port connections at the `ADDON_NM`/
`ADDON_SL`/`ADDON_INV` instantiations. `root_definition_extractor_v1.py`
does not (and, as built, cannot) cover it -- confirmed absent by
grepping the three addon `.v` files directly, not assumed. `icm_v3.py`'s
own addon field table remains hand-typed and unvalidated by the
mechanical cross-check that covers everything else in this document.

## Real firing model differences between the cores, confirmed against RTL bodies not just headers

Every one of these was read from the actual `always @(posedge clk)`
logic, not the header comment alone, before being ported into the
VM (`nano/unicell_super_automaton_v1.py`, `points.md` #337):

- **Single-shot, doubly-full-guarded** (offer once per capture, refuse
  a second arrival until the first drains): RAM (flowing mode),
  comparator.
- **Two-stage capture** (first arrival becomes A, second becomes B,
  independent registers so a new A can start while a previous sum is
  still undrained): adder.
- **Continuously-live** (never blocked, re-arms and re-offers its
  current value every idle tick -- a genuine heartbeat): accumulator
  in static mode, latch, and RAM in fixed_mode (loads once, offers
  forever, never captures again).
- **Single-shot pulse, reset-after-fire** (accumulator's own pulse
  mode, `points.md` #515): a real, different firing shape from its own
  static mode -- fires a discrete crossing pulse and hard-resets to 0
  in the same event, rather than continuously re-offering a running
  total.
- **Zero capture role at all** (sequencer, `points.md` #542): unlike
  every other core here, `arrived_X` does nothing -- it self-advances
  purely on its own ack-drain cycle.
- **Held-reference, per-outcome routing** (branch cell, `points.md`
  #500/#504/#542): the FIRST real arrival sets a reference value,
  every later arrival is classified against it and independently
  routed or genuinely suppressed per outcome -- a real, distinct shape
  none of the other cores share.
- **No `upstream_mask` at all**: nano is the one core with no per-
  direction input gating -- it accepts an arrival from ANY physically
  wired neighbor unconditionally; only `cardinal_edge` classifies
  relay-vs-consume per incoming direction, it doesn't gate acceptance.

None of these cores use an addressed bus -- every one wires N/S/E/W to
physical cardinal neighbors, the same "no addressing, no shared bus"
model `unicell_automaton_v1.py`'s own `CAGrid` already established for
plain nano (`points.md` #342's own design reasoning for why ICM v3
needed a grid POSITION rather than a bus address at all).

## Real verification status, honestly separated by what was actually checked

**v1 (original 6 cores, post this session's own field extensions):**
- **Real Quartus/silicon data**: 233 ALM (`points.md` #524), real
  SDC-constrained `clk_div` Fmax 129.48 MHz, over 5x margin above the
  25 MHz target (`points.md` #525). Earlier baseline (pre-#515/#521/
  #522's own field extensions): 213 ALM, `clk_div` 200.76 MHz
  (`points.md` #322).
- **Real iverilog simulation**: `tb_unicell_super_v1.v` -- core
  selection and isolation confirmed correct across all 6 cores
  (`points.md` #336).
- **Real, independent mechanical cross-check**: every field position
  in this document (except `addon_config` and nano's 5 exposed ports,
  both stated gaps above) re-derived straight from the RTL's own
  comments and found to match `icm_v3.py`'s hand-typed tables exactly,
  zero mismatches (`nano/validate_icm_v3_against_rtl_v1.py`, passing,
  `points.md` #355/#543).
- **REAL, FUNCTIONAL, silicon-confirmed** (not just resource/timing
  data) for every one of this session's own new fields, via a real
  JTAG-readable ISSP debug channel, alias-free (`points.md` #529/
  #537): accumulator's `pulse_mode`/`threshold` (`#537`), adder's
  `subtract_mode` including a genuine borrow case (`#539`), nano's
  exposed `hold_in`/`fb_internal_in` through the real shell (`#540`),
  and latch's `toggle_dir` including the full `CLEAR>SET>TOGGLE`
  priority chain (`#541`).

**v2 (+sequencer):**
- **Real Quartus/silicon data**: 305 ALM, real `clk_div` Fmax 99.57
  MHz, ~4x margin -- genuinely LESS than a single old full-fat cell
  doing only one job, despite packing 7 real cores into one shell
  (`points.md` #526).
- **Real, honest gap**: no dedicated testbench of its own exists for
  v2 specifically (`points.md` #522's own flag) -- `tb_unicell_super_
  v3.v` (below) is the closest real test, since it reuses v2's own
  proven 6-core sequence as its base, but that's a v3 build, not v2.

**v3 (+branch cell):**
- **Real iverilog simulation**: `tb_unicell_super_v3.v` -- 12/12
  checks pass, all 8 cores correctly isolated, including a
  SUBSTANTIVE branch cell test through `core_select` routing (not a
  sanity check): held-reference capture, per-outcome routing, and
  genuine suppression, matching the exact design already confirmed on
  real silicon standalone (`points.md` #530`/`#542).
- **NOT yet Quartus/silicon-confirmed** as an 8-core shell -- no real
  ALM/Fmax number exists yet for v3, and no Quartus self-test target
  has been built for it either. Real, natural next step.

**NOT yet Quartus/silicon-confirmed, any version**: the Tier-1
composed tiles built on top of this shell (`sentinel`,
`dual_threshold_monitor`, `twin_sentinel`) -- all marked
`proven="sim-only"` in their own registration, verified in the VM
only, not yet built on real hardware as these specific multi-cell
layouts.

## What's built on top of this shell, and where to find it

This document deliberately stops at the shell/core RTL level -- the
software stack built on top of it is documented separately, each
piece with its own real verification:
- `nano/icm_v3.py` -- the ICM v3 format, `SUPER_LATCH` encode/decode.
  **Real fix, `points.md` #543:** `IcmV3File.to_dict()`'s own
  `cell_type` field is now genuinely COMPUTED (`minimum_shell_version()`,
  checking which real cores a set of records actually uses), not
  hardcoded to `"unicell_super_v1"` regardless of content -- a file
  using branch cell now correctly reports needing `unicell_super_v3`.
- `nano/example_icm_branch_demo_v1.py` -- a real, working end-to-end
  demonstration (`points.md` #543): build a program (accumulator +
  branch cell) in the VM, save it to a real `.icm.json` file (the
  exact 80-bit `super_latch_hex` words a real host bridge would write
  to the board), reload that file from disk, and confirm the VM
  reproduces identical real behavior from the reloaded data alone.
- `nano/unicell_super_automaton_v1.py` -- the VM (`SuperCell`/
  `SuperGrid`). Branch cell's own dispatch (`_deliver_branch`) was
  already correct from the start (`#519`) -- only its own comments
  describing it as "VM-provisional" were stale post-`#542` and have
  been corrected. Adder's `subtract_mode` and latch's `toggle_dir` are
  now real, dispatched logic here too (`#543`), not just field-table
  entries.
- `nano/super_tile_library_v1.py` / `composed_tile_library_v1.py` --
  the Tier-0/Tier-1 tile library.
- `nano/dsl_lexer_v1.py`/`dsl_parser_v1.py`/`dsl_compiler_v1.py` --
  the Unicell-S DSL and compiler; see `UNICELL_S_DSL_MANUAL.md` for the
  language reference.
- `nano/root_definition_extractor_v1.py` / `generic_field_codec_v1.py`
  -- mechanical, RTL-comment-driven field extraction and a generic
  pack/unpack codec, proven equivalent to `icm_v3.py`'s own hand-typed
  one (`points.md` #355/#356). **Real, honest structural limit found
  this session (`#543`):** cannot see fields wired as individual ports
  scattered away from a core's own field-map comment block (nano's 5
  exposed ports) -- `root_definition.json` carries a manual, explicitly
  labeled override for this one case.


See `points.md` #324-#356 for the original build/verification
narrative, and `#515`-`#543` for this session's own real extensions
(accumulator/adder/latch fields, nano's exposed ports, branch cell's
real RTL slot, the VM sync, and every real silicon confirmation).
