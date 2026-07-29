# Imago UniCell — Active Plan
*Single source of truth for what needs doing and why.*

> **DEFINITIVE TASK PATH (2026-07-29) — supersedes the 2026-07-24 path below.**
> PCIe is PARKED (not blocking, not abandoned) after two weeks isolating the
> BAR0-dead-data symptom down to somewhere upstream of the FPGA entirely --
> link training, config space, the bridge memory window, the fabric itself,
> all confirmed healthy; zero TLPs ever reach the Hard IP's RX decoder,
> reproduced identically by two independent tools (docs/PCIE_ARRIA10_NOTES.md
> §9). That's below what more RTL work or BIOS-toggle guessing can fix --
> genuinely needs a PCIe protocol analyzer and/or specialist help. Revisit
> LAST, once everything below is done, not now while it blocks nothing else.
>
> **New priority, ahead of the cardinal-bit/comparator work below: the
> command-cell RAM-read mechanism.** Realization (2026-07-29): the
> completion-flag + two-counter design from the July 4 session
> (docs/design-notes/bram_load_protocol.md, `loader_fsm_v3.v`) wasn't just
> for one-time boot configuration -- it's the exact reusable serial reader
> command cells need at runtime. `loader_fsm_v3.v`'s `start` port is a
> genuine re-arm pulse (confirmed in the state machine: `S_IDLE: if (start)
> begin cell_idx<=0; done<=1'b0; ... end`), and its config-table source is
> already documented as "a ROM, a BRAM read port, or (in sim) a plain
> array" -- built with this reuse in mind from the start. The runtime loop:
> RAM holds an array of pending commands (we know the addresses) -> the
> SAME shared loader-FSM-style reader walks it serially, one entry at a
> time (only one reader needed, since this is inherently serial anyway) ->
> applies each to whichever cell needs reconfiguring -> a command cell's
> own emitted output (is_command_cell, `cmd_latch[10]`, cmd_emit_bus/data)
> can target RAM as its destination (same "one memory, multiple roles"
> design already in `bram_dp_v3.v`), closing the loop. What's new versus
> what's already built: the boot-time loader is proven for CONFIGURATION
> (topology/methodology, the 3-cycle wire format); the runtime version
> needs the same reader re-purposed/re-triggered for ongoing
> SET_TARGET+INJECT-style DATA application, sourced from a live BRAM read
> port instead of a fixed boot ROM.
>
> **Sequence from here:**
> 1. Add + sim-test the command-cell RAM-read runtime mechanism (above).
>    Sim-first as always -- confirm the re-arm/re-trigger behavior and the
>    RAM-sourced config-table wiring before any Quartus work.
> 2. Some Quartus/silicon work to validate it for real, same discipline as
>    everything else this project has silicon-proven.
> 3. Once implemented and tested: populate the full card (Step 4 below --
>    16-zone/400-cell scale-up), since this is a capability the full card
>    should have from the start, not bolted on after.
> 4. Then the rest of the backlog: native filesystem/Pond work, the
>    compiler/VM catch-up (still stopped at cell v2.3 per points.md),
>    Composer, documentation.
> 5. Only at the end: revisit PCIe, with fresh eyes and/or real specialist
>    help -- not now, while it blocks nothing else on this list.
>
> The cardinal-bit (#42) and comparator/routing (#49/#51) work below
> remains real and still needs doing -- this new priority sits ahead of it,
> not in place of it.

> **2026-07-24 path (still valid for #42/#49/#51, PCIe section superseded
> above) — the current active sequence, supersedes
> the 2026-07-07 SUBSTRATE-REBUILD ROADMAP below for near-term work.** That
> roadmap predates this session's PCIe bring-up and the cell-mechanism decisions
> that came out of it (points.md #42/#49/#51, #47 dropped). This is the real
> path to a single, definitive main design -- everything else catches up to
> THIS, not the other way around.
>
> **Step 1 — PCIe (PARKED, see above, not blocking).** Full chain (Hard IP + PIO
> bridge + CDC bridge + pcie_unicell_bridge) synthesized, pinned, fitted, real
> Fmax measured clean (58.62MHz, points.md #52). BAR0 corrected to 32-bit
> non-prefetchable after the original 64-bit-prefetchable config produced
> universal 0xFFFFFFFF reads; Device/Revision/Subsystem IDs fixed in the Hard
> IP's own parameters after being left at 0.
>
> **2026-07-27/28 detour, now resolved:** the fabric was found to reject
> commands over BOTH JTAG and PCIe (icm64_readstate.tcl failing identically
> either way) -- traced to a floating `UART_RX` pin (never had a .qsf pin/
> pull-up assignment) corrupting `cpu_valid` via the three-master OR. Fixed
> by tying `uart_rx` to constant idle-high in `top_arria10_zone1_v3.v`
> (commit `1c5ea5e`); confirmed on silicon 2026-07-28 --
> `icm64_readstate.tcl` now lands `RECONFIGURE`/`SET_OUTPUT_ADDR` correctly,
> cell fires, output captured (see docs/PCIE_ARRIA10_NOTES.md §7e for the
> full before/after). This was blocking Step 1, not caused by it.
>
> Live BAR read/write test against real cells (the icm64_readstate.tcl
> sequence, replayed over PCIe specifically, not just JTAG) is the
> remaining confirmation before this step closes.
>
> **2026-07-28/29: attempted, isolated to upstream of the FPGA.** BAR0
> reads/writes return 0xFFFFFFFF on every attempt via both the
> project's own celltest tool AND Intel's own Alt_Test.exe. Ruled out,
> each confirmed clean: memory decode, BAR0 address, the pld_core_ready
> fix (byte-diffed against the live compile-folder file), the IP's
> qsys parameters (byte-diffed likewise), link training (Gen2 x8,
> confirmed via Alt_Test.exe AND SignalTap's ltssmstate/pll_locked),
> and fabric health (icm64_readstate.tcl re-confirmed clean on JTAG the
> same session). SignalTap shows the application interface genuinely
> out of reset and ready (txstready/rx_st_ready both high) but ZERO
> TLPs of any kind ever reach the Hard IP's RX decoder
> (rx_st_valid_r/rx_st_bar_hit_o/rxstbardec1 all flat low the entire
> capture). Two independent tools failing identically at the same
> layer, with link/config-space healthy and app-interface ready, points
> at something host/BIOS/slot-level (IOMMU/VT-d is the leading
> candidate), not an RTL or bitstream bug. Full evidence trail in
> docs/PCIE_ARRIA10_NOTES.md §9. Step 1's remaining close-out item is
> blocked on that host-level investigation, not further RTL work.
>
> Full ordered testing
> roadmap for this stage -- repeatability, opcode coverage, the PCIe
> replay itself, and a real-silicon arbitration stress check -- is in
> docs/PCIE_ARRIA10_NOTES.md §8.
>
> **Step 2 — Build #42 into unicell64_v3.v.** Decompose the single global
> `transit_only` bit into 4 independent per-edge cardinal bits (reclaims the
> 3 free bits at cmd_latch[18:16], repurposes transit_only) -- pure decode
> logic, no new physical wiring. Sim-verify (iverilog + full regression)
> before touching silicon.
>
> **Step 3 — Build #49 (+ #51's sizing) into the fabric.** The comparator ->
> pattern -> cardinal -> openness AND-gate chain, plus the local-bus fallback
> (cardinal=0 AND openness=1). Needs two genuinely new registers: the 32-bit
> threshold latch and the 32-bit routing latch (sized 3x6 pattern + 6 cardinal
> + 6 openness + 2 mode = 32, 6-direction/3D-ready per #51). Sim-verify fully
> before silicon. #47 (wraparound) is explicitly OUT of scope here -- dropped,
> not deferred (points.md #47/#50).
>
> **Step 4 — Scale to the full card.** Once #42 and #49 are both proven at the
> current single-zone (25-cell) test scale, move to the full 16-zone/400-cell
> card configuration (a known-good reference point already fitted once before,
> pre-PCIe: 74% logic, ~56MHz Fmax). Re-confirm real Fmax/timing at full scale
> -- not assumed from the single-zone numbers. PCIe integration carries forward
> unchanged; only the fabric-side zone count changes.
>
> **That becomes the main design.** Not a branch, not an experiment sitting
> alongside the old one -- the current baseline everything else is measured
> against. Any bits left free in either register after Step 3 may find uses
> later, but nothing in this task path depends on that.
>
> **Consequence, stated plainly (Alan, 2026-07-24): a lot of the work behind
> this point has fallen far enough behind that it's now irrelevant as written
> -- including the existing model library.** The 2026-07-07 roadmap's Stage 3
> ("migrate existing models in turn") and Stage 6 ("trix models last") assumed
> migrating models onto a substrate that didn't yet have programmable per-edge
> shape at all. Once shape is a runtime config-bit pattern rather than
> something fixed at synthesis, models built against the old fixed-topology
> assumptions may need to change in ways that aren't simple ports -- this
> won't be known for certain until Steps 2-4 land and there's a real substrate
> to check them against. The two-cell holding pattern for MathTrix (points.md
> #13) is one concrete, already-open example of a model whose correctness may
> depend on exactly the semantics this task path is about to change -- worth
> re-checking first once the new substrate exists, not assuming it still holds.

> **SUBSTRATE-REBUILD ROADMAP (2026-07-07) — the current active sequence.**
> This supersedes the older body below for near-term work. It came out of the
> routing_mask rework and the pentacross placement + transit-cell findings
> (points.md #14–#18). The ORDER matters: each stage gates the next, and the
> substrate must be COMPLETE before the first real model is built on it, so that
> what we learn building that model is a real lesson, not an artifact of an
> incomplete substrate ("learning as we go").
>
> **Stage 0 — Complete the substrate (SIM). [DONE 2026-07-07 — transit primitive built & verified, tb_v3_transit green, full regression green.]**
>   Build the transit-cell primitive (points.md #18): a suppress-local flag +
>   methodology opcode next to routing_mask; split the array's local-vs-routing
>   valid paths so a transit cell routes across a boundary WITHOUT presenting on
>   its own cluster's bus. Verify in iverilog (routes across, no local
>   presentation), then full regression. WHY FIRST: whether transit cells exist
>   changes how every model (including the adder) is placed and routed. Building
>   the adder without it would bake in workarounds for something it wouldn't need.
>   NOTE: the pentacross placement rule (#17) may itself change once transit
>   exists — some crossings #17 works to avoid may be cheaply handled by a transit
>   hop. So #17 is the rule for a NO-TRANSIT substrate; revisit/finalise it here,
>   on the complete substrate, before it's locked into the compiler (Stage 3).
>
> **Stage 1 — Build + test the adder (SIM).**
>   Generate RTL from the (possibly revised) pentacross placement, now free to use
>   transit hops where they help. Confirm iverilog matches the event-sim's
>   prediction (correctness AND zero same-cluster collisions). The 37-cell,
>   12-cluster placement is proven in the event-sim already (#17); this turns it
>   into real, tested RTL.
>
> **Stage 2 — Flash + test (SILICON). [DONE 2026-07-09 — transit PROVEN ON DIE: transit=1 crossed east with local bus quiet; transit=0 control drove both. CMD_ARRAY_RESET also confirmed working on silicon.]**
>   One Arria 10 reflash covering ALL of this session's substrate changes together:
>   routing_mask + METH_SET_ROUTING, the CMD_SWAP_AB config_match fix, the array
>   local-vs-routing split, and the transit-cell flag. First real "works in
>   silicon" checkpoint for the new substrate.
>
> **Stage 3 — Migrate existing models in turn.**
>   Move each model to the new substrate, re-verifying as we go — learning forward
>   from the adder build. This is where points.md #7's standing worry bites (no
>   tile's cell count trusted until re-verified against real execution) and where
>   the MathTrix 2-cell question (#13) gets its real answer.
>
> **Stage 4 — Rebuild the compiler.**
>   Now enforcing the (finalised) pentacross placement rule natively
>   (docs/COMPILER_TILE_CONFIG.md), not per-model.
>   ALSO (2026-07-12): placement rules discovered from silicon (like #17) have
>   TWO obligations, not one — the loader/compiler must REJECT illegal
>   placements before they're ever built, AND the VM/simulator must ACCURATELY
>   MODEL what real hardware actually does in a hazard case (the exact #32
>   OR-reduction/corruption signature), not an idealized guess. Placement
>   affects correctness itself here, not just performance — a naive VM that
>   simply OR'd every fired value without modeling the last-firer-wins address
>   behavior would let a design pass simulation clean and then silently
>   corrupt on real silicon. "Sim-first" only holds if the VM is a genuine
>   reflection of the cells' actual placement-dependent behavior, not just a
>   faster version of the loader's own legality check.
>   SECOND CONCRETE CASE (points.md #37): a looping cell (loop_back+latch_in,
>   or CMD_MEM_CALL) continuously re-emits its held value every cycle even
>   while a fresh cross-boundary write to it is in flight — a real, FIXED-
>   bound (~7 cycles, the measured cardinal transit) staleness window, not a
>   stall. Same two obligations as #17: the compiler should be able to flag a
>   program reading a looping value without accounting for known transit
>   latency, and the VM must model the exact staleness/cutover behavior, not
>   an idealized instant-update or blocks-until-fresh guess.
>   ALSO (points.md #19): define the SUBSTRATE MAP format and the
>   synthesis-application mechanism. The map is a single authoritative artifact
>   the user authors, synthesis consumes to place cells + wire bridges, ships
>   with the bitstream as its descriptor, and the compiler reads to precompute
>   routing_mask OFFLINE. It IS the topology (drives placement) rather than a
>   description that could drift -- so the loader's boot-walk VERIFIES against it
>   (CMD_ARRAY_RESET enables the walk) rather than discovering shape at runtime.
>   Kills the CELL_ID-vs-input_address bug class by making address relationships
>   explicit in ONE place all tools read from.
>
> **Stage 5 — Rebuild the workbench, then the composer.**
>   The composer is where the spatial pentacross view ("draw the dataflow arrows
>   between clusters; addressing is a within-cluster detail") becomes the authoring
>   surface. ALSO (points.md #19): this is the USER-FACING AUTHORING FRONTEND for
>   the substrate map -- "draw the cell patterns / shape, the tool emits the map."
>   The map format is the contract between this frontend and Stage 4's
>   synthesis-application mechanism. Supports custom-shaped substrates (a fabric
>   deliberately shaped to streamline a particular process), since the shape is
>   just a different authored map compiled into a fixed bitstream.
>
> **Stage 6 — Trix models/approach LAST.**
>   Folds in the deepest change (points.md #9: trix as .icm artifacts, not Python
>   runtimes). Sensibly last, once everything under it is stable.
>
> **Throughout — keep tabs for the final docs.** points.md is the running ledger;
> log each finding WHEN found, mark proven vs proposed, keep sessions/latest.md
> current. If each stage updates the ledger as it lands, the final docs are a
> consolidation job, not an archaeology job.

---

> **CURRENT STATE (2026-06-27) — body below is from 2026-06-09 and partly STALE
> (hardware now working: Arria 10 GX660 flashing fine over the Waveshare blaster).**
> For live state + next steps, read the catch-up block at the top of
> `sessions/latest.md` first. In short:
> - SILICON: per-cell config proven on the Arria 10 (CMD_LOAD_AT + target latch);
>   the RECONFIGURE-broadcast blocker is gone. Addressing model fully reconciled into
>   docs/ARCHITECTURE.md (invariant, relocatable models, 32-bit partition, Shore climb).
> - NEXT: (1) ICM-file streaming, offset-native — loop (SET_TARGET, LOAD_AT) pairs;
>   (2) packed adder as first heterogeneous ICM on silicon; (3) small: CMD_RECONFIGURE
>   auth-write under physical_mode (invariant clause 3).
> - Read docs/ARCHITECTURE.md "Addressing & Command Authority — INVARIANT" BEFORE
>   touching addressing/auth/targeting.

---

---

## Hardware Status

| Hardware | Status |
|---|---|
| iCEBreaker iCE40UP5K | Silicon validated, 31/31 tests, 4-cell limit (UART bus) |
| Arria 10 GX660 (IEI Mustang-F100) | PCIe alive, FTDI USB faulty — likely recoverable |
| Waveshare USB Blaster V2 + JST cable | £46 — ordered, paid 26th |
| Quartus 25.1 | Installed and licensed on F:\Q |

**Arria 10 diagnosis (refined):** Card draws <60W (IEI spec) — 550W bench PSU is
huge headroom, power starvation unlikely. Slot power optional per IEI spec — card
runs on 6-pin alone, no powered riser needed for isolated test. Display showing
ZERO is the card-ID (DIP switch), not a fault code. Two green LEDs + ID display =
board alive, FPGA powered. Likely faults: flaky FTDI or bad flash bitstream —
both JTAG-recoverable. **First test on cable arrival: jtagconfig → read IDCODE on
the 660. Clean read = JTAG chain + FPGA core alive, card recoverable.**

**Staged card plan:** 660 = proving card (bring-up, shift_in_en, scale test).
Then ~£100 early for Arria 10 1150 = clean performance card + rig seed. Working
660 → son's (dials in remotely; his once it enumerates in Linux).

---

## Naming Conventions — Verilog is Ground Truth

Python names must reflect Verilog names exactly.

- `preload_sel` — cmd_bus field. Python: `PRELOAD_SEL_ZERO`, `PRELOAD_SEL_ONES`
- `shift_sel`   — cmd_bus field. Python: `SHIFT_SEL_IN_EN`, `SHIFT_SEL_OUT_EN`

**Done:** `command_interface.py` aligned to `PRELOAD_SEL_*` (commit 5f0ae0f).
Legacy aliases (`PRELOAD_NONE` etc.) retained for backward compatibility.

---

## Test Suites — Current State

| Suite | Count | Status |
|-------|-------|--------|
| tests/vm/test_compiler_int32.py | 157/157 | ✓ passing |
| tests/vm/test_fp_tiles.py | 236/236 | ✓ passing |
| tests/fpga/test_sanity.py | 31/31 | ✓ silicon validated |

---

## Open Items — Non-Hardware

All previously-listed non-hardware items are now DONE (commits 5f0ae0f, 7c48aae,
0c70987). Remaining non-hardware work is architectural, no urgency:

- [x] Compiler auto-placement of bridge tiles — compile_pipeline_icm() on
      FormatRegistry. Expands BRIDGE_PLACEHOLDER records (gs=0x1) to GS_PASS
      cells with meta provenance. Synthesises connections from records when
      needed. Respects compiler_policy; blocks on errors. 22/22 tests.
- [x] Design-time confidence-threshold warning enforcement in the compiler
      (FormatRegistry.check_pipeline_bridges() — 16/16 tests)
- [x] SI_CHECK dimensional analysis integration — dimension_map added to
      FormatDefinition base + SI_Physics (17 concepts). check_pipeline_bridges()
      verifies bridge output_dimension against target format dimension_map.
      21/21 tests (was 16)
- [x] Bridge section in community contribution guide — updated: promote
      button shipping note corrected, compile-time validation section added
      (check_pipeline_bridges API, policy table, SI dimension note)
- [x] Bridge UI → cell_format.py round-trip — DONE (⬆ promote link +
      batch Export Custom Bridges button in Region Connector)
- [ ] DisplayPond hosted flag (GPU framebuffer passthrough). mathtrix_animate.py
      already covers the mathematical output side; the cell-array fire visualiser
      is deferred to Arria 10 scale.
- [x] BioTrix / ChemTrix / PhysTrix community models — DONE (175/175 tests, session 2026-06-14)

### Completed this session (was the old "open items" list)
- [x] MUL preloaded_a normalisation — bits expanded to full 32-bit words
- [x] Multi-param re-injection — all params to both a_vals and b_vals
- [x] Multi-param ordering test (7) + load/run API test (10) → 157/157
- [x] command_interface.py naming → PRELOAD_SEL_* (legacy aliases kept)
- [x] docs/RUNNING.md + ICM_FORMAT.md — inB references removed
- [x] README animated GIF (Gray-Scott) + paper wavefront figure
- [x] Region Connector: pipeline validation, custom bridges, tooltips, shortcuts
- [x] Dual licence: MIT (software) + CERN-OHL-P v2 (hardware)

## Arria 10 Quartus Bring-Up Notes (2026-06-15)

Hard-won findings — do not re-learn these:

- **Device string:** `10AX066H2F34E2SG` — chip marking says `E22SG` but Quartus
  internal name drops one `2`. Use the Quartus device browser to confirm, never
  type from chip marking alone.
- **IOPLL RST_N is active-low:** `.rst(1'b1)` = normal operation, `.rst(1'b0)` =
  force PLL reset. Passing `1'b0` causes a hard elaboration error during compile.
  Always drive high for normal operation.
- **`dont_touch` attribute ignored:** Quartus silently ignores this (Vivado/yosys
  only). Replace with `(* preserve *)` on zone boundary registers (`cmd_bus_r`,
  `cmd_data_r`, `cmd_valid_r` in `unicell_zone.v`) to prevent optimiser collapsing
  the registered 1-tick bridge handoff. Check Fitter report after first successful
  compile to confirm registers survived.
- **All five files needed:** `unicell.v`, `unicell_array.v`, `unicell_zone.v`,
  `uart_bridge.v`, `top_arria10.v` — Quartus does not auto-discover dependencies.
- **Top-level entity:** must be set to `top_arria10` in Assignments → Settings →
  General — not the project name.
- **PLL:** use IOPLL Intel FPGA IP (not ALTPLL — deprecated for Arria 10).
  50MHz refclk → 200MHz outclk_0. Actual frequency confirmed achievable by IP.
- **Arria 10 deprecated in Standard Edition:** warning is benign, compile proceeds.

---

## Hardware-Gated Items (waiting for Waveshare + JST cable)

- [ ] Arria 10 first bitstream (Quartus, uart_bridge.v)
- [ ] shift_in_en silicon validation (cannot test on iCEBreaker 16-bit bus)
- [ ] Scale test — actual cell count on GX660
- [ ] Paper Section 4 update with Arria 10 results
- [ ] Packed adder tile (make_int32_add_packed) — needs shift bits confirmed
- [ ] MUL rewrite using packed adder — ~650 cells vs current
- [ ] Fabric fire visualiser — cell-by-cell animation (needs scale)
- [ ] SYNC_WAIT hardware test in tests/fpga/
- [ ] FlowTrix hardware run — MLUPS/watt measurement + predicted-vs-measured
      ticks (see FlowTrix Demo section; VM build not gated)

---

## Compiler Optimisations (blocked on Arria 10)

These depend on shift_in_en / shift_out_en being confirmed on Arria 10.
Do not build workarounds — wait for hardware.

- [ ] Packed adder tile — 19 cells vs 482, needs shift bits
- [ ] MUL rewrite using packed adder — ~650 cells vs 2915
- [ ] Wallace tree MUL — ~500 cells, depth ~20
- [ ] x > CONST / x < CONST general case improvement
- [ ] MIF_ADD via packed shift adder — apply packed shift-chain adder to
      stage 4 (24-bit mantissa add) + shift-chain CLZ to stage 5 (normalise).
      Est. 814c -> ~450-550c (30-40% reduction). NOT bigger because the
      dominant cost (stage 3 alignment barrels, ~480c) is already
      shift-optimised. Trade: depth ~79 -> ~90-95 (acceptable for stencils,
      amortised across region). Reason from structure only -- must measure on
      real build. Pairs with shift_in_en validation (same shift ops the
      iCEBreaker cannot fully exercise).

---

## FlowTrix Demo (LBM -- flagship physics demo, agreed 2026-06-12)

Lattice Boltzmann is the best-matched algorithm yet: collision is purely
local arithmetic, streaming is one-hop nearest-neighbour -- on UniCell the
streaming step is not computed at all, it IS the topology. LBM is notoriously
memory-bandwidth-bound on CPU/GPU (the standard metric MLUPS is almost always
quoted memory-bound); distributions resident in cell registers moving one hop
delete that bottleneck. Reference point: NASA/Boeing 777 nose gear in
PowerFLOW -- 6.5B cells, 5,000 cores, 1M+ processor-hours. Not competing on
scale; competing on per-site architecture (each Pleiades core time-slices
~1.3M sites through a memory hierarchy; UniCell sites are resident).

THE DEMO -- small, repeatable, testable against known fact:
  - FlowTrix FormatDefinition (cell_format.py pattern): alphabet = 9 D2Q9
    distribution functions; fixed constants = lattice weights (4/9, 1/9,
    1/36) + velocity vectors in the cell decode table (PhysTrix CODATA
    pattern); operations = collide (BGK), moments (density = OR-reduction
    sum, velocity = weighted sum), bounce-back.
  - Flow past a cylinder at Re ~100-200. Vortex shedding frequency validated
    against the published Strouhal number (experimentally established to
    tight tolerance for a century). Same epistemic structure as NASA
    validating against 777 flight-test acoustics, in miniature. One-sentence
    claim, checkable by anyone: "correct Strouhal number from pure fabric
    topology".
  - BOUNCE-BACK OBSTACLE AS FABRIC CONFIG: the cylinder is cells wired to
    reflect -- geometry IS the wiring, not data checked by a program.
    Purest "topology is computation" demonstration yet. Reshaping the
    obstacle = reconfiguration, not recompile.
  - TEMPORAL BLOCKING to exceed physical cell count: LBM moves one lattice
    hop per timestep, so a block loaded with an N-deep halo can legally run
    N timesteps before exterior state could affect the interior. Run, save
    valid interior, load next block (pipeline-reconfig mechanism, block
    state streamed from DDR, .isi format). Trades halo recompute (cheap
    cells) for bandwidth (the actual bottleneck) -- the embedded deployment
    model proving itself on real physics.
  - mathtrix_animate.py renders the vortex street (MP4/GIF).

METRICS (honesty requirements):
  - Predicted ticks/lattice-update from the compiler (deterministic from
    pipeline depth, same as MIF_DIV 536 / SQRT 584) vs measured on silicon.
    Exact agreement is itself a validation -- fabric timing is knowable in a
    way cache-dependent CPU timing is not.
  - MLUPS/watt and MLUPS/dollar vs the same lattice on a decent CPU/GPU.
    The extrapolatable numbers.
  - State the temporal-blocking tax PLAINLY: ratio of useful interior
    updates to total updates incl. halo recompute, + DDR reload cost per
    block swap. This is what makes the MLUPS claim trustworthy. Also feeds
    the scaling argument: more cells -> fewer swaps -> tax shrinks toward
    zero (the curve the paper draws toward the 8-card rig).

SEQUENCING: FormatDefinition + collide tile + Strouhal validation buildable
in the VM NOW. Hardware MLUPS measurement = one of the first real workloads
on the Arria 10 once the USB Blaster arrives. Grid-refinement variant
(coarse full-domain pass -> temporally-blocked fine pass over the vortex
street, the PowerFLOW VR-regions workflow in miniature) is a stretch goal.
Bridge tile follow-on: tau <-> viscosity <-> Reynolds number is a
FlowTrix-PhysTrix bridge with semantic_confidence = 1.0 (exact physical
identity, not analogy).

---

## Hybrid Hard-IP Architecture (8-card rig -- future design note)

The Arria 10 GX660/1150 contain hardened DSP/ALU blocks (variable-precision
DSP, native fixed/float multiply-accumulate) alongside the soft fabric.
Current model uses ONLY the soft fabric -- every operation built from NOR
cells. Correct for proving the architecture and grounding truth: all models
and tile functionality validated on pure fabric first.

For LARGE FAST DEPLOYMENT (rack of cards), a hybrid is worth exploring:
offload heavy regular arithmetic (MUL/MADD/DIV -- the cell-expensive tiles)
to hardened DSP blocks, freeing soft-fabric cells for the topology/routing/
control logic that is the architecture's actual contribution. DSP does the
multiply; fabric does what only the fabric can do.

Open questions (do NOT resolve until single-card Arria 10 is stable):
- DSP result re-entry: boundary tile like MIF_PACK/UNPACK -- a HARD_MUL
  boundary hands off to DSP and receives result back into a cell.
- Purity: does this break "topology is computation"? No -- same pattern as
  preloaded-A constants or MIF boundary conversion. Fabric still owns
  structure; DSP is just a very fast arithmetic cell.
- Format typing across the boundary: a DSP MAC consuming MIF pairs needs the
  same contract discipline as any other tile.
- Per-card resource split: how many cells vs DSP blocks, and does the
  compiler choose soft-vs-hard per tile from a target-profile budget flag.

Principle to preserve: pure-fabric path stays the reference (ground truth).
Hybrid is an OPTIMISATION layer for deployment scale, never the foundation.
A tile should be expressible both ways, compiler selecting by target profile
(proving = soft, deployment = hybrid).

CRITICAL SCOPE: hybrid is FPGA-ONLY. FPGAs ship with hardened DSP blocks
already on the die -- declining to use them leaves paid-for silicon idle, so
the hybrid reclaims what is already there. On custom UniCell ASIC the whole
consideration disappears: the silicon IS the fabric, there are no hard blocks
to defer to, and the normal soft models run natively at full density. The
hybrid is a platform accommodation for living on someone else's FPGA silicon,
discarded entirely once on purpose-built silicon. It never touches the
reference architecture. FPGA = hybrid (use the idle DSP). ASIC = pure fabric
(the chip is the architecture).

### Hybrid implementation design (FPGA deployment profile)

ICM PROFILES -- three states, one save mechanism (refined this session):

  1. PORTABLE / SOFT-ONLY (compiler output, distribution + testing).
     Soft models for everything + a flag: "max N DSP-eligible ops concurrent".
     Runs anywhere (VM, iCEBreaker, any card). Tag: profile=soft, portable=true.
     This is the correctness-proof and sharing artifact. No card dependency.

  2. CARD-TAILORED / HYBRID RUNTIME (loader output, optimised deployment).
     Loader takes portable .icm + card profile -> substitutes DSP/BRAM markers,
     corrects depths to THIS card's hard-block latencies, re-walks the depth
     accounting. NON-PORTABLE BY CONSTRUCTION -- tied to one card type. MUST be
     stamped: profile=hybrid, card=<model> (e.g. arria10-gx660). Refuse-to-load
     guard: a hybrid image for card A must NOT load on card B without going back
     through the loader's re-tailoring. Loading wrong-card depths = silent
     timing corruption (worst-kind bug). Enforce, do not merely document.

  3. SAVE-BACK -- the file must be self-describing. A bare "DSP at depth X" is
     INSUFFICIENT: it does not say what the DSP is computing. So every
     offloadable op in a saved hybrid .icm carries BOTH:
       - soft model  (canonical: what the op logically IS -- mul/add/MAC...)
       - hard binding (this card: maps to DSP block, depth X)
       - marker linking them ("this DSP marker replaces this soft model")
     Soft model = ground truth/substrate; hard binding = card-specific overlay.

ONE SAVE MECHANISM, ONE DECISION (resolves the "two modes?" question):
  Because the hybrid file ALWAYS carries the soft model under the hard binding,
  there is only one save format. Portability = whether you STRIP the overlay:
    Save portable -> soft models only, drop hard bindings, tag soft.
    Save hybrid   -> soft + hard bindings + depth corrections, stamp card.
  The "intelligence" needed is just the rule: soft model is canonical and
  always present; hard binding is an optional card-stamped overlay. Strip it
  for portability, keep it for the optimised runtime.

LOADER'S REAL JOB (not find-and-replace). Substituting a hard block changes
the timing of everything DOWNSTREAM, not just that op. The loader re-walks the
depth accounting through the program table with substituted latencies. Tractable
because the table is compile-time-resolved and step-sequential -- the loader
re-times a KNOWN dependency graph, it does not schedule from scratch. Compiler
did the structure; loader re-times for the card.

CARD PROFILE FILE (the separate device manifest the loader reads):
  Per hard-block type: { type, count, op_class, depth_ticks }. Plus card id
  for the stamp. This is the "correct the depths by availability of the types
  on the specific card" file. Static (emitted with the gateware build) per the
  earlier resource-manifest decision.

THREE-LAYER SAVE MODEL (refined -- master / targeted base / checkpoint):
  - MASTER: portable soft-only .icm, canonical. Never lost. Runs anywhere.
  - TARGETED BASE: produced by RECOMPILING the master with a target card flag
    (cross-compile, not "decompile") -> soft models + hard bindings together,
    card-stamped. The card-specific base.
  - CHECKPOINT: a timed save during a running program. Uses the targeted base
    and writes only the CHANGED STATE (cell states) on top. Stores progress,
    not the whole program.
  Fallback chain: checkpoint -> targeted base -> master. Lose a checkpoint,
  restart from base. Lose the base, recompile from master. Master never lost
  (portable + canonical).

WHAT A CHECKPOINT SAVES, AND WHY THE FREEZE MAKES IT SIMPLE:
  Save-state happens ONLY AFTER A FREEZE. Freeze halts the working logic --
  nothing clocks new data through, pipelines empty, the whole system quiesces.
  Therefore every DSP/hard block has DRAINED: nothing in flight, by
  construction. The freeze IS the clean boundary -- no need to reason about
  in-flight hard-block results or step boundaries; freeze removes that entire
  problem class.
  Save = CELL STATES ONLY. Cells hold persistent data (yours, readable,
  writable). DSP blocks hold NOTHING persistent between ops, and after a freeze
  are empty + idle -- there is nothing to save. So cell states alone capture
  the COMPLETE persistent state of the frozen system. DSP blocks resume their
  fungible work on unfreeze when data flows again.
  Rule: freeze -> system quiesces -> hard blocks settle -> save cell states.
  "Cell states yes, DSP states no" -- not a limitation, a consequence of DSP
  carrying no persistent state and the freeze guaranteeing none in flight.

NOTE on file vs fabric (clears a worry): keeping the soft model in the saved
file costs DISK BYTES, not FABRIC CELLS. When a hard block is bound the loader
does NOT instantiate the soft model's cells -- the fabric gets the DSP bridge,
not the 3066 cells of MIF_MUL. The cell saving is fully realised on silicon.
The soft model in the file is a few KB of description retained for portability
+ self-description, costing zero fabric. "In the file" and "in the fabric" are
different spaces -- the whole hybrid design depends on that separation.


DUAL-ENCODED ICM. The .icm carries BOTH representations of each offloadable
operation: the soft maths model (NOR-cell tiles) AND the DSP-offload version.
One artifact runs anywhere. Pure system -> loader uses soft models. Hybrid
FPGA -> loader uses DSP path. Hash still verifies because both are declared
in the file -- nothing invented at load time. The dual encoding is also the
overflow safety valve (see below), not just cross-platform portability.

DSP RESOURCE TABLE (lives in Shore). DSP blocks are finite, hardened, at
fixed die locations -- cannot be discovered or relocated at runtime.
Populated once per card at bring-up from the card device profile. Each entry:
  { dsp_address, operation_class, latency_ticks, in_use_by_pond }
Shore owns it because Shore is already the OS-level pond allocator.

ALLOCATION FLOW (placer):
  1. Loader reads .icm, finds peak concurrent DSP demand (see liveness below).
  2. Placer requests N free blocks from Shore's DSP table.
  3. Shore returns N specific addresses, marks them in-use by this pond.
  4. Placer wires those N DSP addresses into the pond, replacing N soft
     MIF_MUL/MADD/DIV tiles with DSP bridge cells.
  5. Next pond to load cannot grab those blocks -- gets next free. Exclusive
     per-pond allocation, same discipline as cell address ranges. Parallelism
     preserved, no contention.

PLACEMENT -- ANCHOR-FIRST SEEDED GRAPH EMBEDDING (agreed 2026-06-12).
Step 4 above must be locality-aware, not first-free. DSP blocks sit in fixed
columns; a block on the far side of the die costs hops, and hops are ticks
(two-arrival model: distance IS latency). Approach -- invert the placement:
  - Pin the DSP-consuming tiles FIRST at known DSP column coordinates
    (most-constrained-first: soft cells are fungible, DSP locations are not.
    Same principle as macro-first ASIC floorplanning).
  - Grow the remaining tiles outward BFS along dataflow edges, each tile at
    the nearest free cell to its already-placed neighbours. Cost function =
    hop count, which directly minimises pipeline latency (not a proxy).
  - Tiles on the dataflow path BETWEEN two DSP anchors are placed along the
    geometric path between them, not merely near one.
  - When two growing regions collide: tie-break on total-hops-added.
LOCALITY TABLE: physical coordinates of DSP blocks + cell regions extracted
from the Quartus post-fit report, baked static, ships with the bitstream as
an .isi sidecar (extends the resource-manifest pattern: declared not
discovered). The table is the SEED COORDINATES for growth.
TIER SPLIT: coordinate table = Tier 1 fact. Seed-and-grow mechanism = Tier 2
(Shore/loader). Anchor-tight vs spread STRATEGY = Tier 3 Companion policy --
multi-tenant hotspotting around DSP columns is a policy concern, do not bake
strategy into the growth algorithm. Keep it parameterisable.
NUMA analogy holds throughout: DSP columns = NUMA nodes; affinity allocation,
distance metric, record-the-cost fallback when local blocks exhaust.
Fragmentation: locality score per allocation gives the Companion the signal
for when compaction is worth a reconfiguration pass.

PEAK CONCURRENCY -- already solved by the program table. The table-driven
pipeline model is inherently sequential through its steps (streams configs
from DDR, reconfigures fabric step by step). Each table step already declares
how many of each model are active at that step -- that IS what the step is.
So peak concurrent DSP demand is just max-across-steps of the model count
column the table ALREADY carries. No liveness inference needed; read it off
the table. DSP allocation grabs the max-across-steps count once, holds those
blocks for the program lifetime, table reuses them step to step exactly as it
reuses cells.

  Why this works: the programs that use DSP offload at scale ARE the linear,
  table-driven ones (config-streaming pipelines). The pathological
  free-dataflow case where liveness would be hard to infer is NOT a case
  you'd deploy via the hybrid -- the architecture's own structure routes
  around the hard problem. Linearity is the enabler, not a limitation.

  FURTHER SIMPLIFICATION -- no summing, just the max. A DSP slice is a GENERAL
  arithmetic unit (add, sub, mul, MAC -- all of it). So a block allocated to a
  pond serves whatever maths the current step needs; blocks are fungible
  across operation types. The allocator does NOT sum per-type counts. It needs
  exactly one number: max(step.model_count for step in table) -- the tallest
  single step. Grab that many fungible blocks, done. N blocks cover N
  simultaneous maths ops whether adds, muls, or a mix.

  Nested-loop caveat (already handled): if several loop bodies are live at the
  same step, each with its own maths models, that step's count reflects the
  total because the compiler expands loops at table-build time. The concurrent
  step simply shows the higher count and the max-scan catches it for free.
  Only dynamic runtime loop instantiation would break this -- which the table
  model does not do. The table is fully resolved before load; everything
  concurrent is enumerated at compile time. "Compiler picks it up at the
  start" is a structural guarantee, not a hope.

OVERFLOW (table exhausted). 8 cards, finite blocks, many ponds -> eventually
a pond asks for N and Shore has fewer free. Design choice, pick explicitly:
  - FALLBACK (preferred): pond uses available DSP + soft tiles for overflow.
    Runs slower but runs. ONLY possible because the .icm carries both
    encodings -- the soft model is the always-present backstop.
  - QUEUE: pond waits in pipeline_queue until blocks free. Use when DSP
    result is required (e.g. latency-critical) and soft fallback too slow.

DSP BLOCK IS STATEFUL. DSP slices have internal pipeline registers: feed,
result emerges N clocks later. Bridge cell is NOT a transparent pass-through
-- it has known latency the placer must add to the pond depth budget. The
two-arrival model handles the wait naturally (cell holds until result
arrives), but depth accounting must know N. Hence latency_ticks in the table.

FORMAT TYPING ACROSS BOUNDARY. A DSP MAC consuming MIF pairs is a typed
boundary like any other. DSP expects a specific operand layout; MIF is a
specific layout. Bridge cell presents MIF to the DSP in the form it wants,
wraps the result back into a MIF pair. Small format adapter -- declared, not
assumed. Same contract discipline as MIF_PACK/UNPACK and every bridge tile.

WHAT THE HYBRID LAYER ACTUALLY NEEDS (summary):
  1. Target profile flag (pure | hybrid) on the loader -- trivial, one bit.
  2. Max-scan allocator -- max(step.model_count), grab fungible blocks --
     nearly free, prototypable in software against a fake table now.
  3. Shore DSP resource table -- mirrors existing cell-range allocation,
     small extension.
  4. DEVICE-SPECIFIC GATEWARE -- the real new work. Verilog must instantiate
     hardened DSP primitives, which are vendor/device-specific (Arria 10 DSP
     != Kintex-7 DSP48 != iCE40). Current gateware is fabric-generic; hybrid
     needs a per-device layer. GATED on a working Arria 10 -- cannot write or
     test DSP instantiation against a card you cannot program.
  5. RESOURCE MANIFEST mechanism -- get the DSP inventory into Shore's table.
     STATIC (preferred, fits the architecture): synth emits a manifest with
     the build -- "N blocks at these addresses, this latency, these ops" --
     ships alongside the bitstream, Shore loads at bring-up. Declared not
     discovered, same philosophy as dual-encoded .icm and pre-resolved table.
     RUNTIME alternative: gateware register block the host reads at bring-up;
     more flexible for variant cards, more gateware + handshake complexity.

SCALE REALITY CHECK: GX660 has ~1,600+ DSP blocks. A single pond needing 1000
simultaneous maths models is implausible -- cell budget exhausts long before
DSP budget. Realistic peak is dozens to low hundreds per pond. Resource table
is not a single-card contention bottleneck; cross-pond contention covered by
the soft-fallback safety valve.

DEPENDENCY: everything except the allocator logic waits on Arria 10 being up,
because device-specific gateware is the foundation the rest sits on. Allocator
could be prototyped now in software against a fake resource table if a chip-at
task is wanted, but it is low value until real gateware declares real blocks.

### Other allocatable hard resources (same pool-allocation pattern as DSP)

The filter: a resource fits the DSP allocation pattern IF it is a FUNGIBLE
POOL of fixed-location hardened blocks doing a self-contained op with a clean
boundary (in -> out, no ongoing state the fabric manages). Test question:
"could two ponds each want their own private copy of this at once?" Yes =
allocatable pool. No = shared infrastructure (manifest-declared, configured
once, NOT pool-allocated).

ALLOCATABLE POOLS (extend the Shore resource table to these):
- BRAM / M20K blocks -- THE strong next one. Arria 10 has thousands. Move
  large tables OFF fabric cells INTO dedicated memory: MIF reciprocal LUT,
  genetic code table, periodic table, format symbol maps, preloaded weight
  sets. Attacks the cell budget the same way DSP does but for TABLES instead
  of arithmetic -- and this architecture is unusually table-heavy, so the win
  is large. Natural fit: address-as-identity and preloaded-table thinking is
  already the model; BRAM is just a bigger faster table that costs no cells.
  Allocate exactly like DSP: program declares table size, Shore allocates a
  block, bridge cell reads/writes it.
- Hardened crypto blocks (AES/SHA) IF the Arria 10 variant has them. Same
  shape: finite, fixed, self-contained, clean boundary. Allocate like DSP
  (need a hash -> grab a block -> data in, digest out). Dovetails with the
  UniCell Security Module concept (fabric-as-root-of-trust). Check whether
  the target variant carries them.

SHARED INFRASTRUCTURE (manifest-declared, NOT pool-allocated -- allocating
these per-pond would cause contention, category error):
- PLLs / clock regions -- infrastructure, configured once at bring-up.
- PCIe / SerDes transceivers -- the host boundary, shared system link.
- DDR memory controller -- single shared gateway (all ponds share it through
  Shore); it is a bus, not a fungible block.

### I/O reservation -- keep cells fed, keep the bus clear (design sketch)

Distinct from the pool-allocation above: this is about SCHEDULING data
movement, not allocating compute blocks. The aim is to stop the fabric
stalling on data and to stop the shared bus (DDR/PCIe) congesting.

Idea: an I/O reservation layer in Shore that, reading the program table's
per-step data needs, pre-stages raw input into BRAM/near-fabric buffers
AHEAD of the step that consumes it, and drains results OUT of result buffers
behind the step that produced them. The cells always find their next input
already staged (fed), and results leave promptly so buffers do not back up
(bus clearer). Because the program table is compile-time-resolved and
step-sequential, the data schedule is KNOWN IN ADVANCE -- same property that
made DSP peak-concurrency a simple max-scan. So I/O reservation is a
prefetch/drain schedule computed from the table, not a runtime guess.

Open questions (do NOT resolve until single-card Arria 10 stable):
- Buffer sizing: how much BRAM reserved as I/O staging vs as table storage --
  a split of the same BRAM pool, decided per program from the table.
- Double-buffering: stage step N+1 input while step N computes (classic
  ping-pong) -- the table already says what N+1 needs.
- Back-pressure: if the DDR/PCIe bus is busy, the schedule must degrade
  gracefully (compute waits on data) rather than overflow a buffer. Two-
  arrival model helps -- a cell simply holds until its staged input arrives.
- Whether this is one mechanism with DSP/BRAM allocation or a separate Shore
  pass that runs after block allocation. Likely separate: allocate blocks
  first, then schedule the data movement among them.

Principle: the table already knows the whole data itinerary. I/O reservation
just acts on it early -- prefetch ahead, drain behind -- so the fabric is
never waiting and the bus is never choked. Same "declared not discovered,
read it off the table" discipline as everything else.

DEFER ALL OF THIS until single-card Arria 10 stable + pure-fabric validated.


---

## Multi-Cage Scaling (far future -- two-regime design note)

Beyond the 8-card single-cage rig: multiple cages networked together.
The key realisation -- this is NOT just a bigger bus. Crossing a cage boundary
crosses from a BUS to a NETWORK, and that changes the timing physics. Two
distinct regimes, joined at a bridge:

INSIDE A CAGE = a fabric.
  Card-to-card over PCIe: tens-hundreds of ns, predictable, fixed-latency.
  Compile-time-resolved timing holds. Fine-grained tiles, tight pipelines,
  depth accounting valid. This is everything designed so far.

ACROSS CAGES = a network of fabrics.
  Cage-to-cage over network: microseconds, VARIABLE (jitter). The two-arrival
  model tolerates latency (cell holds until input arrives) BUT depth
  accounting assumes KNOWN fixed latencies -- network jitter breaks the
  compile-time timing guarantee. Therefore inter-cage bridges must sit at
  COARSE, latency-tolerant boundaries (between whole sub-computations that
  tolerate variable hand-off), NEVER woven into a fine-timed stencil on a
  critical path.

SMARTNIC AS INTER-CAGE BRIDGE (sound -- the strong idea):
  SmartNICs are FPGAs sitting directly on the network fabric (AMD/Xilinx
  Alveo, Intel/Napatech, BlueField-FPGA). A bridge contract is already just a
  boundary tile (in -> transform -> out). Nothing requires that boundary to be
  in the same card as the regions it joins. A bridge tile synthesised onto a
  SmartNIC's fabric converts a typed result IN THE NETWORK PATH: typed result
  leaves cage A, bridge transform applied in flight, delivered typed+converted
  to cage B. No host-CPU round-trip. Architecturally consistent -- the bridge
  was always a boundary; this places it on the wire.

HIERARCHICAL SHORE (the timing/SPOF fix):
  One SBC managing one cage = fine. One SBC as master allocator for many cages
  = coordination chokepoint + single point of failure. Correct pattern:
  per-cage Shore manages its LOCAL pool; a thin top coordinator manages
  BETWEEN cages (delegates, does not micromanage remote blocks). First cage's
  SBC can host the top coordinator. Each cage self-manages.

Reframe that makes it scale: inside a cage = tight fixed-latency fabric;
across cages = network of fabrics joined by coarse, async, latency-tolerant
SmartNIC bridges, each cage self-managing under a thin coordinator. Treat the
network as a bigger bus and it bites on timing. Treat it as a second regime
and it scales.

DEFER -- far future, post-rack. Captured now so the timing caveat is not
forgotten when the rack exists.

---

## Evaluating an FPGA card -- where does it fit? (reusable framework)

When a candidate FPGA card catches the eye, place it by ROLE, not by specs
alone. Four roles in this architecture, each wanting different things:

1. PROVING / ITERATION card (currently iCEBreaker).
   Wants: cheap, fast synth, open toolchain (yosys/nextpnr ideal), small is
   fine. Used to validate single-cell behaviour and catch bugs at minimum
   scale. A new card fits here if it is cheap and iterates fast. Raw size
   does NOT matter -- 4 cells found three bugs that hid at 482.

2. SCALE / COMPUTE card (currently Arria 10 GX660/1150).
   Wants: large LUT/logic count (cell capacity), abundant DSP + BRAM (the
   hybrid pools), DDR (config streaming), PCIe (host link). This is where raw
   size and hard-block count matter. Judge by: how many cells, how many DSP,
   how much BRAM, DDR bandwidth.

3. NETWORK / BRIDGE card (the SmartNIC idea).
   Wants: FPGA fabric ON a network interface. Judge by: does it sit in the
   data path between hosts/cages, can it run a bridge tile in flight. Size
   secondary -- it carries bridges, not bulk compute.

4. EMBEDDED / DEPLOYMENT target (ECU, security module, edge).
   Wants: small, low power, can boot from flash (.isi), runs a fixed
   pipeline-reconfigured program from DDR. Judge by: power envelope, boot
   options, cost at volume. The pipeline-reconfiguration model (small cells,
   stream configs) is what makes tiny targets viable.

PLACEMENT TEST for any new card:
  - Cheap + fast + open tools         -> proving card
  - Big logic + DSP + BRAM + DDR      -> scale card
  - FPGA on a NIC / in the network    -> bridge card
  - Small + low power + flash boot    -> embedded target
  - None of these cleanly             -> probably not worth adopting yet

Caution before buying ANY card: confirm toolchain (Quartus? Vivado? open?),
confirm programming path (onboard USB-JTAG reliable? external needed?), and
confirm it is not a niche part with no community / docs. The Arria 10 FTDI
saga is the lesson -- a card is only as usable as its programming path.

---

## Format Bridge System (architectural — post-community)

BridgeContract base class: DONE (cell_format.py)
FormatRegistry.find_bridge(): DONE
FormatRegistry.discover_bridges(): DONE — declaration-grounded
FUNDAMENTAL_BRIDGES: DONE — 9 bridges, physics + biology + chemistry

Remaining:
- [x] Compiler auto-placement of bridge tiles — DONE (compile_pipeline_icm, 22 tests)
- [x] Design-time warning system (confidence threshold enforcement) — DONE (check_pipeline_bridges)
- [x] SI_CHECK dimensional analysis integration — DONE (dimension_map + 21 tests)
- [x] Bridge section in community guide — DONE

### DSP Bridge Tile — Design Questions Outstanding (2026-06-15)

DSP hard blocks expect standard binary integers or fixed-point — no concept of
MIF/expanded format. Every DSP-bound tile needs a format bridge at its boundary:

    MIF cell → [MIF→INT bridge] → DSP block → [INT→MIF bridge] → MIF cell

Questions to resolve before implementation (cross when crossed):

- [ ] **Conversion ownership:** does the loader insert bridge tiles automatically
      when placing a DSP-anchored tile, or does the tile author declare conversion
      explicitly? Loader-automatic is cleaner for the programmer; requires loader
      to know conversion semantics for every format → cell_format.py FormatDefinition
      already has this information, so loader-automatic is the right path.

- [ ] **Precision contract:** MIF has a specific numeric range — does the DSP path
      preserve it exactly or is there acceptable rounding? Define the contract
      before any tile uses a DSP bridge, not after.

- [ ] **Bridge tile placement:** does the bridge tile live in fabric cells adjacent
      to the DSP column, or in the DSP block's own input registers? Affects tick
      count and the locality table entry format.

- [ ] **Tier assignment:** DSP locality table = Tier 3 policy (OS Companion decides
      which tiles get DSP anchoring). Loader placement = Tier 2 mechanism. Bridge
      tile itself = Tier 1. Do not mix.

- [ ] **Expanded mathtrix models:** internal DSP sees normal numbers only — loader
      must handle MIF↔INT conversion transparently. Design the conversion path
      before touching any mathtrix tile code.

SCOPE: FPGA-only. DSP bridge tiles are never emitted for VM or pure-fabric targets.
The .icm format must carry both soft model and DSP binding so the file is
self-describing on any target (see hybrid design note above).

---

## Deferred (architectural, no near-term action)

- Sentinel/Ward/Shore rethink — 3-cell Sentinel, Python-loop Ward
- Bootloader (.isi round-trip, Verilog loader)
- Branch/decision tree (COMPARE/CHOICE/RESULT/TABLE nodes)
- VoxCell photonic substrate — concept only, not buildable yet
- LLVM frontend — deferred until current changes settle
- SymPy equation input for MathTrix
- DisplayPond fire visualiser — needs Arria 10 scale

---

## Pre-Release Tidying (do before open source release)

- [ ] Root directory tidy — move domain runners (sensortrix_runner.py,
      optitrix_runner.py, flowtrix_*.py, neurotrix_*.py, miditrix_lif.py,
      mathtrix.py, mathtrix_animate.py) into a runners/ or frontend/ folder.
      Core VM files (unicell.py, unicell_array.py, controller.py, gate_states.py,
      compiler*.py, fp_tiles.py, cell_format.py) stay at root — import paths
      depend on them.
- [ ] README rewrite — currently buries the manual link halfway down and reads
      like a dev log. Should be: one sentence what it is, thirty seconds to
      running, where to go next. Manual is the second link not the twelfth.
      Write it to the completed story (Arria 10 results in hand) not retrofitted.

---

## Open Source Release Checklist

Software side essentially ready. Hardware milestone remains.
- [x] MUX selector bug fixed
- [x] Comparison operators fixed (>=, <=, !=)
- [x] Multi-param compiler bug fixed
- [x] MUL preloaded_a bug fixed
- [x] 157/157 compiler tests
- [x] 236/236 tile tests
- [x] 31/31 silicon tests
- [x] Docs consistent and correct
- [x] README with getting-started path
- [x] MIT licence (software)
- [x] CERN-OHL-P v2 (hardware)
- [x] Verbatim official CERN-OHL-P text from ohwr.org (replaced 2026-06-14)
- [ ] Arria 10 working and stable          ← the remaining gate
- [ ] 1D Laplacian (or equivalent) on real Arria 10 hardware

---

## What Not To Do

- Don't add Python workarounds to run_int32_function
- Don't build packed adder before shift bits confirmed on Arria 10
- Don't start another audit document — this is the plan
- Don't mix old PRELOAD_NONE names with new PRELOAD_SEL_* in same file

---

## University Lab Deployment (post-Arria 10)

8 × Arria 10 cards in a secondhand mining rig.
~£1,000 total. Accessible for university labs.
Depends on: single card stable, PCIe pool architecture, pond addressing
across PCIe boundaries. Post-single-card milestone.

---

## Trix Ecosystem (community-driven, ongoing)

Format definitions: DONE — 9 formats, 6 domains + PoliticsTrix
Community space: DONE — scaffold, validate, hash, register, search
Bridge discovery: DONE — declaration-grounded, no guesses
Trix template: DONE — frontend/trix_template.html
MathTrix frontend: DONE — frontend/mathtrix_frontend.html
Region Connector: DONE — composer/region_connector.html

Next community actions:
- BioTrix models (DNA alignment, GC content, codon frequency)
- ChemTrix models (molecular weight, valence check)
- PhysTrix models (unit conversion, dimensional check)
- Compiler auto-placement of bridge tiles

---

## NEXT SESSION — Tile .icm examples + non-Trix community exchange (agreed 2026-06-13)

Two linked items. The first produces artifacts; the second builds the exchange
path for them. They interlock: a raw per-tile .icm IS a "model outside the
Trix system", so the example tiles become the first reference entries of the
new non-Trix contribution kind.

### 1. Per-tile .icm examples in examples/tiles/  (DONE 2026-06-13 via walker)
DELIVERED as examples/walker/walk_tiles.py (a walker, not a static dump — ship
the tool so users expand built-ins, subsets, or their OWN builders on demand
via --builder module:function). Emits the functional set by default, skips the
big I/O handlers + deprecated CLA. .icm matched to the composer raw-load path
(program_id + records, inputs/outputs {name:addr}, format_version 2,
preload_map carried). Bulk output git-ignored (4.1MB full set is bloat); a
152KB curated sample palette committed under examples/tiles/samples/. Tests:
tests/vm/test_walker.py 21/21. The committed samples seed item 2's raw kind.

ORIGINAL RATIONALE (kept for context): the MathTrix frontend -> compiler -> fp_tiles chain produces .icm
from models. Embedding every tile in the composer HTML would bloat it badly
(esp. the FP/MIF tiles). But standalone .icm files sidestep that entirely:
  - The composer ALREADY loads raw .icm/.json via its file input
    (composer/unicell_composer.html: loadFile -> FileReader.readAsText).
    No HTML change needed.
  - The tile-records -> .icm-JSON serialisation path ALREADY exists
    (bootloader/generate_icms.py is the template: records[] + header).
So this is almost free: a small generator iterating TileLibrary._builders,
serialising each tile's records + in_a/in_b/out into the .icm JSON schema,
writing examples/tiles/<NAME>.icm. Users load any primitive directly into the
composer to inspect its format and wire it — a loadable palette, not HTML bulk.
APPROACH:
  - .icm header per tile: name, inputs (in_a/in_b first-bit addrs), outputs
    (out addrs), cell_count, records[]. Mirror generate_icms.py exactly.
  - mark vm_only where cell_count exceeds the small-FPGA budget (composer
    already understands vm_only).
DECISIONS TO MAKE:
  - which tiles to emit: all, or just compute (INT32/FP32/MIF) and skip the
    big I/O handlers (DISPLAY_HANDLER 18,600c etc.) that aren't useful as
    composer building blocks? Lean: emit compute tiles + counters/latches,
    skip the handler tiles (or put them in examples/tiles/handlers/).
  - these are inspection/building-block artifacts, not standalone runnable
    programs (a lone tile needs inputs fed) — note that in the folder README.

### 1b. Walker follow-ups (deferred 2026-06-13, both small)

(A) --module flag: walk a whole user FILE of builders, not just one. Today the
walker handles a single --builder module:function. Add --module mymod that
imports the file and emits an .icm for every make_* returning a Tile — mirrors
how it walks the built-in TileLibrary. Completes the "one library file in, a
set of models out" authoring route (parallel to fp_tiles.py, bypassing the
full compiler). A user's tile-library .py is then itself a shareable non-Trix
contribution (the "library" kind for item 2).

(B) record_hash — walker must compute it AT THE BASE. Currently OMITTED (I
dodged mismatch warnings). Composer load is lenient (loads "no hash"), BUT the
strict/runtime loader path cares (controller.py sha256, line ~421) and a model
meant to be loaded/run needs it. Composer side arguably SHOULD enforce too
(currently warns-but-loads). Must match the composer's canonicalisation EXACTLY
or it warns mismatch:
    composer canonR (unicell_composer.html ~1565):
      JSON.stringify(recs.map(r=>({gs:r.gs,in:r.in,init:r.init,out:r.out})))
    -> fields {gs,in,init,out} ONLY, in THAT order, NO inB.
    -> then SHA-256 hex of the UTF-8 string.
  Python replication (gotchas):
    import json, hashlib
    canon = json.dumps([{"gs":r["gs"],"in":r["in"],"init":r["init"],"out":r["out"]}
                        for r in records], separators=(",",":"))   # no whitespace!
    record_hash = hashlib.sha256(canon.encode()).hexdigest()
  Gotchas: separators=(",",":") to match JS no-space output; field subset+order
  exactly {gs,in,init,out}; init None->null matches. Set icm["record_hash"]=...
  Then verify a generated .icm loads in the composer with "hash verified ✓".

### 2. Expand community/ to exchange NON-Trix models
GAP: community_tools.py is hard-wired to the Trix FormatDefinition pattern —
REQUIRED_FILES = [README.md, format.py, MANIFEST.json], validation checks the
domain against a FormatDefinition class, MANIFEST is formats/models/bridges.
A raw .icm tile/model has NO format.py, NO domain, NO FormatDefinition, so it
cannot be registered today. That is the wall to remove.
PLAN:
  - Add a contribution "kind" field: "trix-domain" (current) vs a new kind
    e.g. "raw-icm" / "tile-library" / "model" for non-Trix artifacts.
  - REQUIRED_FILES varies by kind: trix-domain needs format.py; raw kinds
    need the .icm file(s) + MANIFEST + README, NO format.py.
  - cmd_validate branches on kind (skip the FormatDefinition/domain checks
    for raw kinds; instead validate the .icm schema + cell_count + i/o map).
  - REGISTRY.md groups by kind as well as domain.
  - The examples/tiles/*.icm from item 1 become the seed reference entries of
    the raw-icm kind — closing the loop between the two items.
RATIONALE: lets people share tiles, raw .icm models, and personal libraries
without forcing everything through the FormatDefinition system. Trix stays the
high-level typed path; raw exchange serves everyone below/outside it.

---

## Long horizon: Onion filesystem integration

**Concept:** Integrate the Onion compression/encryption engine into the
native filesystem Pond as an optional block-level security and compression layer.

**Why it fits:**
- FormatDefinition metadata at write time eliminates the Strategist entropy scan —
  the format registry already knows the data type (int16 sensor, float32 physics,
  text) so compression parameters are a lookup, not a heuristic.
- AES-256-GCM is already the last layer in Onion's pipeline and is never pruned
  by the Gain Monitor — "encrypt only, no compression" = Raw + AES, already works.
- HMAC-SHA256 signature on every block means tampering is detectable before decrypt.
- Fits three-tier model cleanly:
    Tier 3 (Companion): security policy — "this Pond encrypts all writes"
    Tier 2 (Ward/Shore): key management, password prompt at Pond boundary
    Tier 1 (fabric): AES-GCM execution

**On-card save path:**
  File written → FormatDefinition tag assigned → Pond security policy checked →
  if secure: Onion Raw+AES wrap (or Delta+LZ77+AES for numerical data) →
  block written to flat pool. Password prompt once at Pond mount, not per-file.
  Key lives in preloaded cell registers for session duration, never hits storage.

**Extra flag needed (trivial, add when filesystem Pond firms up):**
  "compression_disabled" hint — skips Strategist sampling on secure-only writes.
  One bit in filesystem Pond security policy, passed as encrypt_only=True parameter.

**Fast-path encryption note:**
  Onion's PBKDF2 at 600K iterations is archive security, not filesystem throughput.
  For filesystem use: derive a session key once at mount (PBKDF2 once), then use
  ChaCha20-Poly1305 or AES-GCM with that session key per block. Onion already
  separates key derivation (aes256.py _derive_key) from encryption — easy to split.

**Gate:** After Arria 10 is working and native filesystem Pond design firms up.

## Mainstream Trix Demos (post-Arria 10 bring-up, post-FlowTrix)

These all share the same infrastructure: PCIe streaming → DDR → fabric → DDR →
PCIe → GPU/display. None add new infrastructure requirements beyond what
FlowTrix already needs. GPU output path requires card-alive (PCIe live).

All are small focused demos first — a single pipeline proving the concept is
enough. Full implementations follow once the demo lands.

### ImgTrix — Image / Video Processing
Convolution kernels: blur, sharpen, edge detection (Sobel/Canny).
Every pixel neighbourhood is independent — embarrassingly parallel, maps
directly to cell pipeline topology.
- Input: still frame or video stream via PCIe from host
- Compute: convolution kernel compiled to cell topology
- Output: processed frame back via PCIe → GPU → display
- Demo target: live edge detection on a webcam feed at Arria 10 scale
- Note: this card was designed for video processing — Arria 10 GX660 in
  Mustang-F100 was validated for OpenVINO video inference workloads.
  PCIe Gen3 x8 is sized for streaming video frames.
- Dependency: DDR streaming path + PCIe host transfer working

### SigTrix — Signal Processing
FFT, spectrum analysis, noise filtering. Every frequency bin independent.
- Demo target: real-time audio spectrum analysis
- Input: audio stream from host
- Output: frequency domain data → GPU visualisation
- Natural fit: parallel cell pipelines per frequency bin
- Dependency: same PCIe/DDR path as ImgTrix

### MonTrix (or extend FinTrix) — Monte Carlo Simulation
Option pricing, risk modelling. Thousands of independent price paths,
each a pipeline. FinTrix format definition already exists.
- Demo target: Black-Scholes option pricing across a strike price grid
- Embarrassingly parallel — ideal UniCell workload
- Dependency: FinTrix format + PCIe path

### GenTrix — Genomic Sequence Matching
BioTrix already covers DNA/RNA/Amino20. Smith-Waterman alignment is
parallel across candidate sequences.
- Demo target: short-read alignment against a reference sequence
- Dependency: BioTrix models + PCIe path

### Sequencing (all share infrastructure — build in this order):
1. Arria 10 bring-up + bus characterisation        ← now
2. DDR streaming path                               ← next
3. PCIe host transfer working                       ← follows DDR
4. FlowTrix (LBM fluid sim)                        ← agreed flagship
5. ImgTrix (edge detection — most visual)           ← first mainstream demo
6. SigTrix (audio FFT — most accessible)            ← second
7. MonTrix (Monte Carlo — most commercially relevant) ← third
8. GenTrix (sequence alignment — most scientifically  ← fourth
            impactful, ties into eldest's research area)

GPU output note: all visual demos require the PCIe card to be alive and
the host GPU path to be working. The heartbeat LED on bring-up is the
first sign of life; the first frame out via PCIe is the second milestone
that unlocks the entire visual demo stack.

## Hierarchical Address Model (architectural note, 2026-06-15)

The fabric uses 16-bit logical addresses internally. This is not a limitation —
it's a deliberate boundary. Address expansion happens at the fabric edge via
bridge, exactly once per boundary crossing.

### Address hierarchy (inside → outside):

```
[Cell logical address — 16-bit]       65,536 addresses per fabric island
        ↓ zone bridge
[Block address — zone within die]     identifies which zone on the fabric
        ↓ die bridge  
[Die address — fabric island]         identifies which FPGA die (card)
        ↓ card bridge
[Card address — card within cage]     identifies which card in the rig
        ↓ cage bridge (PCIe / network)
[Cage address — rack / node]          identifies which cage/rack
```

Each level is opaque to the level below it. A cell fires a 16-bit logical
address — it has no knowledge of which zone, die, card, or cage it lives in.
The bridge at each boundary holds the translation table and expands as needed.

### Practical encoding (single card, current):
- 16-bit internal: cell logical address, assigned at boot via CMD_BOOT_COMMIT
- Zone is implicit in which zone's output bus the fire appears on
- Card/cage not yet relevant — single card only

### Bridge translation at fabric edge:
External systems (GPU framebuffer, NetTrix, PCIe DMA, network) see addresses
in their own space. The output bridge maps:
  16-bit logical cell address → external address (32/64-bit physical, IP:port, etc.)
The mapping table lives in the bridge (Tier 2), not the fabric (Tier 1).

### NetTrix implication:
Network addressing (IP, port, packet ID) is a wholly different space.
The NetTrix bridge translates fabric fires to network destinations.
The fabric never sees a network address — clean separation maintained.

### Address expansion is a format bridge:
Conceptually identical to a FormatDefinition bridge — the "format" being
translated is the address space itself. Same pattern, same tier placement.

---

## NEAR-TERM SILICON SEQUENCE (Alan, 2026-07-09)

Each step gates the next. All three fit on the card in hand, over JTAG.

### Step 1 — Reflash with the layers exposed [DONE 2026-07-10]
**Goal: confirm CARDINAL routing works in all four directions. ACHIEVED.**
All four directions (N/S/E/W) confirmed on silicon via `fpga/zone1_cardinals.tcl`
against the rebuilt single-zone bitstream (N/S/W sticky capture + widened ISSP
probe selector added to `top_arria10_zone1_v3.v` / `pcie/unicell_issp_bridge.v`).
6 runs, 5 clean 4/4, one isolated non-repeating single-direction miss each on
two separate occasions (East once, West once) — characterized as an
occasional JTAG/edge-detect glitch, not a per-direction RTL defect (see
points.md #18 for the full readout). The bundled #32 wired-OR test (same
build, no extra flash) also came back silicon-confirmed both cases (see
points.md #32) — free N-way OR reduction on shared output address, exact
corruption mode (last-firer's address, contaminated data) on differing
addresses.

The #32-relax-#17 same-address special case is now bundled and confirmed;
the negative test (same depth, different addresses -> confirm corruption) is
also done. **#17's placement rule can now formally read: "no two same-depth
cells in a cluster with DIFFERENT output addresses" — same-address collisions
are a free reduction, not a hazard.**

### Step 2 — Run the CLOCK WALK to find the PCIe refclk pin [PAUSED 2026-07-11 -- inconclusive]
Built and ran the diagnostic against all 8 candidates across all 4 legal I/O
standards (HCSL, LVDS, Differential LVPECL, CML) -- genuinely exhausted the
Quartus-side search space, zero locked every time, with the JTAG-side clock
confirmed alive throughout (not an artifact of a dead probe). Full readout:
points.md #30. Two live hypotheses, neither settled: this board may not route
refclk to any of these dedicated GXB pins at all, or the GXB analog rail may
not be powered. Two next steps queued for a future session: physical board
inspection for a clock buffer IC near the PCIe connector/GXB banks, or the
iEi Mustang Viewer utility (Linux-only, via the card's Micro-USB debug port)
reading GXB rail status + FPGA temperature directly.

NEW LEAD (later same session): Intel's official 10AX066 pin table (device-
level, not board-specific) reveals every RX channel pin ALSO doubles as a
per-channel refclk input -- real search space is 32 candidate pins, not the 8
dedicated CHT/CHB pins tested. See points.md #30 for the full breakdown.
Worth trying before the physical-inspection/iEi-Viewer options, next session.

CONTROL TEST (later still): a new second card of the identical board
revision, proven to enumerate PCIe cleanly moments before testing, failed the
SAME 8-pin sweep identically (zero locked, CLK confirmed alive). This rules
out "card 1 is just defective" -- two independent healthy-vs-unhealthy units
both fail the same way, pointing at the board design itself not routing
refclk to these 8 pins. The 32-pin expansion (above) is now the clear next
step, not one option among several.

DEVICE LIMIT HIT (later still): the 32-at-once build FAILED to fit --
this device has only 16 total IOPLL-capable hard-block locations, die-wide.
Split into two 12-pin builds instead (`clock_walk_top_a.v`/`_b.v` +
matching qsf/sdc/tcl, banks 1C+1D vs 1E+1F, dedicated CHT/CHB pins excluded
since already exhaustively tested). Both reuse the single `fpll_ch0` IOPLL
module. Neither built/run yet -- the next concrete action.

RESULT (later still): Build A rejected ALL 12 candidates identically --
"IO_FUNCTION of GPIO" not found. Cross-checked against Intel's own real PCIe
Hard IP example design: refclk is ALWAYS a separate dedicated pin, never an
RX/TX lane pin. **The 24 per-channel candidates were never real -- the 8
originally-tested dedicated CHT/CHB pins are the ONLY real candidates on this
device, and all 8 are already exhaustively dead** (see points.md #30). Step 2
is now conclusively closed on the plain-IOPLL diagnostic approach.

PCIe HARD IP DIRECT ATTEMPT explored and PARKED: building a real, correctly-
configured, hardware-synthesizable PCIe Hard IP against the Mustang's actual
device/pins is the natural next step, but is a substantially bigger
undertaking (first attempt used the wrong device -- Arria10 GX dev kit part,
not this card's; second attempt targeted the right device but generated in
simulation-only/PIPE-BFM mode, not hardware-synthesizable). Deserves its own
dedicated session -- not pursued further this session.

BREAKTHROUGH (2026-07-12, follow-up session): a THIRD attempt -- a proper
Qsys system (`pcie_test_1.qsys`) rather than a raw IP variation, correctly
targeting `10AX066H2F34E2SG` -- has genuine hardware serial pins
(`xcvr_rx_in0-7`/`xcvr_tx_out0-7`, matching Intel's official hardware signal
table word-for-word) alongside `ref_clk_clk`. This is NOT another simulation
stub. Queued for a dedicated build session: wire a custom top-level, refclk
to one of the 8 known candidates, serial lanes to the Mustang's actual PCIe
x8 pins (a new, separate unknown), proper reset generation, leave the large
`hip_pipe_*` debug bus unconnected for a first attempt. See points.md #30.

PIN DISCOVERY (2026-07-12, later same day): left refclk + all 16 lane pins
unconstrained and compiled clean -- Fitter auto-placed the lane unknown for
free (banks 1C+1D only, 1E/1F unused) AND confirmed `ref_clk_clk` on
`PIN_AB28`/`AB27` (the same pin already exhaustively tested dead). Wrong-pin
hypothesis eliminated -- the 8-pin sweep was testing the right candidate all
along. Next: build this exact Fitter-confirmed configuration for real and
check the genuine Hard IP's own LTSSM/link status, not a plain-IOPLL proxy.
See points.md #30 for full detail.

**STEP 2 CLOSED (2026-07-12, same day) — PCIe ENUMERATED.** Built and flashed
`pcie_hip_test_top.v` with the Fitter-confirmed pins locked in. One real fix
needed along the way: `pin_perst` (PCIe PERST#) must be a raw top-level
primary input with zero internal logic -- Fitter enforces this in hardware,
not a bug. **Windows enumerated a genuine PCIe device: `VEN_1172&DEV_0000&
CC_FF00`** (default Device ID/class code, exactly as UG-20039 said to expect
unmodified -- not an error). The link genuinely trained. This retroactively
resolves the entire refclk mystery: `PIN_AB28`/`AB27` was correct all along --
the plain-IOPLL proxy diagnostic was a systematic FALSE NEGATIVE (most likely
cause: PCIe refclk is commonly spread-spectrum clocked for EMI reduction, and
a generic fixed-frequency IOPLL has no SSC tolerance, while the real Hard
IP's CDR does). Full writeup: points.md #30. Next: real BAR read/write
testing via Intel's bundled driver + `Alt_Test.exe`, then DMA into Ponds.

**LINK TRAINING CONFIRMED, FULL WIDTH (later same day):** Intel's own
low-level PCI interop tool confirmed via direct config-space read: Gen2
(5.0 GT/s), full x8 lane width, stable, entire config space (incl. MSI)
readable cleanly. BAR0 read/write reports FAILED (`0xFFFFFFFF`) -- EXPECTED,
not a new problem: `pcie_test_1.qsys` has no memory-mapped target behind the
Hard IP at all yet (just clock source + bare HIP). NEXT, real: wire an actual
target behind BAR0 -- per this project's own "PCIe is just another bridge,
windowed BAR" architecture, the natural target is the UniCell fabric's own
command/data bus, not generic test RAM. That's the real remaining step to
actual host-driven DMA into Ponds. Full detail: points.md #30.

### Step 3 — DSP units as DYNAMICALLY PARTITIONED chains
**Alan's idea: chop a chain while it runs, giving multiple parallel math chains for
"free".** Confirmed possible by the Arria 10 handbook (683461) §3.4.7 / Table 25:
> "The following signals can **dynamically** control the function of the
> accumulator: NEGATE, LOADCONST, ACCUMULATE."

| Function | NEGATE | LOADCONST | ACCUMULATE |
|---|---|---|---|
| **Zeroing** (disables the accumulator) | 0 | 0 | 0 |
| Preload | 0 | 1 | 0 |
| Accumulation (adds current to previous) | 0 | X | 1 |
| Decimation + Chainout Adder (adds to **previous DSP block's output**) | 1 | 0 | 0 |

Assert Zeroing at a block -> it stops accumulating the chain -> **the chain is cut
at runtime, per cycle.** Every block exposes its own `result[63:0]` alongside
`chainout[63:0]`, so each segment is tapped where it is cut. One physical 27-block
chain (the spine-clock cascade limit, #26) becomes N parallel chains, repartitionable
per tick, using DSPs that are already there and already cascaded.

**Caveats before treating this as free:**
1. **Unverified**: whether "Zeroing" also severs `chainin`, or only the accumulate
   path. The whole idea rests on this. Confirm from the DSP IP docs or by test.
2. **Density cost**: the accumulator and chainout adder are **not supported in two
   independent 18x19 modes** (handbook p53). Chopping needs one multiplier per
   block -> **halves multiplier density.**
3. **Latency is position-dependent**: a segment starting at block *k* has different
   latency than one starting at block 0. Exactly as #25/#26 predicted -- the MAN
   file's DSP entry is a TABLE (mode + registers + chain position -> N), not a
   constant. The binder reads it and inserts fabric delay compensation for residual
   skew.
4. **Interconnect cost**: tapping many `result` ports wires the fabric to several
   DSP outputs, not one chain end. #24 measured 36% peak routing where the fabric
   bus converges -- routing binds before logic. **Free in DSPs, paid in wires.**

## Thermal Monitoring — Sentry Cell Cluster (queued, AFTER Steps 1-3 above, 2026-07-11)

**FPGA sensor to be monitored: on-die temperature.** Path already tested (per
Alan): a sentry cell cluster (the `GS_LATCH_IN` sentry-cell pattern from
`docs/ICM_FORMAT.md` -- single-arrival mode, stays armed, fires on every new
reading rather than needing a fresh two-arrival trigger each time) reads the
temperature sensor and reports the value up through the PTT (Pond Task Table --
`docs/manual.html`'s Ward/PTT layer). Simulated to confirm the reporting path
can trigger either a **freeze** or a **move** command in response to an
overheating cell (or, in this single-card context, the whole card) -- i.e. the
Ward layer reacting to a sensor-driven health signal, not just a compute
result.

This is one entry in what should become a small family of FPGA-internal
sensors surfaced the same way (temperature is the first; others TBD as they
come up) -- worth keeping as a named, explicit "sensors to be monitored" list
rather than a one-off. Queued explicitly AFTER the current near-term silicon
sequence (Steps 1-3 above) and the 2/4-zone scaling measurement build --
architectural/Ward-layer work, not blocking any of the silicon bring-up in
progress.

NEXT (when picked up): identify the actual on-die temperature sensor access
path on the Arria 10 (Intel FPGA IP has a Temperature Sensor / thermal diode
megafunction for Arria 10 -- confirm exact IP name and whether it needs
calibration), wire a sentry cell cluster to poll it and report via PTT, then
re-run the freeze/move simulation against real sensor readings instead of
simulated ones.

## Cell Mechanics Deep Dive — Full Opcode/Flag Audit (queued, AFTER PCIe, 2026-07-12)

**Motivation, stated directly by Alan:** it isn't the individual flags and
opcodes that hide the real gems in this architecture — it's the
*combinations* of them. `points.md #37` is the concrete proof: `loop_back`,
`latch_in`, and `CMD_MEM_CALL` are three mechanisms that have each existed in
the RTL since early in the cell's design, each individually unremarkable, but
composed together (and further composed with the already-proven wired-OR bus,
`#32`) they produce a genuine, previously-unnamed capability — a distributed,
externally-modifiable accumulator, built entirely from parts that already
existed. Nobody had noticed this until a casual conversation happened to
surface it. That's a real risk pattern, not a one-off: if one combination
like this was sitting unflagged, others almost certainly are too.

**Scope, so this doesn't stay vague:** `unicell64_v3.v` currently defines
**56 distinct opcodes** and a `cmd_latch` bit field with at least 12 named
flags beyond topology itself — `output_set`, `latch_A_dis`, `latch_B_dis`,
`start_flag`, `dtype`, `invert_out`, `latch_in`, `priority`, `trace`,
`breakpoint`, `one_shot`, `loop_back`. Three of those — **`priority`,
`trace`, and `breakpoint`** — did not come up anywhere in this entire
session, in any context, despite everything else that got exercised. First
concrete unknowns to start with.

**What the deep dive should actually do, once PCIe is solved:** not just
re-read the code — systematically walk every opcode and every flag bit, and
for each one (and each *pair or triple* of them that can coexist) ask the two
questions that produced real value today:
1. Does this compose with something else into an emergent CAPABILITY nobody's
   named yet — the way `loop_back`+`latch_in`+`MEM_CALL`+wired-OR did?
2. Does this compose with something else into a HAZARD nobody's caught yet —
   the way `#17`'s placement collision and `#37`'s cross-boundary staleness
   window did?

Anything that comes out of this gets the same treatment `#17` and `#37` both
received: a placement/usage rule for the compiler, a modeled behavior for the
VM (per Stage 4's fidelity obligation above), or at minimum a proper name and
an entry in `points.md` so it can't be silently rediscovered a third time by
accident.
