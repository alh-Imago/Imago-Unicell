// tb_adder_second_v4.v -- ledger #1036: the optional second output word (carry) of adder_cell_v4 / adder_cell_v4c. -DCELL=adder_cell_v4 | adder_cell_v4c
`timescale 1ns / 1ps
`ifndef CELL
`define CELL adder_cell_v4c
`endif
module tb_adder_second_v4;
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
    task conf(input sub, input second, input [5:0] sdown);
        begin
            @(posedge clk); cfg = 1;
            cfg_d = 64'h0; cfg_d[5:0] = 6'b000100; cfg_d[11:6] = 6'b001000; cfg_d[12] = sub; cfg_d[33] = second; cfg_d[39:34] = sdown;
            @(posedge clk); cfg = 0; ne = 0; ns = 0; repeat (3) @(posedge clk);
        end
    endtask
    task chk(input c, input [255:0] m); begin if (!c) begin $display("FAIL: %0s (ne=%0d ns=%0d)", m, ne, ns); errors = errors + 1; end end endtask
    initial begin
        #22 rst = 0;
        // 1. carry routed apart (south): sums east, carries south
        conf(0, 1, 6'b000010);
        send(32'hFFFFFFFF); send(32'h1); repeat (30) @(posedge clk);
        send(32'd5); send(32'd3); repeat (30) @(posedge clk);
        chk(ne == 2 && ns == 2, "apart: two sums east, two carries south");
        chk(ev[0] == 0 && sv[0] == 1, "FFFFFFFF + 1 = 0 carry 1");
        chk(ev[1] == 8 && sv[1] == 0, "5 + 3 = 8 carry 0");
        // 2. carry follows the sum on the same face (second_downstream_mask 0): east gets sum, carry, sum, carry
        conf(0, 1, 6'b000000);
        send(32'hFFFFFFFF); send(32'h2); repeat (40) @(posedge clk);
        send(32'd7); send(32'd1); repeat (40) @(posedge clk);
        chk(ne == 4 && ns == 0, "together: four words east");
        chk(ev[0] == 1 && ev[1] == 1 && ev[2] == 8 && ev[3] == 0, "sum,carry,sum,carry in order");
        // 3. subtract: raw carry of a + ~b + 1 (1 when no borrow)
        conf(1, 1, 6'b000010);
        send(32'd5); send(32'd3); repeat (30) @(posedge clk);
        send(32'd3); send(32'd5); repeat (30) @(posedge clk);
        chk(ev[0] == 2 && sv[0] == 1, "5 - 3 = 2, carry 1");
        chk(ev[1] == 32'hFFFFFFFE && sv[1] == 0, "3 - 5 wraps, carry 0");
        // 4. flag off: nothing changes, no second word
        conf(0, 0, 6'b000000);
        send(32'd10); send(32'd20); repeat (30) @(posedge clk);
        chk(ne == 1 && ns == 0 && ev[0] == 30, "flag off: one word only");
        if (errors == 0) $display("PASS: adder second output (carry): routed apart, together, subtract, off");
        else $display("FAIL: errors=%0d", errors);
        $finish;
    end
    initial begin #200000; $display("FAIL: timeout"); $finish; end
endmodule
