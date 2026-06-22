# Session Log — 2026-06-22 (Arria 10 inject bring-up: cell + delivery proven in sim, zone addr-skew fix)

## Headline
Silicon now does config + preload correctly (armed=448, output_set=448,
arrived=448, cell0 cmd_latch/addrs all match the oracle). The remaining failure
— DATA_WRITE inject never fires — was isolated end to end with sim-first and
fixed with a one-line zone change. Pending silicon confirmation of the fix.

## The journey (how the inject bug was cornered)
1. First counter run: armed=448 but output_set=0. Built aggregate counters
   (arrived_count/output_set_count) + selector readback — no IP regen.
2. Reordered harness to BOOT_COMMIT -> SET_OUTPUT -> RECONFIGURE (arm last).
   output_set still 0 -> not an ordering issue.
3. Built cell-0 latch readback (uc_dump): routes cell0's dbg_cmd_latch/
   input_addr/output_addr/a_data to the probe under a view selector
   (cpu_bus[2:0]=3 latch view, =4 a_data). unicell.v UNCHANGED (already exposed
   these). After reflash: config + preload PERFECT on silicon, output_addr=0x200,
   cmd_latch=0x0040002c — matches oracle. Stale-build theory dead.
4. Inject: arrived stays 448, a_data unchanged -> bus_hit never asserts at the
   cell. Inject isolated as the sole failure.
5. Built tb_v23_oracle.v: drove the EXACT silicon command words at the current
   cell. SET_OUTPUT lands (output_addr=0x200, output_set=1), RECONFIGURE arms.
   => cell logic + v2.3 encoding correct. Bug is downstream.
6. Read top_arria10 + array gating: SET_OUTPUT broadcasts correctly, cmd_data
   passes through. Delivery code looked correct -> walked back "it's the ISSP
   coms".
7. Built tb_zone_inject.v: drove the host inject through a full zone exactly as
   the top does. IT FIRES in sim (arrived 28->0, out_data=0x01002340 @ 0x200).
   => delivery LOGIC is correct. Silicon no-fire is TIMING.

## Root cause + fix (commit 85468af)
Zone fed the array `cpu_addr` COMBINATIONALLY (line 136) while cpu_data/cpu_valid
go through the registered `ibus`. On silicon the long combinational address path
arrives late at the bus_valid capture edge -> bus_addr stale -> addr_match fails
-> inject silently drops. Sim has no propagation delay, so it always passed
(cell oracle AND zone sim both fired).
FIX (one line): array.cpu_addr <- ibus_addr (the registered cpu_addr the zone
already computes at line 173). Aligns address with data+valid. Also closes the
banked cell-to-cell chaining addr bug. Sim still fires after the change.
This matches Alan's UART-era memory: timing issues, "had to slow down delivery",
"bus halted until cleared", first-cell-frozen-as-buffer during slow loads —
all the same underneath (bus not coherent at the capture edge). The ibus_addr
fix attacks it one layer lower so the bus IS coherent when latched; if it holds,
the multi-cell load may not need the freeze-and-release crutch.

## Commits this session
- c5b8f46  instrument: arrived_count + output_set_count aggregates (no IP regen)
- 471959a  docs: root Python consolidation audit (AUDIT.md)
- 3dcb36f  fix: shift_diag_v3.tcl self-contained (issp_unicell.tcl runs+closes on source)
- b361a42  fix: SET_OUTPUT before RECONFIGURE in harness
- 785e5d5  instrument: cell-0 latch readback (uc_dump) — unicell.v unchanged
- 85468af  fix: array fed registered ibus_addr + tb_v23_oracle.v + tb_zone_inject.v

## Verification assets added (reusable)
- fpga/verilog/tb_v23_oracle.v   — cell-level v2.3 oracle (raw silicon words)
- fpga/verilog/tb_zone_inject.v  — full delivery-path sim (zone->array->cell)
  Both run under iverilog in seconds. Sim-first cornered this bug without a
  rebuild loop — keep this as the default method.

## Repo housekeeping (AUDIT.md, committed 471959a)
76 root .py files -> proposed imago/{vm,compiler,pond,security,trix,server,
examples}. KEY: _core files (shore/ward/sentinel) are on-fabric ICM logic, NOT
dead. compiler trio layered not drifted. One real drift: shore.py vs shore_v2.py.
Moves DEFERRED until post-silicon-verification rebuild (lands each verified
subsystem into its package as it goes -> directory = done/not-done progress bar).
Decisions pending from Alan in the doc.

## Candidate ideas to capture (TODO: create CANDIDATES.md)
- Models are ARTIFACTS not Python programs (thesis, top of list). Python papers
  over what the fabric can't do; silicon forces the rewrite. A model = an ICM.
- Gate-field GATHER: when gating on, repurpose the 8 gate bits as a byte/nibble/
  bit sub-field selector. Tier TBD. Test = VM adder.
- Shift-SCATTER: both L+R shifts active -> spread selected field across 32-bit
  bus on 8-bit boundaries. Rides on the gather front-end.
- Sub-nibble SELECT: current shifts are nibble-aligned (4-bit) and TRUNCATE
  (left=zero top, right=zero bottom) — single-bit isolation is the real gap.
  Cell already has place-in/compute/place-out via shift_in_en/shift_out_en;
  gate-select + shift are on SEPARATE command bits BY DESIGN so one cell can
  select-then-shift in one transaction. Open Q: does the nibble-grouped CLA
  adder need sub-nibble, or does it route nibbles + carries-as-wires? Test = VM adder.
  NOTE: bank, don't build mid-bring-up. Decide the cell primitive SET on paper,
  freeze once, not one-primitive-per-chat (that made the 76-file mess).

## NEXT SESSION — start here
1. Confirm the inject fires on silicon with the zone fix. ONLY unicell_zone.v
   changed (1 line: array .cpu_addr(ibus_addr)). Verify the pulled zone file has
   `.cpu_addr (ibus_addr)` not `(cpu_addr)`. Rebuild (no IP regen), reflash,
   run fpga/shift_diag_v3.tcl. Tell: arrived drops on inject + out_count ticks +
   out_data=0x01002340 @ 0x0200 = whole chain green on silicon.
2. If it fires: minimal multi-cell ICM over ISSP (per-cell config unproven).
   Watch whether the freeze-as-buffer load crutch is still needed.
3. Then: nibble-grouped CLA adder — VM-FIRST. This is the test that promotes or
   kills the candidate cell primitives above (sub-nibble select etc.).
4. Create CANDIDATES.md (above). Rule on AUDIT.md decisions.
5. Banked: full per-cell latch dump (freeze/save read side, step 2);
   shift primitive (X<<4) vectors once plain inject is green.

## Standing notes
- Sim-first is the proven method: tb_v23_oracle (cell) + tb_zone_inject
  (delivery) found this in seconds vs the rebuild loop.
- ISSP build = 6 Verilog files. Pushes go via PAT URL (rotate after).
  git status "ahead N" is a false alarm (pushed via URL not origin); ls-remote
  to confirm.

---
## UPDATE — inject FIRES on silicon (zone fix confirmed) + first chain attempt

INJECT CONFIRMED on silicon (commit 85468af live): config + preload + inject all
green — armed=448, output_set=448, arrived 448->0 on inject, out_count=1,
out_data=0x01002340 @ 0x0200, cell0 cmd_latch=0x0040002c. The ibus_addr timing
fix worked. Full ICM->silicon round-trip for one cell PROVEN. (Ran twice clean.)

OR-CHAIN attempt (or_chain.tcl, commit f47244b) — physical-mode chain (no
BOOT_COMMIT, default addressing input=CELL_ID output=CELL_ID+1, preload A=0,
OR(0,B)=B passthrough):
  RESULT: config+preload good (armed=448, arrived 448 after preload). Inject ->
  arrived drops 448->0 (cells FIRED) BUT out_count=0, out_data stale. So cells
  fired, no output surfaced.
  tb_zone_chain.v (single zone) showed the chain rippling WITH output (fires=15,
  B intact, out_addr advanced) -> SIM AND SILICON DIVERGE in physical mode.

ALAN'S KEY INSIGHT (the lead to chase): after BOOT_COMMIT cells switch from
PHYSICAL address (CELL_ID) to LOGICAL address (input_address), AND auth_mask
changes. By skipping BOOT_COMMIT the chain stays in physical mode -> the fire
emits into an address space the output-collection/probe isn't watching, or hands
off to unaddressed space. "Shouting at the wrong address." The physical-mode
shortcut for chaining is suspect.

NEXT SESSION — start here:
1. Sim-first: in tb_zone_chain, instrument WHERE the output goes in physical mode
   vs whether out_valid/out_addr actually leave the zone. Confirm the divergence
   (sim surfaces output, silicon doesn't) and find the physical-mode output path
   gap (likely another sim-vs-silicon timing/addr issue like ibus_addr).
2. Reconsider the chain the PROPER way: BOOT_COMMIT -> RUN mode -> per-cell
   LOGICAL addresses (targeted SET_LOGICAL/SET_INPUT by CELL_ID in boot), since
   broadcast BOOT_COMMIT sets all input=same (parallel). This per-cell logical
   addressing IS the real "per-cell config" milestone. Default output=CELL_ID+1
   gives the chain once logical input addrs are set per cell.
3. out_count/out_data probe fields show stale residuals between runs (fresh
   showed out_count=1 out_data=0xffffffff) — confirm the collection actually
   clears/counts in chain mode.

STATUS: single-cell ICM->silicon round-trip PROVEN. Multi-cell chain: cells fire
in a chain but output doesn't surface in physical mode — addressing/auth-after-
boot is the open thread.
