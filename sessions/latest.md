# Session Log — 2026-06-23 — RESOLVED: within-zone OR-chain works on Arria 10 (28 cells, value intact). Root cause of the "no output" was a STALE-SNAPSHOT readback bug in or_chain.tcl, not the fabric.

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
