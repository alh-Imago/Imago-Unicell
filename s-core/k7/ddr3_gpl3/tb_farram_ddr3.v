// tb_farram_ddr3.v - testbench for farram_ddr3_v1 against a behavioural model of UberDDR3's Wishbone port (576-bit line, byte strobe, random stall, random
// ack latency), with the two clocks asynchronous (20 ns and 12 ns period, offset).  GPL-3.0 build only (see README.md).
`timescale 1ns/1ps
module tb_farram_ddr3;
    localparam LANES = 9, WBA = 25, DW = LANES*64, NL = 256;
    reg clk = 0, cclk = 0;
    always #10 clk = ~clk;
    initial begin #3; forever #6 cclk = ~cclk; end

    reg rst = 1, crst_n = 0, req_v = 0, req_we = 0; reg [20:0] req_a = 0; reg [31:0] req_wd = 0;
    wire req_rdy, init_done, busy, ack_v; wire [31:0] ack_d;
    reg calib = 0;
    wire wb_cyc, wb_stb, wb_we; wire [WBA-1:0] wb_addr; wire [DW-1:0] wb_data; wire [LANES*8-1:0] wb_sel;
    reg wb_stall = 1, wb_ack = 0; reg [DW-1:0] wb_rdata = 0;

    farram_ddr3_v1 #(.LANES(LANES), .WBA(WBA)) dut (
        .clk(clk), .rst(rst), .cfg_cl(2'd0), .cfg_dly(2'd0), .cfg_inv(1'b0), .reinit(1'b0),
        .req_v(req_v), .req_we(req_we), .req_a(req_a), .req_wd(req_wd), .req_rdy(req_rdy), .ack_v(ack_v), .ack_d(ack_d), .init_done(init_done), .busy(busy),
        .cclk(cclk), .crst_n(crst_n), .calib_complete(calib),
        .wb_cyc(wb_cyc), .wb_stb(wb_stb), .wb_we(wb_we), .wb_addr(wb_addr), .wb_data(wb_data), .wb_sel(wb_sel),
        .wb_stall(wb_stall), .wb_ack(wb_ack), .wb_rdata(wb_rdata));

    // ---- Wishbone slave model (one transaction at a time is enough for this master, but the model accepts a new one only when idle)
    reg [DW-1:0] mem [0:NL-1];
    integer k, viol = 0, accepted = 0;
    reg [15:0] lf = 16'hACE1;
    reg        busym = 0; reg [3:0] lat = 0; reg m_we = 0; reg [WBA-1:0] m_a = 0;
    reg [DW-1:0] m_d = 0; reg [LANES*8-1:0] m_s = 0;
    initial for (k = 0; k < NL; k = k + 1) mem[k] = 0;
    always @(posedge cclk) begin
        lf <= {lf[14:0], lf[15] ^ lf[13] ^ lf[12] ^ lf[10]};
        wb_ack <= 1'b0;
        wb_stall <= busym | !calib | (lf[2] & lf[5]);
        if (wb_cyc && wb_stb && !wb_stall && !busym) begin
            accepted = accepted + 1;
            busym <= 1'b1; lat <= 4'd4 + lf[3:0] % 8; m_we <= wb_we; m_a <= wb_addr; m_d <= wb_data; m_s <= wb_sel;
            if (wb_addr >= NL) viol = viol + 1;
            if (wb_sel[LANES*8-1:64] != 0) viol = viol + 1;      // the 9th lane's bytes must never be enabled
        end
        if (busym) begin
            if (lat == 0) begin
                busym <= 1'b0; wb_ack <= 1'b1;
                if (m_we) begin for (k = 0; k < LANES*8; k = k + 1) if (m_s[k]) mem[m_a][8*k +: 8] <= m_d[8*k +: 8]; wb_rdata <= 0; end
                else wb_rdata <= mem[m_a];
            end else lat <= lat - 1'b1;
        end
    end

    // ---- reference and driver
    reg [31:0] ref [0:NL*16-1];
    integer errs = 0, ops = 0, i, j;
    reg [31:0] q, rnd;
    task xfer(input we, input [20:0] a, input [31:0] d);
        begin
            @(posedge clk); #1; while (!req_rdy) begin @(posedge clk); #1; end
            req_v = 1; req_we = we; req_a = a; req_wd = d;
            @(posedge clk); #1; req_v = 0;
            while (!ack_v) begin @(posedge clk); #1; end
            q = ack_d; ops = ops + 1;
        end
    endtask
    task wr(input [20:0] a, input [31:0] d); begin xfer(1, a, d); ref[a] = d; end endtask
    task rd(input [20:0] a);
        begin
            xfer(0, a, 0);
            if (q !== ref[a]) begin errs = errs + 1; if (errs < 10) $display("MISMATCH word %0d read %h expected %h", a, q, ref[a]); end
        end
    endtask

    initial begin
        for (i = 0; i < NL*16; i = i + 1) ref[i] = 0;
        #100 rst = 0; crst_n = 1;
        repeat (20) @(posedge clk);
        if (req_rdy !== 1'b0 || init_done !== 1'b0) begin errs = errs + 1; $display("FAIL: ready before calibration"); end
        calib = 1;
        repeat (10) @(posedge clk);
        wait (init_done);
        // 1) every slot of the first four lines, then read all back (also checks neighbours are untouched)
        for (i = 0; i < 64; i = i + 1) wr(i, 32'hC0DE0000 + i * 32'h101);
        for (i = 0; i < 64; i = i + 1) rd(i);
        // 2) unwritten words read as zero
        rd(21'd200); rd(21'd201); rd(21'd4000);
        // 3) random mix over 4096 words (256 lines)
        rnd = 32'h12345678;
        for (j = 0; j < 600; j = j + 1) begin
            rnd = rnd * 32'd1664525 + 32'd1013904223;
            i = (rnd >> 8) & 4095;
            if (rnd[31:29] < 3'd4) wr(i, rnd ^ 32'hA5A5F00F); else rd(i);
        end
        // 4) read everything back
        for (i = 0; i < NL*16; i = i + 1) rd(i);
        if (viol != 0) begin errs = errs + viol; $display("FAIL: %0d protocol violations (address out of range or ECC lane enabled)", viol); end
        if (errs == 0) $display("PASS: %0d pool operations, %0d Wishbone transfers, 0 errors", ops, accepted);
        else $display("FAIL: %0d errors", errs);
        $finish;
    end
    initial begin #50_000_000; $display("FAIL: timeout"); $finish; end
endmodule
