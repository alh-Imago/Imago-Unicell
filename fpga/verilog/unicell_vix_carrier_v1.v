// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
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
//   [159:133] reserved      — 27 bits, genuine future headroom
`default_nettype none
`timescale 1ns / 1ps

module unicell_vix_carrier_v1 #(
    parameter [15:0] CELL_ID = 16'h0000
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

    always @(posedge clk) begin
        if (rst) awaiting_select <= 1'b1;
        else if (consume_as_select) awaiting_select <= 1'b0;
        else if (program_in_rising) awaiting_select <= 1'b1;
    end

    // Real, necessary "ordinary programming" gate -- every one of the
    // 9 cores' own program_in/prog_arrived_in below is ALSO gated on
    // this, so the same real word that gets consumed as a core-select
    // value here can never ALSO be misread as an ordinary field-tweak
    // by whichever core happened to be selected before the redirect.
    wire program_in_ordinary = program_in && !awaiting_select;

    // Real, minimal "boot to a blank baseline" semantic -- matches the
    // VM's own real `_blank_core()`/`boot()`: switches core_select and
    // resets the newly-selected core to a clean, all-zero config, via
    // the SAME real, already-proven cfg_valid/cfg_data mechanism every
    // core already uses, an internally-generated pulse rather than a
    // new reset pathway. Mutually exclusive with the real, external
    // cfg_valid (a genuine boot-load commit and a live-programming
    // redirect can never happen on the same real cycle), so sharing
    // one "effective" set of wires for both is safe and correct.
    wire effective_cfg_valid = cfg_valid || consume_as_select;
    wire [4:0]   effective_incoming_select = consume_as_select ? carrier_prog_word[4:0] : cfg_data[4:0];
    wire [127:0] effective_incoming_config = consume_as_select ? 128'h0 : cfg_data[132:5];

    always @(posedge clk) begin
        if (rst) vix_latch <= 160'h0;
        else if (cfg_valid) vix_latch <= cfg_data;
        else if (consume_as_select) vix_latch <= {27'h0, 128'h0, carrier_prog_word[4:0]};
    end

    // ── REGISTERED select/config -- reflects the SETTLED
    // configuration, used for ONGOING operation (arrival gating,
    // output mux). ──
    wire [4:0]   core_select  = vix_latch[4:0];
    wire [127:0] core_config  = vix_latch[132:5];
    // vix_latch[159:133] deliberately unused -- reserved headroom

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
                      SEL_LATCH = 5'd6, SEL_SEQ = 5'd7, SEL_COMMAND = 5'd8;

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
    wire [127:0] nano_cfg    = incoming_config[127:0];
    wire [63:0]  adder_cfg   = incoming_config[63:0];
    wire [79:0]  ram_cfg     = incoming_config[79:0];
    wire [63:0]  compare_cfg = incoming_config[63:0];
    wire [79:0]  branch_cfg  = incoming_config[79:0];
    wire [63:0]  accum_cfg   = incoming_config[63:0];
    wire [63:0]  latch_cfg   = incoming_config[63:0];
    wire [63:0]  seq_cfg     = incoming_config[63:0];
    wire [63:0]  command_cfg = incoming_config[63:0];

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

    wire command_an, command_as_, command_ae, command_aw, command_ready;
    wire command_fzn, command_fzs, command_fze, command_fzw;
    wire command_pon, command_pos, command_poe, command_pow;
    wire [31:0] command_pdon, command_pdos, command_pdoe, command_pdow;
    wire command_paon, command_paos, command_paoe, command_paow;

    nano_shell_v1 #(.CELL_ID(CELL_ID), .ENABLE_DYNAMIC_ROUTING(1'b0)) CORE_NANO (
        .clk(clk), .rst(rst),
        .active_in_n(active_in_n), .active_in_s(active_in_s), .active_in_e(active_in_e), .active_in_w(active_in_w),
        .freeze_in_n(freeze_in_n), .freeze_in_s(freeze_in_s), .freeze_in_e(freeze_in_e), .freeze_in_w(freeze_in_w),
        .hold_in_n(1'b0), .hold_in_s(1'b0), .hold_in_e(1'b0), .hold_in_w(1'b0),
        .fb_internal_in_n(1'b0), .fb_internal_in_s(1'b0), .fb_internal_in_e(1'b0), .fb_internal_in_w(1'b0),
        .a_reemit_in_n(1'b0), .a_reemit_in_s(1'b0), .a_reemit_in_e(1'b0), .a_reemit_in_w(1'b0),
        .a_update_in_n(1'b0), .a_update_in_s(1'b0), .a_update_in_e(1'b0), .a_update_in_w(1'b0),
        .a_self_update_in_n(1'b0), .a_self_update_in_s(1'b0), .a_self_update_in_e(1'b0), .a_self_update_in_w(1'b0),
        .cfg_valid(cfgv_nano), .cfg_data(nano_cfg),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(sel_nano && arr_n_g), .arrived_s(sel_nano && arr_s_g),
        .arrived_e(sel_nano && arr_e_g), .arrived_w(sel_nano && arr_w_g),
        .data_out_n(nano_dn), .data_out_s(nano_ds), .data_out_e(nano_de), .data_out_w(nano_dw),
        .fire_n(nano_fn), .fire_s(nano_fs), .fire_e(nano_fe), .fire_w(nano_fw),
        .ready_out(nano_ready),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(nano_an), .ack_out_s(nano_as_), .ack_out_e(nano_ae), .ack_out_w(nano_aw),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .program_in(sel_nano && program_in_ordinary), .program_done(nano_pd),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s), .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(sel_nano && prog_arr_n_g), .prog_arrived_in_s(sel_nano && prog_arr_s_g),
        .prog_arrived_in_e(sel_nano && prog_arr_e_g), .prog_arrived_in_w(sel_nano && prog_arr_w_g),
        .prog_ack_out_n(nano_pan), .prog_ack_out_s(nano_pas), .prog_ack_out_e(nano_pae), .prog_ack_out_w(nano_paw)
    );

    adder_shell_v1 #(.CELL_ID(CELL_ID)) CORE_ADDER (
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

    ram_shell_v1 #(.CELL_ID(CELL_ID)) CORE_RAM (
        .clk(clk), .rst(rst),
        .active_in_n(active_in_n), .active_in_s(active_in_s), .active_in_e(active_in_e), .active_in_w(active_in_w),
        .freeze_in_n(freeze_in_n), .freeze_in_s(freeze_in_s), .freeze_in_e(freeze_in_e), .freeze_in_w(freeze_in_w),
        .cfg_valid(cfgv_ram), .cfg_data(ram_cfg),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(sel_ram && arr_n_g), .arrived_s(sel_ram && arr_s_g),
        .arrived_e(sel_ram && arr_e_g), .arrived_w(sel_ram && arr_w_g),
        .data_out_n(ram_dn), .data_out_s(ram_ds), .data_out_e(ram_de), .data_out_w(ram_dw),
        .fire_n(ram_fn), .fire_s(ram_fs), .fire_e(ram_fe), .fire_w(ram_fw),
        .ready_out(ram_ready),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(ram_an), .ack_out_s(ram_as_), .ack_out_e(ram_ae), .ack_out_w(ram_aw),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .program_in(sel_ram && program_in_ordinary), .program_done(ram_pd),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s), .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(sel_ram && prog_arr_n_g), .prog_arrived_in_s(sel_ram && prog_arr_s_g),
        .prog_arrived_in_e(sel_ram && prog_arr_e_g), .prog_arrived_in_w(sel_ram && prog_arr_w_g),
        .prog_ack_out_n(ram_pan), .prog_ack_out_s(ram_pas), .prog_ack_out_e(ram_pae), .prog_ack_out_w(ram_paw),
        .status_data_valid()
    );

    compare_shell_v1 #(.CELL_ID(CELL_ID)) CORE_COMPARE (
        .clk(clk), .rst(rst),
        .active_in_n(active_in_n), .active_in_s(active_in_s), .active_in_e(active_in_e), .active_in_w(active_in_w),
        .freeze_in_n(freeze_in_n), .freeze_in_s(freeze_in_s), .freeze_in_e(freeze_in_e), .freeze_in_w(freeze_in_w),
        .cfg_valid(cfgv_compare), .cfg_data(compare_cfg),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(sel_compare && arr_n_g), .arrived_s(sel_compare && arr_s_g),
        .arrived_e(sel_compare && arr_e_g), .arrived_w(sel_compare && arr_w_g),
        .data_out_n(compare_dn), .data_out_s(compare_ds), .data_out_e(compare_de), .data_out_w(compare_dw),
        .fire_n(compare_fn), .fire_s(compare_fs), .fire_e(compare_fe), .fire_w(compare_fw),
        .ready_out(compare_ready),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(compare_an), .ack_out_s(compare_as_), .ack_out_e(compare_ae), .ack_out_w(compare_aw),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .program_in(sel_compare && program_in_ordinary), .program_done(compare_pd),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s), .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(sel_compare && prog_arr_n_g), .prog_arrived_in_s(sel_compare && prog_arr_s_g),
        .prog_arrived_in_e(sel_compare && prog_arr_e_g), .prog_arrived_in_w(sel_compare && prog_arr_w_g),
        .prog_ack_out_n(compare_pan), .prog_ack_out_s(compare_pas), .prog_ack_out_e(compare_pae), .prog_ack_out_w(compare_paw),
        .status_data_valid()
    );

    branch_shell_v1 #(.CELL_ID(CELL_ID)) CORE_BRANCH (
        .clk(clk), .rst(rst),
        .active_in_n(active_in_n), .active_in_s(active_in_s), .active_in_e(active_in_e), .active_in_w(active_in_w),
        .freeze_in_n(freeze_in_n), .freeze_in_s(freeze_in_s), .freeze_in_e(freeze_in_e), .freeze_in_w(freeze_in_w),
        .cfg_valid(cfgv_branch), .cfg_data(branch_cfg),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(sel_branch && arr_n_g), .arrived_s(sel_branch && arr_s_g),
        .arrived_e(sel_branch && arr_e_g), .arrived_w(sel_branch && arr_w_g),
        .data_out_n(branch_dn), .data_out_s(branch_ds), .data_out_e(branch_de), .data_out_w(branch_dw),
        .fire_n(branch_fn), .fire_s(branch_fs), .fire_e(branch_fe), .fire_w(branch_fw),
        .ready_out(branch_ready),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(branch_an), .ack_out_s(branch_as_), .ack_out_e(branch_ae), .ack_out_w(branch_aw),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .program_in(sel_branch && program_in_ordinary), .program_done(branch_pd),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s), .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(sel_branch && prog_arr_n_g), .prog_arrived_in_s(sel_branch && prog_arr_s_g),
        .prog_arrived_in_e(sel_branch && prog_arr_e_g), .prog_arrived_in_w(sel_branch && prog_arr_w_g),
        .prog_ack_out_n(branch_pan), .prog_ack_out_s(branch_pas), .prog_ack_out_e(branch_pae), .prog_ack_out_w(branch_paw),
        .status_data_valid()
    );

    accumulator_shell_v1 #(.CELL_ID(CELL_ID)) CORE_ACCUM (
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

    latch_shell_v1 #(.CELL_ID(CELL_ID)) CORE_LATCH (
        .clk(clk), .rst(rst),
        .active_in_n(active_in_n), .active_in_s(active_in_s), .active_in_e(active_in_e), .active_in_w(active_in_w),
        .freeze_in_n(freeze_in_n), .freeze_in_s(freeze_in_s), .freeze_in_e(freeze_in_e), .freeze_in_w(freeze_in_w),
        .cfg_valid(cfgv_latch), .cfg_data(latch_cfg),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(sel_latch && arr_n_g), .arrived_s(sel_latch && arr_s_g),
        .arrived_e(sel_latch && arr_e_g), .arrived_w(sel_latch && arr_w_g),
        .data_out_n(latch_dn), .data_out_s(latch_ds), .data_out_e(latch_de), .data_out_w(latch_dw),
        .fire_n(latch_fn), .fire_s(latch_fs), .fire_e(latch_fe), .fire_w(latch_fw),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(latch_an), .ack_out_s(latch_as_), .ack_out_e(latch_ae), .ack_out_w(latch_aw),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .program_in(sel_latch && program_in_ordinary), .program_done(latch_pd),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s), .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(sel_latch && prog_arr_n_g), .prog_arrived_in_s(sel_latch && prog_arr_s_g),
        .prog_arrived_in_e(sel_latch && prog_arr_e_g), .prog_arrived_in_w(sel_latch && prog_arr_w_g),
        .prog_ack_out_n(latch_pan), .prog_ack_out_s(latch_pas), .prog_ack_out_e(latch_pae), .prog_ack_out_w(latch_paw),
        .ready_out(latch_ready), .status_latched()
    );

    sequencer_shell_v1 #(.CELL_ID(CELL_ID)) CORE_SEQ (
        .clk(clk), .rst(rst),
        .active_in_n(active_in_n), .active_in_s(active_in_s), .active_in_e(active_in_e), .active_in_w(active_in_w),
        .freeze_in_n(freeze_in_n), .freeze_in_s(freeze_in_s), .freeze_in_e(freeze_in_e), .freeze_in_w(freeze_in_w),
        .cfg_valid(cfgv_seq), .cfg_data(seq_cfg),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(sel_seq && arr_n_g), .arrived_s(sel_seq && arr_s_g),
        .arrived_e(sel_seq && arr_e_g), .arrived_w(sel_seq && arr_w_g),
        .data_out_n(seq_dn), .data_out_s(seq_ds), .data_out_e(seq_de), .data_out_w(seq_dw),
        .fire_n(seq_fn), .fire_s(seq_fs), .fire_e(seq_fe), .fire_w(seq_fw),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(seq_an), .ack_out_s(seq_as_), .ack_out_e(seq_ae), .ack_out_w(seq_aw),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .program_in(sel_seq && program_in_ordinary), .program_done(seq_pd),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s), .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(sel_seq && prog_arr_n_g), .prog_arrived_in_s(sel_seq && prog_arr_s_g),
        .prog_arrived_in_e(sel_seq && prog_arr_e_g), .prog_arrived_in_w(sel_seq && prog_arr_w_g),
        .prog_ack_out_n(seq_pan), .prog_ack_out_s(seq_pas), .prog_ack_out_e(seq_pae), .prog_ack_out_w(seq_paw),
        .ready_out(seq_ready), .status_seq_index()
    );

    command_shell_v1 #(.CELL_ID(CELL_ID)) CORE_COMMAND (
        .clk(clk), .rst(rst),
        .active_in_n(active_in_n), .active_in_s(active_in_s), .active_in_e(active_in_e), .active_in_w(active_in_w),
        .freeze_in_n(freeze_in_n), .freeze_in_s(freeze_in_s), .freeze_in_e(freeze_in_e), .freeze_in_w(freeze_in_w),
        .cfg_valid(cfgv_command), .cfg_data(command_cfg),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(sel_command && arr_n_g), .arrived_s(sel_command && arr_s_g),
        .arrived_e(sel_command && arr_e_g), .arrived_w(sel_command && arr_w_g),
        .ack_out_n(command_an), .ack_out_s(command_as_), .ack_out_e(command_ae), .ack_out_w(command_aw),
        .ready_out(command_ready),
        .freeze_out_n(command_fzn), .freeze_out_s(command_fzs), .freeze_out_e(command_fze), .freeze_out_w(command_fzw),
        .program_out_n(command_pon), .program_out_s(command_pos), .program_out_e(command_poe), .program_out_w(command_pow),
        .prog_data_out_n(command_pdon), .prog_data_out_s(command_pdos), .prog_data_out_e(command_pdoe), .prog_data_out_w(command_pdow),
        .prog_arrived_out_n(command_paon), .prog_arrived_out_s(command_paos), .prog_arrived_out_e(command_paoe), .prog_arrived_out_w(command_paow),
        .prog_ack_in_n(prog_ack_in_n), .prog_ack_in_s(prog_ack_in_s), .prog_ack_in_e(prog_ack_in_e), .prog_ack_in_w(prog_ack_in_w),
        .program_in(sel_command && program_in_ordinary), .program_done(),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s), .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(sel_command && prog_arr_n_g), .prog_arrived_in_s(sel_command && prog_arr_s_g),
        .prog_arrived_in_e(sel_command && prog_arr_e_g), .prog_arrived_in_w(sel_command && prog_arr_w_g),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .status_active(), .status_freeze_state()
    );

    // ── Real output mux -- exactly one core's outputs ever reach the
    // external ports, selected by the SAME registered core_select
    // used for arrival/config gating. ──
    assign data_out_n = sel_nano ? nano_dn : sel_adder ? adder_dn : sel_ram ? ram_dn :
                         sel_compare ? compare_dn : sel_branch ? branch_dn : sel_accum ? accum_dn :
                         sel_latch ? latch_dn : sel_seq ? seq_dn : 32'h0;
    assign data_out_s = sel_nano ? nano_ds : sel_adder ? adder_ds : sel_ram ? ram_ds :
                         sel_compare ? compare_ds : sel_branch ? branch_ds : sel_accum ? accum_ds :
                         sel_latch ? latch_ds : sel_seq ? seq_ds : 32'h0;
    assign data_out_e = sel_nano ? nano_de : sel_adder ? adder_de : sel_ram ? ram_de :
                         sel_compare ? compare_de : sel_branch ? branch_de : sel_accum ? accum_de :
                         sel_latch ? latch_de : sel_seq ? seq_de : 32'h0;
    assign data_out_w = sel_nano ? nano_dw : sel_adder ? adder_dw : sel_ram ? ram_dw :
                         sel_compare ? compare_dw : sel_branch ? branch_dw : sel_accum ? accum_dw :
                         sel_latch ? latch_dw : sel_seq ? seq_dw : 32'h0;

    assign fire_n = sel_nano ? nano_fn : sel_adder ? adder_fn : sel_ram ? ram_fn :
                    sel_compare ? compare_fn : sel_branch ? branch_fn : sel_accum ? accum_fn :
                    sel_latch ? latch_fn : sel_seq ? seq_fn : 1'b0;
    assign fire_s = sel_nano ? nano_fs : sel_adder ? adder_fs : sel_ram ? ram_fs :
                    sel_compare ? compare_fs : sel_branch ? branch_fs : sel_accum ? accum_fs :
                    sel_latch ? latch_fs : sel_seq ? seq_fs : 1'b0;
    assign fire_e = sel_nano ? nano_fe : sel_adder ? adder_fe : sel_ram ? ram_fe :
                    sel_compare ? compare_fe : sel_branch ? branch_fe : sel_accum ? accum_fe :
                    sel_latch ? latch_fe : sel_seq ? seq_fe : 1'b0;
    assign fire_w = sel_nano ? nano_fw : sel_adder ? adder_fw : sel_ram ? ram_fw :
                    sel_compare ? compare_fw : sel_branch ? branch_fw : sel_accum ? accum_fw :
                    sel_latch ? latch_fw : sel_seq ? seq_fw : 1'b0;

    assign ack_out_n = sel_nano ? nano_an : sel_adder ? adder_an : sel_ram ? ram_an :
                       sel_compare ? compare_an : sel_branch ? branch_an : sel_accum ? accum_an :
                       sel_latch ? latch_an : sel_seq ? seq_an : sel_command ? command_an : 1'b0;
    assign ack_out_s = sel_nano ? nano_as_ : sel_adder ? adder_as_ : sel_ram ? ram_as_ :
                       sel_compare ? compare_as_ : sel_branch ? branch_as_ : sel_accum ? accum_as_ :
                       sel_latch ? latch_as_ : sel_seq ? seq_as_ : sel_command ? command_as_ : 1'b0;
    assign ack_out_e = sel_nano ? nano_ae : sel_adder ? adder_ae : sel_ram ? ram_ae :
                       sel_compare ? compare_ae : sel_branch ? branch_ae : sel_accum ? accum_ae :
                       sel_latch ? latch_ae : sel_seq ? seq_ae : sel_command ? command_ae : 1'b0;
    assign ack_out_w = sel_nano ? nano_aw : sel_adder ? adder_aw : sel_ram ? ram_aw :
                       sel_compare ? compare_aw : sel_branch ? branch_aw : sel_accum ? accum_aw :
                       sel_latch ? latch_aw : sel_seq ? seq_aw : sel_command ? command_aw : 1'b0;

    assign ready_out = sel_nano ? nano_ready : sel_adder ? adder_ready : sel_ram ? ram_ready :
                        sel_compare ? compare_ready : sel_branch ? branch_ready : sel_accum ? accum_ready :
                        sel_latch ? latch_ready : sel_seq ? seq_ready : sel_command ? command_ready : 1'b0;

    assign program_done = sel_nano ? nano_pd : sel_adder ? adder_pd : sel_ram ? ram_pd :
                           sel_compare ? compare_pd : sel_branch ? branch_pd : sel_accum ? accum_pd :
                           sel_latch ? latch_pd : sel_seq ? seq_pd : 1'b0;   // command has no receive-side program_done wired

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

    assign prog_ack_out_n = select_ack_n || (sel_nano ? nano_pan : sel_adder ? adder_pan : sel_ram ? ram_pan :
                             sel_compare ? compare_pan : sel_branch ? branch_pan : sel_accum ? accum_pan :
                             sel_latch ? latch_pan : sel_seq ? seq_pan : 1'b0);
    assign prog_ack_out_s = select_ack_s || (sel_nano ? nano_pas : sel_adder ? adder_pas : sel_ram ? ram_pas :
                             sel_compare ? compare_pas : sel_branch ? branch_pas : sel_accum ? accum_pas :
                             sel_latch ? latch_pas : sel_seq ? seq_pas : 1'b0);
    assign prog_ack_out_e = select_ack_e || (sel_nano ? nano_pae : sel_adder ? adder_pae : sel_ram ? ram_pae :
                             sel_compare ? compare_pae : sel_branch ? branch_pae : sel_accum ? accum_pae :
                             sel_latch ? latch_pae : sel_seq ? seq_pae : 1'b0);
    assign prog_ack_out_w = select_ack_w || (sel_nano ? nano_paw : sel_adder ? adder_paw : sel_ram ? ram_paw :
                             sel_compare ? compare_paw : sel_branch ? branch_paw : sel_accum ? accum_paw :
                             sel_latch ? latch_paw : sel_seq ? seq_paw : 1'b0);

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
