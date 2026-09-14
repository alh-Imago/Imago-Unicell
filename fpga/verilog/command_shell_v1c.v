// command_shell_v1c.v — points.md #720: the real cardinal wrapper for
// command_cell_v4c.v (renamed for naming consistency with the other 8
// _v4c cores -- this core never had an addon chain to remove, see that
// file's own header). Otherwise IDENTICAL to command_shell_v1.v: same
// cardinal OR-combining for active/freeze, same port list, only the
// instantiated core differs.
`default_nettype none
`timescale 1ns / 1ps

module command_shell_v1c #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire         rst,

    input  wire         active_in_n, active_in_s, active_in_e, active_in_w,
    input  wire         freeze_in_n, freeze_in_s, freeze_in_e, freeze_in_w,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,
    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    output wire         ready_out,

    output wire         freeze_out_n, freeze_out_s, freeze_out_e, freeze_out_w,

    output wire         program_out_n, program_out_s, program_out_e, program_out_w,
    output wire [31:0]  prog_data_out_n, prog_data_out_s, prog_data_out_e, prog_data_out_w,
    output wire         prog_arrived_out_n, prog_arrived_out_s, prog_arrived_out_e, prog_arrived_out_w,
    input  wire         prog_ack_in_n, prog_ack_in_s, prog_ack_in_e, prog_ack_in_w,

    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    output wire         status_active,
    output wire         status_freeze_state
);

    wire active_comb = active_in_n | active_in_s | active_in_e | active_in_w;
    wire freeze_comb = freeze_in_n | freeze_in_s | freeze_in_e | freeze_in_w;

    command_cell_v4c #(.CELL_ID(CELL_ID)) CORE (
        .clk(clk), .rst(rst), .active(active_comb),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(arrived_e), .arrived_w(arrived_w),
        .ack_out_n(ack_out_n), .ack_out_s(ack_out_s), .ack_out_e(ack_out_e), .ack_out_w(ack_out_w),
        .ready_out(ready_out),
        .freeze_out_n(freeze_out_n), .freeze_out_s(freeze_out_s),
        .freeze_out_e(freeze_out_e), .freeze_out_w(freeze_out_w),
        .program_out_n(program_out_n), .program_out_s(program_out_s),
        .program_out_e(program_out_e), .program_out_w(program_out_w),
        .prog_data_out_n(prog_data_out_n), .prog_data_out_s(prog_data_out_s),
        .prog_data_out_e(prog_data_out_e), .prog_data_out_w(prog_data_out_w),
        .prog_arrived_out_n(prog_arrived_out_n), .prog_arrived_out_s(prog_arrived_out_s),
        .prog_arrived_out_e(prog_arrived_out_e), .prog_arrived_out_w(prog_arrived_out_w),
        .prog_ack_in_n(prog_ack_in_n), .prog_ack_in_s(prog_ack_in_s),
        .prog_ack_in_e(prog_ack_in_e), .prog_ack_in_w(prog_ack_in_w),
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s),
        .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(prog_arrived_in_n), .prog_arrived_in_s(prog_arrived_in_s),
        .prog_arrived_in_e(prog_arrived_in_e), .prog_arrived_in_w(prog_arrived_in_w),
        .prog_ack_out_n(prog_ack_out_n), .prog_ack_out_s(prog_ack_out_s),
        .prog_ack_out_e(prog_ack_out_e), .prog_ack_out_w(prog_ack_out_w),
        .freeze_in(freeze_comb),
        .status_active(status_active), .status_freeze_state(status_freeze_state)
    );

endmodule
