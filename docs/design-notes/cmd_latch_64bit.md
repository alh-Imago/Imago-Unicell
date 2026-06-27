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
