# New TODO items — 2026-05-17 session
# To be merged into MIGRATION_TODO.md

---

## EXPIRED / SUPERSEDED by silicon validation (2026-05-17)

The following MIGRATION_TODO items are now resolved by the Verilog work
this session. Mark as [x] in MIGRATION_TODO.md:

- [x] CELL SIMPLIFICATION — Command latch redesign (2026-05-14)
      DONE: command latch is 32-bit, confirmed on silicon, two-arrival model validated.

- [x] COMMAND LATCH — Final 32-bit map (2026-05-14)
      DONE: full 32-bit map confirmed. See docs/CELL_INTERNALS.md for authoritative spec.

- [x] CELL TYPE FIELD + SYNC_WAIT simplification (2026-05-14)
      DONE: sync_wait bit repurposed as edge_mode (bit 10). Single input_address,
      arrival counting model validated on silicon. input_b_address REMOVED.

- [x] SECURITY — Auth token & Separate Command Bus
      DONE: cmd_bus port added to unicell.v. 11-bit auth token validated on silicon.
      Boot bypass (auth_mask=0) confirmed working. Silent rejection confirmed.

- [x] SYNC_WAIT removed — input_b_address removed from all Verilog
      DONE: unicell.v has single input_address, counts arrivals.
      input_b_address never existed in the new Verilog — not a removal, just
      confirmed it was never needed.

---

## NEW TODO items — 2026-05-17

### TIER 1 — VM migration (next session, strict order)

- [ ] VM: remove input_b_address and receive_b() from unicell.py (all variants)
      Silicon confirmed: single input_address, two arrivals at same address.
      input_b_address is a pre-silicon convenience abstraction — now retired.
      All three variants: unicell.py, unicell-latch/unicell.py, unicell-edge/unicell.py

- [ ] VM: update tick() to use two-arrival model
      First arrival at input_address → stored in a_data, no fire
      Second arrival at same address → fires gate tree on a_data, output emitted
      This is the v1 compat path in the latch model — make it the ONLY path.
      Remove v2 (input_b_address) path entirely.

- [ ] VM: add latch_in mode to unicell.py
      latch_in=1 → a_arrived stays set after firing (single-arrival mode)
      Used for memory cells and counter cells.
      Maps to cmd_latch[26] in the Verilog.

- [ ] VM: add edge_mode to unicell.py
      edge_mode=1 (cmd_latch[10]) → fires on data transition (posedge/negedge)
      invert_out=1 → negedge, invert_out=0 → posedge
      Maps exactly to Verilog edge_mode wire.

- [ ] VM: update cmd_latch field layout to match confirmed 32-bit spec
      Remove old gate_state bit assignments for type/variant.
      New layout: see docs/CELL_INTERNALS.md (authoritative).

- [ ] VM: add cmd_bus port handling to unicell.py
      CMD_RECONFIGURE, CMD_SET_INPUT_ADDR, CMD_SET_OUTPUT_ADDR
      CMD_FREEZE, CMD_RELEASE, CMD_PING
      Auth token check (boot bypass when auth_mask=0).

### TIER 2 — ICM format update

- [ ] ICM format: rename gs field to cmd_latch (or keep gs with new bit layout)
      Decision needed: backward compat (keep gs) or clean break (rename).
      Recommend: keep gs field name, update bit layout, add format_version field.
      See docs/CELL_INTERNALS.md for new 32-bit cmd_latch spec.

- [ ] ICM format: remove inB field (input_b_address)
      Already removed from Verilog. Remove from ICM format spec and loader.
      docs/ICM_FORMAT.md: mark inB as RETIRED.

- [ ] ICM format: add edge_mode and latch_in fields
      These are bits in cmd_latch — no separate fields needed if gs/cmd_latch
      is stored as full 32-bit word. Just ensure compiler sets correct bits.

- [ ] icm_loader.py: update load sequence for new command latch
      CMD_SET_INPUT_ADDR and CMD_SET_OUTPUT_ADDR are separate commands now.
      CMD_RECONFIGURE carries only the 32-bit cmd_latch word.
      Two-step: set addresses, then reconfigure.

### TIER 3 — Compiler update

- [ ] Compiler: update to emit new command latch bit layout
      cmd_latch bits per docs/CELL_INTERNALS.md.
      No more separate input_b_address routing.
      Y-formation: both upstream cells write to same downstream input_address.

- [ ] Compiler: emit CMD_SET_INPUT_ADDR + CMD_SET_OUTPUT_ADDR as separate ops
      Not bundled into RECONFIGURE sequence.
      Order: SET_IN → SET_OUT → RECONFIGURE (arm last).

- [ ] Compiler: update SYNC_WAIT usage
      SYNC_WAIT is now the default two-arrival model — no flag needed.
      edge_mode (bit 10) selects EDGE cell type, not sync_wait.
      Remove GS_SYNC_WAIT from compiler — it's implicit.

- [ ] Compiler: add memory cell patterns
      STORAGE cell: TOPO_PASS + latch_in=1
      LOOP MEMORY:  any topology + latch_in=1 + loop_back=1
      Three-cell memory access pattern: memory + tap + trigger.

### TIER 4 — Composer (stopped working — fix before update)

- [ ] Composer: diagnose why it stopped working
      Last known state: running pre-2026-05-17. Check what broke.
      Run composer.py and capture the error. Fix before any feature updates.

- [ ] Composer: update model library for new cell model
      Remove input_b_address from tile specs.
      Update SYNC_WAIT tile: now implicit (two arrivals = default).
      Add STORAGE, LOOP MEMORY, COUNTER cell types to library.
      Update cell variant field: standard/latch/posedge/negedge (2 bits).

- [ ] Composer: update cell inspector panel
      Remove Input B addr row.
      Add edge_mode selector (STANDARD/POSEDGE/NEGEDGE).
      Add latch_in checkbox (memory/counter mode).
      Add loop_back checkbox.

### TIER 5 — Model library and tile updates

- [ ] model_library.py: remove input_b_address from all tile specs
      Two-arrival model means no second input address.
      Y-formation tiles: both inputs arrive at same address.

- [ ] model_library.py: add memory cell tiles
      STORAGE_CELL:   1 cell, latch_in=1, TOPO_PASS
      LOOP_COUNTER:   1 cell, latch_in=1, loop_back=1
      THREE_CELL_MEM: 3 cells (memory + tap + trigger pattern)

- [ ] gate_states.py: audit and update
      GS_SYNC_WAIT: mark as RETIRED (two-arrival is now default)
      Add: GS_LATCH_IN, GS_EDGE_MODE, GS_LOOP_BACK constants
      These map to cmd_latch bits 26, 10, 31 respectively.

### TIER 6 — ICM portability test (validation gate)

- [ ] Write test_icm_portability.py
      Compile a simple program (NOT gate chain, two-cell AND via Y-formation)
      Load ICM onto iCEBreaker via bridge
      Verify correct execution on silicon
      This proves full stack: Compiler → ICM → Loader → Silicon → correct output
      This is the gate before Kintex-7 work begins.

- [ ] Write test_icm_portability_memory.py
      Configure a STORAGE cell via ICM
      Write a value, verify re-emission
      Write a new value, verify update
      Proves memory cell model works end-to-end.

### TIER 7 — Kintex-7 (after portability test passes)

- [ ] Kintex-7 top-level Verilog (top_kintex7.v or top_arty_a7.v)
      Full 32-bit addresses (not narrowed to 16-bit)
      ENABLE_LATCH_IN=1 (enough cells/timing to support it)
      Multiple pond support (different cell types in different arrays)
      SHIFT_COUNTER_8 tile fits (9 cells available for ring breakout)

- [ ] 32-bit address validation test
      2-3 cells, full 32-bit input_address/output_address
      Verify timing still passes at 24 MHz
      Documents that 16-bit narrowing was iCEBreaker-only constraint.

- [ ] Multi-pond test (latch + edge ponds)
      4 cells latch + 4 cells edge on Kintex-7
      Bridge converts edge output to latch-compatible two-arrival format
      Validates mixed pond model on real hardware.

---

## COMMAND BUS — Updated bit map (confirmed 2026-05-17)

The command bus as implemented in unicell.v (iCEBreaker validated):

```
bits  3-0:   command code
             0 = CMD_NOP
             1 = CMD_DATA_WRITE       (user+system — bus_valid only, not cmd_valid)
             2 = CMD_SET_INPUT_ADDR   (user+system, cell targeted via bits 26:16)
             3 = CMD_SET_OUTPUT_ADDR  (user+system, cell targeted via bits 26:16)
             4 = CMD_RECONFIGURE      (system, auth required, cell targeted via bits 26:16)
             5 = CMD_FREEZE           (system, auth required, broadcast)
             6 = CMD_RELEASE          (system, auth required, broadcast)
             9 = CMD_PING             (anyone, broadcast)
             7,8,10-15 = reserved

bits 14-4:   auth token (11 bits)
             Checked on CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE
             Boot bypass: auth_mask=0 in cell → accept unconditionally, set auth_mask
             Silent rejection on mismatch

bit   15:    raw_addr (1=raw address, host always sets 1)

bits 26-16:  cell_id (11 bits)
             Target cell for CMD_SET_INPUT_ADDR, CMD_SET_OUTPUT_ADDR, CMD_RECONFIGURE
             0x7FF = broadcast sentinel (reaches all cells — FREEZE/RELEASE/PING)
             Array computes (cmd_bus[26:16] == CELL_ID) at synthesis time (zero runtime cost)

bits 31-27:  reserved (not yet implemented)
```

This supersedes the pre-silicon command bus spec in MIGRATION_TODO.md.
See docs/CELL_INTERNALS.md for full authoritative spec.

---

## CELL_INTERNALS.md — Now the authoritative reference

As of 2026-05-17, docs/CELL_INTERNALS.md is the ground truth for:
- Command latch 32-bit layout
- Command bus bit map
- Two-arrival NOR(A,B) model
- Memory cell modes (STORAGE, LOOP, LATCH)
- Three-cell memory access pattern
- Edge_mode and latch_in behaviour
- Multi-pond mixed model architecture
- iCE40UP5K timing history and SB_GB ceiling
- Silicon validation results

MIGRATION_TODO.md command latch sections (2026-05-14 entries) are superseded.
Architecture.md and VERILOG_SPEC.md need updating to reference CELL_INTERNALS.md.

