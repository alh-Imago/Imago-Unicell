// tb_k7_freeze_v3.v -- simulation of the freeze / save / load kit. BSCANE2 is modelled here (simulation only).
// Two copies of the design: A is commanded over the (modelled) JTAG scan; B runs freely and its cell state is recorded at every count.
`timescale 1ns/1ps
module BSCANE2 #(parameter JTAG_CHAIN = 1) (
    output reg CAPTURE = 0, output reg DRCK = 0, output reg RESET = 0, output reg RUNTEST = 0, output reg SEL = 0,
    output reg SHIFT = 0, output reg TCK = 0, output reg TDI = 0, output reg TMS = 0, output reg UPDATE = 0, input TDO);
endmodule

module tb_k7_freeze_v3;
    reg clk = 0; always #10 clk = ~clk;
    wire a0, a1, a2, b0, b1, b2;
    top #(.HB_BIT(10)) A (.CLK(clk), .LED0(a0), .LED1(a1), .LED2(a2));
    top #(.HB_BIT(10)) B (.CLK(clk), .LED0(b0), .LED1(b1), .LED2(b2));
    reg [831:0] ref_snap [0:2200];
    reg [1663:0] ref_dbg [0:2200];
    reg [31:0] expm [0:7];
    integer fails = 0;
    initial begin
        expm[0] = 32'h0000000A;
        expm[1] = 32'h00000039;
        expm[2] = 32'hFFFFFFF6;
        expm[3] = 32'h00002710;
        expm[4] = 32'hFFF7E68A;
        expm[5] = 32'h7FFFFEAA;
        expm[6] = 32'h0;
    end
    always @(posedge clk) if (B.started && !B.rst_run && B.t < 2200) begin ref_snap[B.t] <= B.dut.snap; ref_dbg[B.t] <= B.dut.dbg; end

    reg [2751:0] rx;
    task tck_pulse; begin #50 A.bscan.TCK = 1; #50 A.bscan.TCK = 0; end endtask
    task scan(input [2751:0] tx); integer i; begin
        A.bscan.SEL = 1;
        A.bscan.CAPTURE = 1; tck_pulse; A.bscan.CAPTURE = 0;
        A.bscan.SHIFT = 1;
        for (i = 0; i < 2752; i = i + 1) begin
            #10 rx[i] = A.bscan.TDO; A.bscan.TDI = tx[i];
            tck_pulse;
        end
        A.bscan.SHIFT = 0;
        A.bscan.UPDATE = 1; tck_pulse; tck_pulse; A.bscan.UPDATE = 0;
        A.bscan.SEL = 0;
        #200;
    end endtask
    function [2751:0] cmd(input [31:0] T, input go, input rel);
        begin cmd = 2752'd0; cmd[31:0] = T; cmd[32] = go; cmd[33] = rel; cmd[34] = 1'b1; end
    endfunction
    // the command that loads the state of an earlier read S back into the card
    function [2751:0] loadcmd(input [2751:0] S);
        begin
            loadcmd = 2752'd0;
            loadcmd[31:0] = 32'hFFFFFFFF; loadcmd[34] = 1'b1; loadcmd[35] = 1'b1;
            loadcmd[95:64]   = S[63:32];                       // t
            loadcmd[103:96]  = S[71:64];                       // ncap  (flags bits 7:0)
            loadcmd[111:104] = S[79:72];                       // k     (flags bits 15:8)
            loadcmd[159:128] = S[127:96];                      // signature
            loadcmd[191:160] = S[159:128];                     // last result
            loadcmd[223:192] = S[223:192];                     // clock of the last result
            loadcmd[2751:1088] = S[2751:1088];                 // hidden state of the cells
        end
    endfunction
    task check(input ok, input [1023:0] what); begin
        if (!ok) begin fails = fails + 1; $display("  FAIL: %0s", what); end
    end endtask

    integer p, q, T, delta, n;
    reg [7:0] mask, allmask;
    reg [831:0] got, want;
    reg [1663:0] got_dbg;
    reg [2751:0] S, D, L, F, C;
    reg [31:0] tl [0:23];
    reg [31:0] sv [0:3];
    initial begin
        tl[0]=30; tl[1]=60; tl[2]=100; tl[3]=150; tl[4]=250; tl[5]=346; tl[6]=500; tl[7]=700; tl[8]=1000; tl[9]=1400;
        tl[10]=45; tl[11]=47; tl[12]=49; tl[13]=52; tl[14]=57; tl[15]=345; tl[16]=349; tl[17]=353; tl[18]=357; tl[19]=707; tl[20]=1003; tl[21]=1500; tl[22]=1560; tl[23]=1561;
        sv[0]=60; sv[1]=346; sv[2]=700; sv[3]=1000;
        allmask = 8'hFF;
        #100000;                                       // the automatic run on both copies has finished
        // 1. pure read after the automatic run
        scan(2752'd0);
        $display("1. read after the automatic run: magic %08X t=%0d flags=%08X sig=%08X last=%08X lastt=%0d (free copy %0d)", rx[31:0], rx[63:32], rx[95:64], rx[127:96], rx[159:128], rx[223:192], B.lastt);
        check(rx[31:0] === 32'h46525A33, "magic FRZ3");
        check(rx[71:64] === 8'd6 && rx[88] === 1'b0, "6 results, not frozen");
        check(rx[127:96] === B.sig && rx[159:128] === expm[5] && rx[223:192] === B.lastt, "signature, last word, clock of the last result equal the free copy");
        check(B.lastt === 32'd1562, "the last result arrives at count 1562 (0x61A, as in the Tang line)");
        check(rx[1088 + 128*9 + 64 +: 6] === 6'd2 && rx[1088 + 128*9 + 64 + 6 +: 6] === 6'd9 && rx[1088 + 128*9 + 96 + 3] === 1'b1, "cell 9 hidden words: masks 2/9, join mode");
        // 2. freeze at counts: the frozen state must equal the free-running state AT the same count (cycle-exact freeze)
        for (p = 0; p < 24; p = p + 1) begin
            T = tl[p];
            scan(cmd(T, 1'b1, 1'b0));
            #(20 * (T + 400));
            scan(2752'd0);
            got = rx[1087:256]; got_dbg = rx[2751:1088];
            check(rx[88] === 1'b1 && rx[63:32] === T, "frozen, held count equals T");
            mask = 0;
            for (delta = -2; delta <= 3; delta = delta + 1) begin
                want = ref_snap[T + delta];
                if (want === got && ref_dbg[T + delta] === got_dbg) mask = mask | (1 << (delta + 2));
            end
            allmask = allmask & mask;
            check(mask != 0, "frozen state (visible and hidden) matches the free-running copy at some offset");
            #50000;
            scan(2752'd0);
            check(rx[1087:256] === got && rx[2751:1088] === got_dbg, "frozen state steady between reads");
        end
        $display("2. offsets matching at EVERY T (bit0 = -2, bit1 = -1, bit2 = 0, bit3 = +1 ...): %b   (000100 = the state AT count T)", allmask[5:0]);
        check(allmask[5:0] === 6'b000100, "cycle-exact: the frozen state is exactly the free-running state at count T");
        // 3. release is cycle-exact: the run continues as if never stopped (same clock for the last result as the free copy)
        for (p = 0; p < 4; p = p + 1) begin
            T = sv[p];
            scan(cmd(T, 1'b1, 1'b0)); #(20 * (T + 400));
            scan(cmd(32'hFFFFFFFF, 1'b0, 1'b1)); #(20 * 6000); scan(2752'd0);
            $display("3. freeze at %0d, release: ncap=%0d sig=%08X last=%08X lastt=%0d", T, rx[71:64], rx[127:96], rx[159:128], rx[223:192]);
            check(rx[71:64] === 8'd6 && rx[127:96] === B.sig && rx[159:128] === expm[5], "results after release equal the free copy");
            check(rx[223:192] === B.lastt, "the last result arrives at the same clock count as in the free copy");
        end
        // 4. SAVE, disturb, LOAD, release
        for (p = 0; p < 4; p = p + 1) begin
            T = sv[p];
            scan(cmd(T, 1'b1, 1'b0)); #(20 * (T + 400)); scan(2752'd0); S = rx;                   // save
            scan(cmd(32'd1400, 1'b1, 1'b0)); #(20 * 1800); scan(2752'd0); D = rx;               // disturb: a different run, frozen at 1400
            check(D[2751:1088] !== S[2751:1088] || T == 1400, "the disturbance changed the cells' state");
            scan(loadcmd(S)); #2000; scan(2752'd0); L = rx;                                       // load and read back
            check(L[1087:256] === S[1087:256] && L[2751:1088] === S[2751:1088], "loaded state read back equals the saved state (visible and hidden)");
            check(L[63:32] === S[63:32] && L[79:64] === S[79:64] && L[127:96] === S[127:96] && L[159:128] === S[159:128] && L[223:192] === S[223:192], "driver state (t, ncap, k, signature, last word, last clock) restored");
            check(L[88] === 1'b1, "frozen after the load");
            scan(cmd(32'hFFFFFFFF, 1'b0, 1'b1)); #(20 * 6000); scan(2752'd0); F = rx;           // release
            $display("4. save at %0d, disturb, load, release: ncap=%0d sig=%08X last=%08X lastt=%0d", T, F[71:64], F[127:96], F[159:128], F[223:192]);
            check(F[71:64] === 8'd6 && F[127:96] === B.sig && F[159:128] === expm[5], "results after load + release equal the free copy");
            check(F[223:192] === B.lastt, "load + release: the last result arrives at the same clock count as in the free copy");
        end
        // 5. negative control: corrupt one saved register (lane_0.in data_reg 100 -> 101 in the state at 346): the final results must change
        scan(cmd(32'd346, 1'b1, 1'b0)); #(20 * 746); scan(2752'd0); S = rx;
        scan(cmd(32'd1400, 1'b1, 1'b0)); #(20 * 1800); scan(2752'd0);
        C = loadcmd(S); C[1088] = ~C[1088];
        scan(C); #2000; scan(cmd(32'hFFFFFFFF, 1'b0, 1'b1)); #(20 * 6000); scan(2752'd0);
        $display("5. corrupted load: ncap=%0d sig=%08X (free copy %08X)", rx[71:64], rx[127:96], B.sig);
        check(rx[127:96] !== B.sig, "negative control: a corrupted loaded state changes the final results");
        if (fails == 0) $display("PASS"); else $display("FAIL (%0d)", fails);
        $finish;
    end
endmodule
