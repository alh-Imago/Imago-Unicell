`timescale 1ns/1ps
module tb;
    reg CLK = 0;
    wire L0, L1, L2;
    top #(.BASE(2)) dut (.CLK(CLK), .LED0(L0), .LED1(L1), .LED2(L2));
    always #10 CLK = ~CLK;
    integer t0=0, t1=0, t2=0;
    reg p0=0, p1=0, p2=0;
    always @(posedge CLK) begin
        if (L0 !== p0) t0 = t0 + 1;
        if (L1 !== p1) t1 = t1 + 1;
        if (L2 !== p2) t2 = t2 + 1;
        p0 = L0; p1 = L1; p2 = L2;
    end
    initial begin
        #(20*512);
        // 512 cycles: about 32 / 64 / 128 toggles (rates 1:2:4); allow one edge of slack
        if (t0 >= 31 && t0 <= 32 && t1 >= 63 && t1 <= 64 && t2 >= 127 && t2 <= 128) $display("PASS toggles %0d %0d %0d", t0, t1, t2);
        else $display("FAIL toggles %0d %0d %0d", t0, t1, t2);
        $finish;
    end
endmodule
