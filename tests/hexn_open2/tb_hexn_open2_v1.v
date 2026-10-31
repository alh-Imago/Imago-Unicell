`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg key = 0, b1 = 1, b2 = 1, b3 = 1;
    wire SPI_MISO, READY, latch, dclk, ddata, buzz; wire [5:0] led;
//MASTER//
    hexn_open_top_v2 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY),
        .BTN1_N(b1), .BTN2_N(b2), .BTN3_N(b3), .DISP_LATCH(latch), .DISP_CLK(dclk), .DISP_DATA(ddata), .BUZZER(buzz), .LED_N(led));
    defparam T.SH.DWELL = 20; defparam T.SH.HALF = 2;
    integer fails = 0, i, seq = 100; reg [8*200:1] dir, fn;
    reg [31:0] tmp [0:255];
    task ms_ticks(input integer k); begin repeat (k * 10) @(posedge clk); end endtask
    task check(input cond, input [255:0] what); begin if (!cond) begin $display("FAIL %0s", what); fails = fails + 1; end else $display("ok %0s", what); end endtask
    task usym(input integer dash, input integer unit, input integer gapms); begin b1 = 0; ms_ticks(dash ? unit * 3 : unit); b1 = 1; ms_ticks(gapms); end endtask
    task wait_idle; begin rd_reg(8'd10); while (rv[4]) rd_reg(8'd10); end endtask
    task load_space(input [3:0] sp, input integer n);        // tmp[0..n-1] -> scratch RAM -> table space sp
        begin for (i = 0; i < n; i = i + 1) wbuf[i] = tmp[i];
            wr_words(16'd0, n); wr_reg(8'd17, {sp, 12'd0, n[15:0]}); seq = seq + 1; wr_reg(8'd19, seq); wait_idle; end
    endtask
    task load_file(input [8*40:1] name, input [3:0] sp, input integer n);
        begin $sformat(fn, "%0s/%0s", dir, name); for (i = 0; i < 256; i = i + 1) tmp[i] = 32'h0; $readmemh(fn, tmp); load_space(sp, n); end
    endtask
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("FAIL no dir"); $finish; end
        wait (T.init_done); repeat (40) @(negedge clk); wait_idle;
        rd_reg(8'd10); check(rv[5] === 1'b1 && rv[4] === 1'b0, "defaults loaded, not busy");
        // ---- defaults behave as stage 1: Morse L (.-..) then a dot is E
        wr_reg(8'd16, 32'h2); wait (T.MC.loaded); ms_ticks(20);
        usym(0, 160, 160); usym(1, 160, 160); usym(0, 160, 160); usym(0, 160, 480); ms_ticks(10); check(T.MC.c3 === 6'd11, "default tables: .-.. is L");
        // ---- a custom DECODE table: a single dot now decodes as Q (16); a custom GLYPH: S (18) shows as 0xA0
        wr_reg(8'd16, 32'h0); ms_ticks(5);
        load_file("dec_custom.hex", 4'd3, 256); load_file("gly_custom.hex", 4'd4, 64);
        wr_reg(8'd16, 32'h2); wait (T.MC.loaded); ms_ticks(20);
        usym(0, 160, 480); ms_ticks(10); check(T.MC.c3 === 6'd16, "custom decode table: . is Q");
        usym(0, 160, 160); usym(0, 160, 160); usym(0, 160, 480); ms_ticks(10); check(T.MC.c3 === 6'd18, "default entries still decode: ... is S");
        repeat (20) @(posedge clk); check(T.gsegs[7:0] === 8'hA0 || T.gsegs[7:0] === 8'h20, "custom glyph table: S shown as 0xA0 (point may be lit)");
        // ---- a custom Morse SCORER table with LINEAR bins (32 ms wide) for a fast key (unit 60 ms)
        wr_reg(8'd16, 32'h0); ms_ticks(5);
        wr_reg(8'd21, 32'h00000051); wr_reg(8'd22, 32'h00000051);              // linear, shift 5, low 0
        load_file("morse_fast.hex", 4'd2, 209);
        wr_reg(8'd16, 32'h2); wait (T.MC.loaded); ms_ticks(20);
        usym(0, 60, 60); usym(0, 60, 60); usym(0, 60, 200); ms_ticks(10); check(T.MC.c3 === 6'd18, "fast key table, linear bins: unit 60 ms ... is S");
        usym(1, 60, 60); usym(1, 60, 60); usym(1, 60, 200); ms_ticks(10); check(T.MC.c3 === 6'd14, "fast key table: --- is O");
        // ---- back to the factory defaults
        wr_reg(8'd16, 32'h0); wr_reg(8'd21, 32'h0); wr_reg(8'd22, 32'h0); ms_ticks(5); seq = seq + 1; wr_reg(8'd23, seq); ms_ticks(2); wait_idle;
        wr_reg(8'd16, 32'h2); wait (T.MC.loaded); ms_ticks(20); usym(0, 160, 480); ms_ticks(10); check(T.MC.c3 === 6'd4, "restore defaults: . is E again");
        // ---- the reaction table: a strict one (good hit only under 128 ms) against the default (under 256 ms)
        wr_reg(8'd16, 32'h0); ms_ticks(5); wr_reg(8'd16, 32'h1); wait (T.RC.st == 3); #1; ms_ticks(170);
        case (T.RC.tgt) 0: b1 = 0; 1: b2 = 0; default: b3 = 0; endcase wait (T.RC.st == 5); repeat (20) @(posedge clk);
        check(T.RC.right === 1'b1 && T.RC.pred === 1'b1, "default reaction table: 170 ms is a good hit"); b1 = 1; b2 = 1; b3 = 1; ms_ticks(10);
        wr_reg(8'd16, 32'h0); ms_ticks(5); load_file("react_strict.hex", 4'd1, 193); wr_reg(8'd16, 32'h1); wait (T.RC.st == 3); #1; ms_ticks(170);
        case (T.RC.tgt) 0: b1 = 0; 1: b2 = 0; default: b3 = 0; endcase wait (T.RC.st == 5); repeat (20) @(posedge clk);
        check(T.RC.right === 1'b1 && T.RC.pred === 1'b0, "strict reaction table: 170 ms is NOT a good hit"); b1 = 1; b2 = 1; b3 = 1; ms_ticks(10);
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (120000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
