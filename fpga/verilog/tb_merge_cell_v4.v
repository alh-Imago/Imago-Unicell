// tb_merge_cell_v4.v -- ledger #1036: the merge core, all four modes. -DCELL=merge_cell_v4 | merge_cell_v4c.  A = north face, B = west face, result east.
`timescale 1ns / 1ps
`ifndef CELL
`define CELL merge_cell_v4c
`endif
module tb_merge_cell_v4;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1, cfg = 0; reg [79:0] cfg_d = 0;
    reg [31:0] din_n = 0, din_w = 0; reg arr_n = 0, arr_w = 0;
    wire [31:0] do_e; wire f_e, ack_n, ack_w, rdy;
    reg ak_e = 0;
    `CELL DUT (.clk(clk), .rst(rst), .active(1'b1), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(din_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(din_w),
        .arrived_n(arr_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(arr_w),
        .data_out_n(), .data_out_s(), .data_out_e(do_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(f_e), .fire_w(), .ready_out(rdy),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(ack_n), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ak_e), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0), .status_data_valid());
    integer errors = 0, ne = 0;
    reg [31:0] ev [0:15];
    always @(posedge clk) begin
        ak_e <= 1'b0;
        if (f_e && !ak_e) begin ev[ne] = do_e; ne = ne + 1; ak_e <= 1'b1; end
    end
    // a sender holds its word (arrived) until the cell acknowledges it
    reg done_n = 1, done_w = 1;
    task send_n(input [31:0] v); begin din_n = v; arr_n = 1; done_n = 0; end endtask
    task send_w(input [31:0] v); begin din_w = v; arr_w = 1; done_w = 0; end endtask
    always @(posedge clk) begin
        if (arr_n && ack_n) begin arr_n <= 0; done_n <= 1; end
        if (arr_w && ack_w) begin arr_w <= 0; done_w <= 1; end
    end
    task conf(input [1:0] m);
        begin
            @(posedge clk); cfg = 1; cfg_d = 80'h0; cfg_d[5:0] = 6'b000100; cfg_d[11:6] = 6'b001001; cfg_d[13:12] = m;   // up = N and W
            @(posedge clk); cfg = 0; ne = 0; repeat (3) @(posedge clk);
        end
    endtask
    task chk(input c, input [511:0] m); begin if (!c) begin $display("FAIL: %0s (ne=%0d)", m, ne); errors = errors + 1; end end endtask
    initial begin
        #22 rst = 0;
        conf(0);                       // A only
        send_n(32'h5); send_w(32'h9); repeat (40) @(posedge clk);
        chk(ne == 1 && ev[0] == 5, "A only: 5 passes");
        chk(arr_w == 1, "A only: B never accepted");
        arr_w = 0;
        conf(1);                       // B only
        send_n(32'h5); send_w(32'h9); repeat (40) @(posedge clk);
        chk(ne == 1 && ev[0] == 9, "B only: 9 passes");
        chk(arr_n == 1, "B only: A never accepted");
        arr_n = 0;
        conf(2);                       // arbitrate: both at once, then a lone one from each side
        send_n(32'h5); send_w(32'h9); repeat (60) @(posedge clk);
        chk(ne == 2 && ev[0] == 5 && ev[1] == 9, "arbitrate: tie goes to A first, then B (never fused)");
        send_n(32'h11); send_w(32'h22); repeat (60) @(posedge clk);
        chk(ne == 4 && ev[2] == 32'h11 && ev[3] == 32'h22, "rr rotates after every grant (B was last, so A first)");
        send_w(32'h33); repeat (30) @(posedge clk);
        chk(ne == 5 && ev[4] == 32'h33, "arbitrate: lone word from B passes");
        conf(3);                       // join-or
        send_n(32'h0F); repeat (30) @(posedge clk);
        chk(ne == 0, "join-or: one half alone never goes out");
        send_w(32'hF0); repeat (30) @(posedge clk);
        chk(ne == 1 && ev[0] == 32'hFF, "join-or: A|B");
        send_w(32'h100); repeat (10) @(posedge clk); send_n(32'h001); repeat (30) @(posedge clk);
        chk(ne == 2 && ev[1] == 32'h101, "join-or: B first, then A");
        if (errors == 0) $display("PASS: merge cell, A only / B only / arbitrate / join-or");
        else $display("FAIL: errors=%0d", errors);
        $finish;
    end
    initial begin #400000; $display("FAIL: timeout"); $finish; end
endmodule
