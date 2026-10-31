`timescale 1ns/1ps
// tb_hexn_store_v6.v -- small testbench for hexn_store_v6.v (and, with +define+V5, hexn_store_v5.v for comparison). Stim word (hex, one per line): {1'b0, cmd[2:0], ev[3:0], rew[7:0], t[15:0]}. Logs "verdict vlevel plevel pbest" after every command, then counters. Sizes by -P.
module tb_hexn_store_v6;
    parameter EVB = 4, IB = 10, RB = 9, RSB = 2, P = 4, CCAP = 32, CA = 5, SW = 8;
    reg clk = 0, rst = 1, cmd_valid = 0; reg [2:0] cmd = 0; reg [EVB-1:0] ev_in = 0; reg [15:0] t_in = 0; reg [3:0] n_prom = 1; reg [15:0] w_win = 80; reg [7:0] rew_in = 0;
    wire busy, done; wire [1:0] verdict, vlevel, plevel; wire [EVB-1:0] pbest, gbest; wire [7:0] pbest_seen, gval; wire [EVB+7:0] ptotal; wire [15:0] n_known, n_cand, n_promoted, n_dropk, n_dropc, n_evict;
    wire [SW+3*EVB+RB+3:0] iw; wire [RB:0] hw; wire [EVB+24:0] ew; wire [22+4*EVB:0] cw;
`ifdef V5
    assign n_evict = 0;
    hexn_store_v5 #(.EVB(EVB), .IB(IB), .RB(RB), .RSB(RSB), .P(P), .CCAP(CCAP), .CA(CA)) dut(
`else
    hexn_store_v6 #(.SW(SW), .EVB(EVB), .IB(IB), .RB(RB), .RSB(RSB), .P(P), .CCAP(CCAP), .CA(CA)) dut(.n_evict(n_evict),
`endif
        .clk(clk), .rst(rst), .cmd_valid(cmd_valid), .cmd(cmd), .ev_in(ev_in), .t_in(t_in), .n_prom(n_prom), .w_win(w_win), .rew_in(rew_in), .vshift(3'd3), .glvl(2'd1), .busy(busy), .done(done),
        .verdict(verdict), .vlevel(vlevel), .plevel(plevel), .pbest(pbest), .pbest_seen(pbest_seen), .ptotal(ptotal), .gbest(gbest), .gval(gval), .n_known(n_known), .n_cand(n_cand), .n_promoted(n_promoted), .n_dropk(n_dropk), .n_dropc(n_dropc),
        .dbg_ia({IB{1'b0}}), .dbg_iw(iw), .dbg_ha({RB{1'b0}}), .dbg_hw(hw), .dbg_ea({(RB+RSB){1'b0}}), .dbg_ew(ew), .dbg_ca({CA{1'b0}}), .dbg_cw(cw));
    always #5 clk = ~clk;
    reg [31:0] mem [0:262143]; integer i, count_n, f, cyc, maxcyc, nn; reg [1023:0] fn, lg;
    initial begin
        if (!$value$plusargs("stim=%s", fn)) $finish; if (!$value$plusargs("count=%d", count_n)) $finish; if (!$value$plusargs("log=%s", lg)) $finish;
        if ($value$plusargs("n=%d", nn)) n_prom = nn;
        maxcyc = 0; $readmemh(fn, mem); f = $fopen(lg, "w"); repeat (3) @(posedge clk); #1 rst = 0; @(posedge clk); #1; while (busy) begin @(posedge clk); #1; end
        for (i = 0; i < count_n; i = i + 1) begin
            cmd = mem[i][30:28]; ev_in = mem[i][27:24]; rew_in = mem[i][23:16]; t_in = mem[i][15:0]; cmd_valid = 1; @(posedge clk); #1; cmd_valid = 0; cyc = 1;
            while (!done && cyc < 200000) begin @(posedge clk); #1; cyc = cyc + 1; end
            if (cyc >= 200000) begin $display("HANG at command %0d", i); $finish; end
            if (cyc > maxcyc) maxcyc = cyc;
            $fdisplay(f, "%0d %0d %0d %0d %0d %0d %0d %0d", verdict, vlevel, plevel, pbest, pbest_seen, ptotal, gbest, $signed(gval));
            @(posedge clk); #1;
        end
        $fdisplay(f, "S %0d %0d %0d %0d %0d %0d", n_known, n_cand, n_promoted, n_dropk, n_dropc, n_evict);
        $display("MAXCYC %0d", maxcyc); $fclose(f); $finish;
    end
endmodule
