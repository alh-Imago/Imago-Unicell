`timescale 1ns/1ps
// tb_hexn_store_v5.v -- testbench for hexn_store_v5.v. Stim word (hex, one per line): {1'b0, cmd[2:0], ev[3:0], rew[7:0], t[15:0]}. Plusargs +stim=<file> +count=<n> +n=<N> +w=<W> +vshift +glvl +log=<out>. Logs "verdict vlevel plevel pbest bseen ptotal gbest gval" after every command, then the counters and a dump of the index (I), row headers (H), entry words (E) and candidates (C). Sizes are set with -P on the command line.
module tb_hexn_store_v5;
    parameter EVB = 4, IB = 10, RB = 9, RSB = 2, P = 4, CCAP = 32, CA = 5;
    localparam TW = 2 + 3 * EVB, KW = 2 + 4 * EVB;
    reg clk = 0, rst = 1, cmd_valid = 0; reg [2:0] cmd = 0; reg [EVB-1:0] ev_in = 0; reg [15:0] t_in = 0; reg [3:0] n_prom = 3; reg [15:0] w_win = 80; reg [7:0] rew_in = 0; reg [2:0] vshift = 3; reg [1:0] glvl = 1;
    wire busy, done; wire [1:0] verdict, vlevel, plevel; wire [EVB-1:0] pbest, gbest; wire [7:0] pbest_seen, gval; wire [EVB+7:0] ptotal; wire [15:0] n_known, n_cand, n_promoted, n_dropk, n_dropc;
    reg [IB-1:0] ia = 0; reg [RB-1:0] ha = 0; reg [RB+RSB-1:0] ea = 0; reg [CA-1:0] ca = 0; wire [2+3*EVB+RB:0] iw; wire [RB:0] hw; wire [EVB+24:0] ew; wire [22+4*EVB:0] cw;
    hexn_store_v5 #(.EVB(EVB), .IB(IB), .RB(RB), .RSB(RSB), .P(P), .CCAP(CCAP), .CA(CA)) dut(.clk(clk), .rst(rst), .cmd_valid(cmd_valid), .cmd(cmd), .ev_in(ev_in), .t_in(t_in), .n_prom(n_prom), .w_win(w_win), .rew_in(rew_in), .vshift(vshift), .glvl(glvl), .busy(busy), .done(done),
        .verdict(verdict), .vlevel(vlevel), .plevel(plevel), .pbest(pbest), .pbest_seen(pbest_seen), .ptotal(ptotal), .gbest(gbest), .gval(gval), .n_known(n_known), .n_cand(n_cand), .n_promoted(n_promoted), .n_dropk(n_dropk), .n_dropc(n_dropc),
        .dbg_ia(ia), .dbg_iw(iw), .dbg_ha(ha), .dbg_hw(hw), .dbg_ea(ea), .dbg_ew(ew), .dbg_ca(ca), .dbg_cw(cw));
    always #5 clk = ~clk;
    reg [31:0] mem [0:262143]; integer vs, gl; integer i, count_n, f, nn, ww, cyc, maxcyc, maxcmd; reg [1023:0] fn, lg;
    initial begin
        if (!$value$plusargs("stim=%s", fn)) $finish; if (!$value$plusargs("count=%d", count_n)) $finish; if (!$value$plusargs("log=%s", lg)) $finish;
        if ($value$plusargs("vshift=%d", vs)) vshift = vs; if ($value$plusargs("glvl=%d", gl)) glvl = gl; if ($value$plusargs("n=%d", nn)) n_prom = nn; if ($value$plusargs("w=%d", ww)) w_win = ww;
        maxcyc = 0; maxcmd = 0; $readmemh(fn, mem); f = $fopen(lg, "w"); repeat (3) @(posedge clk); #1 rst = 0; @(posedge clk); #1; while (busy) begin @(posedge clk); #1; end
        for (i = 0; i < count_n; i = i + 1) begin
            cmd = mem[i][30:28]; ev_in = mem[i][27:24]; rew_in = mem[i][23:16]; t_in = mem[i][15:0]; cmd_valid = 1; @(posedge clk); #1; cmd_valid = 0; cyc = 1;
            while (!done) begin @(posedge clk); #1; cyc = cyc + 1; end
            if (cyc > maxcyc) begin maxcyc = cyc; maxcmd = cmd; end
            $fdisplay(f, "%0d %0d %0d %0d %0d %0d %0d %0d", verdict, vlevel, plevel, pbest, pbest_seen, ptotal, gbest, $signed(gval));
            @(posedge clk); #1;
        end
        $fdisplay(f, "S %0d %0d %0d %0d %0d", n_known, n_cand, n_promoted, n_dropk, n_dropc);
        for (i = 0; i < (1 << IB); i = i + 1) begin ia = i; repeat (3) @(posedge clk); #1; $fdisplay(f, "I %0d %0d %0d %0d", i, iw[2+3*EVB+RB], iw[2+3*EVB+RB] ? iw[RB+TW-1:RB] : 0, iw[2+3*EVB+RB] ? iw[RB-1:0] : 0); end
        for (i = 0; i < (1 << RB); i = i + 1) begin ha = i; repeat (3) @(posedge clk); #1; $fdisplay(f, "H %0d %0d %0d", i, hw[RB], hw[RB] ? hw[RB-1:0] : 0); end
        for (i = 0; i < (1 << (RB + RSB)); i = i + 1) begin ea = i; repeat (3) @(posedge clk); #1; $fdisplay(f, "E %0d %0d %0d %0d %0d %0d", i, ew[EVB+24], ew[EVB+24] ? ew[EVB+23:24] : 0, ew[EVB+24] ? ew[23:16] : 0, ew[EVB+24] ? ew[15:8] : 0, ew[EVB+24] ? $signed(ew[7:0]) : 0); end
        for (i = 0; i < CCAP; i = i + 1) begin ca = i; repeat (3) @(posedge clk); #1; $fdisplay(f, "C %0d %0d %0d %0d %0d", i, cw[KW+20], cw[KW+20] ? cw[KW+19:20] : 0, cw[KW+20] ? cw[19:16] : 0, cw[KW+20] ? cw[15:0] : 0); end
        $display("MAXCYC %0d (cmd %0d)", maxcyc, maxcmd); $fclose(f); $finish;
    end
endmodule
