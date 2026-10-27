`timescale 1ns/1ps
// tb_hexn_store_v1.v -- +stim=<hex file, one 24-bit command per line {cmd[3:0], ev[3:0], t[15:0]}> +count=<n> +n=<N> +w=<W> +log=<out file>. Logs "verdict vlevel plevel pbest bseen ptotal" after every command, then dumps both tables and the counters. KCAP/CCAP/KA/CA are set with -P on the command line.
module tb_hexn_store_v1;
    parameter KCAP = 128, CCAP = 32, KA = 7, CA = 5;
    reg clk = 0, rst = 1, cmd_valid = 0; reg [2:0] cmd = 0, ev_in = 0; reg [15:0] t_in = 0; reg [3:0] n_prom = 3; reg [15:0] w_win = 80;
    wire busy, done; wire [1:0] verdict, vlevel, plevel; wire [2:0] pbest; wire [7:0] pbest_seen; wire [10:0] ptotal; wire [15:0] n_known, n_cand, n_promoted, n_dropk, n_dropc;
    reg [KA-1:0] ka = 0; reg [CA-1:0] ca = 0; wire kv, cv; wire [13:0] kkey, ckey; wire [7:0] kseen, kcon; wire [3:0] ccnt; wire [15:0] cstart;
    hexn_store_v1 #(.KCAP(KCAP), .CCAP(CCAP), .KA(KA), .CA(CA)) dut(.clk(clk), .rst(rst), .cmd_valid(cmd_valid), .cmd(cmd), .ev_in(ev_in), .t_in(t_in), .n_prom(n_prom), .w_win(w_win), .busy(busy), .done(done),
        .verdict(verdict), .vlevel(vlevel), .plevel(plevel), .pbest(pbest), .pbest_seen(pbest_seen), .ptotal(ptotal), .n_known(n_known), .n_cand(n_cand), .n_promoted(n_promoted), .n_dropk(n_dropk), .n_dropc(n_dropc),
        .dbg_ka(ka), .dbg_kv(kv), .dbg_kkey(kkey), .dbg_kseen(kseen), .dbg_kcon(kcon), .dbg_ca(ca), .dbg_cv(cv), .dbg_ckey(ckey), .dbg_ccnt(ccnt), .dbg_cstart(cstart));
    always #5 clk = ~clk;
    reg [23:0] mem [0:262143]; integer i, count_n, f, nn, ww, cyc, maxcyc, maxcmd;  reg [1023:0] fn, lg;
    initial begin
        if (!$value$plusargs("stim=%s", fn)) $finish; if (!$value$plusargs("count=%d", count_n)) $finish; if (!$value$plusargs("log=%s", lg)) $finish;
        if ($value$plusargs("n=%d", nn)) n_prom = nn; if ($value$plusargs("w=%d", ww)) w_win = ww;
        maxcyc = 0; maxcmd = 0; $readmemh(fn, mem); f = $fopen(lg, "w"); repeat (3) @(posedge clk); #1 rst = 0; @(posedge clk); #1;
        for (i = 0; i < count_n; i = i + 1) begin
            cmd = mem[i][23:20]; ev_in = mem[i][18:16]; t_in = mem[i][15:0]; cmd_valid = 1; @(posedge clk); #1; cmd_valid = 0; cyc = 1;
            while (!done) begin @(posedge clk); #1; cyc = cyc + 1; end
            if (cyc > maxcyc) begin maxcyc = cyc; maxcmd = cmd; end
            $fdisplay(f, "%0d %0d %0d %0d %0d %0d", verdict, vlevel, plevel, pbest, pbest_seen, ptotal);
            @(posedge clk); #1;
        end
        $fdisplay(f, "S %0d %0d %0d %0d %0d", n_known, n_cand, n_promoted, n_dropk, n_dropc);
        for (i = 0; i < KCAP; i = i + 1) begin ka = i; #1; $fdisplay(f, "K %0d %0d %0d %0d %0d", i, kv, kv ? kkey : 0, kv ? kseen : 0, kv ? kcon : 0); end
        for (i = 0; i < CCAP; i = i + 1) begin ca = i; #1; $fdisplay(f, "C %0d %0d %0d %0d %0d", i, cv, cv ? ckey : 0, cv ? ccnt : 0, cv ? cstart : 0); end
        $display("MAXCYC %0d (cmd %0d)", maxcyc, maxcmd); $fclose(f); $finish;
    end
endmodule
