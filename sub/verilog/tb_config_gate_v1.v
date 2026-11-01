`default_nettype none
`timescale 1ns / 1ps
// Testbench for config_gate_v1 (spec tests 1-5, 7; test 6 is a SLOW CONSUMER
// stand-in for a busy divider, not the real divider cell).
// Region = adder_cell_v4s (cfg bit 0 = subtract) + sub_to_flex_v1.
module tb_config_gate_v1;
    parameter SETTLE = 1;
    reg clk = 0, rst = 1;
    always #5 clk = ~clk;
    integer fails = 0;
    task chk(input ok, input [479:0] name);
        begin
            if (ok) $display("ok %0s", name);
            else begin $display("FAIL %0s", name); fails = fails + 1; end
        end
    endtask

    // ---------------- producer: a queue of (a,b) words, level valid until acked
    reg [31:0] qa [0:15]; reg [31:0] qb [0:15];
    integer qn = 0, qi = 0; reg prod_en = 0;
    wire [63:0] in_data = {qa[qi], qb[qi]};
    wire in_valid = prod_en && (qi < qn);
    wire in_ack;
    always @(posedge clk) if (!rst && in_ack) qi <= qi + 1;

    // ---------------- gate + region + consumer
    wire [63:0] region_data; wire region_valid, done;
    reg cfg_req = 0; reg [31:0] cfg_word_in = 0;
    wire cfg_valid; wire [31:0] cfg_data; wire cfg_busy, cfg_done; wire [1:0] cfg_err;
    config_gate_v1 #(.WIDTH(64), .CFG_W(32), .SETTLE(SETTLE), .DRAIN_TIMEOUT(40)) G (
        .clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack),
        .region_data(region_data), .region_valid(region_valid), .done(done),
        .cfg_req(cfg_req), .cfg_word_in(cfg_word_in), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .cfg_busy(cfg_busy), .cfg_done(cfg_done), .cfg_err(cfg_err));
    wire [31:0] add_out; wire add_valid;
    adder_cell_v4s A (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .in_a(region_data[63:32]), .in_b(region_data[31:0]), .valid_in(region_valid),
        .data_out(add_out), .valid_out(add_valid));
    wire [31:0] out_data; wire out_valid; reg out_ack = 0;
    sub_to_flex_v1 #(.WIDTH(32)) B (.clk(clk), .rst(rst), .sub_data(add_out), .sub_valid(add_valid),
        .out_data(out_data), .out_valid(out_valid), .out_ack(out_ack), .done(done));
    // consumer: takes a result after `cons_delay` clocks of seeing it (0 = at once)
    integer cons_delay = 0, cons_wait = 0, never = 0;
    reg [31:0] res [0:31]; integer nres = 0;
    always @(posedge clk) begin
        out_ack <= 1'b0;
        if (rst) cons_wait <= 0;
        else if (out_valid && !out_ack && !never) begin
            if (cons_wait >= cons_delay) begin
                out_ack <= 1'b1; cons_wait <= 0;
            end else cons_wait <= cons_wait + 1;
        end
        if (out_valid && out_ack) begin res[nres] <= out_data; nres <= nres + 1; end
    end

    // ---------------- raw adder for test 1 (control, no gate)
    reg rcv = 0, rvin = 0; wire [31:0] rout; wire rvalid;
    adder_cell_v4s R (.clk(clk), .rst(rst), .cfg_valid(rcv), .cfg_data(32'h0),
        .in_a(32'd7), .in_b(32'd1), .valid_in(rvin), .data_out(rout), .valid_out(rvalid));

    // ---------------- helpers
    task req(input [31:0] w);
        begin @(negedge clk); cfg_req = 1; cfg_word_in = w; @(negedge clk); cfg_req = 0; end
    endtask
    task wait_idle; begin
        repeat (3) @(negedge clk);
        while (cfg_busy) @(negedge clk);
    end endtask
    task reset_all; begin
        rst = 1; prod_en = 0; qi = 0; qn = 0; nres = 0; never = 0; cons_delay = 0;
        repeat (3) @(negedge clk); rst = 0; @(negedge clk);
    end endtask
    task fill(input integer n, input [31:0] a, input [31:0] b);
        integer i; begin for (i = 0; i < n; i = i + 1) begin qa[i] = a; qb[i] = b; end qn = n; qi = 0; end
    endtask
    task drain_results(input integer n); integer t; begin
        t = 0; while (nres < n && t < 400) begin @(negedge clk); t = t + 1; end
        repeat (4) @(negedge clk);
    end endtask

    integer i, mono, goodnum;
    initial begin
        repeat (3) @(negedge clk); rst = 0; @(negedge clk);

        // T1 control: a word offered on the cfg_valid clock of a raw cell is dropped
        rcv = 1; rvin = 1; @(negedge clk); rcv = 0; rvin = 0;
        @(negedge clk); @(negedge clk);
        chk(rvalid === 1'b0, "T1 raw cell drops word on cfg clock");
        rvin = 1; @(negedge clk); rvin = 0; #1;
        chk(rvalid === 1'b1, "T1 raw cell takes word after cfg");

        // T2 gate: request in the same clock the first word is presented -> none lost, all new config
        reset_all; req(32'h0);   // initial add mode (arms the adder)
        wait_idle;
        fill(6, 5, 3); cfg_req = 0;
        @(negedge clk); cfg_req = 1; cfg_word_in = 32'h1; prod_en = 1; @(negedge clk); cfg_req = 0;
        drain_results(6);
        chk(nres == 6, "T2 six results, none lost");
        goodnum = 1; for (i = 0; i < nres; i = i + 1) if (res[i] !== 32'd2) goodnum = 0;
        chk(goodnum == 1, "T2 all six use the new config (5-3)");

        // T3 word in flight at request finishes under the old config
        reset_all; req(32'h0); wait_idle;
        fill(6, 5, 3); prod_en = 1;
        @(posedge in_ack); @(negedge clk);       // first word has just been admitted
        req(32'h1);
        drain_results(6);
        chk(nres == 6, "T3 six results, none lost");
        chk(res[0] === 32'd8, "T3 in-flight word used old config");
        mono = 1; for (i = 1; i < nres; i = i + 1) if (res[i] !== 32'd2) mono = 0;
        chk(mono == 1, "T3 later words use new config");

        // T4 second request while busy is rejected, first one applies
        reset_all; req(32'h0); wait_idle;
        fill(4, 9, 4); prod_en = 1;
        @(posedge in_ack); @(negedge clk);
        req(32'h1); req(32'h0);                  // second arrives while busy
        drain_results(4); wait_idle;
        chk(cfg_err[1] === 1'b1, "T4 second request flagged");
        chk(res[3] === 32'd5, "T4 first request (subtract) applied");

        // T5 drain timeout: consumer never takes the result -> old config kept
        reset_all; req(32'h0); wait_idle;
        fill(1, 5, 3); prod_en = 1; never = 1;
        @(posedge in_ack); @(negedge clk);
        req(32'h1);
        repeat (60) @(negedge clk);
        chk(cfg_err[0] === 1'b1, "T5 timeout flagged");
        chk(cfg_busy === 1'b0, "T5 gate reopened after timeout");
        never = 0; fill(1, 20, 6); prod_en = 1;
        drain_results(2);
        chk(res[1] === 32'd26, "T5 old config kept (20+6)");

        // T6 slow consumer (stand-in for a busy divider): drain waits, then configures
        reset_all; req(32'h0); wait_idle;
        cons_delay = 15; fill(2, 5, 3); prod_en = 1;
        @(posedge in_ack); @(negedge clk);
        req(32'h1);
        drain_results(2);
        chk(nres == 2 && res[0] === 32'd8 && res[1] === 32'd2, "T6 slow consumer: old then new");
        chk(cfg_err === 2'b00, "T6 no error");

        // T7 reset in CLOSING and in PROGRAM
        reset_all; req(32'h0); wait_idle;
        fill(1, 5, 3); prod_en = 1; never = 1;
        @(posedge in_ack); @(negedge clk);
        req(32'h1); repeat (3) @(negedge clk);
        chk(cfg_busy === 1'b1, "T7 gate closing before reset");
        rst = 1; repeat (2) @(negedge clk); rst = 0; @(negedge clk);
        chk(cfg_busy === 1'b0 && cfg_err === 2'b00, "T7 reset from CLOSING reopens");
        chk(in_ack === 1'b0 || in_valid === 1'b0, "T7 nothing admitted without data");
        // PROGRAM state is one clock: catch it
        never = 0; prod_en = 0;
        @(negedge clk); cfg_req = 1; cfg_word_in = 32'h0; @(negedge clk); cfg_req = 0;
        @(negedge clk);
        chk(cfg_valid === 1'b1, "T7 program clock seen");
        rst = 1; @(negedge clk); rst = 0; @(negedge clk);
        chk(cfg_busy === 1'b0 && cfg_valid === 1'b0, "T7 reset from PROGRAM reopens");

        if (fails == 0) $display("ALL CONFIG GATE TESTS PASS (SETTLE=%0d)", SETTLE);
        else $display("CONFIG GATE TESTS FAILED: %0d", fails);
        $finish;
    end
    initial begin #200000; $display("FAIL timeout"); $finish; end
endmodule
