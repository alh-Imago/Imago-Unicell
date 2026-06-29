# ════════════════════════════════════════════════════════════════════════════
# NEXT-SESSION CATCH-UP  (read this block, then the canon sections it points to)
# Last session: 2026-06-27 — addressing model reconciled + per-cell config on silicon
# ════════════════════════════════════════════════════════════════════════════

## WHERE WE ARE (one breath)
The morning's blocker — RECONFIGURE broadcasts, so heterogeneous per-cell config was
impossible — is GONE, proven on the Arria 10. A cell is now individually addressable:
target on the full-width address lane, the cell's own addr_match gates it, auth-verified.
On top of that, the whole block→die→card→128-bit addressing model got reconciled into
canon. Clean stopping point: silicon green, canon coherent, git == remote (HEAD 0db4646).

## SILICON-PROVEN (on the die today)
- CMD_LOAD_AT (opcode 23): per-cell targeted reconfigure. zone_target.tcl PASS —
  LOAD_AT cell0=XOR → latch 0x0BC; LOAD_AT cell1=AND → cell0 STILL 0x0BC (exclusion).
- TARGET LATCH in top_arria10.v: SET_TARGET (opcode 24, cells ignore it) holds the
  address lane; LOAD_AT lands on it. The ICM transport primitive. zone_target proves it.
- Regressions green on the new build: gate+chain, command-emit. Reflash was clean.

## READ THESE CANON SECTIONS FIRST (resolved this session — do NOT re-derive)
docs/ARCHITECTURE.md:
  - "Addressing & Command Authority — INVARIANT" — one comparator gates both lanes;
    target on the address lane NEVER the command word (cmd_bus-target anti-pattern is
    named + permanently rejected); auth write-once boot-only; opcodes the only post-boot
    authority. READ THIS BEFORE touching addressing / auth / targeting.
  - "Relocatable models — root + offset" — models are position-independent; offsets in
    the artifact, loader/saver do the root arithmetic, cell stays absolute. Bridge is the
    relative↔absolute seam. Save/load/move (Ward) = one offset mechanism.
  - "Cell view — 32-bit space, 16-bit local" — the partition: low16=cell_id (intra-block,
    the cell's bus), high16=block_id (the BRIDGE's field). Pond fits-in-block or
    spans-blocks via the bridge. Shore-side climb 32→40→44→128 via bridge blocks.

## NEXT (in order)
1. ICM-file streaming: loop (SET_TARGET, LOAD_AT) pairs from a file. Build it
   OFFSET-NATIVE per the relocatable-models canon (records hold offsets from a root;
   loader forms root+offset → absolute; never bake in absolute-only). Block-local 16-bit
   offsets first (adder fits a block); reserve format room to widen. This is the
   compiler↔silicon bridge — the compiler already knows each cell's addr+config.
   >> DONE (2026-06-28, sim): fpga/icm_stream.py streams (SET_TARGET, LOAD_AT) pairs,
      offset-native, transport-pluggable. Triple-verified (oracle + RTL replay + byte-match
      to zone_target.tcl) on examples/icm/xor_and_or.icm. STREAMS topology+arm only on the
      flashed bitstream; arbitrary in/out addressing needs step 1b below.
   1b. Address-targeting reflash: route load_target into cpu_addr_w for opcodes 2/3 +
      cell addr_match-gates SET_INPUT/SET_OUTPUT (mirrors CMD_LOAD_AT). Then full
      (target, topology, in, out) records stream. Spec against the INVARIANT first.
2. Packed adder as the FIRST heterogeneous ICM on silicon (the 22-cell Kogge-Stone adder
   — the thing the whole 2026-06-27 thread was aimed at). Needs per-cell addresses too
   (SET_INPUT_ADDR/SET_OUTPUT_ADDR are already targeted) — a full record is
   (target, topology, in_addr, out_addr), so several pairs per cell, not one.
3. Loose end (small, do while in the cell): bring CMD_RECONFIGURE's auth-write under the
   physical_mode gate so clause 3 of the invariant holds everywhere (CMD_LOAD_AT already
   does it; RECONFIGURE still writes auth in run mode). Sim-testable immediately.

## FILED FOR LATER (thought through, not built — see canon)
- Host-as-allocator (hosted multi-model): used/free map per model, host assigns roots —
  a bookkeeping layer ABOVE the loader. Flat-offset ICM makes it drop in.
- Pond base+offset; PCIe = "another bridge" (windowed BAR, host-physical↔fabric in Shore,
  NOT a 128-bit address carrier). When we reach the PCIe/bus work.

## DRIFT NOTE (the session tax — avoid repeating)
The cmd_bus target side-door happened because a NEW mechanism was proposed instead of
reaching for the address comparator that already existed. Discipline: before adding any
command/auth/targeting mechanism, READ the invariant FIRST and STATE which existing
mechanism the new one duplicates. The address is identity and is full-width — it never
goes in the command word. Alan sets direction; the canon now holds the shape so it
doesn't have to be re-derived from the chat.

# ════════════════════════════════════════════════════════════════════════════
# (detailed session entries below)
# ════════════════════════════════════════════════════════════════════════════

# Session Log — 2026-06-29a — CORRECTION: out-shift was NEVER a stub — it is wired in unicell64 and ALREADY ON THE DIE. Sim-proven; runs on the current bitstream.

## Correction to earlier "stub" claim
Prior logs said m_out_shift_en was "defined/selected but no post-gate shift stage wired."
WRONG. unicell64.v has the full out-shift stage: computed_shifted (line ~511) right-shifts
computed_output by m_shift_amt when shift_out_en (= m_out_shift_en | t_shift_out_en); line
~953 emits computed_shifted as the fired out_buf_data. Internal state (data_reg, a_data /
loop_back / latch_in) keeps the UNSHIFTED computed_output, so out-shift is a clean bus-side
output modifier that never corrupts feedback. It was complete all along — just never exercised.

## Consequence: out-shift needs NO rebuild — it's in the flashed bitstream
The current top_arria10_64 flash uses this unicell64, so out-shift is already on the GX660.
Prove it on the CURRENT bitstream like the mask test (no reflash):
  icm64_outshift.tcl: SET_METHOD out_shift_en + shift_amt=4 (cmd_data=0x00010800), inject
  0x01002340 -> expect fired out_data=0x00100234 (result >>4). Distinct from in-shift's
  0x10023400 and from the raw 0x01002340 — unambiguous.
Sim-proven end-to-end through zone64: tb_zone64_outshift.v -> 0x00100234. PASS.
Field map (SET_METHOD writes cmd_latch[63:32] from cmd_data): nibble_mask=cd[7:0],
mask_en=cd[8], shift_amt=cd[14:9], in_shift_en=cd[15], out_shift_en=cd[16].

## Revised roadmap (out-shift collapses into "already done once tcl run")
1. ✅ in-shift on die (icm64_shift -> 0x10023400). DONE.
2. ✅ nibble mask on die (icm64_mask -> 0x00002340). DONE.
3. [run on CURRENT flash] out-shift: icm64_outshift.tcl -> 0x00100234. (sim PASS; silicon pending)
   Double-ended (in+out) under the address constraint is a clean ROUND-TRIP (<<n>>n identity,
   correct); the two independent single-stage proofs are what establish both stages exist.
4. The only genuinely NEW RTL before the full rebuild is LANES (adds a stage — watch timing
   on the small sample). Debug-select (op26) already in unicell_array64.
5. Then full rebuild (all features + debug-select) -> test all on die -> Python rewrites.

# Session Log — 2026-06-28g — ✅ STORED SHIFT PROVEN ON SILICON. Root cause of the dead bring-up was the missing clock constraint (not the ISSP, not the cell); clean-project rebuild fixed it; 64-bit methodology datapath confirmed on the GX660.

## RESULT: icm64_shift.tcl on top_arria10_64 (GX660)
  fired=1  out_addr=0x0200  out_data=0x10023400   (= 0x01002340 << 4)
  >>> PASS: stored shift applied on silicon — 64-bit methodology datapath confirmed.
The 64-bit cell's methodology half computes correctly in hardware: widened cmd_latch,
SET_METHOD (op25) on the held target lane, stored shift folded into the operand pipeline,
addressing, fire — all end-to-end on die, bit-exact to sim.

## icm64_readstate.tcl (just before): whole substrate alive
cycle_count ticking (796,075,261 -> 798,481,969); 0xDA7A marker reads 0xDA7A (snapshot
latching); cell0 cmd_latch=0x0040002c topo=0x02c armed=1 in=0x0100 out=0x0200; armed_count=400
(ALL 400 cells armed). Clock + command path + addressing + arming + snapshot readback all good.

## ROOT CAUSE of the whole dead bring-up: missing clock constraint (Alan's memory was right)
The earlier projects had NO .sdc/.qsf in the project, so CLK_100M was never promoted to a
global clock network — the fabric never clocked, cycle_count sat at 0, every probe field read
0. NOT the ISSP, NOT the 64-bit cell. Confirmed by the fitter on the good build:
"div_cnt[1]~CLKENA0 (150867 fanout) drives Global Clock Region" — clk_div promoted global,
reaching the whole fabric; clocks table CLK_100M=100MHz, clk_div=25MHz (sane, vs the earlier
degenerate 645MHz-1.5GHz tmin nonsense = unconstrained clock). The ISSP regenerations / probe
width / source-clock were real fixes but never the blocker.

## FIX that worked: clean single-folder project from the proven build
Quartus project had lost its database (clicking any report regenerated from just the .sof;
ISSP scattered under output_files4\). Rebuilt as ONE clean folder with: Unicell64.qsf +
Unicell64.sdc (clock constraint — the missing piece), the PROVEN issp.qsys (21/06, NOT
regenerated), full *64.v chain + unicell64.v + both bridges. One clean compile -> fabric
clocked -> shift passed first try. Lesson (again): clone the working project, change the
minimum; don't assemble fresh. Constraints already banked in fpga/quartus/.

## STATUS vs roadmap
Step 1 (prove the BUILT methodology set on die) = ✅ DONE — BOTH features confirmed:
  - icm64_shift.tcl: inject 0x01002340 -> 0x10023400 (stored shift <<4). PASS on silicon.
  - icm64_mask.tcl:  inject 0x01002340 -> 0x00002340 (nibble_mask 0xF0, hi nibbles zeroed). PASS on silicon.
  Clean A/B: same bitstream, same cell, same inject — only SET_METHOD config differs, output
  differs accordingly. The methodology stack applies the configured op on command, on die. The agreed order continues:
2. Small-sample OUT-SHIFT (the one stubbed cell field) + tests + fit/timing.
3. Small-sample LANES + tests + fit/timing.
4. Full rebuild (all features + debug-select op26, already in unicell_array64) -> test all on die.
5. THEN Python rewrites against the final silicon-proven field set (load-and-run).
Note: nibble MASK is built+sim-proven but not yet separately silicon-confirmed — a one-line
tcl variant (SET_METHOD mask_en+nibble_mask, check masked output) confirms it on THIS bitstream.

# Session Log — 2026-06-28f — Silicon bring-up blocked at the SNAPSHOT TRIGGER (regenerated ISSP source path), not the fabric; target-addressed debug-select wired for next build.

## Where the 64-bit flash stands (top_arria10_64, GX660)
Full die fit GOOD: 185,445 ALM (74%), 157,856 reg, FMAX clk_div 56.2 MHz (target 50 — fine).
Constraints now correct (CLK_100M @ E23 took; clk_div recognised). Probe width fixed to 113
(reads len=29 clean). BUT every snapshot reads ALL ZERO.

## DECISIVE diagnosis: snapshot trigger not firing (NOT clock, NOT cells)
icm64_readstate.tcl selector-4 reads the bridge's HARDCODED 0xDA7A marker as 0x0000. That
constant is wired into the snapshot mux and does not depend on clock/cells/config — the ONLY
way it reads zero is if the snapshot NEVER LATCHES (snap_pulse never fires). So snap_req
(source[65]) edge is not reaching the bridge. cycle_count also static 0 (same cause).
- PROVEN build (top_arria10) TICKS cycle_count on THIS board THIS session (1BD9D5B0->1C033BFA->
  1C2CA20A). So board clock + snapshot mechanism + tcl are all fine when driven by the proven
  ISSP. The fault is isolated to the 64-bit build's FRESHLY-GENERATED ISSP source path.
- Likely cause: source SYNCHRONISATION/pipeline registers not enabled on the regen (bridge
  header warns: "without source clock + sync regs the edge-detects glitch"; snap_req/cmd_go
  are edge-detects). Probe=113, source=66, source-clock-on, enable-off were all set — the
  sync-register option is the remaining suspect.

## FIX for Alan (overnight / morning): copy the PROVEN ISSP IP, do not regenerate
The proven Unicell-Q build's ISSP works on this board right now (ticks). Copy its generated
ISSP IP files (.qsys/.ip/.qip + generated dir) into the 64-bit project wholesale instead of
the freshly-parameterised instance — it already has probe=113, source=66, source clock, and
the correct source registration the bridge was written against. Re-fit, reflash, re-run
icm64_readstate.tcl: the 0xDA7A marker should read 0xDA7A and cycle_count should tick = snapshot
alive. THEN icm64_shift.tcl -> want out_data=0x10023400 (stored shift on die).

## DONE this session (rides the NEXT build): target-addressed debug-select (Alan's idea)
"Use the target address to read just the programmed cells." Wired into unicell_array64.v:
new opcode CMD_DBG_SELECT=26 latches dbg_sel (clog2(NUM_CELLS) bits) from cpu_data; dbg0_*
ports now mux cell_*[dbg_sel] instead of hardwired [0]. Cells have NO decode for op 26 ->
pure side-effect-free debug write. Lets the host walk every cell of zone 0 on die and read
its real config. PROVEN in sim (fpga/verilog/tb_dbgsel64.v): configured cell0 topo=0x0BC,
cell2 topo=0x024; DBG_SELECT 0 reads 0x0BC, DBG_SELECT 2 reads 0x024. PASS.
NOTE: bridge currently wires only zone-0 dbg0 to ISSP, so this reads zone 0's 25 cells;
reading OTHER zones needs a top-level zone-mux (later). This is committed but NOT in the
flashed bitstream yet — rides the next reflash.

## Pending / order unchanged
1. Alan: copy proven ISSP IP -> reflash -> probe-sanity (0xDA7A + cycle tick) -> icm64_shift
   (0x10023400 = in-shift on die).
2. Then small-sample OUT-SHIFT + tests; then small-sample LANES + tests; then full rebuild
   (now also carrying debug-select); then test all features; THEN the Python rewrites against
   the final silicon-proven field set.
Design notes banked today: security_portability.md, hybrid_hard_ip.md.

# Session Log — 2026-06-28e — Silicon bring-up of the 64-bit variant: dead-clock root-caused (missing pin constraint, NOT the cell); constraints banked; agreed feature-completion roadmap before the Python rewrite.

## Silicon session (top_arria10_64, GX660)
- Zone synth (registered I/O): 14,270 ALM / 10,517 reg / 131.68 MHz in-fabric. vs 50 MHz
  target = 2.6x margin. Timing NOT the constraint; density is (~510 ALM/cell).
- Chose 25 cells/zone (400 total). Built top_arria10_64 (16x unicell_zone64, op25 routed).
- FIRST flash: icm64_shift.tcl -> fired=0, all-zero probe. DIAG (icm64_probe_sanity.tcl):
  raw probe len=33 but ALL ZEROS, cycle_count stuck 0 -> FABRIC NOT CLOCKING. Root cause:
  fresh project had NO .qsf/.sdc -> CLK_100M unconstrained, never reached E23, /4 divider
  never ticked. NOT the 64-bit cell. (Same failure as the very first card bring-up.)
- FIX (banked, permanent): fpga/quartus/Unicell-Q.sdc (CLK_100M 100MHz @ E23, clk_div /4),
  Unicell-Q64.qsf (top_arria10_64 + *64.v chain + bridges + PIN_E23), Unicell-Q.qsf (proven
  32-bit fallback). Constraints now IN-REPO so the clock never wanders on a fresh project.
- Re-flashing now (2h build). On completion: run icm64_probe_sanity (cycle_count must TICK),
  then icm64_shift.tcl -> want out_data=0x10023400 (0x01002340<<4 = stored shift on die).

## Cell audit (unicell64.v methodology half)
WIRED + proven in sim: m_in_shift_en + m_shift_amt (input shift), m_mask_en + m_nibble_mask.
STUB: m_out_shift_en — field defined and selected into shift_amt, but NO post-gate output-
shift stage is wired (bus_data_shifted shifts INPUT only). Out-shift is the one cell gap.
The shift test uses a hand-written tcl (SET_METHOD op25 poked directly) — does NOT need the
loader; loader does not emit op25 yet.

## AGREED ROADMAP (Alan) — complete + silicon-prove the cell BEFORE the Python rewrite
1. Finish THIS flash; probe-sanity (clock alive), then icm64_shift (in-shift on die).
2. Rebuild a SMALL sample with OUT-SHIFT wired + tests; confirm pass + fit + timing.
3. Rebuild a SMALL sample with LANES + tests; confirm pass + fit + timing.
4. If all pass and fit/timing hold -> FULL load rebuild (all features, 16 zones).
5. Test ALL features on the full die.
6. THEN the Python rewrites (loader SET_METHOD emission, ICM methodology fields, two-slot
   decoder, format/HMAC) — written ONCE against the FINAL, silicon-proven field set, not a
   moving target. Tested as we go against a fully-specced running substrate: "load and run."
Rationale: writing the loader/format against in-shift-only and again when out-shift/lanes
land is exactly the churn the "prove the cell first, then point Python at it" rule avoids.
The two-slot decoder stays deferred until the field set is final (it's encoding, not feature).

## Open cell items before full rebuild
- Wire out-shift (post-gate right-shift stage mirroring the input shift). Small, low-risk
  (mirrors proven logic). Next small-sample build.
- Lanes (by-source splice default; by-arrival intra-die-only flagged). Reserved bits +
  1 opcode; FIRST in the operand pipeline. Synth-time it (single-cycle ceiling). Next sample.
- Hold the line at 3 operand stages (lane/shift/mask); further features via opcode
  combinations, not new depth (the measured timing-cost rule).

# Session Log — 2026-06-28d — Zone synth measured; 25 cells/zone chosen; FOCUSED datapath-confirm reflash prepared (decoder deferred).

## Zone synth result (top_zone_synth, CELL64=1, registered I/O, 4 pins)
14,270 ALMs / 10,517 registers / FMAX 131.68 MHz for a 28-cell variant zone (real
fabric-internal path: wired-OR bus + routing). vs 50 MHz target = 2.6x margin — timing
is NOT the constraint. ~510 ALM/cell; full 16-zone die of the variant ~228k ALMs (~90%)
at 28 cells — DENSITY is the constraint, not speed.

## Decision: 25 cells/zone (Alan)
25 x 16 = 400 cells, ~81% ALM, comfortable router headroom, plenty to test every feature.
top_zone_synth NUM_CELLS -> 25. (Real reflash top set to 25 too.)

## Decision: lanes DEFERRED (Alan) — "is it needed at this stage? no"
Lanes are a NEW methodology stage = additive capability, not confirmation of what's built.
This reflash CONFIRMS the already-built upper half (stored shift + mask) on silicon. Add
lanes later against a proven base, with clean isolated synth-timing. Don't debug new RTL +
first-silicon shift/mask together (isolate the variable).

## Decision: two-slot decoder DEFERRED to AFTER datapath confirm (Alan)
The placeholder CMD_SET_METHOD (op 25) is SUFFICIENT to silicon-prove shift+mask (same
pattern as CMD_LOAD_AT proving targeting before the streaming loader optimised it). The
real two-slot four-state decoder is an ENCODING optimisation with an under-pinned piece
(writer-opcode cmd_data packing) — write it on a proven datapath, not rushed into the
first-silicon bitstream.

## Reflash prepared (FOCUSED datapath confirm)
- pcie/top_arria10_64.v — variant top (copy of proven top): 16x unicell_zone64, NUM_CELLS=25,
  cpu_addr_w routes load_target for op 25 (CMD_SET_METHOD) like ops 2/3/23. Proven top
  untouched as the known-good fallback. (Quartus-validated by Alan; too large for iverilog
  full-elaborate here — the three surgical edits grep-verified.)
- fpga/verilog/tb_zone64_method.v — PROVES end-to-end in sim: SET_METHOD stored shift<<4
  on the held target through a full zone64, inject 0x01002340 -> fired out_data 0x10023400.
- fpga/icm64_shift.tcl — silicon test mirroring the sim: same sequence, reads fired out_data
  at probe selector 0 (snap_out_data=out_data_l, out_seen@[96]). PASS if out_data=0x10023400.
  No ISSP-bridge change needed (uses the existing fired-output readback).

## NEXT
1. Alan: synth top_zone_synth at 25 (confirm fit ~81%), then build+flash top_arria10_64,
   run icm64_shift.tcl — fired out_data=0x10023400 = stored shift proven on the GX660.
   (A mask variant tcl is a trivial follow: SET_METHOD mask_en+nibble_mask, check masked out.)
2. THEN the real two-slot decoder (four states + arm + one-function guard) on the proven
   datapath; pin the writer-opcode cmd_data packing first.
3. THEN lanes as an isolated stage; then loader format bump + golden ICM; then compiler.

# Session Log — 2026-06-28c — 64-bit cmd_latch: datapath variant built + encoding spec settled.

## What landed
- CMD_RECONFIGURE auth-write now boot-only (clause 3) — committed d70dc1b, tb_reconfig_auth.v.
- Adder dependency check: packed KS needs the cut (stored shift); wide KS (548c) doesn't
  fit the 448-cell die; 16-bit wide KS (~270c) is a no-cut no-reflash option.
- fpga/verilog/unicell64.v — 64-bit cmd_latch VARIANT (proven cell untouched). Upper-half
  methodology fields wired (nibble_mask[39:32], mask_en[40], shift_amount[46:41],
  in_shift_en[47], out_shift_en[48]); stored shift folded into the fixed ladder as
  stored-OR-transient; stored nibble-mask spliced before the gate. Loaded via PLACEHOLDER
  CMD_SET_METHOD (op 25, addr_match-gated) — NOT the real encoding, just a testable write.
  tb_unicell64.v PROVES stored shift (<<4) + nibble-mask (block high 16) drive the datapath.
- docs/design-notes/cmd_latch_64bit.md — RESOLVED section appended: auth 8-bit both sides
  (option a); two-slot opcode encoding settled (8 slot-A + 8 slot-B + 2 flags + arm + 8 auth,
  5 bus spare); opcode implies payload type so NO selector bit; one-function/many-methodology
  as an ENFORCED guard (two-function pass illegal, must refuse); two-pool budget (bus=
  expressivity guard / latch=area don't carve); reserved-means-zero enforced.

## Encoding decisions settled this session (Alan)
- Auth 8-bit both sides — binding constraint is the BUS not the latch; returns 2 bits to
  bus spare (5 total). Methodology latch has 15 reserved (cmd_latch[63:49]).
- Two-slot word = two independent opcode slots; flags gate which are live; cell applies both.
  00 topology-only / 01 function+methodology / 10 function (B ignored) / 11 both methodology.
- Slot B's function is read from its OPCODE, not a selector bit. One function per cell
  (enforced), multiple composable methodologies per pass (the reason the word exists).

## NEXT (named)
1. SYNTH one zone of unicell64 — measure stored-state + mask/shift area vs the 70% fitter
   hang, BEFORE any full die build. (Alan to run between sessions.)
2. Replace placeholder CMD_SET_METHOD with the REAL two-slot decoder (four states + arm +
   at-most-one-function guard). Datapath underneath is proven, doesn't change.
3. Loader/serialiser format-version bump (32->64) + refuse-to-load guard; golden 64-bit ICM
   proven on the die BEFORE pointing the compiler at it.

# Session Log — 2026-06-28b — Address-targeting reflash (Option A): SET_INPUT/SET_OUTPUT addr_match-gated on the held target. Loader now streams full (target, topology, in, out) records. Sim-proven (oracle + RTL); awaiting reflash for silicon. NEXT item 1b DONE in sim.

## The change (3 RTL files — this is the reflash set)
Chosen Option A (Alan): SET_INPUT_ADDR/SET_OUTPUT_ADDR become addr_match-gated in the
CELL, exactly like CMD_LOAD_AT — one comparator gates everything (invariant clause 1/4),
the same mechanism used in normal run-mode addressing, not a boot-only special case. Host
cycles at load time are cheap; correctness is what matters.
- pcie/top_arria10.v: cpu_addr_w now reads the held load_target for opcodes 2 and 3 as
  well as 23. Target (latch) and the new-address value (cpu_data) stop colliding.
- unicell_array.v: SET_INPUT_ADDR(2) dropped from cmd_is_boot_targeted — it (and op 3)
  now BROADCAST and the cell self-gates on addr_match. No parallel array comparator.
  SET_LOGICAL(14) STAYS array-targeted (the boot walk is untouched).
- unicell.v: CMD_SET_INPUT_ADDR / CMD_SET_OUTPUT_ADDR gate on (addr_match && auth_ok).
Per-cell record (all on one held target): SET_TARGET(slot); SET_INPUT(in); SET_OUTPUT(out);
LOAD_AT(topo|arm). 4 transactions/cell.

## Loader (fpga/icm_stream.py) — full-record streaming
build_stream now emits SET_INPUT/SET_OUTPUT per record (stream_addr default ON;
--no-stream-addr for the pre-reflash bitstream). Oracle models the addr_match-gated
SET_IN/OUT. emit_tb checks input_address+output_address per cell. emit_tcl reads cell-0
topology + in + out at probe selector 3 (the bridge packs dbg0_input_addr@[95:80],
dbg0_output_addr@[47:32] alongside cmd_latch@[79:48] — a single snapshot shows all three).

## New test: arbitrary wiring (examples/icm/wired3.icm)
Three cells whose in/out are deliberately NOT the physical defaults; cell0+cell1 both
emit to 0x50 (a wired-OR fan-in the default chain can't express), cell2 to 0x51.
- ORACLE: ALL PASS (topology + in/out per cell; unused cell at defaults = exclusion).
- RTL replay (tb_icm_wired3.v, real unicell): 3/3 cells match topology AND in/out.
  cell2 out=0x51 while cell0/1 out=0x50 by itself disproves broadcast.
- Silicon (fpga/icm_wired3.tcl, needs the reflash): reads cell0 topo=0x0BC, in=0x40,
  out=0x50 at selector 3.

## Regressions (all green on the edited RTL)
tb_top_target, tb_zone_target, tb_zone_chain, tb_zone_inject, tb_zone_adder, tb_zone_emit,
tb_die_boot (boot walk intact), tb_v23_oracle, tb_icm_xor_and_or, tb_icm_wired3 — PASS.
tb_v23_oracle UPDATED to the new model: it now presents the target on the address lane
before SET_OUTPUT (was relying on old broadcast). tb_zone_inject byte-identical original
vs edited. PRE-EXISTING fails (NOT this change, identical on original RTL): tb_cmd_emit
(stale standalone, superseded by tb_zone_emit), tb_bridge_chain (documented all-armed
ripple synthetic artifact).

## NEXT
1. DONE (SILICON, 2026-06-28): reflashed top/array/cell. zone_target / zone_adder /
   zone_emit regressions passed on the die, then icm_wired3.tcl read back cell0
   topo=0x0BC, in=0x40, out=0x50 at probe selector 3 — per-cell address streaming proven
   on the GX660. 0x50 is the wired-OR fan-in (cell0+cell1 → one output), a wiring shape the
   physical-default chain can't express, so arbitrary topology + arbitrary wiring are both
   silicon-confirmed loadable. Ledger limit: cell0 is probe-visible; cell1/cell2 distinct
   in/out are oracle/sim-verified (cell2 out=0x51 vs cell0/1 out=0x50 disproves broadcast),
   not directly read on the die — same read-scope as zone_target. The addressing invariant
   is now a measured property of the fabric, not only a doc claim.
2. Packed Kogge-Stone adder as the first heterogeneous ICM with REAL wiring on silicon
   — now buildable (full (target, topology, in, out) records proven loadable on the die).
   This is the next live target.
3. Loose end still open: CMD_RECONFIGURE auth-write under physical_mode (invariant clause 3).
4. Horizon (deferred to full-silicon era, years out): inter-card comms. Seam is already
   clean — block_id (high 16) + declared-latency handoff; nothing inside a cage may assume a
   free cross-cage wire. Linked bridge-buffer reorder + selective-repeat ARQ sketched (see
   below) but parked; cross-card transport to be written against the real die's transports,
   not designed ahead. Single-card and two-card-federation work between now and then feeds it.

## Architectural notes banked this session (not yet RTL)
- 64-bit cmd_latch cut: its hardest prerequisite (per-cell targetable setup writes) is now
  done — SET_SHIFT/SET_MASK are the same addr_match-gated shape as the proven SET_*/LOAD_AT.
  Remaining: widen latch, stored shift+mask upper half, auth option (a) 8-bit both sides,
  format-version bump + refuse-to-load guard, stack rewrite (serialiser/VM/compiler).
  Risk is area not logic: synth ONE zone with the 64-bit cell before the full build (the
  70% fitter hang was the variable barrel shifter; check the stored-state cost early).
  Build order: hand-write one golden 64-bit ICM, prove it on the die, THEN point the
  compiler at it — don't co-evolve the compiler with unproven RTL.
- Distributed timing: "known latency" must mean ENFORCED bound or confirmed arrival, never
  the typical/average. Bridge latency profile = a portable sidecar (like the .isi DSP table),
  read by the scheduler; wrong interconnect profile is a refuse-to-load hazard like wrong
  cell depths. Card-to-card: GT-direct for tight determinism, SmartNIC/host for coarse
  latency-tolerant handoffs — chosen per bridge.
- Linked bridge-buffer cells (reorder + reliable delivery, parked for the silicon era):
  address-as-sequence-number makes reorder = the addressing (packet N self-files into slot
  base+N); "all slots filled" = N-way AND (fabric-native); gap = unfilled slot (loss detect
  free). Count→address arithmetic belongs at the BRIDGE EDGE (like the loader's root+offset),
  not crammed into auth (auth is the trust gate at the boundary — never repurpose it). The
  per-packet sequence is a travelling FIELD (the old repurposed-CRC slot, born in the command
  word, resolved to a slot address on arrival, then gone). The WINDOW number is a separate
  HELD loop_back cell at each end (persists across buffer clears; carries set-tagging,
  wraparound anti-aliasing — keep sequence space >= 2x window — and duplicate-suppression).
  Resend/confirm = selective-repeat ARQ: sender-side retransmit buffer (the easy-to-forget
  half), NAK via CLZ/gap-bitmap over the occupancy vector, end-of-window marker for prompt
  NAK + staleness timer (Ward's stall_ticks shape) for the marker's own loss, BOTH ends
  carry timers (lost ACK = deadlock otherwise). Integrity: NOT a per-cell CRC (350 cells /
  depth 20 — XOR is the fabric's worst primitive in a serial chain, too costly inline). The
  cross-network transport framing (Aurora/Interlaken/Ethernet FCS) already carries CRC and
  turns corruption into a MISSING frame, which the loss path already handles. Residual
  tamper-evidence = a MAC (mask primitive / security module), not a polynomial. New cell
  (stored shift + loop_back) could build a cheaper CRC if ever truly needed, but the better
  outcome is not spending those cells in fabric at all.

## NEXT (original, superseded above)

## Files (additive + 3 RTL edits + 1 test update)
NEW: examples/icm/wired3.icm, fpga/icm_wired3.tcl, fpga/verilog/tb_icm_wired3.v.
EDITED: pcie/top_arria10.v, fpga/verilog/unicell_array.v, fpga/verilog/unicell.v,
fpga/icm_stream.py, fpga/verilog/tb_v23_oracle.v.

# Session Log — 2026-06-28 — ICM-file streaming loader built on the (SET_TARGET, CMD_LOAD_AT) transport (NEXT item 1). Offset-native, transport-pluggable, triple-verified. Additive — no RTL/existing file touched.

## What was built (the compiler<->silicon bridge, step 1)
fpga/icm_stream.py — streams an ICM as ordered (SET_TARGET addr, CMD_LOAD_AT config)
pairs through the proven address-lane target latch. Offset-native per the relocatable
canon: records hold block-local 16-bit OFFSETS, loader forms root+offset, never bakes
absolute-only. Transport sits behind a Transaction layer (ISSP/UART now, PCIe BAR later
swaps the carrier, not the stream). gs->LOAD_AT config-word translation verified against
the unicell.v decode (topology[9:0] + arm@[11] the proven subset; richer gs<->cmd_data
flag mapping deferred to the 64-bit cut, with a warn-on-unmapped-bits guard so nothing
drops silently).

examples/icm/xor_and_or.icm — first streamed heterogeneous ICM: 3 cells, XOR/AND/OR
(0x0BC/0x007/0x024), contiguous so the physical-default wiring chains them. Same shape
tb_top_target.v proves.

## Triple verification (all agree)
1. Built-in ORACLE (faithful model of top load_target latch + cell CMD_LOAD_AT decode):
   cell0=0x0BC cell1=0x007 cell2=0x024 all armed; unused cell3 stays unconfigured
   (exclusion). ALL PASS.
2. Real RTL replay: --emit tb generates tb_icm_xor_and_or.v that drives the loader's OWN
   stream into unicell_zone/array/cell through the real latch logic. iverilog: 3/3 cells
   match. >>> PASS.
3. Byte-identical to silicon-proven zone_target.tcl: cfg words 0x8BC/0x807/0x824 =
   topology|(1<<11). Generated fpga/icm_xor_and_or.tcl runs on the Arria as-is.

## HONEST SCOPE on the currently-flashed bitstream
Streams per-cell TOPOLOGY+flags+arm (the CMD_LOAD_AT win). Does NOT yet stream arbitrary
per-cell IN/OUT addresses: SET_INPUT_ADDR(2)/SET_OUTPUT_ADDR(3) still take cpu_addr from
cpu_data[15:0] (target==value dual-use), so they only set in/out to the physical CELL_ID.
This ICM relies on physical defaults (in=CELL_ID, out=CELL_ID+1); loader WARNS if a
record's offsets diverge. Per-cell offsets ride in the stream regardless — same file
loads unchanged once the address-targeting reflash lands.

## NEXT (natural step 1b, then 2)
- Address-targeting reflash: route load_target into cpu_addr_w for opcodes 2/3 (top) +
  have the cell addr_match-gate SET_INPUT/SET_OUTPUT — mirrors exactly what CMD_LOAD_AT
  already does. Then the loader streams full (target, topology, in, out) records and the
  packed adder's irregular wiring becomes loadable. Spec against the INVARIANT first.
- Then: packed Kogge-Stone adder as the first heterogeneous ICM with real wiring on silicon.

## Files added (4, additive)
fpga/icm_stream.py, examples/icm/xor_and_or.icm, fpga/icm_xor_and_or.tcl,
fpga/verilog/tb_icm_xor_and_or.v. No existing file modified -> no regression surface.

# Session Log — 2026-06-23 — RESOLVED: within-zone OR-chain works on Arria 10 (28 cells, value intact). Root cause of the "no output" was a STALE-SNAPSHOT readback bug in or_chain.tcl, not the fabric.

## Flat cell addressing + serial boot walk (aligning RTL to ARCHITECTURE.md)
Read docs/ARCHITECTURE.md + addressing_note.md (should have first). Corrected
model: cell address is ONE flat point per block (block boundary = bus boundary);
zones are physical routing only, not an address level. Bridges are dumb physical
wire — routing is done by the destination ADDRESS carried in the cell, not by the
wire. Hierarchy block->die->card->backplane (128-bit) stacks above; Shore owns
everything above the local cell address; the cell latch never grows.

RTL deviations fixed:
1. CELL_ID was zone-local (0..27 x16); ZONE_ID was dead. Added CELL_BASE param to
   unicell_array (zone passes ZONE_ID*NUM_CELLS); CELL_ID = CELL_BASE + c, and
   boot targeting compares cpu_addr against the global flat ID. Zone N now owns
   flat IDs N*NUM_CELLS .. +NUM_CELLS-1. Address is one flat point, no zone field.
2. Reverted the za_out_remote bridge gate I had added — wrong layer. Bridges are
   pure physical wiring; correct cell addressing does all routing.
3. The real missing step was BOOT: nothing laid the flat address map over the
   fabric, so cells came up on physical defaults and a broadcast BOOT_COMMIT set
   EVERY cell to one address ("all cells same in/out address" = no boot walk ran).
   Made CMD_BOOT_COMMIT a per-cell TARGETED command (added opcode 7 to
   cmd_is_boot_targeted). Boot now WALKS: for each flat CELL_ID, BOOT_COMMIT
   targeted -> that cell's logical input_address := ID, auth := token, ->RUN; next.
   Serial (~1 transaction/cell) but lays the correct map. For basic testing
   logical==physical (cpu_addr selector == address payload), which is fine.

SIM PROOF (tb_boot_walk.v, 2 zones/56 cells): after the walk, every cell holds
logical input_address == its flat physical ID, all in RUN, auth set. cell0=0x0000,
cell27=0x001b, cell28=0x001c, cell55=0x0037 — contiguous straight across the zone
boundary. The bootstrap handoff from ARCHITECTURE.md, working.

CONSEQUENCE (action needed before next silicon flash): making BOOT_COMMIT targeted
removes the broadcast BOOT_COMMIT pattern. Any script that did one broadcast
BOOT_COMMIT to set all cells (shift_diag_v3.tcl, or_chain_diag.tcl PART A,
bringup_v23.py) must switch to the walk (BOOT_COMMIT per cell) OR target the
specific cell under test. tb_zone_inject.v already converted (walk-target cell 0,
logical=0) and passes. The silicon tcl scripts are NOT yet updated.

Regressions after all changes: tb_zone_chain fires=15 (physical-mode chain,
unaffected); tb_zone_inject walk-target cell0 out=0x2340@0x200; tb_boot_walk 56/56.

NOTE on the all-armed bridge ripple (tb_bridge_chain): with flat addressing the
token DOES cross the zone boundary (Z0->Z1 confirmed), but an all-cells-armed
ripple floods the next zone's ibus (every fire hits the dumb bridge; non-matching
addresses still assert cpu_valid and interrupt the in-zone or_valid ripple),
stalling mid-zone. This is a synthetic-test artifact (real programs are sparse/
directed, not a full ripple). Separable from addressing — the address map is
correct (proven by tb_boot_walk). Revisit with a sparse directed cross-zone test.


## RESOLUTION (the actual answer)
or_chain_diag.tcl PART B on silicon:
  after inject: out_count=28  out_addr=0x001c  out_data=0x00002340
=> FULL within-zone chain: cell0->cell27 rippled, B passed through OR(0,B)=B
   intact, out_addr reached 0x001c (=28, zone's last cell emits to 28).
PART A (proven PASS_B) gave out_count=1, out_data=0x01002340 => ISSP output
capture was working all along.

The fabric was firing and chaining correctly the WHOLE time. The "out_count=0,
out_data=0, arrived->0 (impossible)" readings were a readback ordering bug in
or_chain.tcl's `show`: it called `rd` (read probe) BEFORE the snapshot, so every
line displayed the PREVIOUS step's snapshot. "after inject" was showing the
"after preload" (pre-fire) state = zeros. Fix: take a fresh view-0 snapshot in
`show` before reading out_* (committed to or_chain.tcl). JTAG shift latency (ms)
>> ripple (~4.5us) so the fresh snapshot always lands after the wave settles.

Consequences:
- The double-drive fix (zone arbiter) was a real cleanup but NOT this bug; it
  neither caused nor fixed the visible symptom. Keep it (cleaner single-drive).
- The per-cell addressing-encoding finding still stands for FUTURE arbitrary
  (irregular) addressing; physical-mode CELL_ID+1 default chain is proven.
- Decode gotchas for the readback: output_set is a SEPARATE reg, NOT cmd_latch[19]
  (dump's outset19=0 is meaningless; 28 fires prove output_set=1). out_data_l is
  NOT cleared on reset (only out_count is) -> stale out_data display when count=0.

## BRIDGE round-robin (cross-zone) — bug found + fixed in sim
Built tb_bridge_chain.v: N zones in a row wired exactly like top_arria10's bh
chain (zone[i].bridge_w_out -> bh[i] -> zone[i+1].bridge_e_in, forward-only).
Config broadcasts to all zones (RECONFIGURE OR, SET_OUTPUT=0 so the active cell
re-emits on the same index, preload A=0). TRIGGER injected into ZONE 0 ONLY, so
any other zone firing can only be the bridge delivering the token.

FOUND (cross-zone delivery was silently broken): a bridge token reaches the
receiving zone's ibus correctly (traced: ibus_valid=1, ibus_addr=0, data intact,
cell0 a_arrived=1) but the cell never fired. Root cause in unicell_array.v line
215: on cpu_valid, `bus_valid <= (cmd_code==8'd1)?1:0`. The bridge token rides
ibus->cpu with the COMMAND bus idle/stale (cmd_code != 1 at the receiving zone),
so bus_valid stayed 0 and the token never reached the cell bus. In-zone chaining
works because it uses the or_valid->bus path, which bypasses this gate; cross-zone
is the only path that hits it -> never exercised until now.

FIX: bus_valid <= !cmd_valid (drive the data bus for any data-carrying cpu cycle
-- host DATA_WRITE or inbound bridge token -- but not for commands, which pulse
cmd_valid). Covers all three cases: host inject (cmd_valid=0)->1, host command
(cmd_valid=1)->0, bridge token (cmd_valid=0)->1.

SIM RESULT (8-zone row): token injected into Z0 only reaches all 8 zones via
bridges, data 0x00002340 intact at every hop, deterministic 8 cycles/hop
(Z0@28 ... Z7@84 = 56 cyc / 7 hops). Regressions pass: single-zone chain
(fires=15, arrived->13) and proven inject (out=0x01002340@0x200, arrived->0).
Per-hop budget ~8 cyc = bridge-out reg + ibus reg + cpu->bus + bus_addr_r +
fire/drain. Vertical (bv, s_out->n_in) uses the identical mechanism.

NEXT (silicon): only unicell_array.v changed -> rebuild + reflash. Cross-zone
chain then extends the within-zone chain past the zone boundary (out_addr will
climb past 0x001c when the token bridges into the next zone). Multi-zone read:
use the per-zone z_out probes / ISSP view, watch out_addr cross the boundary.
Asset: fpga/verilog/tb_bridge_chain.v (parametric N, extensible to the 2x8 grid).

## NEXT (real frontier now): cross-zone bridge handoff
out_addr stops at 0x001c because cell 27 emits to addr 28 and no cell 28 exists
in the zone. Going deeper = the inter-zone BRIDGE path (bh/bv registered handoff),
the least-tested path. Build that chain in sim (multi-zone tb), then silicon.

## (superseded) earlier framing this session

## Root cause of the chain failure (FIX committed)
Instrumented tb_zone_chain. Chain DOES ripple in sim (15 fires, out_addr climbs
1->15, value 0x2340 intact) but only cell 0 cleared a_arrived; every cell
triggered by FEEDBACK fired and then RE-ARMED. Bus trace showed why: every fired
address is driven onto the internal bus TWICE —
  (1) by the array's own or_valid->bus chaining (unicell_array.v ~line 216), and
  (2) by the zone re-injecting the same local fired output via
      `else if (za_out_valid) -> ibus -> array.cpu_*` (unicell_zone.v ~line 176).
The second (lingering) exposure hits the first-arrival store AFTER a_arrived has
cleared, re-arming the just-fired cell. That zone re-injection is redundant — the
array already chains its own output internally, and bridges get za_out on a
separate path — so it does nothing useful and double-drives the bus.

Same family as the ibus_addr skew: a timing-sensitive double-drive that nets one
way in zero-delay sim (arrived stuck HIGH, output surfaces) and the other way on
silicon (arrived->0, no output). FIX: delete the `else if (za_out_valid)`
re-injection branch in the zone arbiter. Host-inject + bridge paths retained.

Sim-verified on the real file (no IP regen, only unicell_zone.v changed):
- tb_zone_chain: fires=15, value intact, arrived 28->13 (was 28->27 with the bug)
- tb_zone_chain_probe: cells 0..14 cleared cleanly, wavefront at cell 15
- tb_zone_inject (proven single-cell): NO regression — out=0x01002340 @ 0x0200, arrived->0

## NEXT (silicon): reflash with this fix, run fpga/or_chain.tcl
Tell = arrived drops on inject AND out_count ticks >1 AND out_data=0x00002340
with out_addr advancing past 0x0001. This is the divergence-resolved test.
If it STILL shows no output: next suspects are the cross-zone bridge handoff
(bh/bv registered path, barely exercised) then the out_count capture in the ISSP
bridge.

## Per-cell addressing — encoding gap (CONFIRMED in sim, design decision pending)
Verified the canonical bring-up order (bringup_v23.py): BOOT_COMMIT sets the
INPUT (logical) addr + auth + flips to RUN; SET_OUTPUT_ADDR sets the OUTPUT addr
SEPARATELY; RECONFIGURE sets topology + arm. Not one sweep. Then found the deeper
issue — the runtime command word cannot set arbitrary per-cell addresses:
- For any non-inject command, cpu_addr = cpu_data[15:0] AND the address payload
  is also cmd_data[15:0] — the SAME 16 bits are both "which cell" and "what
  address" (the array's documented cpu_addr dual-use problem).
- => targeted SET_INPUT_ADDR/SET_LOGICAL can only write input = CELL_ID (identity)
- => SET_OUTPUT_ADDR (opcode 3) is NOT in the boot-targeted list -> it BROADCASTS;
  every cell collapses to one output address.
- => BOOT_COMMIT also broadcasts (all inputs to one value).
Sim proof (tb_target-style dump): SET_INPUT can't move a cell off its CELL_ID;
SET_OUTPUT 0x2000 set ALL cells' output to 0x2000. So today the ONLY source of
distinct per-cell addresses is the synthesis defaults (in=CELL_ID, out=CELL_ID+1)
in physical mode — which is exactly the physical-mode chain shortcut.

## Addressing model correction (Alan) — the real design
ICM carries the payload: configs, latches, AND the per-cell OUT address. The IN
address is NOT stored absolute — it's an offset the loader resolves. Load = create
pond -> assign ward + PTT -> drop ICM at an origin; every address inside is
relative to the pond origin (position-independent; CELL_ID+1 default is just the
origin-0 degenerate case). So per-cell out addresses arrive as ICM offsets, never
as 448 individual targeted SET_OUTPUTs — the command dual-use problem only bites
for IRREGULAR per-cell addresses set after the fact (fan-out trees), not for
relocatable blocks.

## Direction to spec (NOT built — freeze on paper first)
Generalise boot from single-broadcast-address to RANGE/BLOCK boot: carry
[block_start_id, block_end_id] + origin; each cell in window sets base =
origin + (CELL_ID - block_start); ICM offsets ride on top. Range-addressed (a
block, not per-cell) so it sidesteps the cpu_addr collision. Add an assign +
read-back handshake: loader assigns origin, block confirms realised start/end =
the programming info needed later (also where DSP-anchor / .isi seed-coords plug
in). Irregular non-structural per-cell out addresses still need the decoupled
target/payload encoding (take address payload from cmd_data[31:16], target stays
[15:0]; add opcode 3 to boot-targeted) — DEMOTED to "for irregular topologies",
bank it. The block-origin boot extension touches the ICM header (origin binding)
and the loader — design on paper, freeze once, then RTL.

## Verification assets added/used (reusable, iverilog seconds)
- fpga/verilog/tb_zone_chain_probe.v — per-cell a_arrived dump + per-fire address
  log. Proves the re-arm bug and its fix. (bus-trace + addr-target dumps were
  scratch; re-derivable from this.)

## Commits this session
- (this commit) fix: drop redundant local re-injection in zone arbiter
  (double-drive re-arm) + tb_zone_chain_probe.v + session log

## Standing notes (unchanged)
- Sim-first proven again: the re-arm was invisible at the counter level; only the
  per-cell arrived dump + bus trace exposed it.
- Build = 6 Verilog files, no IP regen for this change. Push via PAT URL (rotate
  after). git status "ahead N" is a false alarm — ls-remote is ground truth.

## CORRECTION + preliminary full-die boot model
Refined the boot model per the architecture intent (two earlier missteps fixed):
- Address is a flat BIT-FIELD: (block<<5)|cell — cell in [4:0] (32/block), block in
  [8:5] (16 blocks), 9 bits inside the 16-bit local address. CELL_BASE = ZONE_ID<<5
  (was ZONE_ID*NUM_CELLS). Block N owns N*32..N*32+27.
- REVERTED BOOT_COMMIT to BROADCAST. It is the final AUTH COMMIT (auth is 0000
  during the walk, so one broadcast BOOT_COMMIT sends the auth code to all cells
  and flips good cells to RUN). The per-cell walk is health-check + address, using
  the targeted address opcodes, NOT BOOT_COMMIT. So broadcast BOOT_COMMIT is NOT a
  bug to remove — it has a real job as the last bootstrap step. (Earlier note about
  updating shore/silicon tcl for targeted BOOT_COMMIT is withdrawn.)
- Removed tb_boot_walk.v (used targeted BOOT_COMMIT) — superseded by tb_die_boot.v.

tb_die_boot.v — PRELIMINARY model of the silicon full-die bring-up (4 blocks x 28
cells in sim, scales to 16x28=448): PHASE 1 walks every cell in flat-address order,
probes it (readback = health check), builds the flat block map and a BAD-CELL TABLE
in the boot-RAM area (one simulated defect @ 0x0022 tabled + skipped, 111/112 good);
PHASE 2 broadcast BOOT_COMMIT auth commit -> all cells RUN. Result: flat map
0x0000..0x007b, defect skipped, authed+RUN.

Still TODO (next): relocatable block-base as a RUNTIME register (controller assigns
each block its base in one op; cells offset by local index) for multi-card / block-
granularity relocation — currently the base is the synthesis position ZONE_ID<<5.
The bad-cell skip is modelled at the controller (boot RAM) level, which is correct;
wiring the skip into address assignment is the relocatable version's job.

Regressions green: tb_zone_chain fires=15; tb_zone_inject out=0x01002340@0x200
(broadcast BOOT_COMMIT restored); tb_die_boot 111/112 + auth commit.

## Single-zone adder + chaining + addressing test (no rebuild)
"It's a bootloader change, test one set of cells" — for ONE zone, zone-0 physical
addressing is flat 0..27, identical to the flashed bitstream, so NO FPGA rebuild:
it's all in the test/boot tcl. Built sim + silicon tcl:

- tb_zone_adder.v (sim, PASS): half-adder primitive on cell 0 + OR chain.
  XOR(0x0C,0x0A)=0x6 (sum), AND(0x0C,0x0A)=0x8 (carry), chain ripples fires>=2
  data 0x2340 intact. Key: arbitrary operands come from TWO INJECTS (inject A =
  1st arrival -> stored; inject B = 2nd arrival -> fires topology(A,B)). The
  preload sel field writes only fixed 0x0/0xFFFFFFFF patterns, NOT cmd_data.
- fpga/zone_adder.tcl (silicon, existing bitstream): same sequence on cell 0.
  Topology in RECONFIGURE low bits: XOR=0x0BC AND=0x007 OR=0x024, base 0x52800800.

Adder note: a cell does a BITWISE 2-input boolean op across the 32-bit word, so a
single XOR cell = 32 parallel half-adder sum bits, AND cell = 32 carry bits. The
full multi-bit adder (carry propagation / Kogge-Stone) is a multi-cell structure
chained by address — the building blocks (XOR sum, AND carry) are now proven.

Reminder for silicon: only unicell_array.v/unicell_zone.v changed since the proven
bitstream (bus_valid<=!cmd_valid bridge fix + flat CELL_BASE), both no-ops for
zone 0. zone_adder.tcl runs on the CURRENT card with no reflash.

## zone_adder.tcl — rewritten to proven preload+trigger (silicon run #1 failed)
First silicon run of zone_adder.tcl gave out_count=0 on all three sub-tests. Root
cause: it used TWO self-stored arrivals (inject A, then inject B) for arbitrary
operands — the exact pattern shift_primitive_v2.tcl flags as UNPROVEN over ISSP
(no cell fires). Confirmed preload can only load 0x0 (sel=01) or 0xFFFFFFFF
(sel=10), never an arbitrary a_data, so mixed-operand sums can't run over ISSP.

Rewrote zone_adder.tcl to the PROVEN preload->single-trigger pattern:
  CHAIN: OR(0,B)=B ripples (or_chain pattern, default output).
  XOR gate: preload A=0xFFFFFFFF, trigger B=0x0A -> ~B = 0xFFFFFFF5 (genuine flip).
  AND gate: preload A=0xFFFFFFFF, trigger B=0x0A ->  B = 0x0000000A.
  XOR vs AND give different outputs for the same B => topology select proven.
Each sub-test self-contained (own reset) — the earlier run's chain also failed,
likely accumulated state + lingering SET_OUTPUT 0x200 across shared sub-tests.
Sim-verified the gate values (tb_gate): XOR->0xFFFFFFF5, AND->0x0000000A.

No reflash needed (PC restart only drops the JTAG session; bitstream intact).
NOTE: tb_zone_adder.v (sim) keeps the two-inject mixed-operand version (0x0C+0x0A
-> sum 0x6 / carry 0x8) — it proves the adder MATH is correct in RTL. The ISSP
two-arrival limitation is a separate silicon/probe issue, and real multi-operand
arithmetic is where the packed shift adder (packed_shift_adder.py) takes over.

## SILICON PASS: single-zone gate + chain (zone_adder.tcl) — 3/3
Reflashed Unicell-Q.sof from Quartus (PC restart had wiped the volatile SRAM
config — slot-powered Mustang). Re-ran zone_adder.tcl, all PASS on the Arria 10:
  chain   armed=448 out_count=28 out_addr=0x001c out_data=0x00002340  PASS
  XOR ~B  armed=448 out_count=1  out_addr=0x0200 out_data=0xfffffff5   PASS
  AND B   armed=448 out_count=1  out_addr=0x0200 out_data=0x0000000a   PASS
Chain rippled full 28 cells, value intact (chaining + addressing confirmed). XOR
(0xFFFFFFF5) vs AND (0x0000000A) for the SAME B => topology select genuinely works
on the fabric — gates compute, not passthrough. Adder building blocks proven.

REFLASH-FIRST LESSON: Mustang-F100 config is volatile SRAM, powered from the PCIe
slot. Any host power event (restart/sleep/PCIe re-enumeration) drops the design;
ISSP still enumerates the device IDCODE (hardwired) but armed=0 / all reads zero.
Symptom of lost config = armed=0 after a RECONFIGURE that should arm 448. Fix:
reflash Unicell-Q.sof before any silicon session.

PROVEN ON SILICON now: OR chain (28-cell ripple), XOR gate, AND gate, addressing,
preload->single-trigger path.
STILL SIM-ONLY: mixed-operand add 0x0C+0x0A (ISSP two-arrival limit), flat
CELL_BASE / bus_valid (never recompiled - needs Windows node-locked Quartus),
packed shift adder (needs sub-nibble shift).

## Sub-nibble shift primitive (barrel shifter) — sim proven
Replaced the cell's nibble-only shift ladders (bus_data_shifted / computed_shifted)
with a barrel shifter. Encoding stays backward-compatible: shift_amt =
cmd_data[3:0]*4 + cmd_data[5:4], so cmd_data[5:4]==0 reproduces the proven nibble
shifts exactly, and [5:4]=1..3 adds the sub-nibble bits the packed KS adder needs
for spans 1 and 2. Range 0..31 bits.
Sim proof (tb_shift, shift_out on A=0xFFFFFFFF): >>1=0x7FFFFFFF, >>2=0x3FFFFFFF,
>>4=0x0FFFFFFF, >>8=0x00FFFFFF, >>16=0x0000FFFF, >>5=0x07FFFFFF. All pass.
Regressions green: zone_chain fires=15, zone_inject out=0x01002340, zone_adder OK.
RTL-only (not recompiled to .sof yet) — silicon still has nibble ladder until reflash.

## DESIGN WALL surfaced — shift amount is coupled to the data value
Running the packed adder as a fabric STRUCTURE (not just the primitive) hits two
things the sub-nibble shift alone does not solve:
1. shift_amt lives in cmd_data[5:0] — the SAME 32-bit field as the data value on a
   shift_IN inject. So a LEFT shift (shift_in_en) of an ARBITRARY value collides:
   the value's low 6 bits ARE the shift amount. shift_OUT (right) is clean because
   the value sits in a_data (PASS_A) and the amount rides the ignored trigger B.
   But the packed KS prefix uses LEFT shifts (G << span) on arbitrary words.
2. shift is TRANSIENT (per-command), not stored per-cell. Autonomous cell-to-cell
   chain flow (or_valid->bus) carries no command, so a chain cell can't apply a
   per-cell shift on data passing through it.
=> To run the 22-cell packed adder as a structure, the shift amount should move to
   spare cmd_bus bits (decoupling it from the data word) AND/OR become a stored
   per-cell config field (so each SHL cell holds its span). That is a command-
   encoding design decision — flagged for Alan, not guessed. The primitive is in;
   the orchestration needs this next.

## Command-emit cell — the fabric can command itself (root hole closed)
Root problem surfaced: cells only DRIVE the data bus (out_addr/out_data/out_valid);
nothing in-fabric drives cmd_bus/cmd_data/cmd_valid — those are external-pin-only.
So "the controller generates commands" was circular (Shore/tiles ARE cells). And
making cells emit commands does NOT make them ALUs *provided the command content
arrives as data*: the cell holds no program flow, the richness (opcode/gating/auth)
is assembled as data upstream, ordering is the fabric topology.

DESIGN (Alan): command-emit is a CELL TYPE, not a new latch bit (cmd_latch is full,
all 32 bits allocated). Reserved topology code TOPO_COMMAND_EMIT=0x3C0 (outside the
gate space 0x000..0x0BC). An emit cell on fire drives a_data -> cmd_bus and
output_address -> cmd_data (the target), instead of a gate result onto the data bus.
Auth is the cell's own stored auth_mask (nothing transmitted in). The trigger is the
SECOND data arrival (value ignored) — so the command lands in sync with the data
wave that feeds the commanded cell; ordering solves itself via tree placement.
Command-emit is sparse/local (only transient cells need it; the rest just flows).

RTL (unicell.v): added outputs cmd_emit_bus/cmd_emit_data/cmd_emit_valid + a
cmd_emit buffer mirroring out_buf. On new_data, is_command_cell routes to the
emit buffer (a_data, {0,output_address}) instead of out_buf; drains on odd_phase.
Existing instantiations leave the new outputs unconnected (no array/zone plumbing).

PROOF (tb_cmd_emit.v): cell0 = COMMAND_EMIT, a_data=SET_LOGICAL(0x0E), output_addr=7;
trigger arrival -> cell0 emits cmd_bus=0x0E cmd_data=0x07; cell1 (its cmd bus fed by
cell0's emit) reconfigures itself: input_addr 1->7, physical_mode 1->0. NO controller
in the loop. Regressions green (zone_chain/inject/adder).

REMAINING (design, not blockers): command-bus ARBITRATION in the zone (multiple
emitters + external pin need cpu>n>s>e>w-style discipline); the emit currently fits
TARGETED commands (cmd_data={0,target}) — commands needing a separate payload need a
second stored word or a second emit cell; and the AUTH lockdown for who may hold
topology 0x3C0 (highest privilege). Conduit is proven; zone-level routing is next.

## v3.0 cell — COMMAND_EMIT opcode + review tightening (external review applied)
Bumped unicell.v to Protocol v3.0 (major: command-emit cells). Added the missing
opcode (external review caught that nothing set topology 0x3C0):
  CMD_TOPO_COMMAND_EMIT_COLD = 0x46 (disarmed), CMD_TOPO_COMMAND_EMIT = 0x47 (armed)
sets topology=0x3C0 the same cold/armed way as the other CMD_TOPO_* presets. Proven:
opcode 0x47 turns a cell into an emitter and tb_cmd_emit passes via the opcode path
(cell1 addr 1->7, phys 1->0). Topology 0x3C0 via RECONFIGURE still works too.

Review points applied (the relevant ones):
- group_tag documented in BOOT_COMMIT header (cmd_data[31:24] = gate-filter group).
- bus_hit/cmd_valid time-multiplex rule made explicit ("commands and data are
  time-multiplexed, not concurrent; a same-cycle command suppresses the fire").
- shift comment unified to bit-granular (sub-nibble) in the v3.0 header note.
- emit-path SECURITY comment: a_data only writable under auth_ok; any future
  raw-write-to-a_data opcode must stay auth-guarded.
- dbg_armed clarified (= start_flag only, not full fire-readiness).
- ARRAY_RESET / COMMAND_EMIT documented in header.
Deferred (optional niceties, noted not done): ENABLE_COMMAND_EMIT parameter to
strip the emit path for tiny fabrics; dbg_is_command_cell scan bit. Both are array-
port plumbing; worth doing when the zone-level emit routing is built.

Docs: added "Command-Emit Cells \u2014 The Fabric Commands Itself (v3.0)" section to
ARCHITECTURE.md (root problem, mechanism, why-not-an-ALU, auth, what it unlocks,
open design surface: arbitration / payload-vs-target / auth lockdown).
Regressions green: zone_chain, zone_inject, zone_adder, cmd_emit (opcode + RECONFIGURE).

## Command-emit ROUTED through the fabric (v3.0) — silicon-ready
Wired the emit path through the hierarchy so a COMMAND_EMIT cell actually commands
other cells (previously the emit outputs dangled in the array):
- unicell_array.v: collect each cell's cmd_emit_*; FIRST-CUT priority arbiter
  (lowest index wins, simultaneous emitters dropped — real queue/fairness is a
  later decision); winner muxed into an EFFECTIVE command (eff_cmd_bus/data/valid,
  eff_cpu_addr) that drives the same targeting/decode as a host command; emit_count
  counter output.
- unicell_zone.v: emit_count passthrough.
- top_arria10.v: z_emit[16], .emit_count on all 16 zones, total_emit aggregation,
  connected to issp_host.
- unicell_issp_bridge.v: emit_count input; readable via the EXISTING snap_armed mux
  at selector 3 (src_cpu_bus[1:0]==3) — NO probe-width change, NO IP regen.

SIM PROOF (tb_zone_emit.v): cell0=COMMAND_EMIT (opcode 0x47), a_data loaded via
CMD_SWAP_AB (ISSP-friendly, no two-arrival), single trigger -> cell0 emits
SET_LOGICAL to cell5; cell5 reconfigures (phys 1->0), cell6 UNTOUCHED (targeting
works), emit_count=1. Regressions green (zone_chain/inject/adder).

SILICON: fpga/zone_emit.tcl — configures cell0 emitter, SWAP_AB-loads a_data,
triggers, reads emit_count via probe selector 3. emit_count>0 = fabric commanded
itself on the Arria. (Probe only surfaces cell0, so emit_count is the silicon
observable; full target-reconfigure is sim-proven.)

REBUILD SET (Windows Quartus): unicell.v, unicell_array.v, unicell_zone.v,
top_arria10.v, unicell_issp_bridge.v. All elaborate clean (only external issp/
uart_bridge IP unresolved in the iverilog sandbox). This bitstream tests BOTH
sub-nibble shift AND command-emit. After this passes on silicon, the Verilog truth
includes the fabric commanding itself -> VM/compiler/composer/Trix re-cost + rewrite.

## v3.1 cell — edge model removed, command-cell flag on bit 10
Settled change (the sure thing, landed with regression proof):
- EDGE MODEL REMOVED entirely. The pos/neg-edge path is gone; the latched
  two-arrival model is the only model. Deleted: edge_mode wire, edge_detected,
  prev_data reg (+reset +update), the edge branch in input_val and new_data, the
  !edge_mode gate on first-arrival store. invert_out STAYS (real standard-mode
  output invert at drain); only its edge-polarity use went.
- COMMAND-CELL FLAG moved to cmd_latch[10] (the freed edge_mode bit):
  is_command_cell = cmd_latch[10] — a single-bit tap, NO comparator. Sits directly
  above topology[9:0]. The topology==0x3C0 comparator (448 of them) is deleted.
  TOPO_COMMAND_EMIT localparam retired; 0x3C0 no longer special.
- Two writers, both verified: opcode CMD_TOPO_COMMAND_EMIT (0x46/0x47) sets bit 10;
  RECONFIGURE/ICM lays bit 10 in the config word directly (cmd_data[10], with
  start_flag at cmd_data[11]). May become opcode-only later — cell side unaffected
  (detection stays one tap).
Tests: tb_zone_emit PASS via BOTH the opcode path and the direct RECONFIGURE path
(cell5 commanded phys 1->0, cell6 untouched, emit_count=1). Regressions green
(chain/inject/adder); shift 5/5 supported amounts.

NEXT (proposed, test-first — NOT yet built): gating acts on incoming DATA as a
positional mask (0=pass,1=block), gate selects ONE contiguous nibble-aligned field
(contiguity made unrepresentable in the encoding), shifter aligns it (compact-
left/right, wiring-only). Open: mask-on-data as input stage FEEDING the gate tree
vs REPLACING it — the worked packed Kogge-Stone stage decides it (one-operand select
vs two-operand compute). byte-spread (both shift bits) flagged weakest, needs a named
consumer. First artifact is a sim, not a commit.

## v3.1 PROVEN ON SILICON + 64-bit setup-model design settled (session 2026-06-27)

### SILICON PASS (Arria 10 GX660, USB-Blaster, IDCODE 0x02E250DD)
Full 16-zone build fit CLEAN (the barrel-shifter hang is gone): Auto Fit, router
avg 23% / peak 46% interconnect, hold timing met with 1.6% pad. .sof flashed.
- zone_adder.tcl: armed=448, chain out_count=28 @0x001c=0x00002340 PASS;
  XOR(0xFFFFFFFF,0x0A)=0xFFFFFFF5 PASS; AND=0x0000000A PASS. XOR!=AND => topology
  select works on silicon. v3.1 cell (edge removed, comparator removed, bit-10
  command flag, fixed-ladder shifter) came up clean, NO regressions.
- zone_emit.tcl: emit_count 1->5 on probe selector 3. Command-emit routed THROUGH
  the array arbiter, firing on real silicon — fabric commands itself. HEADLINE PASS.
  (Note: emit_count is free-running, not zeroed on array-reset, so read the DELTA;
   armed=0 at start is just pre-arm reset state, not lost config.)

=> v3.0 + v3.1 cell model now stands on TESTED VERILOG TRUTH.

### CELL MODEL SETTLED THIS SESSION (all committed)
- v3.1: edge model REMOVED entirely (latched two-arrival is the only model);
  command-cell flag = cmd_latch[10] single tap (was edge_mode) — deletes the
  448 topology==0x3C0 comparators. Both writers verified (opcode + RECONFIGURE).
- shift reverted to fixed-pattern ladder (constant shifts = free rewiring);
  variable barrel shifter was the fitter-hang cause. Set {1,2,4,8,12,16,20,24,28}.
- shift framing corrected: NOT left/right but IN-shift (always left, before gate)
  and OUT-shift (always right, after gate); two position bits = 4 states
  {none,in,out,both}; both@same amount = edge-TRIM (free band-pass). One shared
  amount in cmd_data[5:0]. KS adder PROVEN to need input-side shift (test in
  tests/design/test_ks_needs_input_shift.py: input 20000/20000 vs output-only 7/20000).
- gating reworked (DESIGN, test-first, NOT built): data mask is a per-NIBBLE
  positional mask (8 bits, 0=pass/1=block) on the INPUT operand, BEFORE the gate
  tree (feeds it, does NOT replace it). Contiguity enforced at LOAD time, not in
  the cell. The old gate_enable/gate_set were a COMMAND group-filter (drift) —
  being dropped (option 2), the cell keeps address targeting only.

### NEXT POINT TO BE DONE — the 64-bit setup-model cut (design DONE, RTL not started)
Design note: docs/design-notes/cmd_latch_64bit.md (canonical).
- cmd_latch grows 32 -> 64. Lower 32 unchanged; upper 32 holds the SETUP that moves
  off the per-fire bus: nibble_mask[7:0]@[39:32], mask_en@[40], shift_amount[5:0]
  @[46:41], in_shift_en@[47], out_shift_en@[48]. 17 used, [63:49] reserved (15 bits).
- Shift + mask become STORED SETUP (written once via opcode/RECONFIGURE), not per-fire
  bus modifiers. A configured cell then fires on a bare trigger. cmd_bus[8:20]
  modifier band is RELEASED. Runtime bus -> opcode + auth; cmd_data -> address/auth,
  carrying setup payload only during a SET_* write.
- Command-word (setup) encoding: two 8-bit opcode slots [7:0]=A, [15:8]=B;
  bit16 = slot A is topology(0)/methodology(1); bit17 = slot B extends methodology
  to 16-bit; bit18 = arm (asserted only on the completing pass). auth = 8 bits
  (DECIDED: keep 8, NOT 11 — lower 32 is full, no reshuffle). Four write states with
  topology written only when bit16=0, methodology only when bit16/17 set — blank-slot
  zero-wipe structurally impossible.
- Pass cost: topology / topology+shift / topology+mask = ONE pass. Only
  topology + (shift AND mask together) = two passes. Never three.
- REQUIRED before RTL: format-version bump + refuse-to-load guard (32-bit artifact
  vs 64-bit cell = silent corruption); ICM serialiser + VM cell model + compiler
  config-word writer all widen to 64. This is the "everything on tested Verilog
  truth" rewrite, now triggered.

### AFTER 64-BIT: lanes (SIMD), design-scoped only
- 3-bit lane field in reserved space: 1x32 / 2x16 / 4x8 / 8x4 sub-lane subdivision,
  affects data flow. ORDER DECIDED: SHIFT-THEN-LANE (full-width shift stays untouched
  and proven; lane control is a cheap post-shift boundary MASK/clear, not 8 shifters).
  Gives TRUNCATE semantics for free; cross-lane carry only in 1x32 mode (which is
  where the add runs, so nothing lost). Keep lanes REGULAR/binary; irregular semantic
  fields (date ymd) stay an interpretation layer, NOT silicon. Boundary muxes may
  DELETE the adder's mask-faked lane separation — prove on one worked KS stage.
- Branch table may collapse into the command-emit primitive (single-pass
  configure-and-arm = "become this then run") — explore later, not now.

### STEPPED ORDER (each proven before the next leans on it)
1. v3.1 silicon  ✅ DONE this session
2. 64-bit setup-model cut  <- NEXT
3. lanes (shift-then-lane SIMD)  <- after 2 is silicon-proven

## Packed-adder-on-silicon attempt — exposed two real blockers (added to design note)
Tried to build the packed KS adder as an ISSP test before the 64-bit cut. Could not
build it on the current command path; the attempt surfaced (now in cmd_latch_64bit.md):
  1. RECONFIGURE(4) is BROADCAST — only SET_INPUT_ADDR(2)/SET_LOGICAL(14) target one
     cell. You can target a cell's ADDRESS but NOT its TOPOLOGY. So a heterogeneous
     21-cell circuit can't be configured via commands (each RECONFIGURE overwrites all).
     => NEW REQUIREMENT on the cut: SET_* setup opcodes must be per-cell TARGETABLE.
        Without it the fabric can't self-reconfigure into a heterogeneous shape, which
        is what command-emit is for. RECONFIGURE-broadcast is the thing to fix.
  2. Shift amount entangled with operand (shift_amt=cmd_data[5:0]=the inject value's
     low bits). Already fixed by setup model (shift becomes stored config).
  3. Shift itself CONFIRMED CORRECT single-cell: 0x041<<4=0x410, shift_amt=4. The
     fixed ladder is sound. (Multi-cell 0x4100 was the broadcast collision, not a bug.)
CONSEQUENCE: packed adder proves on silicon only AFTER the cut (targetable config +
stored shift). Pre-cut ISSP harness = single-cell/uniform only. Strong evidence FOR
the cut — its two blockers are exactly what the setup model removes.
RUNNABLE NOW on the flashed bitstream: shift_diag_v3.tcl (single-cell shift on silicon).

## Per-cell TARGETED config — the broadcast blocker FIXED (array + cell)
Implemented the targeting fix the packed-adder attempt demanded. Now ANY command
can target a single cell:
  cmd_bus[8]    = target_en   (0 = broadcast as before, 1 = targeted)
  cmd_bus[16:9] = target_addr (the reclaimed gate_enable/gate_set bits)
The cell's old gate_match command group-filter is REMOVED (option-2 reclaim done in
the cell too) — the cell now just obeys the array's cmd_valid; the array does all
address gating. So the reclaimed bits become a real per-cell target instead of a
vague group filter.
PROVEN (sim): targeted RECONFIGURE cell0->XOR(0x0BC), cell1->AND(0x007), cell2
untouched — two DIFFERENT topologies on two cells, impossible this morning. Broadcast
(target_en=0) still reaches all; ALL regressions green (chain/inject/adder/emit).
Files changed: unicell.v (gate_match/group_tag removed), unicell_array.v (target
decode + cell_cmd_valid gating). Needs a REPROGRAM. Silicon test: fpga/zone_target.tcl
(targeted cell0->XOR, then target cell1->AND, confirm cell0 still XOR = exclusion).

This is the loader primitive: an ICM file = a list of (target_addr, config) records,
each a targeted RECONFIGURE. Heterogeneous circuits (the packed adder's 21 cells) are
now command-loadable. Separable from the 64-bit cut (targeting, not width); carries
forward unchanged. NEXT after reprogram: ISSP/UART ICM-file streaming on this primitive.

## CMD_LOAD_AT — per-cell targeting done RIGHT (address lane), + canon hardened
Replaced the wrong cmd_bus side-door with Alan's model and made it canon so it can't
drift again.
- CMD_LOAD_AT (opcode 23): the cell's OWN addr_match gates a targeted reconfigure.
  Target on the full-width ADDRESS LANE (bus_addr), config in cmd_data, auth in cmd_bus.
  auth_mask write boot-only (physical_mode). PROVEN sim: cell0->XOR, cell1->AND, cell2
  untouched (tb_zone_target). Security PROVEN (tb_sec): auth_mask=0x5A cell rejects
  unauthed reconfigure, accepts auth-matched. Regressions green (additive).
- Side-door (cmd_bus[8]/[16:9] target) REVERTED earlier this session. gate_match
  command group-filter removed from the cell (option-2 reclaim).
- CANON: docs/ARCHITECTURE.md now carries "Addressing & Command Authority — INVARIANT"
  (one comparator gates both lanes; target on the address lane never the command word;
  auth write-once boot-only; opcodes the only post-boot authority; the cmd_bus-target
  anti-pattern is named + permanently rejected). Also fixed a stale spot: command-emit
  flag is cmd_latch[10] bit tap, NOT topology 0x3C0 comparator.

### DRIFT NOTE (for next session — do not repeat)
The cmd_bus side-door happened because the assistant proposed a NEW targeting path
instead of reaching for the address comparator that already existed. The fix: before
adding any command/auth/targeting mechanism, READ the ARCHITECTURE.md invariant FIRST
and state which existing mechanism the new one duplicates. The address is identity and
is full-width — it never goes in the command word. This is settled; see the invariant.

### NEXT (stepped, each proven before the next)
1. Alan reflashing v3.1 + CMD_LOAD_AT build (unicell.v changed; unicell_array.v reverted
   to broadcast/boot-targeted). Confirm zone_adder/zone_emit regressions on silicon.
2. Bring CMD_RECONFIGURE auth-write under the physical_mode gate (clause 3 everywhere).
3. TARGET LATCH in top_arria10.v + ISSP bridge: SET_TARGET(addr) holds the address lane,
   CMD_LOAD_AT(config) lands on it. = ICM-streaming primitive (two-word pairs, no IP regen).
4. zone_target.tcl on silicon (per-cell config), then ICM-direct streaming, then the
   packed adder becomes loadable on silicon (its 21 heterogeneous topologies).

## TARGET LATCH built (top) — CMD_LOAD_AT transport, ICM-streaming primitive (sim)
The transport that lights up CMD_LOAD_AT on silicon. TOP-ONLY change; cell untouched.
- top_arria10.v: load_target reg + SET_TARGET (opcode 24, cells ignore it) latches
  cpu_data[15:0] and HOLDS it; cpu_addr_w for CMD_LOAD_AT(23) reads load_target, not
  cpu_data — so target (held) and config (cpu_data) never collide. The hold also fixes
  the registered-bus skew for free (address settled between the two pulses).
- PROVEN (tb_top_target.v): ICM stream of (SET_TARGET addr, LOAD_AT config) pairs
  configured cell0->XOR, cell1->AND, cell5->OR through the real latch logic. This is
  the ICM-file primitive: an ICM = a list of (target_addr, config) pairs.
- Silicon test fpga/zone_target.tcl: reads cell-0 cmd_latch via probe view selector 3
  (bridge already exposes dbg0_cmd_latch there). target cell0=XOR -> latch 0x0BC;
  target cell1=AND -> cell0 latch STILL 0x0BC (exclusion). NEEDS A REFLASH (top changed).
- Canon updated: ARCHITECTURE.md invariant status — target latch DONE(sim), was TODO.

### NEXT
1. Reflash with the target-latch build (top_arria10.v changed; cell/array unchanged
   from the CMD_LOAD_AT flash). Run zone_adder/zone_emit (regression) then zone_target.
2. Then ICM-file streaming over UART/ISSP (loop (SET_TARGET,LOAD_AT) pairs from a file).
3. Then the packed adder loads as a heterogeneous ICM -> silicon proof of the 22-cell adder.
4. Still open: bring CMD_RECONFIGURE auth-write under physical_mode (clause 3 everywhere).

## SILICON PASS — target latch + CMD_LOAD_AT per-cell config on the Arria 10
Reflashed with the target-latch build; all three tcls green on hardware:
- gate+chain: chain out_count=28, XOR=0xFFFFFFF5, AND=0x0000000A (XOR!=AND) — PASS
- command-emit: emit_count 1->5 — PASS (no regression from the top change)
- zone_target (NEW): LOAD_AT cell0=XOR -> cell0 latch=0x0BC PASS; then LOAD_AT cell1=AND
  -> cell0 latch STILL 0x0BC PASS. Per-cell config + EXCLUSION proven on silicon.
=> CMD_LOAD_AT + target latch move from sim-proven to SILICON-PROVEN. The morning's
   broadcast blocker is gone on hardware: addressing is the gate, a command to cell 1
   cannot disturb cell 0. Bottom level of the addressing hierarchy proven on the die.

NEXT (unchanged): ICM-file streaming (loop (SET_TARGET,LOAD_AT) pairs, offset-native per
the relocatable-models canon) -> packed adder as first heterogeneous ICM on silicon.
Loose end: CMD_RECONFIGURE auth-write under physical_mode (clause 3 everywhere).
