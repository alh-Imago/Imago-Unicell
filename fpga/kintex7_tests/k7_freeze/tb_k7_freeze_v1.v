// tb_k7_freeze_v1.v -- simulation of the freeze-and-read kit. BSCANE2 is modelled here (simulation only).
// Two copies of the design: A is commanded over the (modelled) JTAG scan; B runs freely and its cell snapshot is recorded at every clock count,
// so a snapshot read from A after a freeze at count T can be compared with B's state at the same count.
`timescale 1ns/1ps
module BSCANE2 #(parameter JTAG_CHAIN = 1) (
    output reg CAPTURE = 0, output reg DRCK = 0, output reg RESET = 0, output reg RUNTEST = 0, output reg SEL = 0,
    output reg SHIFT = 0, output reg TCK = 0, output reg TDI = 0, output reg TMS = 0, output reg UPDATE = 0, input TDO);
endmodule

module tb_k7_freeze_v1;
    reg clk = 0; always #10 clk = ~clk;
    wire a0, a1, a2, b0, b1, b2;
    top #(.HB_BIT(10)) A (.CLK(clk), .LED0(a0), .LED1(a1), .LED2(a2));
    top #(.HB_BIT(10)) B (.CLK(clk), .LED0(b0), .LED1(b1), .LED2(b2));
    reg [831:0] ref_snap [0:2200];
    reg [31:0] ref_valid_t = 0;
    reg [31:0] expm [0:7];
    integer fails = 0;
    integer ii;
    initial begin
        expm[0] = 32'h0000000A;
        expm[1] = 32'h00000039;
        expm[2] = 32'hFFFFFFF6;
        expm[3] = 32'h00002710;
        expm[4] = 32'hFFF7E68A;
        expm[5] = 32'h7FFFFEAA;
        expm[6] = 32'h0;
    end
    // record B's cell snapshot at every count of its run (B's t counts only while its run is going)
    always @(posedge clk) if (B.started && B.t < 2200) ref_snap[B.t] <= B.dut.snap;

    reg [1023:0] rx;
    task tck_pulse; begin #50 A.bscan.TCK = 1; #50 A.bscan.TCK = 0; end endtask
    task scan(input [1023:0] tx); integer i; begin
        A.bscan.SEL = 1;
        A.bscan.CAPTURE = 1; tck_pulse; A.bscan.CAPTURE = 0;
        A.bscan.SHIFT = 1;
        for (i = 0; i < 1024; i = i + 1) begin
            #10 rx[i] = A.bscan.TDO; A.bscan.TDI = tx[i];
            tck_pulse;
        end
        A.bscan.SHIFT = 0;
        A.bscan.UPDATE = 1; tck_pulse; tck_pulse; A.bscan.UPDATE = 0;
        A.bscan.SEL = 0;
        #200;
    end endtask
    function [1023:0] cmd(input [31:0] T, input go, input rel);
        begin cmd = 1024'd0; cmd[31:0] = T; cmd[32] = go; cmd[33] = rel; cmd[34] = 1'b1; end
    endfunction
    task check(input ok, input [255:0] what); begin
        if (!ok) begin fails = fails + 1; $display("  FAIL: %0s", what); end
    end endtask

    integer p, T, delta, n; reg [7:0] mask, allmask;
    reg [831:0] got, want;
    reg [31:0] tl [0:23];
    initial begin
        tl[0]=30; tl[1]=60; tl[2]=100; tl[3]=150; tl[4]=250; tl[5]=346; tl[6]=500; tl[7]=700; tl[8]=1000; tl[9]=1400;
        tl[10]=45; tl[11]=47; tl[12]=49; tl[13]=52; tl[14]=57; tl[15]=345; tl[16]=349; tl[17]=353; tl[18]=357; tl[19]=700+7; tl[20]=1000+3; tl[21]=1500; tl[22]=1560; tl[23]=1561;
        allmask = 8'hFF;
        #100000;                                       // 100 us (about 5000 clocks): the automatic run on both copies has finished
        // 1. pure read after the automatic run
        scan(1024'd0);
        $display("1. read after the automatic run: magic %08X t=%0d flags=%08X sig=%08X last=%08X T=%08X", rx[31:0], rx[63:32], rx[95:64], rx[127:96], rx[159:128], rx[191:160]);
        check(rx[31:0] === 32'h46525A31, "magic");
        check(rx[79:64] === 16'd6, "6 results in the automatic run");
        check(rx[88] === 1'b0, "not frozen");
        check(rx[159:128] === expm[5] || rx[159:128] === expm[ 5], "last result word");
        // 2. freeze at several counts, compare with B's state; find the alignment delta
        for (p = 0; p < 24; p = p + 1) begin
            T = tl[p];
            scan(cmd(T, 1'b1, 1'b0));                  // go with freeze at T
            #(20 * (T + 400));                          // let the run reach T (plus reset and start-up)
            scan(1024'd0);
            got = rx[1023:192];
            $display("2. T=%0d: frozen=%0d t=%0d ncap=%0d runno=%0d", T, rx[88], rx[63:32], rx[79:64], rx[87:80]);
            check(rx[88] === 1'b1, "frozen flag set");
            check(rx[63:32] === T, "held count equals T");
            mask = 0;
            for (delta = -2; delta <= 3; delta = delta + 1) begin
                want = ref_snap[T + delta];
                if (want === got) mask = mask | (1 << (delta + 2));
            end
            allmask = allmask & mask;
            $display("   cell snapshot equals B's state at count T+d for d in (bit0 = -2, bit2 = 0, bit3 = +1): %b", mask[5:0]);
            check(mask != 0, "snapshot matches the free-running reference at some alignment");
            // hold: read again after waiting, nothing may change
            #50000;
            scan(1024'd0);
            check(rx[1023:192] === got, "frozen state is steady between reads");
        end
        // 3. all alignments agree
        $display("3. offsets matching at EVERY T (bit0 = -2, bit1 = -1, bit2 = 0, bit3 = +1, bit4 = +2, bit5 = +3): %b  (001000 = the state at count T+1)", allmask[5:0]);
        check(allmask[5:0] === 6'b001000, "the frozen state is exactly the free-running state at count T+1 at every T (bit3 = +1; bit0 = -2)");
        // 4. release after a freeze: the computation must still finish correctly
        scan(cmd(346, 1'b1, 1'b0)); #(20 * 800); scan(1024'd0);
        check(rx[88] === 1'b1, "frozen before release");
        scan(cmd(32'hFFFFFFFF, 1'b0, 1'b1)); #(20 * 6000); scan(1024'd0);
        $display("4. after release: frozen=%0d ncap=%0d sig=%08X last=%08X", rx[88], rx[79:64], rx[127:96], rx[159:128]);
        check(rx[88] === 1'b0, "released");
        check(rx[79:64] === 16'd6, "6 results after release");
        check(rx[159:128] === expm[5], "last result unchanged by the freeze");
        check(rx[127:96] === B.sig, "result signature equals the free-running copy's");
        // 5. a second ordinary rerun without freeze gives the same results as the first run
        scan(cmd(32'hFFFFFFFF, 1'b1, 1'b0)); #(20 * 6000); scan(1024'd0);
        check(rx[79:64] === 16'd6 && rx[127:96] === B.sig, "rerun without freeze gives the same signature");
        $display("5. rerun: ncap=%0d sig=%08X (free copy %08X) runno=%0d", rx[79:64], rx[127:96], B.sig, rx[87:80]);
        if (fails == 0) $display("PASS"); else $display("FAIL (%0d)", fails);
        $finish;
    end
endmodule
