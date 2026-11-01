`default_nettype none
`timescale 1ns / 1ps
// Chain of three small limited units (1 Nov 2026): producer -> [gate_v3 -> arith_block_v4 -> sub_to_flex] x3 -> consumer, the units joined by the
// flex hand-off (the sub's chain rule: forward valid, one word in flight, a bridge between units). Stage 1 adds 0 (pass the word's a+b), stage 2 subtracts a constant,
// stage 3 compares >= a constant. Each stage has a model-checker that works out the expected result of every admitted word from the config active at admission.
// SCEN 1 transient fault in stage 2, recovered. 2 two far-apart transient faults, MAX_RETRY=1, both recovered. 3 persistent fault, MAX_RETRY=1 -> dead.
// SCEN 4 downstream stall longer than WATCHDOG: no fault. 5 clean run with random reconfiguration of stage 2, and chain throughput.
module tb_stage #(parameter MAXR = 2) (
    input wire clk, input wire rst, input wire [63:0] in_data, input wire in_valid, output wire in_ack,
    output wire [31:0] out_data, output wire out_valid, input wire out_ack,
    input wire cfg_req, input wire [31:0] cfg_word, input wire kill,
    output wire fault, output wire dead, output wire blocked, output wire [7:0] resets, output wire [7:0] lost, output wire [1:0] cfg_err, output wire cfg_busy, output wire region_rst,
    output wire blk_cfgv, output wire [31:0] blk_cfgd, output wire [63:0] region_data_o
);
    wire [63:0] region_data; wire region_valid, done; wire cfg_done;
    wire rr = rst | region_rst;
    config_gate_v3 #(.WIDTH(64), .CFG_W(32), .SETTLE(1), .DRAIN_TIMEOUT(60), .WATCHDOG(100), .MAX_RETRY(MAXR), .GOOD_WORDS(16)) G (
        .clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack), .region_data(region_data), .region_valid(region_valid),
        .done(done), .res_valid(out_valid), .cfg_req(cfg_req), .cfg_word_in(cfg_word), .cfg_valid(blk_cfgv), .cfg_data(blk_cfgd), .cfg_busy(cfg_busy), .cfg_done(cfg_done), .cfg_err(cfg_err),
        .region_rst(region_rst), .fault(fault), .dead(dead), .blocked(blocked), .resets(resets), .lost(lost));
    wire [31:0] bo; wire bv;
    arith_block_v4 #(.SHARED(1)) B (.clk(clk), .rst(rr), .cfg_valid(blk_cfgv), .cfg_data(blk_cfgd), .in_a(region_data[63:32]), .in_b(region_data[31:0]), .valid_in(region_valid), .data_out(bo), .valid_out(bv));
    sub_to_flex_v1 #(.WIDTH(32)) O (.clk(clk), .rst(rr), .sub_data(bo), .sub_valid(bv & ~kill), .out_data(out_data), .out_valid(out_valid), .out_ack(out_ack), .done(done));
    assign region_data_o = region_data;
endmodule

// reference model and comparator for one stage
module tb_check (
    input wire clk, input wire rst, input wire in_ack, input wire [63:0] in_data, input wire cfgv, input wire [31:0] cfgd,
    input wire take, input wire [31:0] out_data, input wire [7:0] lost, output integer bad, output integer nex, output integer nres
);
    reg [2:0] cmode = 0; reg [7:0] cstep = 0; reg [31:0] ctot = 0; reg [31:0] ex [0:4095]; reg [7:0] lost_prev = 0; reg [31:0] ea, eb, er;
    initial begin bad = 0; nex = 0; nres = 0; end
    always @(posedge clk) if (rst) begin nex = 0; nres = 0; lost_prev <= 0; cmode <= 0; ctot <= 0; end
    else begin
        if (lost != lost_prev) begin lost_prev <= lost; if (nex > nres) nex = nex - 1; end   // the word in flight was lost: forget its expectation
        if (cfgv) begin cmode <= cfgd[2:0]; cstep <= cfgd[15:8]; ctot <= 0; end
        if (in_ack) begin
            ea = in_data[63:32]; eb = in_data[31:0];
            case (cmode)
                0: er = ea + eb; 1: er = ea - eb; 2: er = ($signed(ea) >= $signed(eb)) ? 1 : 0;
                3: er = ($signed(ea) < $signed(eb)) ? 0 : (ea == eb) ? 1 : 2;
                default: begin er = ctot + ((ea[0] && !ea[1]) ? cstep : (ea[1] && !ea[0]) ? -cstep : 0); ctot <= er; end
            endcase
            ex[nex] = er; nex = nex + 1;
        end
        if (take) begin if (nres < nex && out_data === ex[nres]) nres = nres + 1; else begin bad = bad + 1; nres = nres + 1; end end
    end
endmodule

module tb_chain_v1;
    parameter SCEN = 1, MAXR = 2, NW = 300;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    // producer
    reg [31:0] qa [0:511]; reg [31:0] qb [0:511]; integer qi = 0; reg have = 0; reg prod_on = 0;
    wire [63:0] d1 = {qa[qi], qb[qi]}; wire v1 = prod_on && have && (qi < NW); wire a1;
    always @(posedge clk) begin if (rst) have <= 0; else if (a1) begin qi <= qi + 1; have <= 0; end else if (!have && prod_on && ($urandom % 4 != 0)) have <= 1; end
    // chain wires
    wire [31:0] o1, o2, o3; wire ov1, ov2, ov3, oa1, oa2, oa3, a2, a3;
    reg [31:0] B2 = 32'd100, B3 = 32'd7;
    reg rq1 = 0, rq2 = 0, rq3 = 0; reg [31:0] cw1 = 0, cw2 = 0, cw3 = 0; reg k1 = 0, k2 = 0, k3 = 0;
    wire f1, f2, f3, dd1, dd2, dd3, bl1, bl2, bl3, cb1, cb2, cb3, rr1, rr2, rr3; wire [7:0] rs1, rs2, rs3, ls1, ls2, ls3; wire [1:0] ce1, ce2, ce3;
    wire cv1, cv2, cv3; wire [31:0] cd1, cd2, cd3; wire [63:0] rd1, rd2, rd3;
    tb_stage #(.MAXR(MAXR)) S1 (.clk(clk), .rst(rst), .in_data(d1), .in_valid(v1), .in_ack(a1), .out_data(o1), .out_valid(ov1), .out_ack(a2), .cfg_req(rq1), .cfg_word(cw1), .kill(k1),
        .fault(f1), .dead(dd1), .blocked(bl1), .resets(rs1), .lost(ls1), .cfg_err(ce1), .cfg_busy(cb1), .region_rst(rr1), .blk_cfgv(cv1), .blk_cfgd(cd1), .region_data_o(rd1));
    wire [63:0] d2 = {o1, B2};
    tb_stage #(.MAXR(MAXR)) S2 (.clk(clk), .rst(rst), .in_data(d2), .in_valid(ov1), .in_ack(a2), .out_data(o2), .out_valid(ov2), .out_ack(a3), .cfg_req(rq2), .cfg_word(cw2), .kill(k2),
        .fault(f2), .dead(dd2), .blocked(bl2), .resets(rs2), .lost(ls2), .cfg_err(ce2), .cfg_busy(cb2), .region_rst(rr2), .blk_cfgv(cv2), .blk_cfgd(cd2), .region_data_o(rd2));
    wire [63:0] d3 = {o2, B3};
    tb_stage #(.MAXR(MAXR)) S3 (.clk(clk), .rst(rst), .in_data(d3), .in_valid(ov2), .in_ack(a3), .out_data(o3), .out_valid(ov3), .out_ack(oa3), .cfg_req(rq3), .cfg_word(cw3), .kill(k3),
        .fault(f3), .dead(dd3), .blocked(bl3), .resets(rs3), .lost(ls3), .cfg_err(ce3), .cfg_busy(cb3), .region_rst(rr3), .blk_cfgv(cv3), .blk_cfgd(cd3), .region_data_o(rd3));
    // final consumer: random delay, or stalled
    reg stall = 0; integer cwt = 0, cdl = 0; reg ack3 = 0; assign oa3 = ack3;
    always @(posedge clk) begin
        ack3 <= 0;
        if (rst) begin cwt <= 0; cdl <= 0; end
        else if (ov3 && !ack3 && !stall) begin if (cwt >= cdl) begin ack3 <= 1; cwt <= 0; cdl <= $urandom % 3; end else cwt <= cwt + 1; end
    end
    wire take3 = ov3 && ack3;
    integer bad1, bad2, bad3, nex1, nex2, nex3, nr1, nr2, nr3;
    tb_check C1 (.clk(clk), .rst(rst), .in_ack(a1), .in_data(d1), .cfgv(cv1), .cfgd(cd1), .take(ov1 && a2), .out_data(o1), .lost(ls1), .bad(bad1), .nex(nex1), .nres(nr1));
    tb_check C2 (.clk(clk), .rst(rst), .in_ack(a2), .in_data(d2), .cfgv(cv2), .cfgd(cd2), .take(ov2 && a3), .out_data(o2), .lost(ls2), .bad(bad2), .nex(nex2), .nres(nr2));
    tb_check C3 (.clk(clk), .rst(rst), .in_ack(a3), .in_data(d3), .cfgv(cv3), .cfgd(cd3), .take(take3), .out_data(o3), .lost(ls3), .bad(bad3), .nex(nex3), .nres(nr3));
    // kill control on stage 2 (counted in admissions) and bookkeeping
    integer n2 = 0, kills = 0, cyc = 0, t0 = -1, t1 = 0, maxbl = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (!rst && a1 && t0 < 0) t0 <= cyc;
        if (take3) t1 <= cyc;
        if (bl1 | bl2 | bl3) maxbl <= maxbl + 1;
        if (!rst && a2) begin
            n2 <= n2 + 1;
            if ((SCEN == 1 && n2 == 100) || (SCEN == 2 && (n2 == 60 || n2 == 160)) || (SCEN == 3 && n2 == 60)) begin k2 <= 1; kills <= kills + 1; end
        end
        if (SCEN != 3 && rr2) k2 <= 0;   // transient: the fault clears when the region is reset
    end
    // random reconfiguration of stage 2 (SCEN 5)
    integer gap = 30;
    always @(posedge clk) begin
        rq2 <= 0;
        if (SCEN == 5 && prod_on) begin
            if (gap == 0) begin cw2 <= (((1 + ($urandom % 100)) << 8) | ($urandom % 4)); rq2 <= 1; gap <= 15 + ($urandom % 40); end else gap <= gap - 1;
        end
    end
    task setcfg; begin
        @(negedge clk); cw1 = 32'h0; cw2 = 32'h1; cw3 = 32'h2; rq1 = 1; rq2 = 1; rq3 = 1; @(negedge clk); rq1 = 0; rq2 = 0; rq3 = 0; repeat (8) @(negedge clk);
    end endtask
    integer i, t; integer errs = 0;
    task expect_(input ok, input [400:1] what); begin if (!ok) begin errs = errs + 1; $display("FAIL %0s", what); end end endtask
    initial begin
        for (i = 0; i < NW; i = i + 1) begin qa[i] = $urandom; qb[i] = $urandom; end
        repeat (3) @(negedge clk); rst = 0; @(negedge clk);
        setcfg; prod_on = 1;
        if (SCEN == 4) begin repeat (120) @(negedge clk); stall = 1; repeat (400) @(negedge clk); expect_(bl3 || bl2 || bl1, "blocked never rose"); stall = 0; end
        t = 0; while (qi < NW && t < 60000) begin @(negedge clk); t = t + 1; end
        repeat (600) @(negedge clk);
        $display("SCEN %0d MAXR %0d: stage1 faults/resets/lost=%0d/%0d/%0d dead=%0d | stage2 fault=%0d resets=%0d lost=%0d dead=%0d | stage3 resets=%0d lost=%0d | checks bad=%0d/%0d/%0d | words in: s1 %0d s2 %0d s3 %0d out %0d | blocked-clocks %0d",
            SCEN, MAXR, f1, rs1, ls1, dd1, f2, rs2, ls2, dd2, rs3, ls3, bad1, bad2, bad3, nex1, nex2, nex3, nr3, maxbl);
        expect_(bad1 == 0 && bad2 == 0 && bad3 == 0, "a result differed from the model");
        case (SCEN)
            1: begin expect_(rs2 == 1 && ls2 == 1 && !dd2 && f2, "stage2 should recover once"); expect_(rs1 == 0 && rs3 == 0 && !f1 && !f3, "neighbours must not fault"); expect_(nr3 == NW - 1 && nr1 == NW, "word counts"); end
            2: begin expect_(rs2 == 2 && ls2 == 2 && !dd2, "both faults recovered (retries forgiven)"); expect_(nr3 == NW - 2, "word count"); end
            3: begin expect_(dd2 && rs2 == 1 && ls2 == 2, "stage2 should be dead after 1 reset"); expect_(!dd1 && !dd3 && rs1 == 0 && rs3 == 0, "neighbours must not be reset"); expect_(nex2 < NW && qi < NW, "upstream should be held"); expect_(nr3 == nex3, "stage3 only got what stage2 delivered"); end
            4: begin expect_(!f1 && !f2 && !f3 && rs1 == 0 && rs2 == 0 && rs3 == 0, "a downstream stall must not cause a fault or reset"); expect_(nr3 == NW && nr1 == NW, "no word lost in the stall"); end
            5: begin expect_(!f1 && !f2 && !f3 && nr3 == NW, "clean run"); $display("THROUGHPUT chain of 3: %0d clocks for %0d words = %0d clocks per word", t1 - t0, NW, (t1 - t0) / (NW - 1)); end
        endcase
        if (errs == 0) $display("CHAIN SCEN %0d PASS", SCEN); else $display("CHAIN SCEN %0d FAILED (%0d)", SCEN, errs);
        $finish;
    end
endmodule
