# The super carrier shell — Internal Structure & Register Model

**Ground truth: `fpga/verilog/unicell_super_v1.v`. Built 2026-08-16 by
reading the file directly, start to finish, plus drawing on real
verification work already done against it earlier the same session
(`points.md` #336-#356) — this is this cell's FIRST standalone prose
documentation; before this it existed only as `points.md` #315-#324
onward and the RTL's own header comments. If this doc and the Verilog
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
shell held ALL SIX real cores simultaneously (nano's own gate tree,
plus RAM, adder, accumulator, comparator, and latch), with the
ACTIVE one chosen by a runtime config write, not a recompile? Every one
of the 6 cores is ALWAYS physically instantiated and clocked in every
bitstream; only the SELECTED core ever sees genuine `arrived_*`/
`cfg_valid` activity — confirmed directly against the RTL, not assumed
(this is what makes `core_select` a cheap runtime write instead of a
reflash, resolved precisely in a real crossed-wire conversation with
Alan, `points.md` #339).

Real measured cost: isolation/selection overhead ~25.9 ALM (`points.md`
#323), 213 ALM total for the whole shell (`points.md` #322) -- only
~1.7x one ordinary nano cell alone, not 6x. Best timing margin of any
build this session: `clk_div` at 200.76 MHz, 8.03x over the 25 MHz
target (`points.md` #322).

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

`core_select` values 0-5 are the 6 real cores below; **6-31 are real,
deliberate reserved headroom**, per a genuine requirement Alan stated
the day before the session that built this shell (`points.md` #317:
"must stay genuinely extensible... without a field-map reshuffle") --
not leftover space. The RTL's own output mux treats an unassigned
value as inert (all outputs zero), not X.

Loaded by a plain synchronous register write: `if (cfg_valid)
super_latch <= cfg_data`. No address match, no partial-state ambiguity
-- the same atomic, single-cycle commit discipline `CELL_INTERNALS.md`
already documents for the nano cell's own `cmd_latch`.

## The 6 cores, each one's own real `core_config[N:0]` field map

Every table below was read directly from that core's own `.v` file
header, then independently re-confirmed via mechanical extraction this
session (`points.md` #355/#356) -- not transcribed once and trusted.

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

Nano's own `hold_in`/`fb_internal_in`/`a_self_update_in`/`is_command_cell`
remain tied to inactive defaults here -- genuinely still out of scope
for this shell. **The programming channel itself is real, not tied
off any more (`points.md` #390):** `program_in`/`prog_data_in_n/s/e/w`/
`prog_arrived_in_n/s/e/w`/`program_done` are real, top-level shell
ports, gated to reach nano via the same `sel_active_nano` convention
this file already uses for `arrived_*` -- exposing nano's own already-
proven, already-built incremental `PROG_ID`-word reprogramming channel
(confirmed working, `#390`; a real command-cell module driving it end
to end, `#395`) through the shell, not a new mechanism.

**RAM** (`core_select=1`) -- full 42 bits used:
| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |
| `fixed_mode` | `[8]` |
| `load_data_valid` | `[9]` |
| `init_data` | `[41:10]` (32-bit) |

**adder** (`core_select=2`) -- only 8 of 42 bits used; `in_a`/`in_b`
share ONE field (whichever configured direction's arrival lands first
becomes A, the second B -- direction alone doesn't decide the role):
| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |

**accumulator** (`core_select=3`) -- continuously-live, never blocked:
| Field | Bits |
|---|---|
| `inc_dir` | `[3:0]` |
| `dec_dir` | `[7:4]` |
| `downstream_mask` | `[11:8]` |

**comparator** (`core_select=4`) -- stateless, single-arrival:
| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |
| `threshold` | `[39:8]` (32-bit, signed) |

**latch** (`core_select=5`) -- continuously-live, CLEAR wins ties:
| Field | Bits |
|---|---|
| `set_dir` | `[3:0]` |
| `clear_dir` | `[7:4]` |
| `downstream_mask` | `[11:8]` |

All `*_mask`/`*_dir` fields share one one-hot convention, confirmed
identical across every core that has one: **bit0=N, bit1=S, bit2=E,
bit3=W** (`ram_cell_v1.v`'s own comment states this explicitly).

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

## Real firing model differences between the 6 cores, confirmed against RTL bodies not just headers

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
  current value every idle tick -- a genuine heartbeat): accumulator,
  latch, and RAM in fixed_mode (loads once, offers forever, never
  captures again).
- **No `upstream_mask` at all**: nano is the one core with no per-
  direction input gating -- it accepts an arrival from ANY physically
  wired neighbor unconditionally; only `cardinal_edge` classifies
  relay-vs-consume per incoming direction, it doesn't gate acceptance.

None of the 6 cores use an addressed bus -- every one wires N/S/E/W to
physical cardinal neighbors, the same "no addressing, no shared bus"
model `unicell_automaton_v1.py`'s own `CAGrid` already established for
plain nano (`points.md` #342's own design reasoning for why ICM v3
needed a grid POSITION rather than a bus address at all).

## Real verification status, honestly separated by what was actually checked

- **Real Quartus/silicon data**: the super carrier shell itself, 213
  ALM total, ~25.9 ALM isolation/selection overhead, `clk_div` 200.76
  MHz (8.03x margin over the 25 MHz target) -- see `points.md`
  #320-#324 for the full build and measurement narrative.
- **Real iverilog simulation, this session**: `tb_unicell_super_v1.v`
  compiled and run against the real RTL and all 6 real core modules --
  confirmed passing, "core selection and isolation confirmed correct
  across all 6 cores" (`points.md` #336).
- **Real, independent mechanical cross-check**: every field position in
  this document (except `addon_config`, see the stated gap above) was
  re-derived straight from the RTL's own comments via a from-scratch
  parser and found to match the hand-typed Python tables exactly, zero
  mismatches (`points.md` #355).
- **NOT yet Quartus/silicon-confirmed**: the Tier-1 composed tiles built
  on top of this shell (`sentinel`, `dual_threshold_monitor`,
  `twin_sentinel`) -- all marked `proven="sim-only"` in their own
  registration, verified in the VM only, not yet built on real hardware
  as these specific multi-cell layouts.

## What's built on top of this shell, and where to find it

This document deliberately stops at the shell/core RTL level -- the
software stack built on top of it this session is documented
separately, each piece with its own real verification:
- `nano/icm_v3.py` -- the ICM v3 format, `SUPER_LATCH` encode/decode.
- `nano/unicell_super_automaton_v1.py` -- the VM (`SuperCell`/
  `SuperGrid`).
- `nano/super_tile_library_v1.py` / `composed_tile_library_v1.py` --
  the Tier-0/Tier-1 tile library.
- `nano/dsl_lexer_v1.py`/`dsl_parser_v1.py`/`dsl_compiler_v1.py` --
  the Unicell-S DSL and compiler; see `UNICELL_S_DSL_MANUAL.md` for the
  language reference.
- `nano/root_definition_extractor_v1.py` / `generic_field_codec_v1.py`
  -- mechanical, RTL-comment-driven field extraction and a generic
  pack/unpack codec, proven equivalent to `icm_v3.py`'s own hand-typed
  one (`points.md` #355/#356).

See `points.md` #324-#356 for the full narrative of how each piece was
built and verified.
