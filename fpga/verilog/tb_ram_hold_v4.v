// tb_ram_hold_v4.v -- ledger #1035: HOLD mode of ram_cell_v4 / ram_cell_v4c (fixed_mode=1 with a non-empty upstream mask).
// Compile with -DCELL=ram_cell_v4 or -DCELL=ram_cell_v4c.
`timescale 1ns / 1ps
`ifndef CELL
`define CELL ram_cell_v4c
`endif
module tb_ram_hold_v4;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1;
    reg cfg = 0; reg [79:0] cfg_d = 0;
    localparam [5:0] DIR_E6 = 6'b000100, DIR_W6 = 6'b001000;
    reg [31:0] opW = 0; reg pulse_w = 0;
    wire [31:0] dout_e; wire fire_e, ready_o, ack_w;
    reg cons_ack = 0;
    `CELL #(.CELL_ID(16'h0000)) DUT (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(opW),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(pulse_w),
        .data_out_n(), .data_out_s(), .data_out_e(dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0), .status_data_valid()
    );
    integer errors = 0, fires = 0, acks = 0;
    reg [31:0] last_val = 0;
    // consumer: ack one cycle after every fire, log the value
    reg fire_d = 0;
    always @(posedge clk) begin
        cons_ack <= fire_e;
        if (fire_e && !fire_d) begin fires = fires + 1; last_val = dout_e; end
        fire_d <= fire_e;
        if (ack_w) acks = acks + 1;
    end
    task send(input [31:0] v);
        begin opW = v; pulse_w = 1; #10; pulse_w = 0; end
    endtask
    task expect_ok(input cond, input [255:0] msg);
        begin if (!cond) begin $display("FAIL: %0s (t=%0t)", msg, $time); errors = errors + 1; end end
    endtask
    integer f0;
    initial begin
        #12 rst = 0;
        // fixed=1, upstream W, downstream E, no preload
        #10 cfg = 1; cfg_d = {34'h0, 32'h0, 1'b0, 1'b1, DIR_W6, DIR_E6}; #10 cfg = 0;
        #100;
        expect_ok(fires == 0, "empty hold offers nothing");
        expect_ok(ready_o === 1'b1, "empty hold is ready to accept");
        send(32'h0000_00AA);
        #200;
        expect_ok(acks == 1, "first write acknowledged");
        expect_ok(fires >= 3, "held word offered again and again");
        expect_ok(last_val == 32'hAA, "offered word is AA");
        expect_ok(ready_o === 1'b1, "still ready after being filled (replaceable)");
        send(32'hDEAD_BEEF);
        #200;
        expect_ok(acks == 2, "replacement acknowledged");
        expect_ok(last_val == 32'hDEADBEEF, "replacement visible");
        f0 = fires; #200;
        expect_ok(fires > f0, "keeps offering after replacement");
        // preload via load_data_valid
        #10 cfg = 1; cfg_d = {34'h0, 32'h1234_5678, 1'b1, 1'b1, DIR_W6, DIR_E6}; #10 cfg = 0;
        #200;
        expect_ok(last_val == 32'h1234_5678, "preloaded word offered");
        // fixed with NO upstream remains a plain constant, ignores arrivals
        #10 cfg = 1; cfg_d = {34'h0, 32'h77, 1'b1, 1'b1, 6'b0, DIR_E6}; #10 cfg = 0;
        #100; acks = 0;
        send(32'h99);
        #100;
        expect_ok(acks == 0, "constant ignores arrivals");
        expect_ok(last_val == 32'h77, "constant keeps its value");
        expect_ok(ready_o === 1'b0, "constant not ready");
        if (errors == 0) $display("PASS: HOLD (empty/write/repeat/replace/preload/constant)");
        else $display("FAIL: errors=%0d", errors);
        $finish;
    end
endmodule
