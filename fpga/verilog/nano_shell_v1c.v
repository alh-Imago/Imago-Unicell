// nano_shell_v1c.v — points.md #720: the real cardinal wrapper for
// nano_gate_v4c.v (the carrier-specific variant, internal addon
// chain removed -- see that file's own header for the full reasoning).
// Otherwise IDENTICAL to nano_shell_v1.v: same cardinal OR-combining
// for active/freeze, same port list, only the instantiated core differs.
`default_nettype none
`timescale 1ns / 1ps

module nano_shell_v1c #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        ENABLE_DYNAMIC_ROUTING = 1'b0
) (
    input  wire        clk,
    input  wire         rst,

    // ── Real, new cardinal control ports (this file's own real
    // reason for existing) -- each OR-combined below into the exact
    // same flat signal the wrapped core already expects. ──
    input  wire         active_in_n,       active_in_s,       active_in_e,       active_in_w,
    input  wire         freeze_in_n,       freeze_in_s,       freeze_in_e,       freeze_in_w,
    input  wire         hold_in_n,         hold_in_s,         hold_in_e,         hold_in_w,
    input  wire         fb_internal_in_n,  fb_internal_in_s,  fb_internal_in_e,  fb_internal_in_w,
    input  wire         a_reemit_in_n,     a_reemit_in_s,     a_reemit_in_e,     a_reemit_in_w,
    input  wire         a_update_in_n,     a_update_in_s,     a_update_in_e,     a_update_in_w,
    input  wire         a_self_update_in_n, a_self_update_in_s, a_self_update_in_e, a_self_update_in_w,

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

    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w
);

    // ── Real, simple OR-combine -- "any real cardinal neighbor
    // asserting this line activates it," the same combining rule
    // `any_arrived` already uses throughout this project. ──
    wire active_comb        = active_in_n        | active_in_s        | active_in_e        | active_in_w;
    wire freeze_comb        = freeze_in_n        | freeze_in_s        | freeze_in_e        | freeze_in_w;
    wire hold_comb          = hold_in_n          | hold_in_s          | hold_in_e          | hold_in_w;
    wire fb_internal_comb   = fb_internal_in_n   | fb_internal_in_s   | fb_internal_in_e   | fb_internal_in_w;
    wire a_reemit_comb      = a_reemit_in_n      | a_reemit_in_s      | a_reemit_in_e      | a_reemit_in_w;
    wire a_update_comb      = a_update_in_n      | a_update_in_s      | a_update_in_e      | a_update_in_w;
    wire a_self_update_comb = a_self_update_in_n | a_self_update_in_s | a_self_update_in_e | a_self_update_in_w;

    nano_gate_v4c #(
        .CELL_ID(CELL_ID),
        .ENABLE_DYNAMIC_ROUTING(ENABLE_DYNAMIC_ROUTING)
    ) CORE (
        .clk(clk), .rst(rst), .active(active_comb),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(arrived_e), .arrived_w(arrived_w),
        .data_out_n(data_out_n), .data_out_s(data_out_s), .data_out_e(data_out_e), .data_out_w(data_out_w),
        .fire_n(fire_n), .fire_s(fire_s), .fire_e(fire_e), .fire_w(fire_w),
        .ready_out(ready_out),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(ack_out_n), .ack_out_s(ack_out_s), .ack_out_e(ack_out_e), .ack_out_w(ack_out_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_comb),
        .hold_in(hold_comb), .fb_internal_in(fb_internal_comb),
        .a_reemit_in(a_reemit_comb), .a_update_in(a_update_comb), .a_self_update_in(a_self_update_comb),
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s),
        .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(prog_arrived_in_n), .prog_arrived_in_s(prog_arrived_in_s),
        .prog_arrived_in_e(prog_arrived_in_e), .prog_arrived_in_w(prog_arrived_in_w),
        .prog_ack_out_n(prog_ack_out_n), .prog_ack_out_s(prog_ack_out_s),
        .prog_ack_out_e(prog_ack_out_e), .prog_ack_out_w(prog_ack_out_w)
    );

endmodule
