`default_nettype none
`timescale 1ns / 1ps
// join_v1 alone, then join -> config_gate_v3 -> arith_block_v5 (nano mode, sticky B) -> sub_to_flex against the REAL nano_cell_v4s. 1 Nov 2026.
module tb_join_v1;
    parameter SCEN = 1;   // 4 sticky B: a new B must not change a waiting pair.  1 pair mode, random arrival order; 2 sticky B with controlled sequence; 3 join + gate + block (nano XOR, sticky) vs the real nano cell
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    // two producers, each presents a word as a level until acked, random gaps, random bias to A-first or B-first
    reg [31:0] qa [0:1023]; reg [31:0] qb [0:1023]; integer ia = 0, ib = 0, na = 0, nb = 0; reg pa = 0, pb = 0; reg ha = 0, hb = 0; integer bias = 0;
    wire [63:0] jd; wire jv, jack, aack, back;
    wire a_valid = pa && ha && (ia < na), b_valid = pb && hb && (ib < nb);
    always @(posedge clk) if (rst) begin ha <= 0; hb <= 0; end else begin
        if (aack) begin ia <= ia + 1; ha <= 0; end else if (!ha && pa && ($urandom % (bias > 0 ? 6 : 2) == 0)) ha <= 1;
        if (back) begin ib <= ib + 1; hb <= 0; end else if (!hb && pb && ($urandom % (bias < 0 ? 6 : 2) == 0)) hb <= 1;
    end
    wire sticky = (SCEN != 1);
    join_v1 #(.STICKY_B(SCEN != 1)) J (.clk(clk), .rst(rst), .a_data(qa[ia]), .a_valid(a_valid), .a_ack(aack), .b_data(qb[ib]), .b_valid(b_valid), .b_ack(back), .out_data(jd), .out_valid(jv), .out_ack(jack));
    // ---- SCEN 1 / 2 consumer: takes the pair after a random delay
    reg take_en = 0; integer cw = 0, cdl = 0; reg [63:0] got [0:2047]; integer ng = 0; reg ack_r = 0;
    wire plain_ack = (SCEN != 3) && jv && take_en && !ack_r;
    // ---- SCEN 3 chain
    wire [63:0] rdata; wire rv, done, gack; wire cfgv; wire [31:0] cfgd; reg rq = 0; reg [31:0] cw_ = 0; wire cfg_busy, cfg_done, region_rst, fault, dead, blocked; wire [1:0] cfg_err; wire [7:0] rs, ls;
    config_gate_v3 #(.WIDTH(64), .CFG_W(32), .SETTLE(1)) G (.clk(clk), .rst(rst), .in_data(jd), .in_valid(jv & (SCEN == 3)), .in_ack(gack), .region_data(rdata), .region_valid(rv), .done(done), .res_valid(ov),
        .cfg_req(rq), .cfg_word_in(cw_), .cfg_valid(cfgv), .cfg_data(cfgd), .cfg_busy(cfg_busy), .cfg_done(cfg_done), .cfg_err(cfg_err), .region_rst(region_rst), .fault(fault), .dead(dead), .blocked(blocked), .resets(rs), .lost(ls));
    wire [31:0] bo; wire bv; wire [31:0] od; wire ov; reg oack = 0;
    arith_block_v5 #(.SHARED(1), .NANO_TT(1)) B (.clk(clk), .rst(rst | region_rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(rdata[63:32]), .in_b(rdata[31:0]), .valid_in(rv), .data_out(bo), .valid_out(bv));
    sub_to_flex_v1 #(.WIDTH(32)) O (.clk(clk), .rst(rst | region_rst), .sub_data(bo), .sub_valid(bv), .out_data(od), .out_valid(ov), .out_ack(oack), .done(done));
    assign jack = (SCEN == 3) ? gack : plain_ack;
    // real nano cell fed the same way: load_hold when a NEW B is taken by the join, flow = A when a pair is taken
    reg [31:0] nh_d; reg nl = 0; reg [31:0] nf_d; reg nvin = 0; wire [31:0] non; wire nvn; reg ncfg = 0;
    nano_cell_v4s NC (.clk(clk), .rst(rst), .cfg_valid(ncfg), .cfg_data(32'h0BC), .hold_in_data(nh_d), .load_hold(nl), .flow_in_data(nf_d), .valid_in(nvin), .data_out(non), .valid_out(nvn));
    reg [31:0] nano_ref [0:2047]; integer nref = 0; reg [31:0] resv [0:2047]; integer nres = 0;
    always @(posedge clk) begin
        oack <= 0; ack_r <= 0;
        if (!rst && ov && !oack) oack <= 1;
        if (ov && oack) begin resv[nres] <= od; nres <= nres + 1; end
        if (SCEN != 3) begin
            if (jv && jack) begin got[ng] <= jd; ng <= ng + 1; ack_r <= 1; end
            if (jv && !ack_r && take_en) begin if (cw >= cdl) cw <= 0; else cw <= cw + 1; end
        end
    end
    // random delay for the plain consumer: ack only when cw >= cdl (cdl re-drawn after each take)
    always @(posedge clk) if (!rst && SCEN != 3) begin if (jack) cdl <= $urandom % 4; end
    // reference for SCEN 3: the join's behaviour is checked by order; the nano ref is produced by feeding the real nano cell with B (sticky) then A words in the same order
    integer i, t, errs = 0, k;
    reg [31:0] expb [0:2047]; reg [31:0] expa [0:2047]; integer nexp = 0;
    task fail(input [255:0] w); begin errs = errs + 1; if (errs < 8) $display("FAIL %0s", w); end endtask
    initial begin
        for (i = 0; i < 1024; i = i + 1) begin qa[i] = $urandom; qb[i] = $urandom; end
        repeat (3) @(negedge clk); rst = 0; @(negedge clk);
        if (SCEN == 1) begin
            // pair mode: three phases of arrival bias
            na = 300; nb = 300; take_en = 1; pa = 1; pb = 1; bias = 1; repeat (800) @(negedge clk);
            if (ia != 300 || ib != 300) begin /* continue */ end
            t = 0; while ((ng < 300) && t < 20000) begin @(negedge clk); t = t + 1; end
            if (ng != 300) fail("not all 300 pairs came out");
            for (i = 0; i < ng; i = i + 1) if (got[i] !== {qa[i], qb[i]}) fail("pair mismatch (k-th A with k-th B)");
            // B first for a second batch
            ia = 0; ib = 0; ng = 0; for (i = 0; i < 300; i = i + 1) begin qa[i] = $urandom; qb[i] = $urandom; end bias = -1; repeat (50) @(negedge clk);
            t = 0; while ((ng < 300) && t < 20000) begin @(negedge clk); t = t + 1; end
            if (ng != 300) fail("second batch incomplete");
            for (i = 0; i < ng; i = i + 1) if (got[i] !== {qa[i], qb[i]}) fail("second batch pair mismatch");
            // a lone A (no B) must not fire
            ia = 0; ib = 0; ng = 0; na = 1; nb = 0; qa[0] = 32'hDEADBEEF; repeat (60) @(negedge clk); if (ng != 0 || jv) fail("fired with only one operand");
            nb = 1; qb[0] = 32'h12345678; repeat (30) @(negedge clk); if (ng != 1 || got[0] !== {32'hDEADBEEF, 32'h12345678}) fail("did not fire on the second arrival");
        end
        if (SCEN == 2) begin
            // sticky B: B1, five A, B2, five A -- every A pairs with the latest B before it
            take_en = 1; pa = 0; pb = 1; na = 0; nb = 1; qb[0] = 32'hAAAA0001; repeat (20) @(negedge clk);
            pa = 1; na = 5; for (i = 0; i < 5; i = i + 1) qa[i] = 32'h100 + i; repeat (80) @(negedge clk);
            if (ng != 5) fail("five A words with the held B"); for (i = 0; i < ng; i = i + 1) if (got[i] !== {32'h100 + i, 32'hAAAA0001}) fail("sticky pair 1");
            nb = 2; qb[1] = 32'hBBBB0002; repeat (20) @(negedge clk); na = 10; for (i = 5; i < 10; i = i + 1) qa[i] = 32'h100 + i; repeat (80) @(negedge clk);
            if (ng != 10) fail("ten pairs in all"); for (i = 5; i < ng; i = i + 1) if (got[i] !== {32'h100 + i, 32'hBBBB0002}) fail("sticky pair 2 (new B)");
        end
        if (SCEN == 4) begin
            // sticky B: a NEW B offered while a pair is waiting must not change that pair
            take_en = 0; pa = 1; pb = 1; na = 1; nb = 1; qa[0] = 32'hA1A1A1A1; qb[0] = 32'hB1B1B1B1; qb[1] = 32'hB2B2B2B2; repeat (40) @(negedge clk); nb = 2; repeat (40) @(negedge clk);
            if (!jv || jd !== {32'hA1A1A1A1, 32'hB1B1B1B1}) fail("waiting pair changed or missing");
            if (ib != 1) fail("new B taken while pair waited");
            take_en = 1; repeat (30) @(negedge clk);
            if (ng != 1 || got[0] !== {32'hA1A1A1A1, 32'hB1B1B1B1}) fail("pair taken is not the waiting one");
            if (ib != 2) fail("new B not taken after the pair");
            na = 2; qa[1] = 32'hA2A2A2A2; repeat (30) @(negedge clk);
            if (ng != 2 || got[1] !== {32'hA2A2A2A2, 32'hB2B2B2B2}) fail("next A did not pair with new B");
        end
        if (SCEN == 3) begin
            // join (sticky B) -> gate -> block, mode 7 = nano, topology XOR; compared with the REAL nano cell fed load_hold / flow in the same order
            @(negedge clk); ncfg = 1; @(negedge clk); ncfg = 0;
            cw_ = (32'h0BC << 16) | 32'h7; rq = 1; @(negedge clk); rq = 0; repeat (10) @(negedge clk);
            pb = 1; pa = 1; nb = 0; na = 0; repeat (10) @(negedge clk);
            // 6 rounds: new B, then 8 A words
            for (k = 0; k < 6; k = k + 1) begin
                nb = k + 1; qb[k] = $urandom; t = 0; while (ib <= k && t < 2000) begin @(negedge clk); t = t + 1; end   // B taken by the join
                nh_d = qb[k]; nl = 1; @(negedge clk); nl = 0;                                                         // real nano cell: load_hold
                for (i = 0; i < 8; i = i + 1) begin
                    qa[na] = $urandom; na = na + 1;
                    t = 0; while (nres < na && t < 4000) begin @(negedge clk); t = t + 1; end
                    nf_d = qa[na - 1]; nvin = 1; @(negedge clk); #1; nano_ref[nref] = non; nref = nref + 1; nvin = 0; @(negedge clk);
                end
            end
            repeat (50) @(negedge clk);
            if (nres != nref) begin errs = errs + 1; $display("FAIL count %0d vs %0d", nres, nref); end
            for (i = 0; i < nres && i < nref; i = i + 1) if (resv[i] !== nano_ref[i]) begin errs = errs + 1; if (errs < 6) $display("FAIL word %0d got %h want %h", i, resv[i], nano_ref[i]); end
            if (fault || dead) begin errs = errs + 1; $display("FAIL fault"); end
        end
        if (errs == 0) $display("JOIN SCEN %0d PASS", SCEN); else $display("JOIN SCEN %0d FAILED (%0d)", SCEN, errs);
        $finish;
    end
endmodule
