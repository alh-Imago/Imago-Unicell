// tb_link_stress.v - hammer jtag_link_v1 with a host that follows jtagport.py's rules (send a full window only when the last response said ready, delete the bytes
// at once) and a consumer that takes one byte per RXGAP clocks (the link's own pacing).  Counts bytes sent vs bytes received in order.
`timescale 1ns/1ps
module tb;
    localparam K = 32, W = 16 + 8*K;
    reg clk = 0; always #10 clk = ~clk;          // 50 MHz
    reg rst = 1;
    reg j_drck = 0, j_capture = 0, j_shift = 0, j_sel = 0, j_tdi = 0; wire j_tdo;
    wire [7:0] rb_data; wire rb_valid; wire tb_busy; wire act;
    jtag_link_VER #(.K(K)) dut(.clk(clk), .rst(rst), .j_drck(j_drck), .j_capture(j_capture), .j_shift(j_shift), .j_sel(j_sel), .j_tdi(j_tdi), .j_tdo(j_tdo),
                              .rb_data(rb_data), .rb_valid(rb_valid), .tb_data(8'd0), .tb_send(1'b0), .tb_busy(tb_busy), .act(act));
    integer TOTAL = 16384, GAP = 0, sent = 0, got = 0, bad = 0, nscan = 0, dropped_windows = 0;
    reg [7:0] expect_b = 0;
    always @(posedge clk) if (rb_valid) begin got <= got + 1; if (rb_data !== expect_b) begin bad <= bad + 1; expect_b <= rb_data + 1; end else expect_b <= expect_b + 1; end
    reg [W-1:0] wordout, rv; reg ready = 1; integer i, n, r;
    reg [7:0] next_b = 0;
    task scan; input [W-1:0] w; begin
        j_sel = 1; repeat (6) @(posedge clk);
        j_capture = 1; repeat (4) @(posedge clk); j_capture = 0; repeat (4) @(posedge clk);
        j_shift = 1; repeat (4) @(posedge clk);
        for (i = 0; i < W; i = i + 1) begin
            j_tdi = w[i]; rv[i] = j_tdo; repeat (2) @(posedge clk); j_drck = 1; repeat (4) @(posedge clk); j_drck = 0; repeat (2) @(posedge clk);
        end
        j_shift = 0; repeat (6) @(posedge clk); j_sel = 0; repeat (GAP) @(posedge clk);
    end endtask
    initial begin
        if (!$value$plusargs("GAP=%d", GAP)) GAP = 0;
        if (!$value$plusargs("TOTAL=%d", TOTAL)) TOTAL = 16384;
        repeat (20) @(posedge clk); rst = 0; repeat (20) @(posedge clk);
        scan({W{1'b0}} | (4'hA << 12)); scan({W{1'b0}} | (4'hA << 12));       // prime
        while (sent < TOTAL) begin
            n = ready ? ((TOTAL - sent) > K ? K : (TOTAL - sent)) : 0;
            wordout = (4'hA << 12) | n;
            for (r = 0; r < n; r = r + 1) begin wordout[16 + 8*r +: 8] = next_b; next_b = next_b + 1; end
            scan(wordout); nscan = nscan + 1;
            if (rv[15:12] != 4'h5) $display("WRONG MARK");
            sent = sent + n; ready = rv[8];
        end
        repeat (4) scan((4'hA << 12));
        repeat (TOTAL * 530 + 2000) @(posedge clk);                            // let the consumer drain everything
        $display("GAP=%0d clocks between scans: scans=%0d sent=%0d received=%0d in-order-breaks=%0d  lost=%0d bytes (= %0d eight-byte writes)", GAP, nscan, sent, got, bad, sent - got, (sent - got) / 8);
        $finish;
    end
endmodule
