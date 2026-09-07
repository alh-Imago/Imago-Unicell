# Cores & Wrappers — Cross-Reference Table

**A living reference, not a deep dive on any one cell.** For the
detailed internal structure of the original nano/stripped cell itself
(`unicell_stripped_v1.v`/`v2.v`), see `CELL_INTERNALS.md` — that
document isn't repeated here. This file exists to answer a different
question: *across everything built so far, what's a CORE, what's a
WRAPPER, what's neither, and what's actually been proven where?*

**Update this file whenever a new core/wrapper is built or a status
changes** — same discipline as everything else in this project:
`points.md` is the ground-truth ledger for the story of HOW something
was proven; this file is the settled, current SNAPSHOT of WHAT exists.
If they disagree, `points.md` wins — re-check the relevant entry
numbers cited below.

See also: `CELL_GOTCHAS.md` — real, per-cell/mechanism behavioral
facts that will silently bite you if you don't know them (release
triggers, watchdog timescales, hardware-confirmed-vs-sim-only status),
kept separate from this file because they aren't about WHAT exists,
they're about HOW to use it correctly.

## Real design principle: prefer a CORE over a specialist cell, stated explicitly (Alan, 2026-08-25)

**The real, governing reason, not just a style preference:** a new
CORE joins `unicell_super_v1.v`'s own `core_select` mux — meaning
EVERY cell in the grid can become that core, chosen freely at
ICM-programming time. A structure built from cores can be placed
ANYWHERE, and a different ICM program can rearrange the whole grid's
own roles without touching the `.sof` at all. A specialist/dedicated
cell (the DSP wrapper family's own category, below) is wired into
SPECIFIC, FIXED grid positions at `.sof`-build time — its position is
permanent for that bitstream. Building specialist cells by default
would slowly fix more and more of the grid's own layout at synthesis
time, eroding the ICM/Designer/compiler's own real mutability — "any
structure can be anywhere, not fixed in a `.sof` design," Alan's own
words.

**The real, known exception, not a contradiction of the rule:**
genuinely scarce, expensive hard-IP-adjacent resources — the DSP
wrapper family's own real, stated reason for existing outside the
`core_select` mux (`#453`/`#474`): the real ALM tax of making Nios
custom-instruction floating-point hardware a universal option would be
paid by every cell, whether it uses it or not. When the underlying
resource genuinely can't be cheaply replicated in every cell position,
specialist placement is the correct choice, not a shortcut — but it's
the exception, not the default. The recombiner (`#497`) is the recent,
concrete proof the DEFAULT works: rather than a new dedicated packer
cell, it's built entirely from two cores/an addon that are ALREADY
universal (`adder_cell_v1.v`, `shift_lane_addon_v1.v`) — real
capability, zero new position-fixed hardware.

## Real standalone-vs-super-carrier behavior — per #477's own original ask

**The general rule, checked directly against `unicell_super_automaton_
v1.py`'s own dispatch code, not assumed: five of the six cores behave
IDENTICALLY whether run standalone or reconstructed inside the super
shell.** RAM, adder, accumulator, comparator, and latch's own
`_deliver_*`/`_offer_state_*` handlers are faithful, full-featured
reimplementations of their standalone RTL — no reduced field set, no
missing capability.

**Nano is the one real, known exception.** Standalone
(`unicell_stripped_v1.v`, driven directly, no shell), nano exposes its
FULL real feature set — including `dynamic_route_en`/`pattern_low`/
`pattern_equal`/`pattern_high` (real, RTL-confirmed comparator-driven
branching, `#140`/`#156`) and `hold_in`/`fb_internal_in`/`is_command_
cell`. Reconstructed as a core INSIDE the super shell
(`unicell_super_v1.v`'s own `core_select=0` case), only the BASIC
subset is wired through — `topology`/`ready`/`routing_mask`/
`cardinal_edge`. This gap sat unnoticed until directly questioned
(`#490`-`#491`) and is the entire reason the branch/comparator core
(`#491`-`#497`) exists — a real, NEW core built specifically to bring
this class of capability universally into the super shell, per the
design principle above, rather than trying to expose nano's own
reduced-subset gap by wiring more nano-specific pins through
piecemeal.

## The SHELL — identical across every core

Every cell in this table shares the same external interface, regardless
of what's inside. This is the whole point of the SHELL/CORE split
(`points.md` #253): only the CORE differs between rows below.

| Port group | Signals |
|---|---|
| Data | `data_in_n/s/e/w`, `data_out_n/s/e/w` (32-bit each) |
| Handshake | `arrived_n/s/e/w`, `fire_n/s/e/w`, `ready_in_n/s/e/w`, `ack_out_n/s/e/w`, `ack_in_n/s/e/w` |
| Control | `freeze_in`, `cfg_valid`, `cfg_data` (64-bit, field layout is CORE-specific — see each row's own file header) |
| Readiness | `ready_out` — present on most cores; **`accumulator_cell_v1.v`/`latch_cell_v1.v` genuinely lack this port** (see notes below, not an oversight for those two, though its ABSENCE from an early draft of `top_sentinel_discrete_test_v1.v`'s own wiring WAS a real bug, `points.md` #298) |

## CORES — what's inside the shell

| Core | File | Internal capture pattern | Internal shell connection | Real Quartus status |
|---|---|---|---|---|
| Nano (gate tree) | `unicell_stripped_v1.v` | Two-arrival, full gate computation | Direct combinational logic on captured operand(s), see `CELL_INTERNALS.md` for the complete internal model | **Real, standalone** — ~100–106 ALM (`#209`/`#224`) |
| RAM (latch) | `ram_cell_v1.v` | Single-arrival capture, held until drained | Captures once → holds → offers on drain | **Real, standalone** — 3.86 ALM, 277.32 MHz (`#250`) |
| Adder | `adder_cell_v1.v` | Two-arrival matched pair | Captures A, then B (direction-agnostic) → `adder_v1.v` carry chain → offers sum | **Real, standalone** — 5.24 ALM, 233.97 MHz (`#261`) |
| Memory-interface | `mem_interface_cell_v1.v` | Single-arrival, READ/WRITE mode | Captures addr/data → drives `bram_controller_v1.v` | Sim-only |
| Mux (routing) | `mux_cell_v1.v` | Single-arrival, routing-byte decode | Captures value+routing → decrements count → selects one of 3 usable output faces | Real only *inside* the full-system aggregate (`#280`/`#283`/`#286`) — no standalone ALM/Fmax breakdown exists |
| Combiner (root) | `combiner_cell_v1.v` (proven) / `v2.v` (tree-capable, `#295`'s own reference) | Fixed round-robin scan, unconditional advance | Scans configured slots → stamps ID → writes `bram_controller_v1.v`/`v2.v` directly (not through the cardinal offer/drain path) | Real only inside the aggregate — no standalone breakdown |
| Combiner (child) | `combiner_relay_v1.v` | Same round-robin scan as root | Same scan, offers UPWARD via cardinal data+routing instead of writing to BRAM | Real only inside the aggregate |
| Read-splitter | `mem_read_splitter_v1.v` (proven, READ-only) / `_test.v` (debug-write extension) / `_ext.v` (external-memory variant) | Single-arrival address capture | Captures address → drives BRAM → splits DATA/ROUTING onto separate outputs | Real only inside the aggregate |
| **Accumulator** | `accumulator_cell_v1.v` | Hold-and-refire, direction-tagged, capture NEVER blocked | Arrivals on `inc_dir`/`dec_dir` update the internal total unconditionally; the OFFERED snapshot only refreshes when free (`#294`'s own real protocol adaptation) | Sim-only for the core alone; wrapping top-level (`top_sentinel_discrete_test_v2.v`) has a real, SDC-confirmed Quartus fit (`#306`-`#308`) |
| **Comparator** | `compare_cell_v1.v` | Single-arrival, STATELESS | Captures value → compares against a configured threshold → offers boolean result | Sim-only for the core alone; see accumulator's row for the wrapping top-level's real Quartus status |
| **Latch** | `latch_cell_v1.v` | Hold-and-refire, SET/CLEAR, capture NEVER blocked | Arrivals on `set_dir`/`clear_dir` update the internal latch unconditionally; CLEAR takes priority if both arrive the same cycle (`#279`/`#284`'s own established rule) | Sim-only for the core alone; see accumulator's row for the wrapping top-level's real Quartus status |

**A note on the accumulator/latch's missing `ready_out`:** genuinely
correct by design — since capture is never blocked, these two cores are
always ready, so a `ready_out` port would just be tied permanently high.
The REAL bug (`#298`) wasn't the absence of the port on the core itself
— it's that a later integration wired a downstream consumer's
`ready_in` to a wire that was never actually connected to anything,
because the port didn't exist to connect it TO. Worth remembering if
either core is extended: add the port explicitly rather than relying on
implicit "always ready."

## DSP wrappers — dedicated, command-wrapped glue, not a CORE or an ADDON

**New as of 2026-08-23/24, per `points.md` #453/#461-#475.** Sits
outside the SHELL/CORE model entirely, by deliberate design (`#453`,
matching `#427`'s own earlier precedent for the BRAM interface): a
piece of dedicated, command-wrapped fabric-facing infrastructure, not
baked into `unicell_super_v1`'s own `core_select` mux. The whole
architectural case for keeping it separate — placement constraints,
the real ALM tax a universal option would impose on every cell,
regardless of use — is worked through in `#453`/`#474`.

| File | Real IP behind it | Real `n` value | Real status |
|---|---|---|---|
| `dsp_arith_wrapper_v1.v` (OP="ADD") | `alterafpf_add_single` (Nios II Custom Instruction, "Floating Point Hardware 2 Multi-cycle") | 253 | **Real, hardware-confirmed** (`#472`) — fire/ACK/re-arming all correct on actual silicon. Real, precise cost: 354.0 ALM/instance (`#473`, excludes one-time JTAG bridge overhead) |
| `dsp_arith_wrapper_v1.v` (OP="SUB") | same real IP, different `n` | 254 | Sim-only, same entity/protocol path as the hardware-confirmed ADD case |
| `dsp_arith_wrapper_v1.v` (OP="MUL") | same real IP, different `n` | 252 | Sim-only, same entity/protocol path |
| `dsp_compare_wrapper_v1.v` (OP="GE"/"LE"/"NEQ") | Real entity name CONFIRMED (`#496`) — `alterafpf_ge_single_comb`, from Alan's own real generated `.qsys`; genuinely combinational, no clock ports at all | 228/230/226 | Sim-verified clean, zero regression. Not yet run on real silicon (ADD is the only real hardware-confirmed mode, `#472`) |
| `watchdog_v1.v` | n/a — pure fabric logic | n/a | **Real, hardware-confirmed as part of the DSP_ADD build** (`#472`) — genuinely programmable per instance (`cfg_valid`-loaded threshold, `#464`), NOT hardened |
| `host_bridge_dsp_v1.v` | Real ISSP bridge, same proven pattern as every other host bridge this project | n/a | **Real, hardware-confirmed** (`#472`) |

**A real, important finding, not a caveat to skip past:** the real IP
in use does NOT touch the card's own real hard DSP silicon —
`Total DSP Blocks 0 / 1,687` in the real Fitter summary (`#472`).
This is pure soft, fabric-LUT-based floating-point logic. The card's
own real 1,687 DSP blocks remain completely untouched by anything
built here. See `dsp_wrapper_timing.md` for the full real cost
breakdown, real timing table, and real watchdog threshold guidance —
including a genuinely important, hardware-only finding about watchdog
thresholds and real JTAG timescales that no amount of simulation would
have caught.

**Real, honest naming-mistake history, worth keeping for the same
reason the PCIe IP-reference collection exists (`fpga/ip-reference/
README.md`):** the real, top-level instantiable entity name for this
class of IP is whatever you name the instance in IP Catalog, NOT the
internal Qsys component "kind" one level inside it — confirmed the
hard way across two separate real Quartus build attempts (`#470`/
`#471`) before the real, generated `.qsys` file (now checked into
`fpga/ip-reference/`) settled it directly.



These have no shell, no cardinal ports — plain modules that a real core
instantiates internally.

| File | Role | Real Quartus status |
|---|---|---|
| `adder_v1.v` | Raw carry-chain adder | Confirmed real via `adder_cell_v1.v`'s own build |
| `addr_counter_v1.v` | Ack-gated wrapping counter | Confirmed real via its own dedicated top-level (`#249`) |
| `bram_controller_v1.v` | Single-stage synchronous read/write | **Real, standalone**: 145 ALM, 158.78 MHz, exact M20K bit-count match (`#265`) |
| `bram_controller_v2.v` | Registered-read-address fix for hierarchy-depth RAM-inference failure (`#284`) | Real, confirmed via the full-tree-system aggregate build (`#284`/`#286`) — no standalone breakdown |

## The other two architectural categories, per `#253`/`#293`

Not every real component built this project is a CORE (something that
fits inside the shell). Two more categories exist:

| Category | Definition | Real examples | Status |
|---|---|---|---|
| ADDON | Wraps around a cell's own shell from OUTSIDE to extend its capability, while the cell still participates in the cardinal fabric mesh | `shift_lane_addon_v1.v`, `nibble_mask_addon_v1.v`, `invert_addon_v1.v` (`points.md` #311) | **Real, standalone, sim-verified** -- faithfully ported from `unicell64_v3.v`'s own proven shift/lane/nibble-mask/invert mechanisms. Not yet wired into an actual cell instance or Quartus-built. |
| HOST-INTERFACE | No cardinal ports at all, doesn't join the fabric mesh — bridges the fabric to something OUTSIDE it entirely (JTAG today) | `pcie/unicell_issp_bridge.v` (pre-existing, full-cell era), `sentinel_issp_bridge_v1.v` (`#288`) | **Real, hardware-confirmed** (`#291`) — but see `#293`'s own real cost: baked into the bitstream at synthesis time, no runtime toggle, every real hardware exercise needing one this session used its own dedicated Quartus project |

## The super carrier shell — a genuinely different SHELL, not a row in the table above

**New as of 2026-08-15/16, per `points.md` #320-#356 -- see
`SUPER_CELL_INTERNALS.md` for the full field-map/mechanism reference,
not repeated here.** Every row in the SHELL/CORE table above describes
ONE core committed at synthesis time inside ONE ordinary shell. The
super carrier shell (`unicell_super_v1.v`) is a real, different third
thing: a SINGLE physical shell holding ALL SIX real cores (nano, RAM,
adder, accumulator, comparator, latch) simultaneously, runtime-selected
via an 80-bit `SUPER_LATCH` register's own `core_select` field --
config-time selectable, not synthesis-time fixed.

| | Status |
|---|---|
| The shell itself | **Real, Quartus-confirmed**: 213 ALM total, ~25.9 ALM isolation/selection overhead (smaller than any one of the 3 biggest cores it holds), `clk_div` 200.76 MHz, best timing margin of any build this session (`points.md` #320-#323) |
| Self-test FSM | **Real, sim-confirmed** across an extended run, ready for a real Quartus build (`top_unicell_super_test_v1.v`, `points.md` #321) |
| ICM v3 format (`SUPER_LATCH` encode/decode) | **Real, verified two independent ways**: bit-for-bit against `tb_unicell_super_v1.v`'s own real RTL test vectors, AND mechanically re-derived from the RTL's own comments with zero mismatches (`points.md` #336/#355) |
| VM (`SuperCell`/`SuperGrid`) | **Real, tested** -- all 6 cores, event-driven dispatch (`points.md` #337) |
| Tile library (Tier 0 primitives + Tier 1 composed tiles) | **Real, tested in the VM** -- `sentinel`/`dual_threshold_monitor`/`twin_sentinel` all marked `proven="sim-only"`, NOT yet Quartus/silicon-confirmed as these specific multi-cell layouts (`points.md` #338-#342) |
| Compiler (DSL + Python-AST frontends) | **Real, tested** -- see `UNICELL_S_DSL_MANUAL.md` (`points.md` #343-#350) |
| `addon_config`'s own field positions | **Real gap**: not covered by the mechanical RTL-comment extraction that validates everything else -- wired via direct module port connections, a genuinely different RTL pattern (`points.md` #355) |



- **Standalone Quartus data (its own dedicated build, ALM/Fmax isolated to that one core):** nano, RAM, adder, `bram_controller_v1.v`, `addr_counter_v1.v` — the original, earliest-built pieces.
- **Real Quartus data, but only as part of a larger aggregate (no isolated ALM/Fmax number exists for that core alone):** mux, combiner (both variants), splitter (all variants), `bram_controller_v2.v`.
- **Sim-only, but real Quartus fit already confirmed for the wrapping top-level (SDC-verified, real timing):** accumulator, comparator, latch — the three cells themselves aren't independently Quartus-built yet, but `top_sentinel_discrete_test_v2.v` (the self-test wrapping all three) has a real, SDC-confirmed fit: 78 ALM, `clk_div` 272.26 MHz, no failing paths (`points.md` #306-#308).
- **Sim-only, no Quartus attempt yet:** `shift_lane_addon_v1.v`, `nibble_mask_addon_v1.v`, `invert_addon_v1.v` — the first real ADDON instances (`#311`), faithfully ported and testbench-verified, not yet wired into any cell or built in Quartus.
- **A genuinely different SHELL (see its own section above), real at the RTL level, sim-only above it:** the super carrier shell itself is Quartus-confirmed real silicon (`#320`-`#323`); everything built on top of it this session (ICM v3, the VM, the tile library, the compiler) is real and tested in software/simulation, not yet independently Quartus/silicon-confirmed as those specific multi-cell layouts.

## The VIX Carrier — a real, third, newest generation, distinct from both tables above (`points.md` #628-#666, 2026-09-04/05/06)

**Real, important naming warning, stated up front:** this is a
GENUINELY separate lineage from the super carrier shell above, not an
extension of it — despite both using cell/file names that include
"v4." `unicell_super_v4.v` (the 4th shell VERSION in the table above,
wrapping the OLD individual core files like `ram_cell_v1.v`) and
`nano_gate_v4.v`/`command_cell_v4.v`/etc. (the NEW cell GENERATION
described here) are unrelated — a real collision found and deliberately
avoided before any VIX Carrier RTL was written (`unicell_vix_carrier_
v1.v`'s own header), not discovered after the fact. When in doubt,
check which FILE is meant, not just the version number attached to it.

**What it actually is:** a full second, parallel core family —
`nano_gate_v4.v`, `ram_cell_v4.v`, `adder_cell_v4.v`, `accumulator_
cell_v4.v`, `compare_cell_v4.v`, `latch_cell_v4.v`, `sequencer_cell_
v4.v`, `branch_cell_v4.v`, and the genuinely new 9th core, `command_
cell_v4.v` — each wrapped in its own real CARDINAL CONTROL SHELL
(`nano_shell_v1.v`, `ram_shell_v1.v`, `adder_shell_v1.v`,
`accumulator_shell_v1.v`, `compare_shell_v1.v`, `latch_shell_v1.v`,
`sequencer_shell_v1.v`, `branch_shell_v1.v`, `command_shell_v1.v`,
`points.md` #639/#645/#646), then all 9 combined into one real,
mutually-exclusive, runtime-`core_select`ed physical cell:
`unicell_vix_carrier_v1.v` ("V" for version, "IX" for the real 9th-core
count — Alan's own naming, `#647`).

**Why the cardinal control shells exist, the real reason, not
cosmetic:** per Alan's own direct design call, every one of a core's
flat, single-bit live-control ports (`active`, `freeze_in`, and — for
nano specifically — `hold_in`/`fb_internal_in`/`a_reemit_in`/
`a_update_in`/`a_self_update_in`) becomes a real 4-way cardinal port
set (`_n/_s/_e/_w`), OR-combined internally, matching the same
per-direction shape `program_in`'s own channel already used. This is
what makes the command core (below) able to genuinely freeze/hold/
reemit/update a neighboring cell over a real physical link, instead of
a flat wire with no real hardware meaning.

**The command core — genuinely new, not a variant of an existing
core:** one core, mode-selected, deployed as two simultaneously-active
instances in a real topology (the same pattern `ram_cell_v4.v`'s own
`fixed_mode` bit already uses):
- **TRIGGER mode** (`mode=0`) watches a real cardinal buffer stream for
  a config-set 4-bit toggle pattern — the outermost gate in the whole
  pipeline, detecting its own start/end of burst.
- **PROGRAMMER mode** (`mode=1`), downstream of trigger's own gating,
  freezes its real target, asserts `program_out`, and relays each
  captured word onto the target's real programming channel — the
  DRIVE side of the programming handshake every other core only ever
  RECEIVES, new to this core alone in the family.

**`VIX_LATCH[159:0]`, the real config register, a deliberately round
number with real reserved headroom, not packed tight:**

| Field | Bits | Meaning |
|---|---|---|
| `core_select` | `[4:0]` | `0`=nano `1`=adder `2`=ram `3`=compare `4`=branch `5`=accumulator `6`=latch `7`=sequencer `8`=command; `9`-`31` reserved |
| `core_config` | `[132:5]` | 128 bits, a UNION not a struct — sized to the single widest real core (nano), reinterpreted per `core_select`, zero reshuffling since every core's own real field layout already starts at bit 0 of its own space |
| reserved | `[159:133]` | 27 bits, genuine future headroom |

**Real, genuinely new mechanisms beyond the old lineage, not just a
bigger clone of it:** (1) the cardinal control shells above; (2)
real, safety-critical programming-channel routing the old lineage
never needed — `PROG_ID` values collide across core types (`PROG_ID=0`
means `topology` on nano, `downstream_mask` on adder), so `program_in`/
`prog_arrived_in_*` are gated to the SELECTED core only, the same
mutual-exclusion principle `cfg_valid` already used, extended to the
live reprogramming channel; (3) `core_config` widened to 128 real bits
(nano's own real width), not the old lineage's 42-bit union; (4) the
command core's own genuinely new external ports (`freeze_out_*`, the
drive-side programming channel).

**Real, current status, honestly stated:**

| | Status |
|---|---|
| RTL (all 9 cores + 9 cardinal shells + the carrier itself) | **Real, sim-verified** — every core's testbench passes, plus a full carrier-level testbench (`tb_unicell_vix_carrier_v1.v`) and real end-to-end tests (a real, bounded loop-ring construction wired through the cardinal shells, `#640`; a command core genuinely programming a fresh, never-configured target end to end, `#644`) |
| Quartus/real silicon | **Not yet run.** `project_assemble_v1.py --shell vix` (`#648`) exists and can generate a real N-cell VIX Carrier project, but the Quartus license expired (`#649`) before it could be run — no real ALM/Fmax numbers exist for this family yet |
| VM (`VixCarrierCell`/`VixCarrierGrid`/`VixCarrierSlot`) | **Real, tested** — genuinely subclasses `SuperCell` (the 8 already-modeled core types keep their own proven dispatch, inherited for free), adding only the command core as new mechanism (`#655`-`#658`, `#660`) |
| ICM file format | **Does not exist yet.** ICM v3/v4 (below) are scoped to the OLD core lineage only — the VIX Carrier has no portable, on-disk program format of its own; it lives in RTL simulation and the VM's own in-memory classes only |
| Compiler/DSL reachability | **Not yet wired in.** The DSL/LLVM-IR frontends target the OLD lineage's tile library; promoting any of this to a compiler target is real, separate, unstarted work |


