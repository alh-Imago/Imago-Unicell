// tb_corner_cell_v4.v -- ledger #1035: corner wiring core. Compile with -DCELL=corner_cell_v4 or corner_cell_v4c.
`timescale 1ns / 1ps
`ifndef CELL
`define CELL corner_cell_v4c
`endif
module tb_corner_cell_v4;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1, cfg = 0; reg [79:0] cfg_d = 0;
    reg [31:0] din_n = 0, din_s = 0, din_e = 0, din_w = 0;
    reg arr_n = 0, arr_s = 0, arr_e = 0, arr_w = 0;
    wire [31:0] do_n, do_s, do_e, do_w; wire f_n, f_s, f_e, f_w, rdy, a_n, a_s, a_e, a_w;
    reg ak_n = 0, ak_s = 0, ak_e = 0, ak_w = 0;
    `CELL DUT (.clk(clk), .rst(rst), .active(1'b1), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(din_n), .data_in_s(din_s), .data_in_e(din_e), .data_in_w(din_w),
        .arrived_n(arr_n), .arrived_s(arr_s), .arrived_e(arr_e), .arrived_w(arr_w),
        .data_out_n(do_n), .data_out_s(do_s), .data_out_e(do_e), .data_out_w(do_w),
        .fire_n(f_n), .fire_s(f_s), .fire_e(f_e), .fire_w(f_w), .ready_out(rdy),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(a_n), .ack_out_s(a_s), .ack_out_e(a_e), .ack_out_w(a_w),
        .ack_in_n(ak_n), .ack_in_s(ak_s), .ack_in_e(ak_e), .ack_in_w(ak_w),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(), .freeze_in(1'b0), .status_data_valid());
    // consumer on every face: ack one cycle after a fire, log value
    integer errors = 0;
    reg [31:0] got_n, got_s, got_e, got_w; reg gn = 0, gs = 0, ge = 0, gw = 0;
    always @(posedge clk) begin
        ak_n <= f_n; ak_s <= f_s; ak_e <= f_e; ak_w <= f_w;
        if (f_n && !ak_n) begin got_n <= do_n; gn <= 1; end
        if (f_s && !ak_s) begin got_s <= do_s; gs <= 1; end
        if (f_e && !ak_e) begin got_e <= do_e; ge <= 1; end
        if (f_w && !ak_w) begin got_w <= do_w; gw <= 1; end
        // senders drop their pulse once acknowledged
        if (a_n) arr_n <= 0; if (a_s) arr_s <= 0; if (a_e) arr_e <= 0; if (a_w) arr_w <= 0;
    end
    task chk(input c, input [255:0] m); begin if (!c) begin $display("FAIL: %0s", m); errors = errors + 1; end end endtask
    task clr; begin gn = 0; gs = 0; ge = 0; gw = 0; end endtask
    task setturn(input t); begin #10 cfg = 1; cfg_d = {79'h0, t}; #10 cfg = 0; clr; end endtask
    initial begin
        #22 rst = 0;
        setturn(0);
        // turn 0: E<->N, W<->S -- all four directions at once
        din_w = 32'h11; arr_w = 1; din_n = 32'h22; arr_n = 1; din_e = 32'h33; arr_e = 1; din_s = 32'h44; arr_s = 1;
        #120;
        chk(gs && got_s == 32'h11, "turn0 W->S");
        chk(ge && got_e == 32'h22, "turn0 N->E");
        chk(gn && got_n == 32'h33, "turn0 E->N");
        chk(gw && got_w == 32'h44, "turn0 S->W");
        setturn(1);
        // turn 1: E<->S, W<->N
        din_w = 32'hA1; arr_w = 1; din_n = 32'hB2; arr_n = 1; din_e = 32'hC3; arr_e = 1; din_s = 32'hD4; arr_s = 1;
        #120;
        chk(gn && got_n == 32'hA1, "turn1 W->N");
        chk(gw && got_w == 32'hB2, "turn1 N->W");
        chk(gs && got_s == 32'hC3, "turn1 E->S");
        chk(ge && got_e == 32'hD4, "turn1 S->E");
        chk(rdy === 1'b1, "ready after drain");
        if (errors == 0) $display("PASS: corner cell, both turns, four independent directions");
        else $display("FAIL: errors=%0d", errors);
        $finish;
    end
endmodule
