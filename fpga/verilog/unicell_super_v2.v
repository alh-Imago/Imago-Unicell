// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// unicell_super_v2.v — v2, points.md #421/#422: unicell_super_v1.v
// (#304/#315/#317/#319, real Quartus baseline 213 ALM / 200.76 MHz at
// #322) cloned per this project's own standing discipline (never
// modify a proven file in place) to add a 7th real core, SEL_SEQ
// (`sequencer_cell_v1.v`), the first promotion from #418's own real
// assessment of session-built specialist modules. Everything below
// this point is unchanged from v1 except the SEL_SEQ additions,
// clearly marked "v2" at each site.
//
// unicell_super_v1.v's own original header, preserved for context:
// the FIRST real "super carrier shell" / fat
// unicell (points.md #304, #315, #317, #319). Holds all 6 real,
// already-proven cores (nano gate-tree, RAM, adder, accumulator,
// comparator, latch) physically present simultaneously inside ONE
// cell, MUTUALLY EXCLUSIVE (Alan, 2026-08-15) — exactly one is active
// at a time, selected by configuration, not synthesis. Directly
// reverses #263's own logged ICM-portability collapse: core choice is
// a CONFIG-time decision again, the same guarantee the ICM format
// depended on before #253's SHELL/CORE model broke it — though #314
// already established this is genuinely NEW territory, not a
// restoration of anything the FULL cell ever had.
//
// SUPER_LATCH[79:0] layout — 80 bits, a deliberately round number with
// real reserved headroom (Alan, 2026-08-15), not packed tight to
// exactly today's needs:
//   [4:0]    core_select   — 0=nano 1=RAM 2=adder 3=accumulator
//                            4=comparator 5=latch, 6-31 reserved
//                            (#317: must stay genuinely extensible)
//   [46:5]   core_config   — 42 bits, UNION not struct (#315): sized to
//                            the single widest real core (RAM, 42 bits),
//                            reinterpreted per core_select, not summed
//                            across all six. Every non-nano core's own
//                            real cfg_data layout already starts at bit
//                            0 of its own space, confirmed directly
//                            against each core's RTL before this was
//                            built — so core_config[N:0] maps onto each
//                            one's own real fields with zero reshuffling.
//   [66:47]  addon_config  — 20 bits, IDENTICAL to #313's own proposed
//                            ADDON_LATCH[19:0] layout, unchanged
//   [79:67]  reserved      — 13 bits, genuine future headroom (not
//                            "shell routing" as #315's own first-pass
//                            categorization called it — routing_mask/
//                            cardinal_edge/ready turned out to be
//                            NANO-SPECIFIC fields, already accounted
//                            for within nano's own share of
//                            core_config, not a separate universal
//                            layer every core needs — a real
//                            correction made before building, not
//                            after)
//
// SCOPE, stated honestly: nano's own EXTRA ports beyond the basic
// cardinal handshake — command-cell mode (cmd_in/cmd_out), feedback
// (fb_internal_in/a_reemit_in/a_update_in/a_self_update_in), and the
// dedicated dynamic-reprogramming channel (program_in/prog_data_in_*/
// prog_arrived_in_*) — are OUT OF SCOPE for this first build. When
// nano is the selected core, all of those inputs are tied to their
// safe/inactive defaults. This is a real, known limitation of this
// first version, not something hidden — a plain nano gate-tree core
// works fully; nano's command-cell/feedback/reprogram extras do not.
//
// ISOLATION MECHANISM: every one of the 6 cores is always physically
// instantiated and clocked (FPGA fabric has no per-core power gating),
// but only the SELECTED core ever sees genuine `arrived_*`/`cfg_valid`
// — every other core's inputs are gated to 0, so non-selected cores
// never capture, never load config, never fire. This is the concrete
// mechanism behind #304's own "insular" cost hypothesis — real ALM/
// timing cost is measurable in Quartus, not assumed.
`default_nettype none
`timescale 1ns / 1ps

module unicell_super_v2 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire         rst,

    input  wire         cfg_valid,
    input  wire [79:0]  cfg_data,      // SUPER_LATCH, see header

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    // ── nano's own dynamic-reprogramming channel, exposed at the shell
    // level (points.md #390) -- closes the gap this file's own header
    // comment already documented honestly as out of scope for the first
    // build. Gated to only reach nano when it's the CURRENTLY ACTIVE
    // selected core (sel_active_nano, the same convention already used
    // for arrived_*), matching the "only the selected core ever sees
    // genuine activity" isolation principle established elsewhere in
    // this file. Inert (ties to nano's own safe defaults) whenever any
    // other core is selected. ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,

    output wire [4:0]   status_core_select   // debug tap only
);

    // ── SUPER_LATCH, committed atomically on cfg_valid — same
    // whole-word-commit convention as every other core here. ──
    reg [79:0] super_latch = 80'h0;
    always @(posedge clk) begin
        if (rst) super_latch <= 80'h0;
        else if (cfg_valid) super_latch <= cfg_data;
    end

    // ── REGISTERED select/config -- reflects the SETTLED configuration,
    // used for ONGOING operation (arrival gating, output mux). ──
    wire [4:0]  core_select  = super_latch[4:0];
    wire [41:0] core_config  = super_latch[46:5];
    wire [19:0] addon_config = super_latch[66:47];
    // super_latch[79:67] deliberately unused -- reserved headroom (#317)

    // ── INCOMING select/config -- the value ABOUT TO BE committed,
    // straight off cfg_data. Real bug found and fixed here (2026-08-15,
    // logged as #320): gating a NEW config's delivery on the OLD
    // (pre-update) registered core_select means a config switching TO
    // a new core can never actually reach that core -- exactly the same
    // class of stale-value race already root-caused once this session
    // (#306). The core_select/core_config a LOAD must be gated on is
    // the one ARRIVING this cycle, not the one still sitting in the
    // register from before. ──
    wire [4:0]  incoming_select  = cfg_data[4:0];
    wire [41:0] incoming_config  = cfg_data[46:5];

    localparam [4:0] SEL_NANO = 5'd0, SEL_RAM = 5'd1, SEL_ADDER = 5'd2,
                      SEL_ACC = 5'd3, SEL_CMP = 5'd4, SEL_LATCH = 5'd5,
                      SEL_SEQ = 5'd6;   // v2, points.md #421/#422: the sequencer,
                                        // promoted per #418's own assessment

    // ── Per-core gated cfg_valid — only the SELECTED core ever
    // genuinely loads config; the other 5 stay at their reset default
    // (all-zero) forever, matching every core's own confirmed reset
    // behavior. ──
    wire cfg_valid_nano  = cfg_valid && (incoming_select == SEL_NANO);
    wire cfg_valid_ram   = cfg_valid && (incoming_select == SEL_RAM);
    wire cfg_valid_adder = cfg_valid && (incoming_select == SEL_ADDER);
    wire cfg_valid_acc   = cfg_valid && (incoming_select == SEL_ACC);
    wire cfg_valid_cmp   = cfg_valid && (incoming_select == SEL_CMP);
    wire cfg_valid_latch = cfg_valid && (incoming_select == SEL_LATCH);
    wire cfg_valid_seq   = cfg_valid && (incoming_select == SEL_SEQ);

    // ── Per-core gated arrivals — only the selected core ever sees a
    // genuine arrival; every other core stays completely idle, no
    // captures attempted at all (not merely "no offers"). ──
    wire sel_active_nano  = (core_select == SEL_NANO);
    wire sel_active_ram   = (core_select == SEL_RAM);
    wire sel_active_adder = (core_select == SEL_ADDER);
    wire sel_active_acc   = (core_select == SEL_ACC);
    wire sel_active_cmp   = (core_select == SEL_CMP);
    wire sel_active_latch = (core_select == SEL_LATCH);
    wire sel_active_seq   = (core_select == SEL_SEQ);

    // ── nano's own real cfg_data reconstructed from core_config's
    // shared low bits, placed at nano's OWN real field positions
    // (topology[9:0], ready[13], routing_mask[69:64],
    // cardinal_edge[75:70] -- confirmed directly against unicell_
    // stripped_v1.v before building this). Everything else in nano's
    // 128-bit space (including [127:96] out_buffer, which is runtime-
    // computed state, not config) is zeroed. ──
    wire [127:0] nano_cfg_data;
    assign nano_cfg_data[9:0]    = incoming_config[9:0];    // topology
    assign nano_cfg_data[12:10]  = 3'b0;
    assign nano_cfg_data[13]     = incoming_config[10];     // ready
    assign nano_cfg_data[63:14]  = 50'b0;
    assign nano_cfg_data[69:64]  = incoming_config[16:11];  // routing_mask
    assign nano_cfg_data[75:70]  = incoming_config[22:17];  // cardinal_edge
    assign nano_cfg_data[127:76] = 52'b0;

    // ── REAL EXTENSION (points.md #522), matching unicell_super_v1.v's
    // own identical fix (this file duplicates the instantiation rather
    // than wrapping v1, so needed the same fix independently): nano's
    // own real hold_in/fb_internal_in/a_reemit_in/a_update_in/
    // a_self_update_in ports, previously tied to constant 0, exposed
    // via core_config bits [27:23]. See v1's own header comment for
    // the full real reasoning (ports not cfg_data fields, driven
    // combinationally not latched, sel_active_nano-gated, and the
    // honest note that this exposes the capability without yet making
    // it lightweight-runtime-toggleable). ──
    wire nano_hold_in          = incoming_config[23] && sel_active_nano;
    wire nano_fb_internal_in   = incoming_config[24] && sel_active_nano;
    wire nano_a_reemit_in      = incoming_config[25] && sel_active_nano;
    wire nano_a_update_in      = incoming_config[26] && sel_active_nano;
    wire nano_a_self_update_in = incoming_config[27] && sel_active_nano;

    wire [31:0] n_dout_n, n_dout_s, n_dout_e, n_dout_w;
    wire n_fire_n, n_fire_s, n_fire_e, n_fire_w, n_ready, n_ack_n, n_ack_s, n_ack_e, n_ack_w;
    wire n_program_done;

    unicell_stripped_v1 #(.CELL_ID(CELL_ID)) CORE_NANO (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid_nano), .cfg_data(nano_cfg_data),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n && sel_active_nano), .arrived_s(arrived_s && sel_active_nano),
        .arrived_e(arrived_e && sel_active_nano), .arrived_w(arrived_w && sel_active_nano),
        .data_out_n(n_dout_n), .data_out_s(n_dout_s), .data_out_e(n_dout_e), .data_out_w(n_dout_w),
        .fire_n(n_fire_n), .fire_s(n_fire_s), .fire_e(n_fire_e), .fire_w(n_fire_w),
        .ready_out(n_ready),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(n_ack_n), .ack_out_s(n_ack_s), .ack_out_e(n_ack_e), .ack_out_w(n_ack_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(freeze_in),
        .hold_in(nano_hold_in), .fb_internal_in(nano_fb_internal_in),
        .a_reemit_in(nano_a_reemit_in), .a_update_in(nano_a_update_in), .a_self_update_in(nano_a_self_update_in),
        .program_in(program_in && sel_active_nano), .program_done(n_program_done),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s),
        .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(prog_arrived_in_n && sel_active_nano),
        .prog_arrived_in_s(prog_arrived_in_s && sel_active_nano),
        .prog_arrived_in_e(prog_arrived_in_e && sel_active_nano),
        .prog_arrived_in_w(prog_arrived_in_w && sel_active_nano),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    // ── RAM, adder, accumulator, comparator, latch — every one of
    // these five already has its own real cfg_data layout starting at
    // bit 0 of its own space, confirmed directly against each core's
    // RTL, so core_config[N-1:0] passes straight through with zero
    // reshuffling. ──
    wire [31:0] r_dout_n, r_dout_s, r_dout_e, r_dout_w;
    wire r_fire_n, r_fire_s, r_fire_e, r_fire_w, r_ready, r_ack_n, r_ack_s, r_ack_e, r_ack_w;

    ram_cell_v1 #(.CELL_ID(CELL_ID)) CORE_RAM (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid_ram), .cfg_data({22'b0, incoming_config[41:0]}),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n && sel_active_ram), .arrived_s(arrived_s && sel_active_ram),
        .arrived_e(arrived_e && sel_active_ram), .arrived_w(arrived_w && sel_active_ram),
        .data_out_n(r_dout_n), .data_out_s(r_dout_s), .data_out_e(r_dout_e), .data_out_w(r_dout_w),
        .fire_n(r_fire_n), .fire_s(r_fire_s), .fire_e(r_fire_e), .fire_w(r_fire_w),
        .ready_out(r_ready),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(r_ack_n), .ack_out_s(r_ack_s), .ack_out_e(r_ack_e), .ack_out_w(r_ack_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_in), .status_data_valid()
    );

    wire [31:0] a_dout_n, a_dout_s, a_dout_e, a_dout_w;
    wire a_fire_n, a_fire_s, a_fire_e, a_fire_w, a_ready, a_ack_n, a_ack_s, a_ack_e, a_ack_w;

    adder_cell_v1 #(.CELL_ID(CELL_ID)) CORE_ADDER (
        .clk(clk), .rst(rst),
        // Widened #521, matching the same fix in unicell_super_v1.v
        // (this file duplicates that instantiation rather than
        // wrapping it, so needed the identical fix independently).
        .cfg_valid(cfg_valid_adder), .cfg_data({55'b0, incoming_config[8:0]}),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n && sel_active_adder), .arrived_s(arrived_s && sel_active_adder),
        .arrived_e(arrived_e && sel_active_adder), .arrived_w(arrived_w && sel_active_adder),
        .data_out_n(a_dout_n), .data_out_s(a_dout_s), .data_out_e(a_dout_e), .data_out_w(a_dout_w),
        .fire_n(a_fire_n), .fire_s(a_fire_s), .fire_e(a_fire_e), .fire_w(a_fire_w),
        .ready_out(a_ready),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(a_ack_n), .ack_out_s(a_ack_s), .ack_out_e(a_ack_e), .ack_out_w(a_ack_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_in), .status_data_valid(), .status_a_arrived()
    );

    wire [31:0] c_dout_n, c_dout_s, c_dout_e, c_dout_w;
    wire c_fire_n, c_fire_s, c_fire_e, c_fire_w, c_ready, c_ack_n, c_ack_s, c_ack_e, c_ack_w;

    accumulator_cell_v1 #(.CELL_ID(CELL_ID)) CORE_ACC (
        .clk(clk), .rst(rst),
        // Widened #506/#515, matching the same fix in unicell_super_v1.v
        // (this file duplicates that instantiation rather than wrapping
        // it, so needed the identical fix independently).
        .cfg_valid(cfg_valid_acc), .cfg_data({27'b0, incoming_config[36:0]}),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n && sel_active_acc), .arrived_s(arrived_s && sel_active_acc),
        .arrived_e(arrived_e && sel_active_acc), .arrived_w(arrived_w && sel_active_acc),
        .data_out_n(c_dout_n), .data_out_s(c_dout_s), .data_out_e(c_dout_e), .data_out_w(c_dout_w),
        .fire_n(c_fire_n), .fire_s(c_fire_s), .fire_e(c_fire_e), .fire_w(c_fire_w),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(c_ack_n), .ack_out_s(c_ack_s), .ack_out_e(c_ack_e), .ack_out_w(c_ack_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_in), .ready_out(c_ready), .status_negative()
    );

    wire [31:0] m_dout_n, m_dout_s, m_dout_e, m_dout_w;
    wire m_fire_n, m_fire_s, m_fire_e, m_fire_w, m_ready, m_ack_n, m_ack_s, m_ack_e, m_ack_w;

    compare_cell_v1 #(.CELL_ID(CELL_ID)) CORE_CMP (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid_cmp), .cfg_data({24'b0, incoming_config[39:0]}),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n && sel_active_cmp), .arrived_s(arrived_s && sel_active_cmp),
        .arrived_e(arrived_e && sel_active_cmp), .arrived_w(arrived_w && sel_active_cmp),
        .data_out_n(m_dout_n), .data_out_s(m_dout_s), .data_out_e(m_dout_e), .data_out_w(m_dout_w),
        .fire_n(m_fire_n), .fire_s(m_fire_s), .fire_e(m_fire_e), .fire_w(m_fire_w),
        .ready_out(m_ready),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(m_ack_n), .ack_out_s(m_ack_s), .ack_out_e(m_ack_e), .ack_out_w(m_ack_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_in), .status_data_valid()
    );

    wire [31:0] l_dout_n, l_dout_s, l_dout_e, l_dout_w;
    wire l_fire_n, l_fire_s, l_fire_e, l_fire_w, l_ready, l_ack_n, l_ack_s, l_ack_e, l_ack_w;

    latch_cell_v1 #(.CELL_ID(CELL_ID)) CORE_LATCH (
        .clk(clk), .rst(rst),
        // Widened #522, matching the same fix in unicell_super_v1.v.
        .cfg_valid(cfg_valid_latch), .cfg_data({48'b0, incoming_config[15:0]}),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n && sel_active_latch), .arrived_s(arrived_s && sel_active_latch),
        .arrived_e(arrived_e && sel_active_latch), .arrived_w(arrived_w && sel_active_latch),
        .data_out_n(l_dout_n), .data_out_s(l_dout_s), .data_out_e(l_dout_e), .data_out_w(l_dout_w),
        .fire_n(l_fire_n), .fire_s(l_fire_s), .fire_e(l_fire_e), .fire_w(l_fire_w),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(l_ack_n), .ack_out_s(l_ack_s), .ack_out_e(l_ack_e), .ack_out_w(l_ack_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_in), .ready_out(l_ready), .status_latched()
    );

    // ── v2, points.md #421/#422: sequencer_cell_v1 as SEL_SEQ, the
    // first core promoted per #418's own real assessment -- cycles
    // through a short, fixed, host-configured value list via the
    // ORDINARY cardinal ports, real distinct territory none of the
    // other 6 cores cover. cfg_data field map matches sequencer_cell_
    // v1.v's own header exactly: [7:0]/[15:8]/[23:16]/[31:24] the 4
    // values, [33:32] SEQUENCE_LEN, [37:34] downstream_mask -- 38 of
    // the 42-bit core_config budget used, 4 spare. ──
    wire [31:0] q_dout_n, q_dout_s, q_dout_e, q_dout_w;
    wire q_fire_n, q_fire_s, q_fire_e, q_fire_w, q_ready, q_ack_n, q_ack_s, q_ack_e, q_ack_w;

    sequencer_cell_v1 #(.CELL_ID(CELL_ID)) CORE_SEQ (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid_seq), .cfg_data({26'b0, incoming_config[37:0]}),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n && sel_active_seq), .arrived_s(arrived_s && sel_active_seq),
        .arrived_e(arrived_e && sel_active_seq), .arrived_w(arrived_w && sel_active_seq),
        .data_out_n(q_dout_n), .data_out_s(q_dout_s), .data_out_e(q_dout_e), .data_out_w(q_dout_w),
        .fire_n(q_fire_n), .fire_s(q_fire_s), .fire_e(q_fire_e), .fire_w(q_fire_w),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(q_ack_n), .ack_out_s(q_ack_s), .ack_out_e(q_ack_e), .ack_out_w(q_ack_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_in), .ready_out(q_ready), .status_seq_index()
    );

    // ── Output mux — only the SELECTED core's outputs ever reach the
    // real fabric. ──
    reg [31:0] mux_dout_n, mux_dout_s, mux_dout_e, mux_dout_w;
    reg mux_fire_n, mux_fire_s, mux_fire_e, mux_fire_w;
    reg mux_ready;
    reg mux_ack_n, mux_ack_s, mux_ack_e, mux_ack_w;
    reg mux_program_done;

    always @(*) begin
        case (core_select)
            SEL_NANO: begin
                mux_dout_n=n_dout_n; mux_dout_s=n_dout_s; mux_dout_e=n_dout_e; mux_dout_w=n_dout_w;
                mux_fire_n=n_fire_n; mux_fire_s=n_fire_s; mux_fire_e=n_fire_e; mux_fire_w=n_fire_w;
                mux_ready=n_ready;
                mux_ack_n=n_ack_n; mux_ack_s=n_ack_s; mux_ack_e=n_ack_e; mux_ack_w=n_ack_w;
                mux_program_done=n_program_done;
            end
            SEL_RAM: begin
                mux_dout_n=r_dout_n; mux_dout_s=r_dout_s; mux_dout_e=r_dout_e; mux_dout_w=r_dout_w;
                mux_fire_n=r_fire_n; mux_fire_s=r_fire_s; mux_fire_e=r_fire_e; mux_fire_w=r_fire_w;
                mux_ready=r_ready;
                mux_ack_n=r_ack_n; mux_ack_s=r_ack_s; mux_ack_e=r_ack_e; mux_ack_w=r_ack_w; mux_program_done=1'b0;
            end
            SEL_ADDER: begin
                mux_dout_n=a_dout_n; mux_dout_s=a_dout_s; mux_dout_e=a_dout_e; mux_dout_w=a_dout_w;
                mux_fire_n=a_fire_n; mux_fire_s=a_fire_s; mux_fire_e=a_fire_e; mux_fire_w=a_fire_w;
                mux_ready=a_ready;
                mux_ack_n=a_ack_n; mux_ack_s=a_ack_s; mux_ack_e=a_ack_e; mux_ack_w=a_ack_w; mux_program_done=1'b0;
            end
            SEL_ACC: begin
                mux_dout_n=c_dout_n; mux_dout_s=c_dout_s; mux_dout_e=c_dout_e; mux_dout_w=c_dout_w;
                mux_fire_n=c_fire_n; mux_fire_s=c_fire_s; mux_fire_e=c_fire_e; mux_fire_w=c_fire_w;
                mux_ready=c_ready;
                mux_ack_n=c_ack_n; mux_ack_s=c_ack_s; mux_ack_e=c_ack_e; mux_ack_w=c_ack_w; mux_program_done=1'b0;
            end
            SEL_CMP: begin
                mux_dout_n=m_dout_n; mux_dout_s=m_dout_s; mux_dout_e=m_dout_e; mux_dout_w=m_dout_w;
                mux_fire_n=m_fire_n; mux_fire_s=m_fire_s; mux_fire_e=m_fire_e; mux_fire_w=m_fire_w;
                mux_ready=m_ready;
                mux_ack_n=m_ack_n; mux_ack_s=m_ack_s; mux_ack_e=m_ack_e; mux_ack_w=m_ack_w; mux_program_done=1'b0;
            end
            SEL_LATCH: begin
                mux_dout_n=l_dout_n; mux_dout_s=l_dout_s; mux_dout_e=l_dout_e; mux_dout_w=l_dout_w;
                mux_fire_n=l_fire_n; mux_fire_s=l_fire_s; mux_fire_e=l_fire_e; mux_fire_w=l_fire_w;
                mux_ready=l_ready;
                mux_ack_n=l_ack_n; mux_ack_s=l_ack_s; mux_ack_e=l_ack_e; mux_ack_w=l_ack_w; mux_program_done=1'b0;
            end
            SEL_SEQ: begin
                mux_dout_n=q_dout_n; mux_dout_s=q_dout_s; mux_dout_e=q_dout_e; mux_dout_w=q_dout_w;
                mux_fire_n=q_fire_n; mux_fire_s=q_fire_s; mux_fire_e=q_fire_e; mux_fire_w=q_fire_w;
                mux_ready=q_ready;
                mux_ack_n=q_ack_n; mux_ack_s=q_ack_s; mux_ack_e=q_ack_e; mux_ack_w=q_ack_w; mux_program_done=1'b0;
            end
            default: begin  // unassigned core_select values (7-31) -- inert, not X
                mux_dout_n=32'h0; mux_dout_s=32'h0; mux_dout_e=32'h0; mux_dout_w=32'h0;
                mux_fire_n=1'b0; mux_fire_s=1'b0; mux_fire_e=1'b0; mux_fire_w=1'b0;
                mux_ready=1'b0;
                mux_ack_n=1'b0; mux_ack_s=1'b0; mux_ack_e=1'b0; mux_ack_w=1'b0; mux_program_done=1'b0;
            end
        endcase
    end

    // ── The three real ADDONs (#311), wired on the periphery, always
    // present regardless of which core is selected (#310's own split:
    // addons are core-independent, on the periphery). Order matches
    // #312's own proven wiring: nibble_mask -> shift/lane -> invert. ──
    wire [31:0] after_mask, after_shiftlane, addon_out;

    nibble_mask_addon_v1 ADDON_NM (
        .mask_en(addon_config[8]), .nibble_mask(addon_config[7:0]),
        .data_in(mux_dout_n), .data_out(after_mask)
    );
    shift_lane_addon_v1 ADDON_SL (
        .direction(addon_config[15]), .shift_en(addon_config[14]),
        .shift_amt(addon_config[13:9]), .lane_cut(addon_config[18:16]),
        .data_in(after_mask), .data_out(after_shiftlane)
    );
    invert_addon_v1 ADDON_INV (
        .invert_en(addon_config[19]),
        .data_in(after_shiftlane), .data_out(addon_out)
    );

    assign data_out_n = addon_out;
    assign data_out_s = addon_out;
    assign data_out_e = addon_out;
    assign data_out_w = addon_out;

    assign fire_n = mux_fire_n;
    assign fire_s = mux_fire_s;
    assign fire_e = mux_fire_e;
    assign fire_w = mux_fire_w;
    assign ready_out = mux_ready;
    assign program_done = mux_program_done;
    assign ack_out_n = mux_ack_n;
    assign ack_out_s = mux_ack_s;
    assign ack_out_e = mux_ack_e;
    assign ack_out_w = mux_ack_w;

    assign status_core_select = core_select;

endmodule
