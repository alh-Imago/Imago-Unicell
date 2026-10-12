// tb_vixen_nano_cfg_v1.v -- ledger #1105: nano_gate_v4e's hold / feedback / re-emit / update / self-update behaviours set from CONFIG (cmd_latch[18:14]) must equal the same behaviours
// set by the live wires of nano_gate_v4c's interface. Two v4e cells get identical random stimulus; cell A has the live wires driven and the config bits clear, cell B the other way round;
// every clock the outputs must agree, for six combinations. A control run (B with the config bits clear) must DISAGREE, or the stimulus proves nothing. Also PROG_ID 7 sets the bits live.
`timescale 1ns / 1ps
module tb_vixen_nano_cfg_v1;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1;
    reg cfg_valid = 0; reg [127:0] cfg_a = 0, cfg_b = 0;
    reg [4:0] live = 0;
    reg [31:0] din = 0; reg arr = 0; reg ack = 0;
    wire [31:0] oa, ob; wire fa, fb, ra, rb;
    reg program_in = 0; reg [31:0] pdata = 0; reg parr = 0;
    nano_gate_v4e #(.CELL_ID(16'h0001), .ENABLE_DYNAMIC_ROUTING(1'b0)) A (
        .clk(clk), .rst(rst), .active(1'b1), .cfg_valid(cfg_valid), .cfg_data(cfg_a),
        .data_in_n(din), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(arr), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(oa), .data_out_w(), .fire_n(), .fire_s(), .fire_e(fa), .fire_w(),
        .ready_out(ra), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(), .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(live[0]), .fb_internal_in(live[1]), .a_reemit_in(live[2]), .a_update_in(live[3]), .a_self_update_in(live[4]),
        .program_in(1'b0), .program_done(), .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w());
    nano_gate_v4e #(.CELL_ID(16'h0002), .ENABLE_DYNAMIC_ROUTING(1'b0)) B (
        .clk(clk), .rst(rst), .active(1'b1), .cfg_valid(cfg_valid), .cfg_data(cfg_b),
        .data_in_n(din), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(arr), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(ob), .data_out_w(), .fire_n(), .fire_s(), .fire_e(fb), .fire_w(),
        .ready_out(rb), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(), .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0), .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(program_in), .program_done(), .prog_data_in_n(pdata), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(parr), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w());
    integer errors = 0, checks = 0, mism = 0, fires = 0;
    reg [31:0] lfsr = 32'hACE1_2468;
    task step; begin lfsr = {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]}; end endtask
    always @(posedge clk) begin
        if (fa) fires <= fires + 1;
    end
    task run(input integer n, input compare);
        integer k;
        begin
            for (k = 0; k < n; k = k + 1) begin
                @(negedge clk);
                step; arr = (lfsr[2:0] < 3); din = {lfsr[15:0], lfsr[31:16]} & 32'h0000_FFFF | 32'h0000_0001; ack = lfsr[6] | lfsr[7];
                #1;
                if (compare && (oa !== ob || fa !== fb || ra !== rb)) begin if (mism == 0) $display("  first mismatch t=%0t oa=%h ob=%h fa=%b fb=%b ra=%b rb=%b aA=%b aB=%b", $time, oa, ob, fa, fb, ra, rb, A.a_arrived, B.a_arrived); mism = mism + 1; end
            end
        end
    endtask
    task cfgboth(input [4:0] m, input b_has_bits);
        reg [127:0] base;
        begin
            base = 128'h0; base[9:0] = 10'h007; base[69:64] = 6'b000100; base[13] = 1'b1;
            @(negedge clk); live = m; cfg_a = base; cfg_b = base | (b_has_bits ? ({123'h0, m} << 14) : 128'h0); cfg_valid = 1; @(negedge clk); cfg_valid = 0;
        end
    endtask
    task chk(input cond, input [255:0] what);
        begin checks = checks + 1; if (!cond) begin errors = errors + 1; $display("FAIL: %0s (t=%0t)", what, $time); end end
    endtask
    integer idx; reg [4:0] ms [0:5];
    initial begin
        ms[0] = 5'b00001; ms[1] = 5'b00101; ms[2] = 5'b00011; ms[3] = 5'b01001; ms[4] = 5'b10001; ms[5] = 5'b11111;
        repeat (3) @(negedge clk); rst = 0;
        for (idx = 0; idx < 6; idx = idx + 1) begin
            cfgboth(ms[idx], 1); mism = 0; fires = 0; run(400, 1);
            chk(mism == 0, "config bits behave exactly like the live wires");
            chk(fires > 3 || ms[idx] == 5'b01001, "the stimulus makes the cell fire (the comparison is not empty; hold+update never fires by design)"); $display("  combo %b: fires=%0d mismatches=%0d", ms[idx], fires, mism);
        end
        // control: B without its config bits must disagree with A that has the live hold wire
        cfgboth(5'b00001, 0); mism = 0; run(400, 1);
        chk(mism > 0, "control: without the config bit the cells differ (hold is real)");
        // live programming: PROG_ID 7 sets the bits in B (A has the wires): equal again
        @(negedge clk); rst = 1; arr = 0; ack = 0; live = 0; @(negedge clk); rst = 0;   // a config load does not clear data_reg / a_arrived: start both cells from a true reset
        cfgboth(5'b00000, 0); @(negedge clk); arr = 0; ack = 0; repeat (3) @(negedge clk);   // A: no hold wire yet; B: no hold bit yet (the load sets a_arrived from the hold at load time)
        @(negedge clk); program_in = 1; pdata = {8'h0, 4'd7, 20'd1}; parr = 1; live = 5'b00001; @(negedge clk); parr = 0;   // wire and word land on the same clock
        @(negedge clk); pdata = {8'h0, 4'd15, 19'h0, 1'b1}; parr = 1; @(negedge clk); parr = 0; program_in = 0;
        repeat (4) @(negedge clk);
        mism = 0; run(300, 1);
        chk(mism == 0, "live PROG_ID 7 path: hold set by programming equals the live wire");
        if (errors == 0) $display("PASS: tb_vixen_nano_cfg_v1 -- %0d checks", checks);
        else $display("FAIL: tb_vixen_nano_cfg_v1 -- %0d of %0d checks failed", errors, checks);
        $finish;
    end
endmodule
