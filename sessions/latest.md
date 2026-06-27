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
