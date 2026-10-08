// tb_mul_second_v5.v -- ledger #1036: the second output word (high word) of mul_cell_v5 / mul_cell_v5c. -DCELL=mul_cell_v5 | mul_cell_v5c
`timescale 1ns / 1ps
`ifndef CELL
`define CELL mul_cell_v5c
`endif
module tb_mul_second_v5;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1, cfg = 0; reg [63:0] cfg_d = 0;
    reg [31:0] din_w = 0; reg arr_w = 0;
    wire [31:0] do_e, do_s; wire f_e, f_s, ack_w, rdy;
    reg ak_e = 0, ak_s = 0;
    `CELL DUT (.clk(clk), .rst(rst), .active(1'b1), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(din_w),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(arr_w),
        .data_out_n(), .data_out_s(do_s), .data_out_e(do_e), .data_out_w(),
        .fire_n(), .fire_s(f_s), .fire_e(f_e), .fire_w(), .ready_out(rdy),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_w),
        .ack_in_n(1'b0), .ack_in_s(ak_s), .ack_in_e(ak_e), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0), .status_data_valid(), .status_a_arrived());
    integer errors = 0, ne = 0, ns = 0;
    reg [31:0] ev [0:15]; reg [31:0] sv [0:15];
    // handshake consumer: take a word on fire when no ack is in flight, ack it for one cycle (a re-armed second word keeps fire high, so edges cannot be used)
    always @(posedge clk) begin
        ak_e <= 1'b0; ak_s <= 1'b0;
        if (f_e && !ak_e) begin ev[ne] = do_e; ne = ne + 1; ak_e <= 1'b1; end
        if (f_s && !ak_s) begin sv[ns] = do_s; ns = ns + 1; ak_s <= 1'b1; end
    end
    task send(input [31:0] v);
        begin din_w = v; arr_w = 1; @(posedge clk); while (!ack_w) @(posedge clk); arr_w = 0; @(posedge clk); end
    endtask
    task conf(input second, input [5:0] sdown);
        begin
            @(posedge clk); cfg = 1;
            cfg_d = 64'h0; cfg_d[5:0] = 6'b000100; cfg_d[11:6] = 6'b001000; cfg_d[12] = second; cfg_d[39:34] = sdown;
            @(posedge clk); cfg = 0; ne = 0; ns = 0; repeat (3) @(posedge clk);
        end
    endtask
    task chk(input c, input [255:0] m); begin if (!c) begin $display("FAIL: %0s (ne=%0d ns=%0d)", m, ne, ns); errors = errors + 1; end end endtask
    initial begin
        #22 rst = 0;
        conf(1, 6'b000010);                  // high word south
        send(32'h00010000); send(32'h00010000); repeat (40) @(posedge clk);
        send(32'hFFFFFFFF); send(32'hFFFFFFFF); repeat (40) @(posedge clk);
        chk(ne == 2 && ns == 2, "apart: two low words east, two high words south");
        chk(ev[0] == 0 && sv[0] == 1, "0x10000 * 0x10000: low 0, high 1");
        chk(ev[1] == 1 && sv[1] == 32'hFFFFFFFE, "FFFFFFFF^2: low 1, high FFFFFFFE");
        conf(1, 6'b000000);                  // high word follows the low word
        send(32'd7); send(32'd3); repeat (40) @(posedge clk);
        chk(ne == 2 && ns == 0 && ev[0] == 21 && ev[1] == 0, "together: low then high east");
        conf(0, 6'b000000);                  // flag off: low word only
        send(32'd6); send(32'd7); repeat (40) @(posedge clk);
        chk(ne == 1 && ns == 0 && ev[0] == 42, "flag off: one word");
        if (errors == 0) $display("PASS: mul second output (high word): routed apart, together, off");
        else $display("FAIL: errors=%0d", errors);
        $finish;
    end
    initial begin #200000; $display("FAIL: timeout"); $finish; end
endmodule
