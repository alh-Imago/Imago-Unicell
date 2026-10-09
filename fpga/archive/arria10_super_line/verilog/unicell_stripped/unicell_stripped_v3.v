// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// unicell_stripped_v3.v — points.md #566: adds the optional external-
// storage capability proven on the other 7 real cores. Real, important
// lineage note, checked before naming this file, not assumed:
// unicell_stripped_v2.v ALREADY EXISTS (points.md #189/#190) as a
// real, separate, standalone 256-bit unified-latch rebuild -- it is
// NOT used by the real shell (unicell_super_v3.v instantiates v1
// directly), and this file is cloned from v1, not from v2. Different
// real lineage, different real purpose -- v2 folds data_reg into
// cmd_latch; this file keeps v1's own field layout completely
// unchanged and instead makes cmd_latch/data_reg/etc. optionally
// externally-stored, for use inside the super carrier shell.
//
// Zero behavioral change to the default path. Same optional external-
// storage mechanism proven on the other 7 real cores, applied here
// with real, extra care given this core's own genuinely richer
// structure: 7 mutually-exclusive priority branches (programming,
// internal feedback, A-update, A-reemit, capture, fire, relay),
// several of which write DIFFERENT, OVERLAPPING bit-slices of the
// same 128-bit cmd_latch rather than one clean value each.
//
// freeze_in is left completely unchanged, still a real, independent
// per-core port -- the freeze-centralization idea discussed alongside
// this conversion is real, shell-level, later work (decoding
// core_select into 8 individual freeze lines instead of wiring the
// same signal to all 8), and needs no change here at all.
//
// Real, precise bit layout for the 170-bit external state word:
//   [127:0]   cmd_latch
//   [159:128] data_reg (32 bits)
//   [160]     a_arrived
//   [166:161] pending_ack (6 bits)
//   [167]     program_done_r
//   [168]     error_frozen
//   [169]     armed
`default_nettype none
`timescale 1ns / 1ps

module unicell_stripped_v3 #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        ENABLE_DYNAMIC_ROUTING = 1'b0,
    parameter        EXTERNAL_STORAGE = 0
) (
    input  wire        clk,
    input  wire         rst,

    input  wire         cfg_valid,
    input  wire [127:0] cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire [31:0]  cmd_in_n,    cmd_in_s,    cmd_in_e,    cmd_in_w,
    output wire [31:0]  cmd_out_n,   cmd_out_s,   cmd_out_e,   cmd_out_w,

    input  wire         freeze_in,
    input  wire         hold_in,
    input  wire         fb_internal_in,
    input  wire         a_reemit_in,
    input  wire         a_update_in,
    input  wire         a_self_update_in,

    input  wire         program_in,
    output wire         program_done,

    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    // ── real, optional external-storage interface (points.md #566) ──
    input  wire [169:0] ext_state_in,
    output wire [169:0] ext_state_out
);

    // ── Real, internal-mode registers -- used only when
    // EXTERNAL_STORAGE=0, byte-for-byte identical to v1. ──
    reg [127:0] int_cmd_latch  = 128'h0;
    reg [31:0]  int_data_reg   = 32'h0;
    reg         int_a_arrived  = 1'b0;
    reg [5:0]   int_pending_ack= 6'h0;
    reg         int_program_done_r = 1'b0;
    reg         int_error_frozen   = 1'b0;
    reg         int_armed          = 1'b0;

    wire [127:0] cmd_latch   = EXTERNAL_STORAGE ? ext_state_in[127:0]   : int_cmd_latch;
    wire [31:0]  data_reg    = EXTERNAL_STORAGE ? ext_state_in[159:128] : int_data_reg;
    wire         a_arrived   = EXTERNAL_STORAGE ? ext_state_in[160]     : int_a_arrived;
    wire [5:0]   pending_ack = EXTERNAL_STORAGE ? ext_state_in[166:161] : int_pending_ack;
    wire         program_done_r = EXTERNAL_STORAGE ? ext_state_in[167] : int_program_done_r;
    wire         error_frozen   = EXTERNAL_STORAGE ? ext_state_in[168] : int_error_frozen;
    wire         armed          = EXTERNAL_STORAGE ? ext_state_in[169] : int_armed;

    // ── Real computation logic, IDENTICAL to v1 from here on -- every
    // wire below reads ONLY through the selector wires above. ──
    wire [9:0] topology     = cmd_latch[9:0];
    wire       ready_bit    = cmd_latch[13];
    wire [5:0] routing_mask = cmd_latch[69:64];
    wire [5:0] cardinal_edge= cmd_latch[75:70];
    wire [31:0] out_buffer  = cmd_latch[127:96];

    wire [3:0] pattern_low    = cmd_latch[79:76];
    wire [3:0] pattern_equal  = cmd_latch[85:82];
    wire [3:0] pattern_high   = cmd_latch[91:88];
    wire       dynamic_route_en = cmd_latch[94];

    wire is_command_cell = cmd_latch[10];
    wire effective_hold   = hold_in     || is_command_cell;
    wire effective_reemit = a_reemit_in || is_command_cell;

    assign ready_out = ready_bit && armed;
    assign program_done = program_done_r;

    wire prog_any_arrived = prog_arrived_in_n | prog_arrived_in_s | prog_arrived_in_e | prog_arrived_in_w;
    wire prog_sel_n = prog_arrived_in_n;
    wire prog_sel_s = prog_arrived_in_s && !prog_arrived_in_n;
    wire prog_sel_e = prog_arrived_in_e && !prog_arrived_in_n && !prog_arrived_in_s;
    wire prog_sel_w = prog_arrived_in_w && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e;
    wire [31:0] prog_data_val = prog_sel_n ? prog_data_in_n :
                                prog_sel_s ? prog_data_in_s :
                                prog_sel_e ? prog_data_in_e :
                                             prog_data_in_w;

    localparam [2:0] PROG_ID_TOPOLOGY     = 3'd0;
    localparam [2:0] PROG_ID_ROUTING_MASK = 3'd1;
    localparam [2:0] PROG_ID_CARDINAL_EDGE= 3'd2;
    localparam [2:0] PROG_ID_PATTERN_LOW  = 3'd3;
    localparam [2:0] PROG_ID_PATTERN_EQUAL= 3'd4;
    localparam [2:0] PROG_ID_PATTERN_HIGH = 3'd5;
    localparam [2:0] PROG_ID_DYN_ROUTE_EN = 3'd6;
    localparam [2:0] PROG_ID_COMPLETE     = 3'd7;

    wire [2:0]  prog_id   = prog_data_val[18:16];
    wire [15:0] prog_word = prog_data_val[15:0];

    wire programming_active = program_in && prog_any_arrived;

    assign prog_ack_out_n = programming_active && prog_sel_n;
    assign prog_ack_out_s = programming_active && prog_sel_s;
    assign prog_ack_out_e = programming_active && prog_sel_e;
    assign prog_ack_out_w = programming_active && prog_sel_w;

    wire sel_n = arrived_n;
    wire sel_s = arrived_s;
    wire sel_e = arrived_e;
    wire sel_w = arrived_w;

    wire any_arrived = arrived_n | arrived_s | arrived_e | arrived_w;
    wire [31:0] arrived_val = (arrived_n ? data_in_n : 32'h0) |
                              (arrived_s ? data_in_s : 32'h0) |
                              (arrived_e ? data_in_e : 32'h0) |
                              (arrived_w ? data_in_w : 32'h0);

    wire selected_is_relay = (sel_n && cardinal_edge[0]) ||
                             (sel_s && cardinal_edge[1]) ||
                             (sel_e && cardinal_edge[2]) ||
                             (sel_w && cardinal_edge[3]);
    wire relay_arrived   = any_arrived && selected_is_relay;
    wire consume_arrived = any_arrived && !selected_is_relay;

    wire any_relay_dir   = (sel_n && cardinal_edge[0]) || (sel_s && cardinal_edge[1]) ||
                           (sel_e && cardinal_edge[2]) || (sel_w && cardinal_edge[3]);
    wire any_consume_dir = (sel_n && !cardinal_edge[0]) || (sel_s && !cardinal_edge[1]) ||
                           (sel_e && !cardinal_edge[2]) || (sel_w && !cardinal_edge[3]);
    wire relay_mismatch  = any_arrived && any_relay_dir && any_consume_dir;

    wire effective_freeze = freeze_in || error_frozen || !armed;

    wire capture_now = consume_arrived && !a_arrived && !effective_freeze && !program_in;

    wire internal_fb_active = hold_in && fb_internal_in && !effective_freeze && !program_in;

    wire a_reemit_active = effective_hold && effective_reemit && a_arrived && consume_arrived &&
                           ready_bit && targets_all_ready && !effective_freeze && !program_in;
    wire a_update_active = hold_in && a_update_in && consume_arrived && !effective_freeze && !program_in;

    wire [31:0] input_val  = a_arrived ? data_reg : arrived_val;
    wire [31:0] second_val = internal_fb_active ? out_buffer :
                              (a_arrived ? arrived_val : data_reg);

    wire [3:0] effective_routing;

    generate
    if (ENABLE_DYNAMIC_ROUTING) begin : gen_dynamic_routing
        wire cmp_gt = (second_val > input_val);
        wire cmp_lt = (second_val < input_val);
        wire [3:0] selected_pattern = cmp_gt ? pattern_high :
                                      cmp_lt ? pattern_low  :
                                               pattern_equal;
        assign effective_routing = dynamic_route_en ? (selected_pattern & routing_mask[3:0])
                                                     : routing_mask[3:0];
    end else begin : gen_static_routing_only
        assign effective_routing = routing_mask[3:0];
    end
    endgenerate

    wire [31:0] g0 = ~(input_val  | input_val);
    wire [31:0] g1 = ~(second_val | second_val);
    wire [31:0] g2 = ~(g0 | g1);
    wire [31:0] g3 = ~(g2 | g2);
    wire [31:0] g4 = ~(input_val  | second_val);
    wire [31:0] g5 = ~(g4 | g4);
    wire [31:0] g6 = ~(input_val  | g4);
    wire [31:0] g7 = ~(second_val | g4);
    wire [31:0] g8 = ~(g6 | g7);
    wire [31:0] g9 = ~(g8 | g8);

    reg [31:0] computed_output;
    always @(*) begin
        computed_output = input_val;
        case (topology)
            10'h000: computed_output = input_val;
            10'h02C: computed_output = second_val;
            10'h001: computed_output = g0;
            10'h002: computed_output = g1;
            10'h004: computed_output = g4;
            10'h007: computed_output = g2;
            10'h024: computed_output = g5;
            10'h027: computed_output = g3;
            10'h0BC: computed_output = g9;
            10'h03C: computed_output = g8;
            10'h030: computed_output = 32'h0;
            10'h0B0: computed_output = 32'hFFFFFFFF;
            default: computed_output = input_val;
        endcase
    end

    wire new_data = consume_arrived && a_arrived;

    wire want_n = effective_routing[0];
    wire want_s = effective_routing[1];
    wire want_e = effective_routing[2];
    wire want_w = effective_routing[3];

    wire targets_all_ready = (!want_n || ready_in_n) &&
                             (!want_s || ready_in_s) &&
                             (!want_e || ready_in_e) &&
                             (!want_w || ready_in_w);

    wire can_fire = new_data && ready_bit && targets_all_ready && !effective_freeze && !program_in;
    wire relay_fire = relay_arrived && ready_bit && targets_all_ready && !effective_freeze && !program_in;

    wire consumed_now = capture_now || can_fire || relay_fire || a_reemit_active || a_update_active;
    assign ack_out_n = consumed_now && sel_n;
    assign ack_out_s = consumed_now && sel_s;
    assign ack_out_e = consumed_now && sel_e;
    assign ack_out_w = consumed_now && sel_w;

    wire [5:0] targeted_vec = {2'b00, want_w, want_e, want_s, want_n};
    wire [5:0] ack_in_vec   = {2'b00, ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire       any_fire     = can_fire || relay_fire || a_reemit_active;
    wire [5:0] next_pending_ack = any_fire            ? (targeted_vec & ~ack_in_vec) :
                                  (pending_ack != 6'h0) ? (pending_ack  & ~ack_in_vec) :
                                                          pending_ack;
    wire next_ready = hold_in || (next_pending_ack == 6'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    assign cmd_out_n = 32'h0;
    assign cmd_out_s = 32'h0;
    assign cmd_out_e = 32'h0;
    assign cmd_out_w = 32'h0;

    // ── Real next-state computation for cmd_latch, matching v1's own
    // real, sequential priority chain EXACTLY -- built up bit-slice by
    // bit-slice, since different branches touch DIFFERENT, overlapping
    // parts of the same 128-bit word. Default: unchanged, then each
    // branch overrides only the slice it actually writes in v1. ──
    reg [127:0] next_cmd_latch_comb;
    always @(*) begin
        next_cmd_latch_comb = cmd_latch;  // default: unchanged
        if (programming_active) begin
            case (prog_id)
                PROG_ID_TOPOLOGY:      next_cmd_latch_comb[9:0]   = prog_word[9:0];
                PROG_ID_ROUTING_MASK:  next_cmd_latch_comb[67:64] = prog_word[3:0];
                PROG_ID_CARDINAL_EDGE: next_cmd_latch_comb[73:70] = prog_word[3:0];
                PROG_ID_PATTERN_LOW:   next_cmd_latch_comb[79:76] = prog_word[3:0];
                PROG_ID_PATTERN_EQUAL: next_cmd_latch_comb[85:82] = prog_word[3:0];
                PROG_ID_PATTERN_HIGH:  next_cmd_latch_comb[91:88] = prog_word[3:0];
                PROG_ID_DYN_ROUTE_EN:  next_cmd_latch_comb[94]    = prog_word[0];
                PROG_ID_COMPLETE:      next_cmd_latch_comb[13]    = 1'b1;
                default: ;
            endcase
        end else if (internal_fb_active) begin
            if (!a_self_update_in)
                next_cmd_latch_comb[127:96] = computed_output;
        end else if (a_update_active) begin
            // writes data_reg, not cmd_latch
        end else if (a_reemit_active) begin
            next_cmd_latch_comb[127:96] = data_reg;
        end else if (capture_now) begin
            // writes data_reg/a_arrived, not cmd_latch
        end else if (can_fire) begin
            next_cmd_latch_comb[127:96] = computed_output;
        end else if (relay_fire) begin
            next_cmd_latch_comb[127:96] = arrived_val;
        end
        // ready bit (cmd_latch[13]) always driven off next_ready, every
        // cycle, matching v1's own real final line exactly.
        next_cmd_latch_comb[13] = next_ready;
    end

    wire [127:0] next_cmd_latch_reg =
        (rst) ? 128'h0 :
        (cfg_valid) ? {cfg_data[127:14], 1'b1, cfg_data[12:0]} :
        next_cmd_latch_comb;

    wire [31:0] next_data_reg_reg =
        (rst) ? 32'h0 :
        (cfg_valid) ? data_reg :
        (internal_fb_active && a_self_update_in) ? computed_output :
        (a_update_active) ? arrived_val :
        (capture_now) ? arrived_val :
        data_reg;

    wire next_a_arrived_reg =
        (rst) ? 1'b0 :
        (cfg_valid) ? a_arrived :
        (capture_now) ? 1'b1 :
        (can_fire) ? hold_in :
        a_arrived;

    wire [5:0] next_pending_ack_reg = (rst) ? 6'h0 : (cfg_valid) ? 6'h0 : next_pending_ack;

    wire next_program_done_r_reg =
        (rst) ? 1'b0 :
        (cfg_valid) ? program_done_r :
        (programming_active && prog_id == PROG_ID_COMPLETE) ? 1'b1 :
        (!program_in) ? 1'b0 : program_done_r;

    wire next_error_frozen_reg =
        (rst) ? 1'b0 :
        (cfg_valid) ? 1'b0 :
        (programming_active && prog_id == PROG_ID_COMPLETE) ? 1'b0 :
        (relay_mismatch) ? 1'b1 : error_frozen;

    wire next_armed_reg =
        (rst) ? 1'b0 :
        (cfg_valid) ? 1'b1 :
        (programming_active && prog_id == PROG_ID_COMPLETE) ? prog_word[0] :
        armed;

    assign ext_state_out = {next_armed_reg, next_error_frozen_reg, next_program_done_r_reg,
                             next_pending_ack_reg, next_a_arrived_reg, next_data_reg_reg,
                             next_cmd_latch_reg};

    generate
        if (!EXTERNAL_STORAGE) begin : internal_storage
            always @(posedge clk) begin
                int_cmd_latch      <= next_cmd_latch_reg;
                int_data_reg       <= next_data_reg_reg;
                int_a_arrived      <= next_a_arrived_reg;
                int_pending_ack    <= next_pending_ack_reg;
                int_program_done_r <= next_program_done_r_reg;
                int_error_frozen   <= next_error_frozen_reg;
                int_armed          <= next_armed_reg;
            end
        end
    endgenerate

endmodule
