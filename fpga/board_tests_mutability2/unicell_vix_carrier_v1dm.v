// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// unicell_vix_carrier_v1d.v — the VIX Carrier, "d" variant: real,
// live, incremental reprogramming of the carrier's OWN shared addon
// block (addon_config + shift_fine), decoupled from the atomic
// vix_latch/cfg_valid whole-word commit. Cloned from
// unicell_vix_carrier_v1.v, per points.md #841 -- Alan's own direct
// naming, continuing the same single-letter-suffix convention
// `_v4c` already established (points.md #720): "c" named the
// config-off-shell/carrier-stripped variant of each CORE; "d" names
// this carrier-level DYNAMIC-addon-reconfiguration variant.
//
// Real motivation, not a speculative feature: fp32 ADD's mantissa-
// alignment stage needs a runtime-computed, data-dependent shift
// amount (the exponent difference) applied to the shift addon. Every
// standalone v4 core already has genuine live PROG_ID-driven
// addon_config reprogramming (confirmed directly, adder_cell_v4.v's
// own PROG_ID_ADDON_CONFIG) -- but standalone v4 cores' own local
// addon chains predate shift_fine and don't have it. The carrier DOES
// have real shift_fine hardware (the single shared addon chain,
// `#722`), but -- confirmed directly before writing anything here --
// vix_latch, including its addon_config/shift_fine bits, is
// committed ONLY atomically on cfg_valid; no incremental path
// reaches it at all. This file adds one, mirroring the exact
// PROG_ID pattern already proven on every standalone v4 core, applied
// once at the carrier level instead of once per core -- matching
// Alan's own point: repeating it per core would be exactly the
// wasteful duplication `_v4c` already removed; it belongs here,
// where the addon chain itself now lives.
//
// unicell_vix_carrier_v1.v — the VIX Carrier ("V" for version, "IX"
// for the 9th real core count -- Alan's own naming, deliberately NOT
// continuing the old `unicell_super_v1`-`v8` numbering, since that
// would collide: `unicell_super_v4.v` already exists as an unrelated,
// earlier-lineage file built on the OLD individual core versions
// (`ram_cell_v1`, `adder_cell_v1`, `accumulator_cell_v3`, etc.), not
// this session's own "unified carrier v4" generation
// (`nano_gate_v4.v`/`command_cell_v4.v`/etc.) -- a real naming
// collision found and avoided before any RTL was written, not
// discovered after the fact.
//
// Real, proven ARCHITECTURE reused directly from that old lineage
// (`unicell_super_v1.v`'s own real header, `points.md` #304/#315/
// #317/#319): all 9 real cores physically present simultaneously,
// MUTUALLY EXCLUSIVE -- exactly one active at a time, selected by
// configuration (`core_select`), not synthesis. Same real ISOLATION
// mechanism: every core is always physically instantiated and clocked
// (FPGA fabric has no per-core power gating), but only the SELECTED
// core ever sees genuine `arrived_*`/`cfg_valid`/`program_in`/
// `prog_arrived_in_*` -- every other core's inputs are gated to 0, so
// non-selected cores never capture, never load config, never program,
// never fire.
//
// Real, GENUINELY NEW work beyond the old lineage, not just a bigger
// clone of it:
//   1. Wraps the real per-core CARDINAL CONTROL SHELLS (`#639`/`#645`/
//      `#646`), not bare cores -- `active`/`freeze_in` arrive here as
//      real 4-way cardinal ports and are simply broadcast to all 9
//      shells unchanged (safe: non-selected cores never act on them,
//      since cfg_valid/arrived/program_in stay gated to 0 regardless).
//   2. Real, SAFETY-CRITICAL programming-channel routing the old
//      lineage never had to solve (it predates the whole `PROG_ID`
//      mechanism): `PROG_ID` values COLLIDE across core types
//      (`PROG_ID=0` means `topology` on nano, `downstream_mask` on
//      adder) -- broadcasting one incoming programming word to all 9
//      simultaneously would misconfigure the 8 cores that aren't
//      selected. `program_in`/`prog_arrived_in_*` are gated to the
//      SELECTED core only, exactly the same mutual-exclusion
//      principle already used for `cfg_valid`, just extended to the
//      live reprogramming channel.
//   3. `core_config` widened to 128 real bits (nano's own real
//      `cfg_data` width in this generation), not the old lineage's
//      42-bit union -- a real, meaningful jump, not cosmetic.
//   4. Command's own genuinely NEW external ports (`freeze_out_*`,
//      the drive-side programming channel) -- no other of the 9 cores
//      has anything like this; they reach all the way out to this
//      carrier's own external ports, muxed exactly like everything
//      else, active only when `core_select=SEL_COMMAND`.
//
// VIX_LATCH[159:0] layout -- a deliberately round number with real
// reserved headroom, matching the old lineage's own stated philosophy
// (not packed tight to exactly today's needs):
//   [4:0]     core_select   — 0=nano 1=adder 2=ram 3=compare 4=branch
//                             5=accumulator 6=latch 7=sequencer
//                             8=command, 9-31 reserved (must stay
//                             genuinely extensible, same real
//                             discipline as the old lineage's own)
//   [132:5]   core_config   — 128 bits, UNION not struct: sized to the
//                             single widest real core (nano, 128 bits),
//                             reinterpreted per core_select. Every
//                             core's own real cfg_data layout already
//                             starts at bit 0 of its own space
//                             (confirmed directly against each core's
//                             own RTL before this was built) -- so
//                             core_config[N-1:0] maps onto each one's
//                             own real fields with ZERO reshuffling,
//                             simpler than the old lineage needed for
//                             nano specifically.
//   [159:133] reserved      — 27 bits, genuine future headroom.
//                             points.md #722: 22 of these bits now
//                             hold the real, SINGLE, shared addon
//                             chain's own config (`[154:135]` =
//                             addon_config, 20 bits; `[156:155]` =
//                             shift_fine, 2 bits) -- `[159:157]`
//                             (3 bits) still genuinely unused. See
//                             `#720`/`#722`'s own real history: an
//                             earlier attempt (`#719`) put this same
//                             allocation to a redundant, four-times-
//                             duplicated use; corrected once every
//                             core's own internal chain was genuinely
//                             removed (`_v4c`).
`default_nettype none
`timescale 1ns / 1ps

// GENERATED by tools/make_carrier_subset_v2.py (ledger #1088) from unicell_vix_carrier_v1d.v; cores kept: accum, adder, mul
module unicell_vix_carrier_v1dm #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        DIV_STEPS = 1   // ledger #1077: the division core's quotient bits per clock (build-time; every carrier of a grid is built alike)
) (
    input  wire        clk,
    input  wire         rst,

    // ── Real cardinal control, broadcast to all 9 shells unchanged --
    // safe because cfg_valid/arrived/program_in stay gated to the
    // selected core only, regardless of what active/freeze show. ──
    input  wire         active_in_n, active_in_s, active_in_e, active_in_w,
    input  wire         freeze_in_n, freeze_in_s, freeze_in_e, freeze_in_w,

    input  wire         cfg_valid,
    input  wire [159:0] cfg_data,      // VIX_LATCH, see header

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    // ── Standard RECEIVE-side programming channel -- real, safety-
    // critical: gated to the SELECTED core only (see header point 2). ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    // ── Command's own genuinely new external ports -- meaningful only
    // when core_select=SEL_COMMAND, tied to safe defaults otherwise. ──
    output wire         freeze_out_n, freeze_out_s, freeze_out_e, freeze_out_w,
    output wire         program_out_n, program_out_s, program_out_e, program_out_w,
    output wire [31:0]  prog_data_out_n, prog_data_out_s, prog_data_out_e, prog_data_out_w,
    output wire         prog_arrived_out_n, prog_arrived_out_s, prog_arrived_out_e, prog_arrived_out_w,
    input  wire         prog_ack_in_n, prog_ack_in_s, prog_ack_in_e, prog_ack_in_w,

    output wire [4:0]   status_core_select   // debug tap only
);

    // ── VIX_LATCH, committed atomically on cfg_valid -- same whole-
    // word-commit convention as every core in this family. Points.md
    // #666: ALSO committed by a real, internal "first live-programming
    // word is a core-select" pulse -- see below. ──
    reg [159:0] vix_latch = 160'h0;

    // ── Points.md #666: real RTL implementation of #658's own proven
    // VM design (VixCarrierSlot.relay_word()) -- the receive-side
    // channel now INSISTS the first real word of any fresh live-
    // programming session be a raw core-select value, enforced here,
    // at the receiving carrier, exactly matching the VM's own real
    // design. Real, honest gap this closes: #665 found and stated
    // plainly that the real RTL had no such mechanism at all -- this
    // entry builds it, not assumed done already.
    //
    // "Awaiting select" real edge-detected state -- re-armed on every
    // real program_in rising edge (a fresh session starting), cleared
    // the cycle the first real word is consumed as a core-select
    // value. Starts armed on reset, matching a safe, consistent
    // default for the very first live session after power-up.
    reg program_in_prev = 1'b0;
    always @(posedge clk) program_in_prev <= program_in;
    wire program_in_rising = program_in && !program_in_prev;

    reg awaiting_select = 1'b1;

    // Real, subtle bug found and fixed by simulation, not assumed
    // correct from reading the code: program_in's own FIRST real
    // rising edge and the FIRST real word's own arrival happen on the
    // exact SAME cycle -- command's own program_out only ever asserts
    // once its own active_r becomes 1, which happens on the SAME
    // cycle it captures its own first watch arrival. So
    // program_in_rising and consume_as_select are BOTH true together
    // on that first real cycle, and priority matters: consume_as_
    // select must win (clearing awaiting_select), never program_in_
    // rising (which would incorrectly re-arm it) -- checked in that
    // order below, not the reverse. Found by an RTL testbench hanging
    // (every word after the first got silently re-consumed as another
    // core-select attempt, since awaiting_select never actually
    // cleared), not caught by inspection alone.

    // Real, carrier-level "any real word arrived" -- the SAME real
    // priority-mux convention (N>S>E>W) every core's own internal
    // watch logic already uses, applied here once at the carrier
    // level for this one, new purpose.
    wire prog_any_arrived_carrier = prog_arrived_in_n || prog_arrived_in_s ||
                                     prog_arrived_in_e || prog_arrived_in_w;
    wire [31:0] carrier_prog_word = prog_arrived_in_n ? prog_data_in_n :
                                     prog_arrived_in_s ? prog_data_in_s :
                                     prog_arrived_in_e ? prog_data_in_e :
                                                          prog_data_in_w;

    // Real, decisive condition -- fires exactly once per session, on
    // whichever real cycle the first real word actually arrives.
    wire consume_as_select = program_in && awaiting_select && prog_any_arrived_carrier;

    // points.md #841: SEL_ADDON_CONFIG is a real, reserved pseudo-
    // target, not a core -- choosing it addresses the carrier's OWN
    // shared addon block for subsequent ordinary words, WITHOUT
    // touching core_select/core_config/vix_latch at all. Real,
    // necessary split: consume_as_select's own generic "treat the
    // first word as core_select, reset to a fresh core" behaviour
    // must NOT fire when the chosen value means "address the addon
    // block instead" -- that would silently deselect/reset whatever
    // core is currently running, exactly the disruption this
    // mechanism exists to avoid.
    localparam [4:0] SEL_ADDON_CONFIG = 5'd11;
    wire choosing_addon = consume_as_select && (carrier_prog_word[4:0] == SEL_ADDON_CONFIG);
    wire choosing_core  = consume_as_select && !choosing_addon;

    always @(posedge clk) begin
        if (rst) awaiting_select <= 1'b1;
        else if (consume_as_select) awaiting_select <= 1'b0;
        else if (program_in_rising) awaiting_select <= 1'b1;
    end

    // Real, registered "currently addressing the addon block, not any
    // core" state -- set only by choosing_addon, cleared by an
    // explicit real core reselect or a fresh session starting (a new
    // session must always re-choose, matching awaiting_select's own
    // real re-arm convention exactly).
    reg addon_addressed = 1'b0;
    always @(posedge clk) begin
        if (rst) addon_addressed <= 1'b0;
        else if (choosing_addon) addon_addressed <= 1'b1;
        else if (choosing_core) addon_addressed <= 1'b0;
        else if (program_in_rising) addon_addressed <= 1'b0;
    end

    // Real, necessary "ordinary programming" gate -- every one of the
    // 9 cores' own program_in/prog_arrived_in below is ALSO gated on
    // this, so the same real word that gets consumed as a core-select
    // value here can never ALSO be misread as an ordinary field-tweak
    // by whichever core happened to be selected before the redirect.
    // points.md #841: ALSO excludes addon_addressed -- while the
    // carrier is addressing its own addon block, ordinary words must
    // land on the new local addon registers below, never on whichever
    // core happens to be selected.
    wire program_in_ordinary = program_in && !awaiting_select && !addon_addressed;
    wire addon_program_in_ordinary = program_in && !awaiting_select && addon_addressed;

    // Real, minimal "boot to a blank baseline" semantic -- matches the
    // VM's own real `_blank_core()`/`boot()`: switches core_select and
    // resets the newly-selected core to a clean, all-zero config, via
    // the SAME real, already-proven cfg_valid/cfg_data mechanism every
    // core already uses, an internally-generated pulse rather than a
    // new reset pathway. Mutually exclusive with the real, external
    // cfg_valid (a genuine boot-load commit and a live-programming
    // redirect can never happen on the same real cycle), so sharing
    // one "effective" set of wires for both is safe and correct.
    // points.md #841: effective_cfg_valid/incoming_select/config now
    // gate on choosing_core, not the wider consume_as_select -- a
    // real, necessary narrowing, since choosing_addon must never reset
    // or reselect any core.
    wire effective_cfg_valid = cfg_valid || choosing_core;
    wire [4:0]   effective_incoming_select = choosing_core ? carrier_prog_word[4:0] : cfg_data[4:0];
    wire [127:0] effective_incoming_config = choosing_core ? 128'h0 : cfg_data[132:5];

    always @(posedge clk) begin
        if (rst) vix_latch <= 160'h0;
        else if (cfg_valid) vix_latch <= cfg_data;
        else if (choosing_core) vix_latch <= {27'h0, 128'h0, carrier_prog_word[4:0]};
        // choosing_addon: vix_latch deliberately UNCHANGED -- addressing
        // the addon block must never disturb the active core or its config.
    end

    // ── REGISTERED select/config -- reflects the SETTLED
    // configuration, used for ONGOING operation (arrival gating,
    // output mux). ──
    wire [4:0]   core_select  = vix_latch[4:0];
    wire [127:0] core_config  = vix_latch[132:5];
    // points.md #722: real, corrected second attempt at using the
    // previously-unused reserved headroom -- ports the FULL real
    // addon chain (#312's own proven order: nibble_mask -> shift_fine
    // -> shift_lane -> invert), needing exactly 22 real bits (20 for
    // addon_config, 2 for shift_fine), matching unicell_super_v9.v's
    // own real widths exactly. `#719`'s own first attempt at this same
    // allocation was correct; only ITS OWN APPLICATION was wrong (a
    // real, redundant SECOND chain layered on top of one already
    // built into 8 of the 9 real cores, `#720`'s own real finding) --
    // now that every core's own internal chain has been genuinely
    // removed (`_v4c`, `#720`), this shell-level chain is the ONLY
    // one left, applied ONCE here rather than four times (`#722`'s own
    // real correction to `#719`'s own "instantiate per direction"
    // compromise, see below). 5 bits of the original 27 remain
    // genuinely reserved.
    // points.md #841: addon_config/shift_fine now come from a real,
    // separate local latch, NOT read directly off vix_latch -- see the
    // local_addon_config/local_shift_fine block below. vix_latch still
    // carries these bits (unchanged storage, harmless) purely as the
    // real BOOT-TIME seed source on a full atomic cfg_valid commit;
    // ongoing operation and live reprogramming both go through the new
    // local registers instead.
    // vix_latch[159:157] still deliberately unused -- reserved headroom

    // ── points.md #841: real, live, per-field addon reprogramming --
    // the carrier-level mirror of every standalone v4 core's own
    // proven PROG_ID_ADDON_CONFIG (adder_cell_v4.v etc.), applied once
    // here instead of once per core. Seeded from cfg_data on a full
    // atomic boot commit (so an existing whole-word load still fully
    // determines addon behaviour, unchanged); updated incrementally
    // afterward via SEL_ADDON_CONFIG-addressed ordinary words, with NO
    // effect on core_select, core_config, or which core is running. ──
    localparam [2:0] PROG_ID_ADDON_LOCAL_ADDON_CONFIG = 3'd0;
    localparam [2:0] PROG_ID_ADDON_LOCAL_SHIFT_FINE   = 3'd1;
    localparam [2:0] PROG_ID_ADDON_COMPLETE           = 3'd7;

    reg [19:0] local_addon_config = 20'h0;
    reg [1:0]  local_shift_fine   = 2'h0;
    reg        addon_program_done = 1'b0;

    wire        addon_word_arrived = addon_program_in_ordinary && prog_any_arrived_carrier;
    wire [2:0]  addon_prog_id      = carrier_prog_word[22:20];
    wire [19:0] addon_prog_word    = carrier_prog_word[19:0];

    always @(posedge clk) begin
        if (rst) begin
            local_addon_config  <= 20'h0;
            local_shift_fine    <= 2'h0;
            addon_program_done  <= 1'b0;
        end else if (cfg_valid) begin
            local_addon_config  <= cfg_data[154:135];
            local_shift_fine    <= cfg_data[156:155];
            addon_program_done  <= 1'b0;
        end else if (choosing_addon) begin
            addon_program_done  <= 1'b0;   // fresh addressing session clears any prior completion flag
        end else if (addon_word_arrived) begin
            case (addon_prog_id)
                PROG_ID_ADDON_LOCAL_ADDON_CONFIG: local_addon_config <= addon_prog_word[19:0];
                PROG_ID_ADDON_LOCAL_SHIFT_FINE:   local_shift_fine   <= addon_prog_word[1:0];
                PROG_ID_ADDON_COMPLETE:           addon_program_done <= 1'b1;
                default: ; // unrecognized ID -- no-op, matches every other core's own real convention
            endcase
        end
    end

    wire [19:0]  addon_config = local_addon_config;
    wire [1:0]   shift_fine   = local_shift_fine;

    // ── INCOMING select/config -- the value ABOUT TO BE committed,
    // straight off cfg_data OR the real, internal select-redirect
    // pulse above. Same real bug class the old lineage already found
    // and fixed once (#320): gating a NEW config's delivery on the
    // OLD (pre-update) registered core_select means a config switching
    // TO a new core can never actually reach it -- the core_select/
    // core_config a LOAD must be gated on is the one ARRIVING this
    // cycle. ──
    wire [4:0]   incoming_select = effective_incoming_select;
    wire [127:0] incoming_config = effective_incoming_config;

    localparam [4:0] SEL_NANO = 5'd0, SEL_ADDER = 5'd1, SEL_RAM = 5'd2,
                      SEL_COMPARE = 5'd3, SEL_BRANCH = 5'd4, SEL_ACCUM = 5'd5,
                      SEL_LATCH = 5'd6, SEL_SEQ = 5'd7, SEL_COMMAND = 5'd8,
                      SEL_MUL = 5'd9,   // points.md #726: the 10th real core
                      SEL_PRIORITY = 5'd10,   // points.md #731: the 11th real core
                      SEL_CORNER = 5'd12,   // ledger #1035 (12, not 11: v1d reserves 11 for SEL_ADDON_CONFIG): the 12th core -- the corner wiring tile (E<->N,W<->S or E<->S,W<->N)
                      SEL_CROSS = 5'd13,   // ledger #1036: the 13th core -- the cross wiring tile (W<->E, N<->S)
                      SEL_MERGE = 5'd14,
                      SEL_DIV = 5'd15;   // ledger #1073: the 15th core -- the division core (quotient / remainder, one or two words)   // ledger #1036: the 14th core -- the merge core (A only / B only / arbitrate / join-or)

    // ── Per-core gated cfg_valid -- only the SELECTED core ever
    // genuinely loads config; the other 8 stay at their reset default
    // forever. ──
    wire cfgv_nano    = effective_cfg_valid && (incoming_select == SEL_NANO);
    wire cfgv_adder   = effective_cfg_valid && (incoming_select == SEL_ADDER);
    wire cfgv_ram     = effective_cfg_valid && (incoming_select == SEL_RAM);
    wire cfgv_compare = effective_cfg_valid && (incoming_select == SEL_COMPARE);
    wire cfgv_branch  = effective_cfg_valid && (incoming_select == SEL_BRANCH);
    wire cfgv_accum   = effective_cfg_valid && (incoming_select == SEL_ACCUM);
    wire cfgv_latch   = effective_cfg_valid && (incoming_select == SEL_LATCH);
    wire cfgv_seq     = effective_cfg_valid && (incoming_select == SEL_SEQ);
    wire cfgv_command = effective_cfg_valid && (incoming_select == SEL_COMMAND);
    wire cfgv_mul     = effective_cfg_valid && (incoming_select == SEL_MUL);
    wire cfgv_priority = effective_cfg_valid && (incoming_select == SEL_PRIORITY);
    wire cfgv_corner   = effective_cfg_valid && (incoming_select == SEL_CORNER);
    wire cfgv_cross    = effective_cfg_valid && (incoming_select == SEL_CROSS);
    wire cfgv_merge    = effective_cfg_valid && (incoming_select == SEL_MERGE);
    wire cfgv_div      = effective_cfg_valid && (incoming_select == SEL_DIV);

    // ── Per-core gated arrivals -- only the selected core ever sees a
    // genuine arrival; every other core stays completely idle. ──
    wire sel_nano    = (core_select == SEL_NANO);
    wire sel_adder   = (core_select == SEL_ADDER);
    wire sel_ram     = (core_select == SEL_RAM);
    wire sel_compare = (core_select == SEL_COMPARE);
    wire sel_branch  = (core_select == SEL_BRANCH);
    wire sel_accum   = (core_select == SEL_ACCUM);
    wire sel_latch   = (core_select == SEL_LATCH);
    wire sel_seq     = (core_select == SEL_SEQ);
    wire sel_command = (core_select == SEL_COMMAND);
    wire sel_mul     = (core_select == SEL_MUL);
    wire sel_priority = (core_select == SEL_PRIORITY);
    wire sel_corner   = (core_select == SEL_CORNER);
    wire sel_cross    = (core_select == SEL_CROSS);
    wire sel_merge    = (core_select == SEL_MERGE);
    wire sel_div      = (core_select == SEL_DIV);

    wire arr_n_g = arrived_n, arr_s_g = arrived_s, arr_e_g = arrived_e, arr_w_g = arrived_w;

    // ── Real, safety-critical: programming channel gated to the
    // selected core only (header point 2). ──
    wire prog_arr_n_g = prog_arrived_in_n && !awaiting_select,
         prog_arr_s_g = prog_arrived_in_s && !awaiting_select,
         prog_arr_e_g = prog_arrived_in_e && !awaiting_select,
         prog_arr_w_g = prog_arrived_in_w && !awaiting_select;

    // ── Each core's own real cfg_data, reconstructed directly from
    // INCOMING_CONFIG (same-cycle, straight off cfg_data), NOT the
    // registered core_config. Real, necessary fix, found by tracing an
    // actual failure: cfgv_X is gated on incoming_select (same-cycle,
    // deliberately, to avoid the exact stale-value race the old
    // lineage already found and fixed once, #320) -- feeding the
    // reconstructed cfg_data from the REGISTERED core_config instead
    // means the cfg_valid pulse and the correct config value never
    // land on the same cycle, so the target core captures cfg_valid=1
    // alongside a still-stale (all-zero) config. Every core's own real
    // field map already starts at bit 0 of its own space, so zero
    // reshuffling is needed either way -- only the source register
    // was wrong. ──
    // points.md #723: a real, genuine bug found and reverted directly
    // -- an earlier attempt at this same "config-off-shell" fix fed
    // each core's own cfg_data from core_config (the shell's own
    // STABLE, REGISTERED value), reasoning by direct analogy to
    // unicell_super_v9.v's own #699 fix. Confirmed by an actual failing
    // testbench, not assumed correct: core_config only reflects a new
    // commit ONE CLOCK CYCLE AFTER cfg_valid fires (a registered value,
    // updated via the SAME posedge that commits vix_latch), while each
    // core's own cfg_valid pulse (cfgv_nano etc.) is COMBINATIONAL,
    // asserted during the SAME cycle as the external cfg_valid --
    // meaning a core latching cfg_data on ITS OWN cfg_valid would
    // capture the OLD, pre-commit core_config value, one cycle late.
    // v9's own _v3 cells never hit this, since they read core_config
    // CONTINUOUSLY rather than latching once on cfg_valid -- the fix
    // that's correct for a continuous reader is wrong for a one-shot
    // latcher. incoming_config (combinational, reflecting the value
    // ABOUT to be committed at the exact moment cfg_valid fires) is the
    // real, correct source for these _v4c cores' own atomic boot-load
    // path -- restored here, unchanged from before this file's own
    // #719/#722 history.
    wire [127:0] nano_cfg    = incoming_config[127:0];
    wire [63:0]  adder_cfg   = incoming_config[63:0];
    wire [79:0]  ram_cfg     = incoming_config[79:0];
    wire [63:0]  compare_cfg = incoming_config[63:0];
    wire [79:0]  branch_cfg  = incoming_config[79:0];
    wire [63:0]  accum_cfg   = incoming_config[63:0];
    wire [63:0]  latch_cfg   = incoming_config[63:0];
    wire [63:0]  seq_cfg     = incoming_config[63:0];
    wire [63:0]  command_cfg = incoming_config[63:0];
    wire [63:0]  mul_cfg     = incoming_config[63:0];
    wire [63:0]  priority_cfg = incoming_config[63:0];
    wire [79:0]  corner_cfg   = incoming_config[79:0];
    wire [79:0]  cross_cfg    = incoming_config[79:0];
    wire [79:0]  merge_cfg    = incoming_config[79:0];
    wire [63:0]  div_cfg      = incoming_config[63:0];

    // ── Per-core outputs, wired from each instance below. ──
    wire [31:0] nano_dn, nano_ds, nano_de, nano_dw;
    wire nano_fn, nano_fs, nano_fe, nano_fw, nano_ready, nano_an, nano_as_, nano_ae, nano_aw, nano_pd;
    wire nano_pan, nano_pas, nano_pae, nano_paw;

    wire [31:0] adder_dn, adder_ds, adder_de, adder_dw;
    wire adder_fn, adder_fs, adder_fe, adder_fw, adder_ready, adder_an, adder_as_, adder_ae, adder_aw, adder_pd;
    wire adder_pan, adder_pas, adder_pae, adder_paw;

    wire [31:0] ram_dn, ram_ds, ram_de, ram_dw;
    wire ram_fn, ram_fs, ram_fe, ram_fw, ram_ready, ram_an, ram_as_, ram_ae, ram_aw, ram_pd;
    wire ram_pan, ram_pas, ram_pae, ram_paw;

    wire [31:0] compare_dn, compare_ds, compare_de, compare_dw;
    wire compare_fn, compare_fs, compare_fe, compare_fw, compare_ready, compare_an, compare_as_, compare_ae, compare_aw, compare_pd;
    wire compare_pan, compare_pas, compare_pae, compare_paw;

    wire [31:0] branch_dn, branch_ds, branch_de, branch_dw;
    wire branch_fn, branch_fs, branch_fe, branch_fw, branch_ready, branch_an, branch_as_, branch_ae, branch_aw, branch_pd;
    wire branch_pan, branch_pas, branch_pae, branch_paw;

    wire [31:0] accum_dn, accum_ds, accum_de, accum_dw;
    wire accum_fn, accum_fs, accum_fe, accum_fw, accum_ready, accum_an, accum_as_, accum_ae, accum_aw, accum_pd;
    wire accum_pan, accum_pas, accum_pae, accum_paw;

    wire [31:0] latch_dn, latch_ds, latch_de, latch_dw;
    wire latch_fn, latch_fs, latch_fe, latch_fw, latch_ready, latch_an, latch_as_, latch_ae, latch_aw, latch_pd;
    wire latch_pan, latch_pas, latch_pae, latch_paw;

    wire [31:0] seq_dn, seq_ds, seq_de, seq_dw;
    wire seq_fn, seq_fs, seq_fe, seq_fw, seq_ready, seq_an, seq_as_, seq_ae, seq_aw, seq_pd;
    wire seq_pan, seq_pas, seq_pae, seq_paw;

    wire [31:0] mul_dn, mul_ds, mul_de, mul_dw;
    wire mul_fn, mul_fs, mul_fe, mul_fw, mul_ready, mul_an, mul_as_, mul_ae, mul_aw, mul_pd;
    wire mul_pan, mul_pas, mul_pae, mul_paw;

    wire [31:0] priority_dn, priority_ds, priority_de, priority_dw;
    wire priority_fn, priority_fs, priority_fe, priority_fw, priority_ready, priority_an, priority_as_, priority_ae, priority_aw, priority_pd;
    wire priority_pan, priority_pas, priority_pae, priority_paw;
    wire priority_dv_unused;
    wire [31:0] corner_dn, corner_ds, corner_de, corner_dw;
    wire corner_fn, corner_fs, corner_fe, corner_fw, corner_ready, corner_an, corner_as_, corner_ae, corner_aw, corner_pd;
    wire corner_pan, corner_pas, corner_pae, corner_paw;
    wire corner_dv_unused;
    wire [31:0] cross_dn, cross_ds, cross_de, cross_dw;
    wire cross_fn, cross_fs, cross_fe, cross_fw, cross_ready, cross_an, cross_as_, cross_ae, cross_aw, cross_pd;
    wire cross_pan, cross_pas, cross_pae, cross_paw;
    wire [31:0] merge_dn, merge_ds, merge_de, merge_dw;
    wire merge_fn, merge_fs, merge_fe, merge_fw, merge_ready, merge_an, merge_as_, merge_ae, merge_aw, merge_pd;
    wire merge_pan, merge_pas, merge_pae, merge_paw;
    wire [31:0] div_dn, div_ds, div_de, div_dw;
    wire div_fn, div_fs, div_fe, div_fw, div_ready, div_an, div_as_, div_ae, div_aw, div_pd;
    wire div_pan, div_pas, div_pae, div_paw;
    wire [1:0] priority_wd_unused;

    wire command_an, command_as_, command_ae, command_aw, command_ready;
    wire command_fzn, command_fzs, command_fze, command_fzw;
    wire command_pon, command_pos, command_poe, command_pow;
    wire [31:0] command_pdon, command_pdos, command_pdoe, command_pdow;
    wire command_paon, command_paos, command_paoe, command_paow;

    // nano removed (ledger #1088): its outputs are tied to 0
    assign nano_ae = 0;
    assign nano_an = 0;
    assign nano_as_ = 0;
    assign nano_aw = 0;
    assign nano_de = 0;
    assign nano_dn = 0;
    assign nano_ds = 0;
    assign nano_dw = 0;
    assign nano_fe = 0;
    assign nano_fn = 0;
    assign nano_fs = 0;
    assign nano_fw = 0;
    assign nano_pae = 0;
    assign nano_pan = 0;
    assign nano_pas = 0;
    assign nano_paw = 0;
    assign nano_pd = 0;
    assign nano_ready = 0;

    adder_shell_v1c #(.CELL_ID(CELL_ID)) CORE_ADDER (
        .clk(clk), .rst(rst),
        .active_in_n(active_in_n), .active_in_s(active_in_s), .active_in_e(active_in_e), .active_in_w(active_in_w),
        .freeze_in_n(freeze_in_n), .freeze_in_s(freeze_in_s), .freeze_in_e(freeze_in_e), .freeze_in_w(freeze_in_w),
        .cfg_valid(cfgv_adder), .cfg_data(adder_cfg),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(sel_adder && arr_n_g), .arrived_s(sel_adder && arr_s_g),
        .arrived_e(sel_adder && arr_e_g), .arrived_w(sel_adder && arr_w_g),
        .data_out_n(adder_dn), .data_out_s(adder_ds), .data_out_e(adder_de), .data_out_w(adder_dw),
        .fire_n(adder_fn), .fire_s(adder_fs), .fire_e(adder_fe), .fire_w(adder_fw),
        .ready_out(adder_ready),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(adder_an), .ack_out_s(adder_as_), .ack_out_e(adder_ae), .ack_out_w(adder_aw),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .program_in(sel_adder && program_in_ordinary), .program_done(adder_pd),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s), .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(sel_adder && prog_arr_n_g), .prog_arrived_in_s(sel_adder && prog_arr_s_g),
        .prog_arrived_in_e(sel_adder && prog_arr_e_g), .prog_arrived_in_w(sel_adder && prog_arr_w_g),
        .prog_ack_out_n(adder_pan), .prog_ack_out_s(adder_pas), .prog_ack_out_e(adder_pae), .prog_ack_out_w(adder_paw),
        .status_data_valid(), .status_a_arrived()
    );

    // ram removed (ledger #1088): its outputs are tied to 0
    assign ram_ae = 0;
    assign ram_an = 0;
    assign ram_as_ = 0;
    assign ram_aw = 0;
    assign ram_de = 0;
    assign ram_dn = 0;
    assign ram_ds = 0;
    assign ram_dw = 0;
    assign ram_fe = 0;
    assign ram_fn = 0;
    assign ram_fs = 0;
    assign ram_fw = 0;
    assign ram_pae = 0;
    assign ram_pan = 0;
    assign ram_pas = 0;
    assign ram_paw = 0;
    assign ram_pd = 0;
    assign ram_ready = 0;

    // compare removed (ledger #1088): its outputs are tied to 0
    assign compare_ae = 0;
    assign compare_an = 0;
    assign compare_as_ = 0;
    assign compare_aw = 0;
    assign compare_de = 0;
    assign compare_dn = 0;
    assign compare_ds = 0;
    assign compare_dw = 0;
    assign compare_fe = 0;
    assign compare_fn = 0;
    assign compare_fs = 0;
    assign compare_fw = 0;
    assign compare_pae = 0;
    assign compare_pan = 0;
    assign compare_pas = 0;
    assign compare_paw = 0;
    assign compare_pd = 0;
    assign compare_ready = 0;

    // branch removed (ledger #1088): its outputs are tied to 0
    assign branch_ae = 0;
    assign branch_an = 0;
    assign branch_as_ = 0;
    assign branch_aw = 0;
    assign branch_de = 0;
    assign branch_dn = 0;
    assign branch_ds = 0;
    assign branch_dw = 0;
    assign branch_fe = 0;
    assign branch_fn = 0;
    assign branch_fs = 0;
    assign branch_fw = 0;
    assign branch_pae = 0;
    assign branch_pan = 0;
    assign branch_pas = 0;
    assign branch_paw = 0;
    assign branch_pd = 0;
    assign branch_ready = 0;

    accumulator_shell_v1c #(.CELL_ID(CELL_ID)) CORE_ACCUM (
        .clk(clk), .rst(rst),
        .active_in_n(active_in_n), .active_in_s(active_in_s), .active_in_e(active_in_e), .active_in_w(active_in_w),
        .freeze_in_n(freeze_in_n), .freeze_in_s(freeze_in_s), .freeze_in_e(freeze_in_e), .freeze_in_w(freeze_in_w),
        .cfg_valid(cfgv_accum), .cfg_data(accum_cfg),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(sel_accum && arr_n_g), .arrived_s(sel_accum && arr_s_g),
        .arrived_e(sel_accum && arr_e_g), .arrived_w(sel_accum && arr_w_g),
        .data_out_n(accum_dn), .data_out_s(accum_ds), .data_out_e(accum_de), .data_out_w(accum_dw),
        .fire_n(accum_fn), .fire_s(accum_fs), .fire_e(accum_fe), .fire_w(accum_fw),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(accum_an), .ack_out_s(accum_as_), .ack_out_e(accum_ae), .ack_out_w(accum_aw),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .program_in(sel_accum && program_in_ordinary), .program_done(accum_pd),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s), .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(sel_accum && prog_arr_n_g), .prog_arrived_in_s(sel_accum && prog_arr_s_g),
        .prog_arrived_in_e(sel_accum && prog_arr_e_g), .prog_arrived_in_w(sel_accum && prog_arr_w_g),
        .prog_ack_out_n(accum_pan), .prog_ack_out_s(accum_pas), .prog_ack_out_e(accum_pae), .prog_ack_out_w(accum_paw),
        .ready_out(accum_ready), .status_negative()
    );

    // latch removed (ledger #1088): its outputs are tied to 0
    assign latch_ae = 0;
    assign latch_an = 0;
    assign latch_as_ = 0;
    assign latch_aw = 0;
    assign latch_de = 0;
    assign latch_dn = 0;
    assign latch_ds = 0;
    assign latch_dw = 0;
    assign latch_fe = 0;
    assign latch_fn = 0;
    assign latch_fs = 0;
    assign latch_fw = 0;
    assign latch_pae = 0;
    assign latch_pan = 0;
    assign latch_pas = 0;
    assign latch_paw = 0;
    assign latch_pd = 0;
    assign latch_ready = 0;

    // seq removed (ledger #1088): its outputs are tied to 0
    assign seq_ae = 0;
    assign seq_an = 0;
    assign seq_as_ = 0;
    assign seq_aw = 0;
    assign seq_de = 0;
    assign seq_dn = 0;
    assign seq_ds = 0;
    assign seq_dw = 0;
    assign seq_fe = 0;
    assign seq_fn = 0;
    assign seq_fs = 0;
    assign seq_fw = 0;
    assign seq_pae = 0;
    assign seq_pan = 0;
    assign seq_pas = 0;
    assign seq_paw = 0;
    assign seq_pd = 0;
    assign seq_ready = 0;

    // points.md #726: the 10th real core, wired following the exact
    // same real convention as every other one here.
    mul_shell_v1c #(.CELL_ID(CELL_ID)) CORE_MUL (
        .clk(clk), .rst(rst),
        .active_in_n(active_in_n), .active_in_s(active_in_s), .active_in_e(active_in_e), .active_in_w(active_in_w),
        .freeze_in_n(freeze_in_n), .freeze_in_s(freeze_in_s), .freeze_in_e(freeze_in_e), .freeze_in_w(freeze_in_w),
        .cfg_valid(cfgv_mul), .cfg_data(mul_cfg),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(sel_mul && arr_n_g), .arrived_s(sel_mul && arr_s_g),
        .arrived_e(sel_mul && arr_e_g), .arrived_w(sel_mul && arr_w_g),
        .data_out_n(mul_dn), .data_out_s(mul_ds), .data_out_e(mul_de), .data_out_w(mul_dw),
        .fire_n(mul_fn), .fire_s(mul_fs), .fire_e(mul_fe), .fire_w(mul_fw),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(mul_an), .ack_out_s(mul_as_), .ack_out_e(mul_ae), .ack_out_w(mul_aw),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .program_in(sel_mul && program_in_ordinary), .program_done(mul_pd),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s), .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(sel_mul && prog_arr_n_g), .prog_arrived_in_s(sel_mul && prog_arr_s_g),
        .prog_arrived_in_e(sel_mul && prog_arr_e_g), .prog_arrived_in_w(sel_mul && prog_arr_w_g),
        .prog_ack_out_n(mul_pan), .prog_ack_out_s(mul_pas), .prog_ack_out_e(mul_pae), .prog_ack_out_w(mul_paw),
        .ready_out(mul_ready), .status_data_valid(), .status_a_arrived()
    );

    // points.md #731: the 11th real core, wired following the exact
    // same real convention as every other one here.
    // priority removed (ledger #1088): its outputs are tied to 0
    assign priority_ae = 0;
    assign priority_an = 0;
    assign priority_as_ = 0;
    assign priority_aw = 0;
    assign priority_de = 0;
    assign priority_dn = 0;
    assign priority_ds = 0;
    assign priority_dv_unused = 0;
    assign priority_dw = 0;
    assign priority_fe = 0;
    assign priority_fn = 0;
    assign priority_fs = 0;
    assign priority_fw = 0;
    assign priority_pae = 0;
    assign priority_pan = 0;
    assign priority_pas = 0;
    assign priority_paw = 0;
    assign priority_pd = 0;
    assign priority_ready = 0;
    assign priority_wd_unused = 0;

    // ledger #1035: the 12th core, the corner wiring tile, wired like every other one.
    // corner removed (ledger #1088): its outputs are tied to 0
    assign corner_ae = 0;
    assign corner_an = 0;
    assign corner_as_ = 0;
    assign corner_aw = 0;
    assign corner_de = 0;
    assign corner_dn = 0;
    assign corner_ds = 0;
    assign corner_dv_unused = 0;
    assign corner_dw = 0;
    assign corner_fe = 0;
    assign corner_fn = 0;
    assign corner_fs = 0;
    assign corner_fw = 0;
    assign corner_pae = 0;
    assign corner_pan = 0;
    assign corner_pas = 0;
    assign corner_paw = 0;
    assign corner_pd = 0;
    assign corner_ready = 0;

    // ledger #1036: the 13th core, the cross wiring tile.
    // cross removed (ledger #1088): its outputs are tied to 0
    assign cross_ae = 0;
    assign cross_an = 0;
    assign cross_as_ = 0;
    assign cross_aw = 0;
    assign cross_de = 0;
    assign cross_dn = 0;
    assign cross_ds = 0;
    assign cross_dw = 0;
    assign cross_fe = 0;
    assign cross_fn = 0;
    assign cross_fs = 0;
    assign cross_fw = 0;
    assign cross_pae = 0;
    assign cross_pan = 0;
    assign cross_pas = 0;
    assign cross_paw = 0;
    assign cross_pd = 0;
    assign cross_ready = 0;

    // ledger #1036: the 14th core, the merge core.
    // merge removed (ledger #1088): its outputs are tied to 0
    assign merge_ae = 0;
    assign merge_an = 0;
    assign merge_as_ = 0;
    assign merge_aw = 0;
    assign merge_de = 0;
    assign merge_dn = 0;
    assign merge_ds = 0;
    assign merge_dw = 0;
    assign merge_fe = 0;
    assign merge_fn = 0;
    assign merge_fs = 0;
    assign merge_fw = 0;
    assign merge_pae = 0;
    assign merge_pan = 0;
    assign merge_pas = 0;
    assign merge_paw = 0;
    assign merge_pd = 0;
    assign merge_ready = 0;

    // ledger #1036: the 15th core, the division core (ledger #1073).
    // div removed (ledger #1088): its outputs are tied to 0
    assign div_ae = 0;
    assign div_an = 0;
    assign div_as_ = 0;
    assign div_aw = 0;
    assign div_de = 0;
    assign div_dn = 0;
    assign div_ds = 0;
    assign div_dw = 0;
    assign div_fe = 0;
    assign div_fn = 0;
    assign div_fs = 0;
    assign div_fw = 0;
    assign div_pae = 0;
    assign div_pan = 0;
    assign div_pas = 0;
    assign div_paw = 0;
    assign div_pd = 0;
    assign div_ready = 0;

    // command removed (ledger #1088): its outputs are tied to 0
    assign command_ae = 0;
    assign command_an = 0;
    assign command_as_ = 0;
    assign command_aw = 0;
    assign command_fze = 0;
    assign command_fzn = 0;
    assign command_fzs = 0;
    assign command_fzw = 0;
    assign command_paoe = 0;
    assign command_paon = 0;
    assign command_paos = 0;
    assign command_paow = 0;
    assign command_pdoe = 0;
    assign command_pdon = 0;
    assign command_pdos = 0;
    assign command_pdow = 0;
    assign command_poe = 0;
    assign command_pon = 0;
    assign command_pos = 0;
    assign command_pow = 0;
    assign command_ready = 0;

    // ── Real output mux -- exactly one core's outputs ever reach the
    // external ports, selected by the SAME registered core_select
    // used for arrival/config gating. ──
    //
    // points.md #722: real, corrected shape -- a cell offers the
    // IDENTICAL computed value in every direction (#611's own
    // established fact; confirmed directly for VIX's own per-
    // direction _dn/_ds/_de/_dw signals too, which are always the
    // same value for any given core, just gated differently per
    // direction via fire_n/s/e/w rather than carrying different data).
    // `#719`'s own first attempt didn't rely on this and instantiated
    // the whole addon chain FOUR TIMES, once per direction, to avoid
    // touching this mux's own shape -- a real, ~4x area cost, now
    // corrected: ONE shared mux output feeds ONE addon chain, whose
    // single result is broadcast to all four directions, matching
    // unicell_super_v9.v's own real, efficient shape exactly.
    wire [31:0] mux_dout = sel_nano ? nano_dn : sel_adder ? adder_dn : sel_ram ? ram_dn :
                           sel_compare ? compare_dn : sel_branch ? branch_dn : sel_accum ? accum_dn :
                           sel_latch ? latch_dn : sel_seq ? seq_dn : sel_mul ? mul_dn : sel_priority ? priority_dn : sel_corner ? corner_dn : sel_cross ? cross_dn : sel_merge ? merge_dn : sel_div ? div_dn : 32'h0;

    wire [31:0] after_mask, after_fineshift, after_shiftlane, addon_out;
    wire [1:0]  shift_fine_applied;

    nibble_mask_addon_v1 ADDON_NM (
        .mask_en(addon_config[8]), .nibble_mask(addon_config[7:0]),
        .data_in(mux_dout), .data_out(after_mask)
    );
    shift_fine_addon_v1 ADDON_SF (
        .direction(addon_config[15]), .shift_en(addon_config[14]),
        .shift_amount(shift_fine),
        .data_in(after_mask), .data_out(after_fineshift),
        .shift_amount_out(shift_fine_applied)
    );
    shift_lane_addon_v2 ADDON_SL (
        .direction(addon_config[15]), .shift_en(addon_config[14]),
        .shift_amt(addon_config[13:9]), .lane_cut(addon_config[18:16]),
        .shift_fine_in(shift_fine_applied),
        .data_in(after_fineshift), .data_out(after_shiftlane)
    );
    invert_addon_v1 ADDON_INV (
        .invert_en(addon_config[19]),
        .data_in(after_shiftlane), .data_out(addon_out)
    );

    // ledger #1036: a wiring tile (corner / cross) carries a DIFFERENT word out of each face and transforms nothing, so it bypasses the shared addon chain and drives its own four data outputs.
    assign data_out_n = sel_corner ? corner_dn : sel_cross ? cross_dn : addon_out;
    assign data_out_s = sel_corner ? corner_ds : sel_cross ? cross_ds : addon_out;
    assign data_out_e = sel_corner ? corner_de : sel_cross ? cross_de : addon_out;
    assign data_out_w = sel_corner ? corner_dw : sel_cross ? cross_dw : addon_out;

    assign fire_n = sel_nano ? nano_fn : sel_adder ? adder_fn : sel_ram ? ram_fn :
                    sel_compare ? compare_fn : sel_branch ? branch_fn : sel_accum ? accum_fn :
                    sel_latch ? latch_fn : sel_seq ? seq_fn : sel_mul ? mul_fn : sel_priority ? priority_fn : sel_corner ? corner_fn : sel_cross ? cross_fn : sel_merge ? merge_fn : sel_div ? div_fn : 1'b0;
    assign fire_s = sel_nano ? nano_fs : sel_adder ? adder_fs : sel_ram ? ram_fs :
                    sel_compare ? compare_fs : sel_branch ? branch_fs : sel_accum ? accum_fs :
                    sel_latch ? latch_fs : sel_seq ? seq_fs : sel_mul ? mul_fs : sel_priority ? priority_fs : sel_corner ? corner_fs : sel_cross ? cross_fs : sel_merge ? merge_fs : sel_div ? div_fs : 1'b0;
    assign fire_e = sel_nano ? nano_fe : sel_adder ? adder_fe : sel_ram ? ram_fe :
                    sel_compare ? compare_fe : sel_branch ? branch_fe : sel_accum ? accum_fe :
                    sel_latch ? latch_fe : sel_seq ? seq_fe : sel_mul ? mul_fe : sel_priority ? priority_fe : sel_corner ? corner_fe : sel_cross ? cross_fe : sel_merge ? merge_fe : sel_div ? div_fe : 1'b0;
    assign fire_w = sel_nano ? nano_fw : sel_adder ? adder_fw : sel_ram ? ram_fw :
                    sel_compare ? compare_fw : sel_branch ? branch_fw : sel_accum ? accum_fw :
                    sel_latch ? latch_fw : sel_seq ? seq_fw : sel_mul ? mul_fw : sel_priority ? priority_fw : sel_corner ? corner_fw : sel_cross ? cross_fw : sel_merge ? merge_fw : sel_div ? div_fw : 1'b0;

    assign ack_out_n = sel_nano ? nano_an : sel_adder ? adder_an : sel_ram ? ram_an :
                       sel_compare ? compare_an : sel_branch ? branch_an : sel_accum ? accum_an :
                       sel_latch ? latch_an : sel_seq ? seq_an : sel_mul ? mul_an : sel_priority ? priority_an : sel_corner ? corner_an : sel_cross ? cross_an : sel_merge ? merge_an : sel_div ? div_an : sel_command ? command_an : 1'b0;
    assign ack_out_s = sel_nano ? nano_as_ : sel_adder ? adder_as_ : sel_ram ? ram_as_ :
                       sel_compare ? compare_as_ : sel_branch ? branch_as_ : sel_accum ? accum_as_ :
                       sel_latch ? latch_as_ : sel_seq ? seq_as_ : sel_mul ? mul_as_ : sel_priority ? priority_as_ : sel_corner ? corner_as_ : sel_cross ? cross_as_ : sel_merge ? merge_as_ : sel_div ? div_as_ : sel_command ? command_as_ : 1'b0;
    assign ack_out_e = sel_nano ? nano_ae : sel_adder ? adder_ae : sel_ram ? ram_ae :
                       sel_compare ? compare_ae : sel_branch ? branch_ae : sel_accum ? accum_ae :
                       sel_latch ? latch_ae : sel_seq ? seq_ae : sel_mul ? mul_ae : sel_priority ? priority_ae : sel_corner ? corner_ae : sel_cross ? cross_ae : sel_merge ? merge_ae : sel_div ? div_ae : sel_command ? command_ae : 1'b0;
    assign ack_out_w = sel_nano ? nano_aw : sel_adder ? adder_aw : sel_ram ? ram_aw :
                       sel_compare ? compare_aw : sel_branch ? branch_aw : sel_accum ? accum_aw :
                       sel_latch ? latch_aw : sel_seq ? seq_aw : sel_mul ? mul_aw : sel_priority ? priority_aw : sel_corner ? corner_aw : sel_cross ? cross_aw : sel_merge ? merge_aw : sel_div ? div_aw : sel_command ? command_aw : 1'b0;

    assign ready_out = sel_nano ? nano_ready : sel_adder ? adder_ready : sel_ram ? ram_ready :
                        sel_compare ? compare_ready : sel_branch ? branch_ready : sel_accum ? accum_ready :
                        sel_latch ? latch_ready : sel_seq ? seq_ready : sel_mul ? mul_ready : sel_priority ? priority_ready : sel_corner ? corner_ready : sel_cross ? cross_ready : sel_merge ? merge_ready : sel_div ? div_ready : sel_command ? command_ready : 1'b0;

    assign program_done = addon_addressed ? addon_program_done :
                           sel_nano ? nano_pd : sel_adder ? adder_pd : sel_ram ? ram_pd :
                           sel_compare ? compare_pd : sel_branch ? branch_pd : sel_accum ? accum_pd :
                           sel_latch ? latch_pd : sel_seq ? seq_pd : sel_mul ? mul_pd : sel_priority ? priority_pd : sel_corner ? corner_pd : sel_cross ? cross_pd : sel_merge ? merge_pd : sel_div ? div_pd : 1'b0;   // command has no receive-side program_done wired

    // ── Points.md #666: real, necessary synthetic ack -- when the
    // carrier itself consumes a word as a core-select value, NO
    // individual core's own prog_arrived_in was ever asserted for it
    // (consume_as_select fires before any per-core routing), so no
    // core produces the real prog_ack_out the sender is waiting for.
    // Found by a real RTL testbench hanging (the sender's own relay
    // never sent a second word, stuck waiting for an ack that would
    // never arrive) -- traced to this exact cause, not assumed. Fires
    // a real, one-cycle synthetic ack back in whichever direction the
    // word actually arrived from, matching the same real priority
    // (N>S>E>W) `carrier_prog_word` itself already uses. ──
    wire select_ack_n = consume_as_select && prog_arrived_in_n;
    wire select_ack_s = consume_as_select && !prog_arrived_in_n && prog_arrived_in_s;
    wire select_ack_e = consume_as_select && !prog_arrived_in_n && !prog_arrived_in_s && prog_arrived_in_e;
    wire select_ack_w = consume_as_select && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e && prog_arrived_in_w;

    // points.md #841: the SAME real necessity as select_ack above, for
    // the same real reason -- an addon-addressed ordinary word is
    // consumed directly by the new local addon registers, never by any
    // per-core module, so no core's own prog_ack_out would ever fire
    // for it without this.
    wire addon_ack_n = addon_word_arrived && prog_arrived_in_n;
    wire addon_ack_s = addon_word_arrived && !prog_arrived_in_n && prog_arrived_in_s;
    wire addon_ack_e = addon_word_arrived && !prog_arrived_in_n && !prog_arrived_in_s && prog_arrived_in_e;
    wire addon_ack_w = addon_word_arrived && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e && prog_arrived_in_w;

    assign prog_ack_out_n = select_ack_n || addon_ack_n || (sel_nano ? nano_pan : sel_adder ? adder_pan : sel_ram ? ram_pan :
                             sel_compare ? compare_pan : sel_branch ? branch_pan : sel_accum ? accum_pan :
                             sel_latch ? latch_pan : sel_seq ? seq_pan : sel_mul ? mul_pan : sel_priority ? priority_pan : sel_corner ? corner_pan : sel_cross ? cross_pan : sel_merge ? merge_pan : sel_div ? div_pan : 1'b0);
    assign prog_ack_out_s = select_ack_s || addon_ack_s || (sel_nano ? nano_pas : sel_adder ? adder_pas : sel_ram ? ram_pas :
                             sel_compare ? compare_pas : sel_branch ? branch_pas : sel_accum ? accum_pas :
                             sel_latch ? latch_pas : sel_seq ? seq_pas : sel_mul ? mul_pas : sel_priority ? priority_pas : sel_corner ? corner_pas : sel_cross ? cross_pas : sel_merge ? merge_pas : sel_div ? div_pas : 1'b0);
    assign prog_ack_out_e = select_ack_e || addon_ack_e || (sel_nano ? nano_pae : sel_adder ? adder_pae : sel_ram ? ram_pae :
                             sel_compare ? compare_pae : sel_branch ? branch_pae : sel_accum ? accum_pae :
                             sel_latch ? latch_pae : sel_seq ? seq_pae : sel_mul ? mul_pae : sel_priority ? priority_pae : sel_corner ? corner_pae : sel_cross ? cross_pae : sel_merge ? merge_pae : sel_div ? div_pae : 1'b0);
    assign prog_ack_out_w = select_ack_w || addon_ack_w || (sel_nano ? nano_paw : sel_adder ? adder_paw : sel_ram ? ram_paw :
                             sel_compare ? compare_paw : sel_branch ? branch_paw : sel_accum ? accum_paw :
                             sel_latch ? latch_paw : sel_seq ? seq_paw : sel_mul ? mul_paw : sel_priority ? priority_paw : sel_corner ? corner_paw : sel_cross ? cross_paw : sel_merge ? merge_paw : sel_div ? div_paw : 1'b0);

    // ── Command's own genuinely new ports -- meaningful only when
    // core_select=SEL_COMMAND, safe defaults otherwise. ──
    assign freeze_out_n = sel_command ? command_fzn : 1'b0;
    assign freeze_out_s = sel_command ? command_fzs : 1'b0;
    assign freeze_out_e = sel_command ? command_fze : 1'b0;
    assign freeze_out_w = sel_command ? command_fzw : 1'b0;
    assign program_out_n = sel_command ? command_pon : 1'b0;
    assign program_out_s = sel_command ? command_pos : 1'b0;
    assign program_out_e = sel_command ? command_poe : 1'b0;
    assign program_out_w = sel_command ? command_pow : 1'b0;
    assign prog_data_out_n = sel_command ? command_pdon : 32'h0;
    assign prog_data_out_s = sel_command ? command_pdos : 32'h0;
    assign prog_data_out_e = sel_command ? command_pdoe : 32'h0;
    assign prog_data_out_w = sel_command ? command_pdow : 32'h0;
    assign prog_arrived_out_n = sel_command ? command_paon : 1'b0;
    assign prog_arrived_out_s = sel_command ? command_paos : 1'b0;
    assign prog_arrived_out_e = sel_command ? command_paoe : 1'b0;
    assign prog_arrived_out_w = sel_command ? command_paow : 1'b0;

    assign status_core_select = core_select;

endmodule
