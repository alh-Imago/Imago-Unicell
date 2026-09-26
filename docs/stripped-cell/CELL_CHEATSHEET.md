# Cell & Carrier Cheat Sheet — quick reference

**Purpose:** a fast lookup for design work — name, what it does, how
many arrivals it needs to fire, and its config shape — without having
to re-open the RTL each time. Complements, doesn't replace:
`CORES_AND_WRAPPERS_REFERENCE.md` (build/proof status, standalone-vs-
carrier differences, design principles) and `CELL_GOTCHAS.md`
(behavioral traps). If this file and the RTL ever disagree, the RTL
wins — this is a summary, not the source of truth.

**Must be updated whenever a core/carrier's own real function,
field map, or arrival behaviour changes** — same living-document
discipline as the other cross-reference docs.

**`_v4` vs `_v4c`, the one fact that matters most for design work:**
`_v4` = standalone core, own local 3-stage addon chain (`nibble_mask
-> shift_lane -> invert`), NO `shift_fine`. `_v4c` = carrier-embedded
variant, addon chain REMOVED entirely — the carrier itself
(`unicell_vix_carrier_v1.v`/`v1d.v`) supplies ONE shared 4-stage chain
(`nibble_mask -> shift_fine -> shift_lane -> invert`) for whichever
core is selected. A `_v4c` core used outside a carrier has no addon
capability at all.

---

## The Carrier

| | |
|---|---|
| **File** | `unicell_vix_carrier_v1.v` (base), `unicell_vix_carrier_v1d.v` (adds live addon reprogramming, `#841`) |
| **What it is** | ONE physical position holding all 11 real core types simultaneously, mutually exclusive, `core_select`-switched at runtime (not a rebuild) |
| **Config** | `VIX_LATCH[159:0]`: `[4:0]` core_select, `[132:5]` core_config (128-bit union, per-core), `[154:135]` addon_config (20 bits), `[156:155]` shift_fine (2 bits), rest reserved |
| **Boot config** | Atomic — `cfg_valid` commits the WHOLE `VIX_LATCH` in one cycle |
| **Live per-core config** | Each core's own fields are incrementally, independently PROG_ID-writable at runtime (config-off-shell) without touching other fields or resetting the core |
| **Live addon config (`v1d` only)** | A reserved pseudo-target, `SEL_ADDON_CONFIG=5'd11`, lets a programming session address the carrier's OWN shared `addon_config`/`shift_fine` incrementally, with zero effect on `core_select`/`core_config` — real, sim-proven, `#841` |
| **Programming channel** | Gated to whichever core is selected only — `PROG_ID` values collide across core types, so routing matters |
| **Core-select values** | 0=nano 1=adder 2=ram 3=compare 4=branch 5=accumulator 6=latch 7=sequencer 8=command 9=mul 10=priority, 11=addon-config (`v1d`, pseudo-target, not a core), 12-31 reserved |

---

## The 11 Cores

| Core | Arrivals to fire | Function | Notes |
|---|---|---|---|
| **nano** (`nano_gate_v4[c]`) | **2** — always, even single-operand topologies (the standing "dummy second arrival" rule) | NOR-universal primitive: 12 real gate/topology codes (AND/OR/XOR/NOT/PASS/etc.), the composition building block everything else can be built from | The one core with a real capability GAP inside the carrier vs standalone: full feature set (dynamic routing, hold/feedback) only exists standalone; carrier-embedded exposes just topology/ready/routing_mask/cardinal_edge |
| **adder** (`adder_cell_v4[c]`) | **2** — real two-stage A/B capture, both genuine operands | 32-bit add, or subtract via `subtract_mode` (two's complement) | Exponent-difference computation for float work uses this directly |
| **ram** (`ram_cell_v4[c]`) | **1** — single-arrival capture, no A/B staging | Stores one 32-bit value (`init_data`), offers it; `fixed_mode` = never captures, offers a constant forever | Widest standalone config (80 bits) — `init_data` alone is 32 bits |
| **compare** (`compare_cell_v4[c]`) | **1** — single-arrival capture, computed against a configured value | Signed `>=` against a configured 32-bit `threshold` | `threshold` needs two half-word PROG_ID writes (too wide for one) |
| **branch** (`branch_cell_v4[c]`) | **1** to set the held reference, **1 per subsequent comparison** | Held-reference two-phase compare: first arrival becomes the baseline (never itself compared); every later arrival compared against it, routed by a 3-outcome (`<`/`=`/`>`) table, each independently configured | Most structurally complex core — 15 real fields, needed a 4-bit PROG_ID (not 3-bit) just on field COUNT. Real ROLLING MODE: the just-compared value can become the new reference (drift detection) |
| **accumulator** (`accumulator_cell_v4[c]`) | **continuous** — two independent triggers (`inc_dir`/`dec_dir`), not a matched pair, never one-shot | A live, always-running total; `step_amount` per increment/decrement, `pulse_mode` for reset-after-threshold | State updates unconditionally even when `active=0` — only the OFFERED snapshot freezes, not the internal total |
| **latch** (`latch_cell_v4[c]`) | **continuous** — one arrival per SET/CLEAR/TOGGLE trigger | A single persistent bit; SET/CLEAR/TOGGLE, priority CLEAR > SET > TOGGLE if several land the same cycle | Cheapest core standalone (~8.5 ALM at N=1). Addon chain still useful on 1 bit — invert flips all 32 offered bits, shift relocates which position carries it |
| **sequencer** (`sequencer_cell_v4[c]`) | **0** — genuinely no capture side at all | Offers a config-fixed cyclic list of up to 4 real 8-bit values, in order, advancing only once the current offer is acked | `ack_out` is permanently tied low on every direction — nothing to acknowledge, ever |
| **command** (`command_cell_v4[c]`) | mode=0 (TRIGGER): watches continuously for a 4-bit toggle pattern; mode=1 (PROGRAMMER): starts on first arrival | TWO simultaneously-active roles on one core type: TRIGGER freezes/unfreezes a buffer stream on a symmetric toggle match; PROGRAMMER relays captured words onto a TARGET cell's own real programming channel — genuine live, runtime reprogramming of another cell | The "hidden superpower" — proven end-to-end programming a fresh, never-configured target live (`#644`). No addon chain (never produces a dataflow value) |
| **mul** (`mul_cell_v4[c]`) | **2** — same two-stage A/B shape as adder | 32-bit multiply (`bitwise_multiplier_32bit`), low 32 bits of the product offered | Purely combinational multiplier — zero extra latency vs add/sub. High 32 bits computed but not offered by this core |
| **priority** (`priority_cell_v4[c]`) | **1**, chosen from potentially several simultaneous candidates | Arbitrates which of several simultaneously-arrived inputs gets captured first — configurable per-direction rank (2 bits each); `scheduling_mode` selects strict priority (0) or weighted round-robin (1) | Only core whose job IS the arrival-selection decision itself, not what happens after capture. Strict mode can starve low-rank ports under sustained load — that's why weighted mode exists |

---

## Quick answers to common design questions

- **"Does this core need one arrival or two?"** — see the table above.
  nano is the only one where "two" is a formality (dummy second
  arrival) rather than two genuine operands (adder/mul).
- **"Can I live-reprogram a field on a running core without resetting
  it?"** — yes, for any core's own fields, via its PROG_ID channel
  (config-off-shell). For the carrier's shared addon block
  (`shift_amt`/`shift_fine`/etc.), only on `v1d` via
  `SEL_ADDON_CONFIG` — `v1` cannot.
- **"Does this core have its own addon chain if used standalone
  (outside a carrier)?"** — only `_v4` (non-c) cores do, and even
  then, never `shift_fine`. A bare `_v4c` core has no addon capability
  at all outside a carrier.
- **"Which core has no output/consume side?"** — sequencer has no
  capture (offer-only); command's trigger mode consumes but produces
  no ordinary dataflow output.
- **"Which cores keep running state alive even when `active=0`?"** —
  accumulator and latch (continuously-live models) — everything else
  is one-shot capture-then-offer.
