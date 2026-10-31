`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg key = 0;
    wire SPI_MISO, READY; wire [5:0] led;
    tri1 [15:0] pool; reg [15:0] ext = 16'hFFFF, ext_oe = 16'h0000;
    genvar g; generate for (g = 0; g < 16; g = g + 1) begin : X assign pool[g] = ext_oe[g] ? ext[g] : 1'bz; end endgenerate
//MASTER//
    hexn_open_top_v5 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .POOL(pool), .LED_N(led));
    defparam T.SH.DWELL = 20; defparam T.SH.HALF = 2;
    integer fails = 0, i, bad, ns, nr, seq = 50; reg [8*200:1] dir, fn; reg saw12, saw6;
    reg [31:0] pset [0:63]; reg [31:0] strm [0:511]; reg [31:0] expr [0:255];
    task ms_ticks(input integer n); begin repeat (n * 10) @(posedge clk); end endtask
    task check(input cond, input [255:0] what); begin if (!cond) begin $display("FAIL %0s", what); fails = fails + 1; end else $display("ok %0s", what); end endtask
    task press(input integer pin); begin ext[pin] = 0; ext_oe[pin] = 1; end endtask
    task unpress(input integer pin); begin ext_oe[pin] = 0; ext[pin] = 1; end endtask
    always @(negedge pool[12]) saw12 = 1; always @(negedge pool[6]) saw6 = 1;
    task wait_idle; begin rd_reg(8'd10); while (rv[4]) rd_reg(8'd10); end endtask
    task wait_raw; begin rd_reg(8'd10); while (rv[6]) rd_reg(8'd10); end endtask
    task set_preset(input integer n); begin wr_reg(8'd29, 32'd0); repeat (40) @(negedge clk); wr_reg(8'd29, n); repeat (200) @(negedge clk); end endtask
    task game(input integer base, output reg ok);
        begin wait (T.RC.st == 3); #1; ms_ticks(170); press(base + T.RC.tgt); wait (T.RC.st == 5); repeat (20) @(posedge clk);
              ok = (T.RC.right === 1'b1 && T.RC.pred === 1'b1); ms_ticks(120); unpress(base + T.RC.tgt); ms_ticks(10); end
    endtask
    task usym(input integer dash, input integer unit, input integer gapms); begin press(0); ms_ticks(dash ? unit * 3 : unit); unpress(0); ms_ticks(gapms); end endtask
    reg ok;
    initial begin
        if (!$value$plusargs("dir=%s", dir) || !$value$plusargs("ns=%d", ns) || !$value$plusargs("nr=%d", nr)) begin $display("FAIL args"); $finish; end
        $sformat(fn, "%0s/preset.hex", dir); $readmemh(fn, pset); $sformat(fn, "%0s/stream.hex", dir); $readmemh(fn, strm); $sformat(fn, "%0s/expect.hex", dir); $readmemh(fn, expr);
        saw12 = 0; saw6 = 0; wait (T.init_done); repeat (40) @(negedge clk);
        // ---- factory presets, no mode register written at all
        set_preset(1); rd_reg(8'd10); check(rv[1:0] === 2'd1 && rv[7] === 1'b1, "preset 1: reaction game selected (mode 1), preset-active bit set");
        game(0, ok); check(ok, "preset 1 plays: a good hit scores");
        set_preset(2); wait (T.MC.loaded); ms_ticks(20); usym(0, 160, 480); ms_ticks(10); check(T.MC.c3 === 6'd4, "preset 2: Morse key decodes . as E");
        set_preset(0); rd_reg(8'd10); check(rv[1:0] === 2'd0 && rv[7] === 1'b0 && READY === 1'b0, "preset 0: back to the direct registers (mode 0, idle)");
        wr_reg(8'd16, 32'h2); repeat (50) @(negedge clk); rd_reg(8'd10); check(rv[1:0] === 2'd2, "direct control still works with no preset active"); wr_reg(8'd16, 32'h0);
        // ---- a CUSTOM preset 6 (loaded into table space 5): reaction game, buttons on pool pins 9..11, buzzer on pool pin 12
        for (i = 0; i < 64; i = i + 1) wbuf[i] = pset[i]; wr_words(16'd0, 64); wr_reg(8'd17, {4'd5, 12'd0, 16'd64}); seq = seq + 1; wr_reg(8'd19, seq); wait_idle;
        set_preset(6); saw12 = 0; saw6 = 0; game(9, ok); check(ok && saw12 && !saw6, "custom preset 6: buttons on pins 9..11 and buzzer on pin 12, from ONE write");
        // ---- two judges: preset 4 = raw stream, two judges. Control words and table loads for A and B ride in the same stream.
        set_preset(4); rd_reg(8'd10); check(rv[1:0] === 2'd3, "preset 4: mode 3, raw stream");
        for (i = 0; i < 128; i = i + 1) wbuf[i] = strm[i]; wr_words(16'd0, 128);
        for (i = 0; i < 128; i = i + 1) wbuf[i] = strm[128 + i]; wr_words(16'd128, 128);
        for (i = 0; i < ns - 256; i = i + 1) wbuf[i] = strm[256 + i]; wr_words(16'd256, ns - 256);
        wr_reg(8'd24, (600 << 16) | ns); seq = seq + 1; wr_reg(8'd25, seq); repeat (20) @(negedge clk); wait_raw;
        rd_words(16'd600, nr); bad = 0; for (i = 0; i < nr; i = i + 1) if (rbuf[i] !== expr[i]) bad = bad + 1;
        check(bad == 0, "two judges: every A and B result equals the reference (tables loaded by control words inside the stream)");
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (80000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
