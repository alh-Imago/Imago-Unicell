`timescale 1ns/1ps
// tb_hexn_open9_v1: DUMP and GUARDED RESTORE of the judges' weights through the whole open unit v9 over SPI. +dir holds, for each phase p: s<p>.hex (the stream), e<p>.hex (expected result words), meta.hex (per phase: stream words, result words, out_base).
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg key = 0;
    wire SPI_MISO, READY; wire [5:0] led;
    tri1 [15:0] pool;
//MASTER//
    hexn_open_top_v9 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .POOL(pool), .LED_N(led));
    defparam T.SH.DWELL = 20; defparam T.SH.HALF = 2;
    integer fails = 0, i, k, p, bad, np, ns, nr, ob, seq = 90, chunk, first_bad; reg [8*200:1] dir, fn;
    reg [31:0] strm [0:1023]; reg [31:0] expr [0:1023]; reg [31:0] meta [0:63];
    task check(input cond, input [639:0] what); begin if (!cond) begin $display("FAIL %0s", what); fails = fails + 1; end else $display("ok %0s", what); end endtask
    task wait_raw; begin rd_reg(8'd10); while (rv[6]) rd_reg(8'd10); end endtask
    initial begin
        if (!$value$plusargs("dir=%s", dir) || !$value$plusargs("np=%d", np)) begin $display("FAIL args"); $finish; end
        $sformat(fn, "%0s/meta.hex", dir); $readmemh(fn, meta);
        wait (T.init_done); repeat (40) @(negedge clk);
        wr_reg(8'd28, 32'd0); wr_reg(8'd16, 32'd3); repeat (40) @(negedge clk);          // mode 3 = raw stream; judge control starts at 0 (loads go to A)
        for (p = 0; p < np; p = p + 1) begin
            ns = meta[3*p]; nr = meta[3*p+1]; ob = meta[3*p+2];
            $sformat(fn, "%0s/s%0d.hex", dir, p); $readmemh(fn, strm); $sformat(fn, "%0s/e%0d.hex", dir, p); $readmemh(fn, expr);
            for (k = 0; k < ns; k = k + 256) begin
                chunk = (ns - k > 256) ? 256 : ns - k; for (i = 0; i < chunk; i = i + 1) wbuf[i] = strm[k + i]; wr_words(k, chunk);
            end
            wr_reg(8'd24, (ob << 16) | ns); seq = seq + 1; wr_reg(8'd25, seq); repeat (20) @(negedge clk); wait_raw;
            bad = 0; first_bad = -1;
            for (k = 0; k < nr; k = k + 256) begin
                chunk = (nr - k > 256) ? 256 : nr - k; rd_words(ob + k, chunk);
                for (i = 0; i < chunk; i = i + 1) if (rbuf[i] !== expr[k + i]) begin bad = bad + 1; if (first_bad < 0) first_bad = k + i; if (bad <= 4) $display("  word %0d: got %h expected %h", k + i, rbuf[i], expr[k + i]); end
            end
            if (bad) $display("phase %0d: %0d of %0d words differ, first at %0d", p, bad, nr, first_bad);
            check(bad == 0, {"phase ", 8'h30 + p[7:0], " results equal the expected words"});
        end
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (200000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
