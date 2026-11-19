// tb_k7fu.v - tb_k7.v for the multi-block top sc_top_k7_v9 (parameter NB blocks of S slices).  Cloned from tb_k7.v (left as proven).
`timescale 1ns/1ps
// Simulation of sc_top_k7_v1 (cores + block-RAM far RAM + batch sequencer + JTAG byte link) with a behavioural BSCANE2 and a host that scans the
// user register the way jtagport.py will.  +cmds=<file>: "B xx" send one byte (hex), "W n" wait for n reply bytes then continue (hex), "D n" idle n clocks.
// +out=<file>: reply bytes, hex per line.  +maxcyc=<n>.  The clock is 50 MHz (20 ns); TCK is 6.25 MHz (8 clocks).
module BSCANE2 #(parameter JTAG_CHAIN = 1) (output CAPTURE, DRCK, RESET, RUNTEST, SEL, SHIFT, TCK, TDI, TMS, UPDATE, input TDO);
    reg cap = 0, drck = 0, sel = 0, shf = 0, tdi = 0, upd = 0;
    assign CAPTURE = cap; assign DRCK = drck; assign SEL = sel; assign SHIFT = shf; assign TDI = tdi; assign UPDATE = upd;
    assign RESET = 0; assign RUNTEST = 0; assign TCK = 0; assign TMS = 0;
    // scan(width, in_bits) -> out_bits: sets up Capture-DR, one TCK period of capture, then width shift clocks
    reg [1023:0] out_bits;
    task scan(input integer width, input [1023:0] in_bits);
        integer k;
        begin
            out_bits = 0; sel = 1;
            #40 cap = 1; drck = 1; #80 drck = 0; #40 cap = 0;              // Capture-DR: one clock, DRCK pulses
            #40 shf = 1;
            for (k = 0; k < width; k = k + 1) begin
                tdi = in_bits[k]; #40; drck = 1; out_bits[k] = TDO; #80; drck = 0; #40;
            end
            shf = 0; upd = 1; #80 upd = 0; sel = 0; #200;
        end
    endtask
endmodule

module tb_k7fu;
    parameter NB = 2, S = 4, FZ = 1, ULW = 2, QD = 16, IMW = 128, DMW = 16, DSH = 256, SHL = 14, JK = 32, RXGAP = 64;
    localparam W = 16 + 8*JK;
    reg clk = 0; always #10 clk = ~clk;
    wire [2:0] led;
    sc_top_k7_v9 #(.NB(NB), .S(S), .QD(QD), .IMEM_WORDS(IMW), .DMW(DMW), .DSH(DSH), .SHL(SHL), .JK(JK), .RXGAP(RXGAP), .FZ(FZ), .ULW(ULW), .FAR_AW(14)) dut (.SYS_CLK(clk), .led(led));

    integer fo, fc, r, n, nrep = 0, expect_rep = 0; reg [7:0] tag; reg [1023:0] cmdname, outname; integer maxcyc, cyc = 0;
    always @(posedge clk) begin cyc <= cyc + 1; if (cyc >= maxcyc) begin $display("maxcyc reached"); $fclose(fo); $finish; end end

    // host-side link state
    reg [7:0] txq [0:65535]; integer txh = 0, txt = 0;      // bytes waiting to go to the design
    reg [7:0] rxq [0:65535]; integer rxh = 0, rxt = 0;      // bytes received
    reg ready = 1; reg ack_pending = 0, was_ack = 0;
    reg [1023:0] wbits; reg [1023:0] gotbits; integer i, m, nout;
    // one exchange: send up to JK queued bytes with the ack flag if we hold unacked bytes, read the window
    task exchange;
        begin
            m = 0; wbits = 0;
            if (ready) begin while (m < JK && txh != txt) begin wbits[16 + 8*m +: 8] = txq[txh]; txh = txh + 1; m = m + 1; end end
            wbits[7:0] = m; wbits[8] = ack_pending; wbits[15:12] = 4'hA;
            was_ack = ack_pending; ack_pending = 0;
            dut.bscan.scan(W, wbits);
            gotbits = dut.bscan.out_bits;
            nout = gotbits[7:0]; ready = gotbits[8];
            if (gotbits[15:12] !== 4'h5) $display("BAD response marker %h", gotbits[15:12]);
            if (!was_ack) for (i = 0; i < nout; i = i + 1) begin rxq[rxt] = gotbits[16 + 8*i +: 8]; rxt = rxt + 1; end   // the response to an ack scan is the old window: ignore it
            if (nout != 0 && !was_ack) ack_pending = 1;
        end
    endtask
    integer idle;
    initial begin
        if (!$value$plusargs("cmds=%s", cmdname)) begin $display("need +cmds"); $finish; end
        if (!$value$plusargs("out=%s", outname))  begin $display("need +out");  $finish; end
        if (!$value$plusargs("maxcyc=%d", maxcyc)) maxcyc = 40000000;
        fo = $fopen(outname, "w"); fc = $fopen(cmdname, "r");
        repeat (400) @(posedge clk);
        while (!$feof(fc)) begin
            r = $fscanf(fc, "%c %h\n", tag, n);
            if (r == 2) begin
                if (tag == "B") begin txq[txt] = n[7:0]; txt = txt + 1; end
                else if (tag == "D") begin                          // a wait: first push out what is queued (the real host flushes after every command)
                    if (txh != txt) begin while (txh != txt) exchange; exchange; end
                    repeat (n) @(posedge clk);
                end
                else if (tag == "W") begin                          // flush: exchange until n reply bytes have arrived (or give up)
                    idle = 0; expect_rep = expect_rep + n;
                    while (rxt < expect_rep && idle < 4000) begin exchange; idle = idle + 1; repeat (200) @(posedge clk); end
                    if (rxt < expect_rep) $display("TIMEOUT waiting for reply bytes: have %0d want %0d", rxt, expect_rep);
                end
            end
        end
        // final: drain and ack
        exchange; exchange;
        for (i = 0; i < rxt; i = i + 1) $fdisplay(fo, "%02x", rxq[i]);
        $display("done: sent %0d bytes, received %0d", txt, rxt);
        $fclose(fo); $finish;
    end
endmodule
