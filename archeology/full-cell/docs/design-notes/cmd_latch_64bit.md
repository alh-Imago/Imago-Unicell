# cmd_latch — proposed 64-bit map (setup model)

Status: DESIGN NOTE, not yet RTL. Format-version bump (32 -> 64) with a hard
refuse-to-load guard required before this lands.

The driver: shift and nibble-mask move from per-fire BUS modifiers to stored
SETUP. A configured cell then fires on a bare trigger — no modifier stream on the
bus. The cost is stored state per cell, which is why this is a deliberate
die-scale decision. The map below shows it costs only **17 of the upper 32 bits**,
leaving 15 reserved — so a 64-bit word is mostly headroom, not need.

## Lower 32 — UNCHANGED (existing fields)

    [9:0]   topology       NOR gate selection (wires straight to gates)
    [10]    command_cell   1 = command-emit cell (single-bit tap, no comparator)
    [18:11] auth_mask      8-bit security token
    [19]    output_set     1 = output address configured, cell may fire
    [20]    latch_A_dis    disable A latch store (PASS(B) effect)
    [21]    latch_B_dis    disable B arrival trigger (PASS(A) effect)
    [22]    start_flag     1 = armed and listening
    [24:23] dtype          00=NUMERIC 01=SIGNED 10=ALPHA 11=DATETIME
    [25]    invert_out     invert computed output
    [26]    latch_in       hold a_arrived after firing (single-arrival re-fire)
    [27]    priority       high-priority scheduling
    [28]    trace          log every fire
    [29]    breakpoint     halt array on fire
    [30]    one_shot       fire once then disarm
    [31]    loop_back      feed output back as next a_data

## Upper 32 — NEW (setup that moved off the bus) + reserved

    [39:32] nibble_mask[7:0]   per-nibble PASS(0)/BLOCK(1), applied to the input
                               operand on the way into the gate. Contiguity is a
                               LOAD-TIME guarantee (loader only emits contiguous
                               runs when shift is used); the field itself can hold
                               any pattern for plain positional masking.
    [40]    mask_en            1 = nibble mask active
    [46:41] shift_amount[5:0]  0..31 bits.  [44:41] = nibble count x4,
                               [46:45] = sub-nibble remainder. One shared amount.
    [47]    in_shift_en        shift input LEFT  by shift_amount, before the gate
    [48]    out_shift_en       shift result RIGHT by shift_amount, after the gate
    --------------------------------------------------------------------------
    [63:49] RESERVED (15 bits) expansion runway — see candidates below

Upper-half usage: 17 bits used (32..48), 15 reserved (49..63).

## Command-word encoding (setup writes) — cmd_bus

A setup write carries TWO 8-bit opcode slots plus control. Bit 16 says what slot A
means; bit 17 extends the methodology write to a second slot. This is the same
reinterpret-the-field-below trick as command_cell: one bit changes what the slot
beneath it means, no second decoder.

    cmd_bus
    [7:0]    opcode A          slot A op
    [15:8]   opcode B          slot B op
    [16]     A_is_methodology  0 = slot A -> topology (lower 32)
                               1 = slot A -> methodology (upper 32)
    [17]     B_to_methodology  1 = slot B also feeds methodology (extends to 16-bit)
    [18]     arm               asserted ONLY on the pass that completes the cell
    [29:19]  auth_token        11 bits
    [30]     spare
    [31]     spare

    cmd_data
    [31:0]   payload for an arbitrary (non-preset) write of a 32-bit latch half

### The four write states ([16][17])

    [16][17]
     0  0   topology only            slot A -> topology; methodology untouched
     0  1   topology + methodology    A -> topology, B -> methodology (8-bit)
     1  0   methodology, lower 8 only  A -> methodology; upper 8 ignored
     1  1   methodology, 16-bit        both slots -> methodology

Guard: topology is written only when [16]=0; methodology only when [16]=1 OR [17]=1.
A pass never zero-wipes a half it did not intend to write (the blank-upper-slot
contention is structurally impossible).

### Pass-cost ladder

    topology only ............................... 1 pass   (0 0)
    topology + shift ............................ 1 pass   (0 1, B = shift preset)
    topology + mask ............................. 1 pass   (0 1, B = mask preset)
    topology + BOTH shift AND mask .............. 2 passes (16-bit methodology needs
                                                  both slots, leaving none for
                                                  topology -> topology first, then
                                                  1 1; arm on the second)

So the ONLY cell that needs a second pass is one needing shift AND data-gating
together. Everything else — the vast majority — configures and arms in one command.
Fabric-driven reconfig is therefore one command cell in the common case, two only
for the shift+mask cell. Never three.

### Arm rule

Bit 18 (arm) is INDEPENDENT of bits 16/17. It is asserted on whichever pass leaves
the cell fully configured — the last meaningful write — not tied to any one row. A
topology-only cell arms on its single pass; a shift+mask cell arms on its second.
Half-configured cells never arm (the BOOT_COMMIT "configure quiet, arm last" rule).

### Auth width — DECISION NEEDED (the one open snag)

Bus auth_token sits at [29:19] = 11 bits, but that width is an artefact of what was
left on the bus, not a need for 11 bits of token. The latch auth_mask is 8 bits, and
the lower 32 is FULL — there is no room to widen auth_mask to 11 in place (it would
push output_set/latch_dis/start_flag/dtype up by 3 and cascade the whole flag band).

Two clean resolutions, pick one:
  (a) Keep auth 8 bits on BOTH sides. auth_token occupies [26:19], bus bits [29:27]
      join the spares. No latch change, no reshuffle. Cleanest. Default unless more
      token space is genuinely wanted.
  (b) Widen auth_mask to 11 — requires reshuffling the lower-32 flag band (or moving
      the 3 extra auth bits into the upper 32). Only worth it if 8-bit tokens (256
      values) are too few at die scale.

A bus token wider than the stored mask is a silent auth bug, so bus and latch MUST
end the same width whichever option is taken.

## What this means for the bus (the payoff)

With shift + mask stored here, the per-fire bus collapses:
  - cmd_bus  -> opcode[7:0] + auth_token[28:21]   (modifier band [8:20] freed)
  - cmd_data -> address / auth only at runtime; carries the SETUP payload only
               during a SET_* / RECONFIGURE write.
The whole cmd_bus[8:20] band (old gate-filter, preload, shift) is released — not
repurposed, released.

## Opcode table impact

256 entries, ~46 used (0-22 core, 48-71 topology presets), ~209 free. Setup needs
only a handful of writer verbs (e.g. SET_SHIFT, SET_MASK) — values ride as
arguments in cmd_data during the write, never as opcodes. No table growth needed.

## Width decision

Used = 49 bits (lower 32 + upper 17). A 48-bit latch can't hold it (needs 17 upper,
has 16) and leaves no headroom. 64-bit is the clean boundary with 15 reserved bits.
So: 64-bit word, but it is mostly expansion room, not consumed need.

## Reserved [63:49] — candidate future uses (15 bits)

  - separate out-shift amount (6 bits) IF an operation ever needs in != out
  - second mask field / mask-on-A-vs-B select (per-operand masking)
  - additional gate/topology modes beyond the current 10-bit field
  - wider auth_mask at die scale
  - cell-role / tile-type tag for loader placement

## Required before RTL

  1. Format-version bump; refuse-to-load guard rejects 32-bit artifacts against a
     64-bit cell and vice versa (wrong width -> silent corruption).
  2. ICM serialiser, VM cell model, compiler config-word writer all widen to 64.
     This is the "everything based on tested Verilog truth" rewrite, triggered here.

## FINDINGS — packed-adder-on-silicon attempt (2026-06-27)

Tried to build the packed Kogge-Stone adder as an ISSP silicon test. It could NOT
be built on the current command path, and the reasons are requirements on this cut:

1. RECONFIGURE IS BROADCAST. Only SET_INPUT_ADDR(2) and SET_LOGICAL(14) target a
   single cell; RECONFIGURE(4) — the only way to set a cell's TOPOLOGY — hits every
   cell. So a heterogeneous circuit (the adder's 21 cells with different topologies)
   CANNOT be configured through commands: each RECONFIGURE overwrites the last, all
   cells end up identical. You can target a cell's ADDRESS but not its FUNCTION.
   => REQUIREMENT: the new SET_* setup opcodes (lower=topology, upper=methodology)
      MUST be per-cell TARGETABLE, unlike RECONFIGURE. Without that, heterogeneous
      circuits are only loadable via ICM, never via commands — and the fabric
      cannot reconfigure itself into a heterogeneous shape (which command-emit needs).

2. SHIFT AMOUNT IS ENTANGLED WITH THE OPERAND. In the transient model shift_amt =
   cmd_data[5:0], but during an inject cmd_data IS the operand, so the shift control
   rides the data's low bits (verified: B=0x041, B[3:0]=1 -> shift 4 -> 0x410,
   shift_amt=4 correct, but the amount and the value are the same field). Clean
   per-stage shifts are impossible while shift is a transient bus modifier.
   => Already resolved by the setup model: shift becomes STORED config (upper latch),
      set once per cell, decoupled from the per-fire operand.

3. SHIFT ITSELF IS CORRECT. Single-cell: 0x041<<4 = 0x410, internal shift_amt=4.
   The fixed-pattern ladder is sound. (The earlier 0x4100 was the broadcast collision
   double-shifting, not a shifter fault.)

CONSEQUENCE FOR THE ROADMAP: the packed adder proves on silicon only AFTER this cut,
when (a) SET_* config is targetable per cell and (b) shift is stored setup. It is NOT
provable on the current ISSP harness. Pre-cut, the ISSP harness can prove single-cell
/ uniform behaviour only (shift primitive, gates, chain, command-emit — all done).
This is strong evidence FOR the cut: the model's two blockers are exactly what it fixes.

## TARGETING + SECURITY MODEL (folds into this cut)

The packed-adder attempt exposed that RECONFIGURE broadcasts. A first fix put a
target in cmd_bus[8]/[16:9] — REVERTED, because the address must be full-width on
its own lane, not crammed into spare command bits (it would not scale past a toy
zone). The correct model, to be built as part of this cut:

ONE comparator, addressing not "targeting":
  - The cell's existing address comparator (addr_match) gates EVERYTHING. On a cycle
    where the address lane matches, the cell looks at both lanes:
      data lane    -> load / fire (run-time data, as today)
      command lane -> if auth_ok, act (reconfigure / address-load); else ignore
  - Address and payload arrive TOGETHER (one event, two lanes), sampled on the same
    cycle. Data-event and command-event are mutually exclusive in a cycle (the
    existing time-multiplex), but address is never separated from its payload.
  - The target rides the ADDRESS LANE at full width (scales to 32/128-bit), NOT the
    command word. Command cells emit (output_address -> address lane, config ->
    command lane) — exactly what a host write does. The address never shares a word
    with the config, so it never has to fit in the latch.

SECURITY MODEL (the reason for the above — must be preserved):
  - auth_code is WRITE-ONCE at boot. The data-bus route into the auth latch is open
    ONLY in physical_mode; when the cell leaves boot (physical_mode -> 0) that route
    CLOSES PERMANENTLY. After boot, nothing can set or change a cell's auth.
  - Post-boot, the ONLY authority over a configured cell is an auth-verified OPCODE.
    There is no side door: the data bus carries values, never config. RECONFIGURE is
    a verified command (auth proves legitimacy); topology/config post-boot comes ONLY
    via the opcode set.
  - Address-load is the one post-boot data-path special case: a verified opcode that
    says "this is authorised — take the value off the DATA bus into the in/out address
    latch". Auth in the command word, address value on the data lane (full width).
  - Properties: identity unforgeable (address comparator, boot-set); authority
    unstealable (auth write-once, route closes after boot); action unsmuggleable
    (reconfigure is opcode-only + auth-verified). A running fabric cannot be
    reprogrammed without the boot-established auth code, which is itself unreachable
    after boot.

  => Per-cell targeting "opens up" precisely because of this: once commands are
     addressed via the full-width address lane and gated by the cell's own comparator,
     any cell is individually addressable — heterogeneous config (the 21-cell adder)
     becomes natural, with the security model intact. This is a CUT-ERA build, not a
     2-word-bus hack.

DONE NOW (pre-cut): removed the cmd_bus target side-door; removed the cell's
gate_match command group-filter (the reclaimed bits are free). Regressions green.

## BUILT + PROVEN (sim): CMD_LOAD_AT — address-lane per-cell targeting (opcode 23)

The targeting model is implemented and proven, additive (no existing opcode touched):
  - CMD_LOAD_AT applies config to a cell ONLY if the cell's own addr_match gates it.
    Target rides the ADDRESS LANE (cpu_addr -> bus_addr -> addr_match, full width);
    config rides cmd_data; auth rides cmd_bus. No address crammed into the command word.
  - auth-verified: auth_ok required. auth_mask written ONLY in physical_mode (boot) —
    after boot the data-path route to auth is closed.
  - Timing: the address must lead the command pulse so bus_addr_r is settled when
    cmd_valid is sampled (the registered-bus skew). The load_at sequence drives the
    address for 2 cycles, then pulses the command with the address held.
PROVEN (tb_zone_target.v): cell0->XOR, cell1->AND, cell2 untouched. Regressions green.
PROVEN security (tb_sec): a cell with auth_mask=0x5A REJECTS an unauthed CMD_LOAD_AT
(stays XOR) and ACCEPTS the auth-matched one (->AND). Identity unforgeable, authority
unstealable, action unsmuggleable — all three hold.

### ISSP TRANSPORT GAP (the path to silicon + ICM streaming)
The cell model is correct, but the 2-word ISSP can't drive it directly: top derives
cpu_addr = cpu_data[15:0] (opcode!=1), so target and config collide in cpu_data. The
clean fix is also the ICM-streaming primitive Alan wants — a TARGET LATCH in the top:
  - SET_TARGET(addr): one ISSP pulse latches cpu_data into a target register that
    drives cpu_addr (the address lane) and HOLDS it.
  - CMD_LOAD_AT(config): next ISSP pulse sends opcode+auth+config; the address lane
    still holds the target; the addressed cell loads.
  - Stream an ICM file as pairs of pulses: (SET_TARGET addr, LOAD_AT config) per record.
This keeps the 2-word ISSP (no IP regen), puts the address on the full-width lane (the
latch can be widened to 32-bit later), and gives single-cell programming + general
ICM-direct loading. Build next: target latch in pcie/top_arria10.v + ISSP bridge, then
zone_target.tcl drives SET_TARGET/LOAD_AT pairs.

# ════════════════════════════════════════════════════════════════════════════
# RESOLVED (2026-06-28) — spec settled + datapath variant built (unicell64.v)
# ════════════════════════════════════════════════════════════════════════════

## Auth width — DECIDED: option (a), 8-bit both sides

Auth stays 8 bits on the bus AND in the latch. auth_token remains at cmd_bus[28:21]
(unchanged from the 32-bit cell); auth_mask remains at cmd_latch[18:11]. No reshuffle,
no truncation seam (bus and latch the same width). Reason held over (b): the binding
constraint is the COMMAND BUS, not the latch — the token has to ride the bus to be
checked, and the bus is where spare ran out. Widening the stored mask past what the
token can carry buys bits you can't fill. (Bonus: keeping auth at 8 not 11 returns
TWO bits to the bus spare pool — see budget below.)

## Command word — the two-slot opcode encoding (settled)

The word is TWO INDEPENDENT OPCODE SLOTS, not "topology + methodology payload". Each
slot carries an opcode and the cell acts on it; the two state flags gate which slots
are live this pass; the cell applies BOTH live slots in one transaction. This exists
to minimise config cycles — fully dress a cell in as few passes as possible.

    cmd_bus
    [7:0]    opcode slot A
    [15:8]   opcode slot B
    [17:16]  state flags (see four states)
    [18]     arm        — asserted ONLY on the pass that completes the cell
    [28:21]  auth_token — 8 bits (unchanged position)
    [20:19]  FREED      — was shift_sel; transient shift retired, now stored
    [31:29]  spare
    => 27 bits used, 5 SPARE on the bus (8+8+2+1+8). None pre-committed.

    Four states ([16][17], read as "what is slot A / does B join methodology"):
      00  topology only           A=function/topology; B idle; methodology untouched
      01  function + methodology   A=function; B=methodology  (the common 2-in-1 pass)
      10  function only, B ignored A=function; B slot ignored
      11  both slots methodology   A,B both methodology (two methodologies, one pass)

## Opcode implies payload type — NO selector bit needed (correction)

Earlier draft thought slot B needed a "shift vs mask" selector bit. It does NOT: the
OPCODE in the slot is self-describing (SET_SHIFT vs SET_MASK are different opcodes),
exactly as slot A's opcode says "topology" with no flag. So the slots are self-typed
and the 5 bus spares stay fully reserved — none spent on a selector.

## The one-function / many-methodology rule — ENFORCED GUARD (not a guideline)

A cell runs EXACTLY ONE function (one gate topology — mutually exclusive by physics:
one gate, one output). It can carry TWO OR MORE methodologies at once (shift, mask,
… — they COMPOSE on the operand, they don't compete for the gate). This asymmetry is
the real content of the encoding:
  - Two METHODOLOGY opcodes in the two slots = LEGAL and is the whole point (state 11):
    shift in one slot, mask in the other, both applied, one pass. Collapses the old
    two-pass shift+mask cell to one.
  - Two FUNCTION opcodes (one per slot) = ILLEGAL. A cell can't be two topologies; the
    second would silently clobber the first. The decoder MUST REFUSE such a pass
    (refuse-to-load discipline), not half-apply it. A two-function pass that silently
    keeps the last is exactly the bug that passes every test and surprises in the field.
So: slots compose freely on the methodology side, mutually exclusive on the function
side. The decoder enforces "at most one function opcode across the two slots."

## Pass-cost ladder (unchanged, restated under the settled encoding)

    topology only ............................ 1 pass (00)
    topology + shift ......................... 1 pass (01, B = SET_SHIFT)
    topology + mask .......................... 1 pass (01, B = SET_MASK)
    topology + shift AND mask ................ 2 passes (topology first; then 11 with
                                               SET_SHIFT + SET_MASK; arm on the second)
Only the shift+AND+mask cell needs two passes. Everything else: one. Never three.

## Two-pool budget — bus bits vs latch bits are NOT one budget

These pools have opposite economics; never trade one as if it were the other.
  - COMMAND-BUS spare (5 bits): PER-TRANSACTION EXPRESSIVITY. Cheap to hold, PRECIOUS
    to allocate — every transaction pays the encoding forever. A new FLAG costs a bus
    bit. Keep these as unspent runway; the unforeseeable next feature rides the bus.
  - METHODOLOGY-LATCH spare (15 bits, cmd_latch[63:49]): PER-CELL STORED STATE = AREA
    (15 flip-flops in EVERY cell, die-scale). Cheap to allocate, EXPENSIVE to hold. A
    new methodology FIELD costs latch bits (area) + an opcode (free, table has ~209).
  Rule of thumb: bus bits = expressivity (guard them), latch bits = area (don't carve
  speculatively). Leave both at reserve until a real workload demands a named field.

## Reserved-means-zero — ENFORCED

cmd_latch[63:49] (15 reserved) and any unused upper bits read back zero and a
methodology write must not set them. Enforced, not merely intended — so that when a
reserved bit is later given meaning, no old bitstream has garbage in what becomes a
live position. Same instinct as refuse-to-load.

## Build status (2026-06-28)

DONE — datapath variant fpga/verilog/unicell64.v (copy of the proven cell):
  - cmd_latch widened 32 -> 64; upper-half fields wired per the map
    (nibble_mask[39:32], mask_en[40], shift_amount[46:41], in_shift_en[47],
     out_shift_en[48]); reset to 64'h0.
  - STORED shift folded into the existing fixed-pattern ladder as stored-OR-transient
    (stored takes precedence; transient bus path still works — nothing the 32-bit cell
    did breaks). Stored nibble-mask spliced after shift, before the gate (per-nibble AND).
  - Loaded in sim via a PLACEHOLDER opcode CMD_SET_METHOD (op 25), addr_match-gated on
    the held target, cmd_data -> cmd_latch[63:32]. This is NOT the real encoding — it is
    a clean, unambiguous write path so the datapath is testable and synthesisable now.
  - Proven: tb_unicell64.v — stored shift (<<4) and stored nibble-mask (block high 16)
    both land in the latch AND drive the datapath. PASS.
  - Synth-ready: synth ONE zone of unicell64 before any full build — the 64-bit cut was
    always an area decision; this variant is the thing to measure (stored-state cost +
    mask/shift logic) against the 70%-fitter-hang risk, BEFORE committing a die build.

## NEXT (named task, not yet done)

Replace the placeholder CMD_SET_METHOD with the REAL two-slot decoder per the settled
encoding above: read the two flag bits, apply slot A and/or B opcodes, write topology
from A and methodology from A/B per the four states, arm on the arm bit, and ENFORCE
the at-most-one-function guard. The datapath underneath is already proven and does not
change — this is decode logic on a working foundation. Then the loader/serialiser
(Python) format-version bump (32 -> 64) + refuse-to-load guard, then a golden 64-bit
ICM proven on the die BEFORE pointing the compiler at it.

# ════════════════════════════════════════════════════════════════════════════
# RESERVED-BITS EXPLORATION + THE SINGLE-CYCLE CEILING (2026-06-28)
# ════════════════════════════════════════════════════════════════════════════

## What the 15 reserved bits are FOR

They are an exploration runway: try a new methodology while it is still just a
RECOMPILE — no format break, no bus change, opcode is free. Add the field in the
reserved range, wire a stage, synth, measure. That is the intended workflow. Any idea
that comes to mind gets cheaply tested here. BUT every candidate is costed on TWO axes,
and the second is the binding one:
  1. BITS  — latch area (a few flip-flops/cell, die-scale). 15 to spend. Rarely the limit.
  2. DELAY — combinational depth added to the cell's operand pipeline. THIS is the limit.

## The methodology stack is an INTERNAL pipeline that MUST stay single-cycle EXTERNALLY

Inside the cell the methodologies are ORDERED stages on one operand:
    lane-assemble -> shift -> nibble-mask -> [GATE] -> out-shift
Order is fixed and load-bearing: lane-then-shift != shift-then-lane. Lanes are operand
CONSTRUCTION; shift/mask are operand PROCESSING — so lanes go FIRST (assemble the word,
then process it). Any new stage must declare its fixed position in this pipeline.

From OUTSIDE the cell, all of this must still look like ONE FIRE — a single cycle. That
is the contract the whole fixed-latency fabric rests on: a cell is a known, fixed
latency (one tick), and compile-time timing closure depends on it. The stages are
combinational, so each one ADDS PROPAGATION DELAY between operand-in and gate-out.

### THE CEILING (hard)
The sum of stage delays + the gate + the emit path must fit inside ONE clock period.
Layer too many methodologies and the cell's combinational path exceeds the period — it
MISSES THE CYCLE. That is not a graceful degrade: it is a timing-closure failure, and
the dangerous form is the one that "passes" a loose sim and fails on silicon (the
inject-skew class). So:
  - The number of methodologies a cell can apply AT ONCE is bounded by the TIMING
    BUDGET, not by the 15 bits. Bits are plentiful; nanoseconds are not.
  - Every reserved-bit candidate must be SYNTH-TIMED, not just bit-counted, before it is
    trusted. Measure the cell's worst-case path with the stage enabled.
  - This is a core reason to synth ONE zone of unicell64 first: it establishes the delay
    headroom — how much pipeline budget is left for lanes and future stages — before any
    die build commits to a stack depth.

### Escape valve (deliberate, not default)
A cell too heavily dressed to close in one tick COULD become a known multi-cycle cell
(latency = a compile-time-known integer >1), which preserves determinism the same way a
bridge's declared latency does — known latency is the invariant, not one-tick latency.
But this adds per-cell latency tracking to the timing model and the compiler, and a
multi-cycle cell is SLOWER, so it is a deliberate exception for density-worth-the-latency
cases ONLY. Default stance: keep cells single-cycle; cap the stack to fit one period;
treat multi-cycle dressed cells as an explicit, compiler-accounted choice, never a
silent fallback.

## Lane stage — reserved-bits candidate (costed, ordered, NOT yet RTL)

A splice/merge stage that assembles the operand from two halves — the natural inverse of
chunked compute (reassemble 32-bit chunks; pack two 16-bit results for transport). Cheap:
it is rewiring, not logic.
  - COST: ~3-4 latch bits (lane mode + optional split point) + 1 opcode. Leaves ~11 bits.
  - ORDER: FIRST in the pipeline (operand construction precedes processing).
  - MODES: by-source splice (low from addr X, high from addr Y) is the DEFAULT — order-
    insensitive, bridge-safe, composes freely with shift+mask anywhere. The by-ARRIVAL
    splice (low from first arrival, high from second) makes arrival order load-bearing —
    fine intra-die, a latent bug across any variable-latency boundary — so it carries an
    INTRA-DIE-ONLY flag and must never straddle a bridge.
  - With lanes in, a cell could apply three composable stages in one fire (lane + shift +
    mask) — a small configurable operand datapath in front of the gate. Subject to the
    single-cycle ceiling above: three stages only if they close in one period (synth says).

## Workflow rule (for any future methodology idea)
Add field in reserved range -> wire stage at its fixed pipeline position -> SYNTH-TIME it
-> if it closes in one period, keep; if not, it is a multi-cycle exception or it is cut.
Explore freely in bits; respect the clock. Reserved-means-zero holds until a stage ships.

# ════════════════════════════════════════════════════════════════════════════
# MEASURED: standalone cell synth (2026-06-28) + zone-synth harness + the
#           "combine via opcodes, not new depth" rule
# ════════════════════════════════════════════════════════════════════════════

## Standalone cell synth — the cost of the cut (Arria 10 10AX066H2F34E2SG, Quartus 25.1std)

Both synth'd identically (all ports pinned to I/O, no virtual pins — so the ABSOLUTE
fmax is I/O-distorted in BOTH; the DELTA is the honest signal).

                 ALMs    Registers   Fmax (standalone, I/O-distorted)
    unicell      513     378         291.29 MHz
    unicell64    531     394         246.79 MHz
    delta        +18     +16         -44.5 MHz  (~-15%)

Read: AREA is a near non-event — +18 ALMs (~3.5%) and +16 registers per cell (the
~17 stored methodology bits made concrete). Across 448 cells that is ~8k ALMs / ~7k
registers on a 251,680-ALM part already <20% used — area is NOT the constraint.
TIMING is where the cut lands — ~0.6 ns extra combinational depth through the operand
pipeline (stored-shift mux + nibble-mask AND), a ~15% standalone-fmax drop. 247 MHz
standalone is still far above any realistic fabric clock, so margin was SPENT, not
exhausted — but the direction is the early-warning instrument: each future stage spends
more of the same budget.

CAVEAT: absolute fmax is I/O-pinned, NOT the in-fabric number. Real operating fmax is a
zone-level question (wired-OR bus + inter-cell routing in the path) and will be lower.
Use top_zone_synth.v for that.

## Zone-synth harness — for the REAL in-fabric fmax/fit

fpga/verilog/top_zone_synth.v : one zone with REGISTERED I/O (flop -> zone -> flop, so
the critical path is fabric-internal not I/O), minimal pins, all outputs reduced to one
registered bit (fitter can't optimise the fabric away). Parameter CELL64 selects:
    CELL64=1 -> unicell_zone64 (variant)    <- the thing to measure
    CELL64=0 -> unicell_zone   (proven baseline, apples-to-apples)
Variant chain is SEPARATE files (unicell64.v / unicell_array64.v / unicell_zone64.v) so
the proven unicell.v/_array.v/_zone.v and ALL their testbench hierarchy paths are
UNTOUCHED. Files: top_zone_synth.v + the three *64.v + the three proven files.
Set top-level = top_zone_synth; synth CELL64=1 and CELL64=0 at identical settings; the
fmax/ALM delta is the real zone-level cost. (Unify the *64 variants back into the proven
files via a parameter only once the variant is the chosen silicon cell.)

## DESIGN RULE (Alan, 2026-06-28): expressivity via OPCODE COMBINATIONS, not new depth

The timing delta above is a real, cumulative cost. Therefore future additions must
ENHANCE the existing stages, not pile on independent combinational depth:
  - The three stages (lane, shift, mask) are the fixed operand pipeline. Hold the line
    at that depth — the cell stays within its current (single-cycle, ≤2-cycle headroom)
    timing envelope.
  - New CAPABILITIES come from SPECIAL OPCODES that invoke predefined COMBINATIONS of
    those three existing stages (and the gate), NOT from new hardware stages. An opcode
    is free (≈209 table slots); a combination reuses hardware already in the path, so it
    adds ZERO depth. This mirrors the two-slot encoding: compose opcodes, don't deepen
    silicon.
  - So "use shift + mask + lane together, or some specific combination" becomes a named
    opcode-setup, and the cell remains within the two-cycle max currently held. Depth is
    frozen; expressivity grows in the (free) opcode space.
  - Any proposal that would add a FOURTH combinational stage must be synth-timed and is a
    multi-cycle exception or a cut — never a silent depth increase.

## STAGE 2 FINDING (structural): slot A collides with the outer opcode selector

Building the two-slot decoder surfaced a genuine encoding issue. The decoder lives under
CMD_SET_METHOD (opcode 25), dispatched by the OUTER `case(cmd_opcode)` where cmd_opcode =
cmd_bus[7:0]. But the spec puts SLOT A in cmd_bus[7:0] too — the SAME bits. So when slot A
carries a methodology opcode (e.g. METH_SET_SHIFT_IN=31), cmd_bus[7:0]=31, and the outer decode
dispatches to opcode 31, NEVER reaching the CMD_SET_METHOD(25) handler. States that put a
methodology in slot A therefore fail; states with slot A = topology or methodology-in-slot-B work.

Proven in Stage-2 test: states 00, 01 (mask in B), lane-in-B, arm, auth-protect, and the
wrong-auth guard ALL PASS. Only the shift states (methodology in slot A) fail — exactly the
collision.

THE FORK (needs Alan's decision — command-word structure):
Option 1: slot A is NOT a free opcode field. cmd_bus[7:0] stays the command selector (25 =
  SET_METHOD); "slot A" becomes a methodology-index in a DIFFERENT field, or the topology/first-
  methodology rides cmd_data. Cleaner outer decode, but "two opcode slots" becomes "one opcode +
  structured payload".
Option 2: two-tier decode. Outer opcode 25 means "two-slot word follows"; then slot A [7:0] is
  RE-READ as a methodology/topology op INSIDE the 25 handler — but that requires 25 to be the
  outer opcode, which means slot A can't also be [7:0]. Same collision. Doesn't resolve.
Option 3: move the slots. Outer opcode stays [7:0]=25; slot A = [15:8], slot B = [23:16], flags
  move up. Frees [7:0] as the pure selector. Costs more bus bits (auth would need to move/shrink).
Option 4: slot A IS the outer opcode (no separate 25). A methodology opcode in [7:0] directly
  triggers its own handler; the "two-slot" B + flags ride the upper bits as MODIFIERS on that
  opcode. I.e. there is no CMD_SET_METHOD wrapper — each methodology op is a top-level opcode,
  and [15:8]/[16][17] extend it with a second methodology. This may be the most natural: it
  matches how the cell already works (top-level opcodes), and "compose two methodologies" becomes
  "opcode in A + optional second methodology in B".

Reverted the Stage-2 decoder attempt (kept repo green). Stage 1 (auth relocation) stands proven.
The decoder needs the fork resolved before it can be correct. Recommend discussing Option 4 vs 3.

## RESOLVED (Stage 2): COLLAPSED encoding — self-describing opcodes, ONE validity bit

Alan's insight resolved the slot-A/selector collision AND simplified the spec: the two type-flags
were overkill. If each opcode is self-describing about which latch it writes, the "A is
methodology" flag is redundant. So the wrapper (CMD_SET_METHOD) is REMOVED and:

  [7:0]   slot A opcode  — IS the opcode (dispatched by the outer case directly). Self-describing:
                           a methodology op writes its methodology field; a topology op writes
                           topology. No collision — slot A can't clash with a selector because it
                           IS the selector.
  [15:8]  slot B opcode  — optional SECOND methodology, composed in the same pass.
  [16]    B_valid        — the ONE surviving flag: "slot B holds valid data, decode it" (0 =
                           ignore B). This is the one thing an opcode CAN'T self-describe —
                           whether it is meant to be present vs rubbish/uninitialised.
  [17]    (freed)        — old second flag gone.
  [18]    arm            — transient, arms the cell on the completing pass (KEPT — Alan: important
                           transient flag).
  [29:19] auth_token     — 11-bit (Stage 1).
  [31:30] spare.

Methodology opcodes: METH_SET_MASK(30), METH_SET_SHIFT_IN(31), METH_SET_SHIFT_OUT(32),
METH_SET_LANE(33) — all TOP-LEVEL cases. Each writes only its field [51:32]; NEVER auth [63:53].
GUARD (one-function invariant): slot B may carry ONLY a methodology op; a topology (function) op
in B is refused (no-op) — trivial because opcodes are self-describing.

PROVEN: tb_v3_twoslot.v — 15/15 PASS. A-only mask/shift (incl. the previously-colliding shift-in-
A, now fixed), A+B compose (shift+lane one pass), arm, B_valid=0 ignores B, topology-in-B refused,
auth untouched throughout, wrong-auth rejected. This SUPERSEDES the two-flag four-state design
above (which had the collision + a redundant bit). Simpler, safer, one bus bit reclaimed.
