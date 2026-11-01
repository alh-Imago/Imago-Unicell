`default_nettype none
`timescale 1ns / 1ps
// config_gate_v1 in front of arith_block_v4, random stream with random reconfigurations (1 Nov 2026).
// GATED=1: producer -> config_gate_v1 -> arith_block_v4 -> sub_to_flex_v1 -> consumer. GATED=0 (control): the existing
// flex_to_sub_v1 and the configuration driven straight into the block at random clocks.
// Invariant checked for GATED=1: every word is processed under the config that was active when it was admitted, none lost, order kept.
// Phase 2 (GATED=1 only): a word that produces NO result (accumulate mode, neither pulse) leaves the one-word bridge busy for good.
module tb_gate_block_v2;
    parameter GATED = 1, NW = 1500;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    // ---- producer: level valid until acked, random bubbles between words
    reg [31:0] qa [0:2047]; reg [31:0] qb [0:2047]; integer qn = 0, qi = 0; reg have = 0; reg prod_on = 0;
    wire [63:0] in_data = {qa[qi], qb[qi]}; wire in_valid = prod_on && have && (qi < qn); wire in_ack;
    always @(posedge clk) begin
        if (rst) begin have <= 0; end
        else if (in_ack) begin qi <= qi + 1; have <= 0; end
        else if (!have && prod_on && ($urandom % 4 != 0)) have <= 1;
    end
    // ---- config driver
    reg cfg_req = 0; reg [31:0] cfg_word = 0; reg raw_cfgv = 0;
    wire g_cfgv; wire [31:0] g_cfgd; wire [63:0] region_data; wire region_valid; wire done; wire cfg_busy, cfg_done; wire [1:0] cfg_err; wire fault; reg kill = 0;
    wire blk_cfgv = GATED ? g_cfgv : raw_cfgv; wire [31:0] blk_cfgd = GATED ? g_cfgd : cfg_word;
    generate if (GATED) begin : g1
        config_gate_v2 #(.WIDTH(64), .CFG_W(32), .SETTLE(1), .DRAIN_TIMEOUT(60), .WATCHDOG(100)) G (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack),
            .region_data(region_data), .region_valid(region_valid), .done(done), .cfg_req(cfg_req), .cfg_word_in(cfg_word), .cfg_valid(g_cfgv), .cfg_data(g_cfgd),
            .cfg_busy(cfg_busy), .cfg_done(cfg_done), .cfg_err(cfg_err), .fault(fault));
    end else begin : g0
        reg [63:0] rd; reg rv; reg busy;
        assign in_ack = in_valid & ~busy & ~rst; assign region_data = rd; assign region_valid = rv; assign cfg_busy = 0; assign cfg_done = 0; assign cfg_err = 0; assign fault = 0; assign g_cfgv = 0; assign g_cfgd = 0;
        always @(posedge clk) begin
            if (rst) begin busy <= 0; rv <= 0; rd <= 0; end
            else begin rv <= in_ack; if (in_ack) begin rd <= in_data; busy <= 1; end else if (done) busy <= 0; end
        end
    end endgenerate
    wire [31:0] bo; wire bv;
    arith_block_v4 #(.SHARED(1)) B (.clk(clk), .rst(rst), .cfg_valid(blk_cfgv), .cfg_data(blk_cfgd), .in_a(region_data[63:32]), .in_b(region_data[31:0]), .valid_in(region_valid), .data_out(bo), .valid_out(bv));
    wire [31:0] out_data; wire out_valid; reg out_ack = 0;
    sub_to_flex_v1 #(.WIDTH(32)) O (.clk(clk), .rst(rst), .sub_data(bo), .sub_valid(bv & ~kill), .out_data(out_data), .out_valid(out_valid), .out_ack(out_ack), .done(done));
    // ---- consumer: random delay 0..3
    reg [31:0] res [0:2047]; integer nres = 0, cw = 0, cd = 0;
    always @(posedge clk) begin
        out_ack <= 0;
        if (rst) begin cw <= 0; cd <= 0; end
        else if (out_valid && !out_ack) begin if (cw >= cd) begin out_ack <= 1; cw <= 0; cd <= $urandom % 4; end else cw <= cw + 1; end
        if (out_valid && out_ack) begin res[nres] <= out_data; nres <= nres + 1; end
    end
    // ---- monitor / reference model: config seen by the block, expected result at admission
    reg [2:0] cmode = 0; reg [7:0] cstep = 0; reg [31:0] ctot = 0; reg mon_en = 1; reg [31:0] ex [0:2047]; integer nex = 0, nconf = 0;
    reg [31:0] ea, eb, er;
    always @(posedge clk) if (!rst) begin
        if (blk_cfgv) begin cmode <= blk_cfgd[2:0]; cstep <= blk_cfgd[15:8]; ctot <= 0; nconf <= nconf + 1; end
        if (in_ack && mon_en) begin
            ea = in_data[63:32]; eb = in_data[31:0];
            case (cmode)
                0: er = ea + eb;
                1: er = ea - eb;
                2: er = ($signed(ea) >= $signed(eb)) ? 1 : 0;
                3: er = ($signed(ea) < $signed(eb)) ? 0 : (ea == eb) ? 1 : 2;
                default: begin er = ctot + ((ea[0] && !ea[1]) ? cstep : (ea[1] && !ea[0]) ? -cstep : 0); ctot <= er; end
            endcase
            ex[nex] = er; nex = nex + 1;
        end
    end
    // ---- random reconfiguration requests while the stream runs
    integer gap = 10, nreq = 0; reg stream_on = 0;
    always @(posedge clk) begin
        cfg_req <= 0; raw_cfgv <= 0;
        if (stream_on) begin
            if (gap == 0) begin
                cfg_word <= (((1 + ($urandom % 200)) << 8) | ($urandom % 5)); nreq <= nreq + 1;
                if (GATED) cfg_req <= 1; else raw_cfgv <= 1;
                gap <= 4 + ($urandom % 40);
            end else gap <= gap - 1;
        end
    end
    integer i, bad = 0, t;
    initial begin
        for (i = 0; i < NW; i = i + 1) begin qa[i] = $urandom; qa[i][1:0] = 1 + ($urandom % 3); qb[i] = $urandom; end
        qn = NW;
        repeat (3) @(negedge clk); rst = 0; @(negedge clk);
        // initial config: mode 0 through the same door
        cfg_word = 32'h0; if (GATED) cfg_req = 1; else raw_cfgv = 1; @(negedge clk); cfg_req = 0; raw_cfgv = 0; repeat (4) @(negedge clk);
        prod_on = 1; stream_on = 1;
        t = 0; while (qi < qn && t < 40000) begin @(negedge clk); t = t + 1; end
        stream_on = 0; repeat (200) @(negedge clk);
        if (GATED) begin
            bad = 0; if (nres != nex) begin bad = bad + 1; $display("COUNT: admitted %0d results %0d", nex, nres); end
            for (i = 0; i < nres && i < nex; i = i + 1) if (res[i] !== ex[i]) begin bad = bad + 1; if (bad < 6) $display("WORD %0d: got %h want %h", i, res[i], ex[i]); end
            if (bad == 0 && qi == qn) $display("ALL GATE+BLOCK TESTS PASS (%0d words, %0d config changes seen, %0d requests, rejected=%b)", nex, nconf, nreq, cfg_err[1]);
            else $display("GATE+BLOCK FAILED: %0d problems, %0d of %0d words admitted", bad, qi, qn);
            // phase 2: accumulate mode, a word with NEITHER pulse is now answered, so the second word is admitted too
            mon_en = 0; prod_on = 0; @(negedge clk); cfg_word = 32'h0000_0004; cfg_req = 1; @(negedge clk); cfg_req = 0; repeat (8) @(negedge clk);
            qa[0] = 32'h0; qb[0] = 0; qa[1] = 32'h1; qb[1] = 0; qn = 2; qi = 0; have = 0; prod_on = 1;
            repeat (80) @(negedge clk);
            $display("PHASE2 no-pulse word: admitted=%0d (2 = every word answered)", qi);
            if (fault !== 1'b0) $display("PHASE2 FAIL fault raised without a stuck cell");
            // phase 3: the region goes dead (answers never reach the bridge): the watchdog must raise `fault`
            prod_on = 0; repeat (4) @(negedge clk); kill = 1; qa[0] = 32'h1; qb[0] = 0; qa[1] = 32'h1; qb[1] = 0; qn = 2; qi = 0; have = 0; prod_on = 1;
            repeat (60) @(negedge clk);
            $display("PHASE3 dead region, 60 clocks: fault=%b (0 expected, not yet)", fault);
            repeat (120) @(negedge clk);
            $display("PHASE3 dead region, 180 clocks: fault=%b (1 expected) admitted=%0d (1: the second word waits behind the stuck one)", fault, qi);
        end else begin
            for (i = 0; i < nres && i < nex; i = i + 1) if (res[i] !== ex[i]) bad = bad + 1;
            if (nres != nex) bad = bad + 1;
            if (bad > 0) $display("CONTROL SHOWS CORRUPTION: %0d problems; admitted %0d of %0d words, %0d results", bad, qi, qn, nres);
            else $display("CONTROL SHOWS NO CORRUPTION (unexpected)");
        end
        $finish;
    end
endmodule
