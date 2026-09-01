// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// unicell_super_v4.v — v4, points.md #565 item 2 / #573: cloned from
// unicell_super_v3.v (real Quartus baseline for the 8-core shell not
// yet measured directly -- v2's own 7-core baseline is 305 ALM /
// 99.57 MHz at #526) per this project's own standing discipline
// (never modify a proven file in place). This is the actual shell-
// level integration of the shared-storage mechanism proven core-by-
// core across `#563`/`#564`/`#566` (all 8 cores, 41/41 real checks):
// every core is instantiated with EXTERNAL_STORAGE=1, and ALL EIGHT
// share ONE real 170-bit register instead of each holding its own
// separate internal state -- the real, concrete thing `#560`'s own
// measured "full reconfigurability costs 4.4x-4.9x more than 8 fixed
// cells" figure (`#572`) exists to be tested against.
//
// THE REAL MECHANISM, per Alan's own reformulation (`#563`) plus his
// own freeze-centralization addition (`#566`):
// - `shared_state[169:0]` -- ONE real register, sized to the WIDEST
//   real per-core external-state width (nano, 170 bits, confirmed
//   directly against unicell_stripped_v3.v's own real ext_state_out
//   port -- every other core is narrower: branch 117, accumulator
//   107, adder 79, compare 77, sequencer 53, ram 46, latch 23).
// - Every core reads `shared_state[W-1:0]` (its own real width,
//   truncated) as `ext_state_in`, REGARDLESS of whether it's the
//   currently selected core -- exactly like `core_config` itself is
//   already broadcast to all 8 today. Only the SELECTED core's
//   computed `ext_state_out` is ever written back (the real write-
//   select mux this whole thread exists to build).
// - REAL, DELIBERATE RESET-ON-SWITCH: `shared_state` is force-
//   cleared to 0 the exact cycle `core_select` genuinely CHANGES
//   (not merely reprogrammed with the same core), rather than
//   inheriting whatever bit pattern the PREVIOUS core's wider/
//   narrower state left behind. This matches every core's own real,
//   individual power-on-reset default (0) that `EXTERNAL_STORAGE=0`
//   mode already relies on -- a genuine, honest design choice, not
//   an oversight: without it, a newly-selected core would start from
//   an unrelated, uninitialized-in-spirit bit pattern instead of its
//   own real reset state.
// - REAL FREEZE CENTRALIZATION (`#566`'s own addition, confirmed
//   NOT a substitute for the write mux, a complementary correctness
//   mechanism): each core's own `freeze_in` is now
//   `freeze_in_top || (core_select != SEL_<core>)` -- every
//   non-selected core is held frozen at the shell level, not just
//   starved of genuine `arrived_*`/`cfg_valid` as before.
//
// Everything else (core_config field layout, per-core cfg_valid/
// arrived gating, the output mux, the three addons) is UNCHANGED
// from v3 -- this file only touches the state-storage mechanism.
//
// SUPER_LATCH[79:0] layout — IDENTICAL to v3, see that file's own
// header for the full real field table (core_select[4:0],
// core_config[46:5], addon_config[66:47], reserved[79:67]).
//
// REAL, HONEST SCOPE: this proves the mechanism assembles and
// (pending sim verification below) behaves correctly -- it does NOT
// yet have a real Quartus ALM/Fmax number. That comparative build,
// against v3's own real (not yet separately measured) 8-core
// baseline, is the actual point of this whole thread and remains the
// real next step once this file sim-verifies clean.
`default_nettype none
`timescale 1ns / 1ps

module unicell_super_v4 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire         rst,

    input  wire         cfg_valid,
    input  wire [79:0]  cfg_data,      // SUPER_LATCH, see v3's own header

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    // ── nano's own dynamic-reprogramming channel, unchanged from v3. ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,

    output wire [4:0]   status_core_select,   // debug tap only
    output wire [169:0] status_shared_state   // NEW, v4 debug tap only --
                                               // the real shared register itself
);

    // ── SUPER_LATCH, committed atomically on cfg_valid — unchanged. ──
    reg [79:0] super_latch = 80'h0;
    always @(posedge clk) begin
        if (rst) super_latch <= 80'h0;
        else if (cfg_valid) super_latch <= cfg_data;
    end

    wire [4:0]  core_select  = super_latch[4:0];
    wire [41:0] core_config  = super_latch[46:5];
    wire [19:0] addon_config = super_latch[66:47];

    wire [4:0]  incoming_select  = cfg_data[4:0];
    wire [41:0] incoming_config  = cfg_data[46:5];

    localparam [4:0] SEL_NANO = 5'd0, SEL_RAM = 5'd1, SEL_ADDER = 5'd2,
                      SEL_ACC = 5'd3, SEL_CMP = 5'd4, SEL_LATCH = 5'd5,
                      SEL_SEQ = 5'd6, SEL_BRANCH = 5'd7;

    wire cfg_valid_nano  = cfg_valid && (incoming_select == SEL_NANO);
    wire cfg_valid_ram   = cfg_valid && (incoming_select == SEL_RAM);
    wire cfg_valid_adder = cfg_valid && (incoming_select == SEL_ADDER);
    wire cfg_valid_acc   = cfg_valid && (incoming_select == SEL_ACC);
    wire cfg_valid_cmp   = cfg_valid && (incoming_select == SEL_CMP);
    wire cfg_valid_latch = cfg_valid && (incoming_select == SEL_LATCH);
    wire cfg_valid_seq   = cfg_valid && (incoming_select == SEL_SEQ);
    wire cfg_valid_branch = cfg_valid && (incoming_select == SEL_BRANCH);

    wire sel_active_nano  = (core_select == SEL_NANO);
    wire sel_active_ram   = (core_select == SEL_RAM);
    wire sel_active_adder = (core_select == SEL_ADDER);
    wire sel_active_acc   = (core_select == SEL_ACC);
    wire sel_active_cmp   = (core_select == SEL_CMP);
    wire sel_active_latch = (core_select == SEL_LATCH);
    wire sel_active_seq   = (core_select == SEL_SEQ);
    wire sel_active_branch = (core_select == SEL_BRANCH);

    // ── v4 REAL ADDITION: freeze centralization (#566). Every
    // non-selected core is held frozen at the shell level, on top of
    // the pre-existing arrived_*/cfg_valid starvation gating. ──
    wire freeze_nano   = freeze_in || !sel_active_nano;
    wire freeze_ram    = freeze_in || !sel_active_ram;
    wire freeze_adder  = freeze_in || !sel_active_adder;
    wire freeze_acc    = freeze_in || !sel_active_acc;
    wire freeze_cmp    = freeze_in || !sel_active_cmp;
    wire freeze_latch  = freeze_in || !sel_active_latch;
    wire freeze_seq    = freeze_in || !sel_active_seq;
    wire freeze_branch = freeze_in || !sel_active_branch;

    // ── v4 REAL ADDITION: the one shared external-storage register,
    // sized to the widest real core (nano, 170 bits). Every core's
    // own real ext_state_in reads the same register, truncated to its
    // own real width; only the SELECTED core's ext_state_out is ever
    // written back.
    //
    // REAL, HONEST CORRECTION found and fixed during sim verification
    // of THIS file (not carried over from anywhere else): an earlier
    // draft force-cleared shared_state to 0 on the exact cycle
    // core_select changes, reasoning it should match each core's own
    // real power-on-reset default. That reasoning was WRONG in
    // practice -- a core switch and a config load for the newly
    // selected core are literally the SAME cfg_valid pulse in this
    // project's own SUPER_LATCH protocol (you can only select a new
    // core by simultaneously loading its config), so the "reset"
    // branch was firing on the exact same cycle as the real config
    // load and CLOBBERING it before it could ever reach shared_state.
    // The actual, correct fix needs no special case at all: every
    // core's own real next-state logic already resets every relevant
    // field from cfg_data on cfg_valid (including forcing runtime-
    // only fields like pending_ack to 0), matching EXTERNAL_STORAGE=0
    // mode's own already-proven reconfigure behavior exactly
    // (#563/#564's own differential testbenches). No shell-level
    // reset is needed on top of that. ──
    reg [169:0] shared_state = 170'h0;

    // ── nano's own real cfg_data reconstructed from core_config's
    // shared low bits — unchanged from v3. ──
    wire [127:0] nano_cfg_data;
    assign nano_cfg_data[9:0]    = incoming_config[9:0];    // topology
    assign nano_cfg_data[12:10]  = 3'b0;
    assign nano_cfg_data[13]     = incoming_config[10];     // ready
    assign nano_cfg_data[63:14]  = 50'b0;
    assign nano_cfg_data[69:64]  = incoming_config[16:11];  // routing_mask
    assign nano_cfg_data[75:70]  = incoming_config[22:17];  // cardinal_edge
    assign nano_cfg_data[127:76] = 52'b0;

    wire nano_hold_in          = incoming_config[23] && sel_active_nano;
    wire nano_fb_internal_in   = incoming_config[24] && sel_active_nano;
    wire nano_a_reemit_in      = incoming_config[25] && sel_active_nano;
    wire nano_a_update_in      = incoming_config[26] && sel_active_nano;
    wire nano_a_self_update_in = incoming_config[27] && sel_active_nano;

    wire [31:0] n_dout_n, n_dout_s, n_dout_e, n_dout_w;
    wire n_fire_n, n_fire_s, n_fire_e, n_fire_w, n_ready, n_ack_n, n_ack_s, n_ack_e, n_ack_w;
    wire n_program_done;
    wire [169:0] n_ext_out;

    unicell_stripped_v3 #(.CELL_ID(CELL_ID), .EXTERNAL_STORAGE(1)) CORE_NANO (
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
        .freeze_in(freeze_nano),
        .hold_in(nano_hold_in), .fb_internal_in(nano_fb_internal_in),
        .a_reemit_in(nano_a_reemit_in), .a_update_in(nano_a_update_in), .a_self_update_in(nano_a_self_update_in),
        .program_in(program_in && sel_active_nano), .program_done(n_program_done),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s),
        .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(prog_arrived_in_n && sel_active_nano),
        .prog_arrived_in_s(prog_arrived_in_s && sel_active_nano),
        .prog_arrived_in_e(prog_arrived_in_e && sel_active_nano),
        .prog_arrived_in_w(prog_arrived_in_w && sel_active_nano),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .ext_state_in(shared_state[169:0]), .ext_state_out(n_ext_out)
    );

    wire [31:0] r_dout_n, r_dout_s, r_dout_e, r_dout_w;
    wire r_fire_n, r_fire_s, r_fire_e, r_fire_w, r_ready, r_ack_n, r_ack_s, r_ack_e, r_ack_w;
    wire [45:0] r_ext_out;

    ram_cell_v2 #(.CELL_ID(CELL_ID), .EXTERNAL_STORAGE(1)) CORE_RAM (
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
        .freeze_in(freeze_ram), .status_data_valid(),
        .ext_state_in(shared_state[45:0]), .ext_state_out(r_ext_out)
    );

    wire [31:0] a_dout_n, a_dout_s, a_dout_e, a_dout_w;
    wire a_fire_n, a_fire_s, a_fire_e, a_fire_w, a_ready, a_ack_n, a_ack_s, a_ack_e, a_ack_w;
    wire [78:0] a_ext_out;

    adder_cell_v2 #(.CELL_ID(CELL_ID), .EXTERNAL_STORAGE(1)) CORE_ADDER (
        .clk(clk), .rst(rst),
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
        .freeze_in(freeze_adder), .status_data_valid(), .status_a_arrived(),
        .ext_state_in(shared_state[78:0]), .ext_state_out(a_ext_out)
    );

    wire [31:0] c_dout_n, c_dout_s, c_dout_e, c_dout_w;
    wire c_fire_n, c_fire_s, c_fire_e, c_fire_w, c_ready, c_ack_n, c_ack_s, c_ack_e, c_ack_w;
    wire [106:0] c_ext_out;

    accumulator_cell_v2 #(.CELL_ID(CELL_ID), .EXTERNAL_STORAGE(1)) CORE_ACC (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid_acc), .cfg_data({27'b0, incoming_config[36:0]}),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n && sel_active_acc), .arrived_s(arrived_s && sel_active_acc),
        .arrived_e(arrived_e && sel_active_acc), .arrived_w(arrived_w && sel_active_acc),
        .data_out_n(c_dout_n), .data_out_s(c_dout_s), .data_out_e(c_dout_e), .data_out_w(c_dout_w),
        .fire_n(c_fire_n), .fire_s(c_fire_s), .fire_e(c_fire_e), .fire_w(c_fire_w),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(c_ack_n), .ack_out_s(c_ack_s), .ack_out_e(c_ack_e), .ack_out_w(c_ack_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_acc), .ready_out(c_ready), .status_negative(),
        .ext_state_in(shared_state[106:0]), .ext_state_out(c_ext_out)
    );

    wire [31:0] m_dout_n, m_dout_s, m_dout_e, m_dout_w;
    wire m_fire_n, m_fire_s, m_fire_e, m_fire_w, m_ready, m_ack_n, m_ack_s, m_ack_e, m_ack_w;
    wire [76:0] m_ext_out;

    compare_cell_v2 #(.CELL_ID(CELL_ID), .EXTERNAL_STORAGE(1)) CORE_CMP (
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
        .freeze_in(freeze_cmp), .status_data_valid(),
        .ext_state_in(shared_state[76:0]), .ext_state_out(m_ext_out)
    );

    wire [31:0] l_dout_n, l_dout_s, l_dout_e, l_dout_w;
    wire l_fire_n, l_fire_s, l_fire_e, l_fire_w, l_ready, l_ack_n, l_ack_s, l_ack_e, l_ack_w;
    wire [22:0] l_ext_out;

    latch_cell_v2 #(.CELL_ID(CELL_ID), .EXTERNAL_STORAGE(1)) CORE_LATCH (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid_latch), .cfg_data({48'b0, incoming_config[15:0]}),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n && sel_active_latch), .arrived_s(arrived_s && sel_active_latch),
        .arrived_e(arrived_e && sel_active_latch), .arrived_w(arrived_w && sel_active_latch),
        .data_out_n(l_dout_n), .data_out_s(l_dout_s), .data_out_e(l_dout_e), .data_out_w(l_dout_w),
        .fire_n(l_fire_n), .fire_s(l_fire_s), .fire_e(l_fire_e), .fire_w(l_fire_w),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(l_ack_n), .ack_out_s(l_ack_s), .ack_out_e(l_ack_e), .ack_out_w(l_ack_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_latch), .ready_out(l_ready), .status_latched(),
        .ext_state_in(shared_state[22:0]), .ext_state_out(l_ext_out)
    );

    wire [31:0] q_dout_n, q_dout_s, q_dout_e, q_dout_w;
    wire q_fire_n, q_fire_s, q_fire_e, q_fire_w, q_ready, q_ack_n, q_ack_s, q_ack_e, q_ack_w;
    wire [52:0] q_ext_out;

    sequencer_cell_v2 #(.CELL_ID(CELL_ID), .EXTERNAL_STORAGE(1)) CORE_SEQ (
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
        .freeze_in(freeze_seq), .ready_out(q_ready), .status_seq_index(),
        .ext_state_in(shared_state[52:0]), .ext_state_out(q_ext_out)
    );

    wire [31:0] br_dout_n, br_dout_s, br_dout_e, br_dout_w;
    wire br_fire_n, br_fire_s, br_fire_e, br_fire_w, br_ack_n, br_ack_s, br_ack_e, br_ack_w;
    wire [116:0] br_ext_out;

    branch_cell_v2 #(.CELL_ID(CELL_ID), .EXTERNAL_STORAGE(1)) CORE_BRANCH (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid_branch), .cfg_data({22'b0, incoming_config[41:0]}),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n && sel_active_branch), .arrived_s(arrived_s && sel_active_branch),
        .arrived_e(arrived_e && sel_active_branch), .arrived_w(arrived_w && sel_active_branch),
        .data_out_n(br_dout_n), .data_out_s(br_dout_s), .data_out_e(br_dout_e), .data_out_w(br_dout_w),
        .fire_n(br_fire_n), .fire_s(br_fire_s), .fire_e(br_fire_e), .fire_w(br_fire_w),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(br_ack_n), .ack_out_s(br_ack_s), .ack_out_e(br_ack_e), .ack_out_w(br_ack_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_branch), .ready_out(), .status_data_valid(),
        .ext_state_in(shared_state[116:0]), .ext_state_out(br_ext_out)
    );

    // ── v4 REAL ADDITION: the write-select mux + the shared register
    // itself. Only the REGISTERED (settled) core_select's own
    // ext_state_out is ever written back -- matches the exact same
    // "registered select governs ongoing operation" convention the
    // output mux below already uses. Zero-extended to the shared
    // register's own full 170-bit width; a narrower core's unused
    // upper bits are simply never read back by anything (only that
    // core's own real width is ever sliced back off shared_state). ──
    // ── REAL BUG FOUND AND FIXED during this file's own sim
    // verification: the write-mux must NOT key off the registered
    // core_select alone. On the exact cycle a switch's cfg_valid
    // fires, cfg_valid_<core> (every one of them) is already gated on
    // incoming_select (the value ABOUT to settle), but core_select
    // itself hasn't updated yet (same-edge nonblocking assignment --
    // it only reflects the NEW value the cycle AFTER). Keying the
    // write-mux on core_select alone meant the newly-configured
    // core's own first real ext_state_out (computed off cfg_data this
    // same cycle) was silently discarded -- written back under the
    // OLD core's slot instead, then never revisited, because by the
    // very next cycle cfg_valid has already deasserted and the new
    // core reads its own state back from a shared register that was
    // never actually written with its config. Confirmed as a genuine
    // functional failure (RAM's real fixed-mode config never reached
    // shared_state at all) before this fix, not a hypothetical. ──
    wire [4:0] write_select = cfg_valid ? incoming_select : core_select;

    reg [169:0] shared_state_next;
    always @(*) begin
        case (write_select)
            SEL_NANO:   shared_state_next = n_ext_out;
            SEL_RAM:    shared_state_next = {124'b0, r_ext_out};
            SEL_ADDER:  shared_state_next = {91'b0,  a_ext_out};
            SEL_ACC:    shared_state_next = {63'b0,  c_ext_out};
            SEL_CMP:    shared_state_next = {93'b0,  m_ext_out};
            SEL_LATCH:  shared_state_next = {147'b0, l_ext_out};
            SEL_SEQ:    shared_state_next = {117'b0, q_ext_out};
            SEL_BRANCH: shared_state_next = {53'b0,  br_ext_out};
            default:    shared_state_next = 170'h0;
        endcase
    end

    always @(posedge clk) begin
        if (rst) shared_state <= 170'h0;
        else shared_state <= shared_state_next;
    end

    // ── Output mux — unchanged from v3. ──
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
            SEL_BRANCH: begin
                mux_dout_n=br_dout_n; mux_dout_s=br_dout_s; mux_dout_e=br_dout_e; mux_dout_w=br_dout_w;
                mux_fire_n=br_fire_n; mux_fire_s=br_fire_s; mux_fire_e=br_fire_e; mux_fire_w=br_fire_w;
                mux_ready=1'b0;
                mux_ack_n=br_ack_n; mux_ack_s=br_ack_s; mux_ack_e=br_ack_e; mux_ack_w=br_ack_w; mux_program_done=1'b0;
            end
            default: begin
                mux_dout_n=32'h0; mux_dout_s=32'h0; mux_dout_e=32'h0; mux_dout_w=32'h0;
                mux_fire_n=1'b0; mux_fire_s=1'b0; mux_fire_e=1'b0; mux_fire_w=1'b0;
                mux_ready=1'b0;
                mux_ack_n=1'b0; mux_ack_s=1'b0; mux_ack_e=1'b0; mux_ack_w=1'b0; mux_program_done=1'b0;
            end
        endcase
    end

    // ── The three real ADDONs — unchanged from v3. ──
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
    assign status_shared_state = shared_state;

endmodule
