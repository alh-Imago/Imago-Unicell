`timescale 1ns/1ps
// Simulation of sc_top_pool13 (cores + far RAM) against sdram_model.v.  The clock is 27 MHz (37 ns) because the model checks timings in ns.
//   +cmds=<file>: "B xx" send one byte (hex), "D n" idle n clocks (hex).  +out=<file>: received bytes, hex per line.
//   +maxcyc=<n>: stop after n clocks.   +skew=<ns>: extra delay on data coming back from the model (default 0).
module tb_top_far;
    parameter S = 2, QD = 16, IMW = 128, DMW = 16, DSH = 256, SHL = 14, DIV = 8;
    reg clk = 0; always #18.5 clk = ~clk;
    reg rx = 1'b1; wire tx; wire [5:0] led_n;
    wire sclk, cke, cs_n, ras_n, cas_n, wen_n; wire [3:0] dqm; wire [10:0] sa; wire [1:0] ba; wire [31:0] dq;
    sc_top_pool13 #(.S(S), .QD(QD), .IMEM_WORDS(IMW), .DMW(DMW), .DSH(DSH), .SHL(SHL), .BAUD_DIV(DIV), .LONGEST(1), .FINE(0)) dut (.clk(clk), .uart_rx(rx), .uart_tx(tx), .led_n(led_n),
        .O_sdram_clk(sclk), .O_sdram_cke(cke), .O_sdram_cs_n(cs_n), .O_sdram_ras_n(ras_n), .O_sdram_cas_n(cas_n), .O_sdram_wen_n(wen_n),
        .O_sdram_dqm(dqm), .O_sdram_addr(sa), .O_sdram_ba(ba), .IO_sdram_dq(dq));
    sdram_model mdl (.clk(sclk), .cke(cke), .cs_n(cs_n), .ras_n(ras_n), .cas_n(cas_n), .we_n(wen_n), .dqm(dqm), .addr(sa), .ba(ba), .dq(dq));

    task send_byte(input [7:0] b);
        integer k;
        begin
            rx <= 1'b0; repeat (DIV) @(posedge clk);
            for (k = 0; k < 8; k = k + 1) begin rx <= b[k]; repeat (DIV) @(posedge clk); end
            rx <= 1'b1; repeat (DIV) @(posedge clk);
        end
    endtask

    integer fo; reg [1023:0] cmdname, outname;
    initial begin
        forever begin
            @(negedge tx);
            repeat (DIV + DIV/2) @(posedge clk);
            begin : rxb
                reg [7:0] v; integer k;
                for (k = 0; k < 8; k = k + 1) begin v[k] = tx; repeat (DIV) @(posedge clk); end
                $fdisplay(fo, "%02x", v);
            end
        end
    end

    integer fc, r, n; reg [7:0] tag; integer maxcyc, cyc = 0;
    always @(posedge clk) begin cyc <= cyc + 1; if (cyc >= maxcyc) begin $display("maxcyc reached"); $fclose(fo); $finish; end end
    initial begin
        if (!$value$plusargs("cmds=%s", cmdname)) begin $display("need +cmds"); $finish; end
        if (!$value$plusargs("out=%s", outname))  begin $display("need +out");  $finish; end
        if (!$value$plusargs("maxcyc=%d", maxcyc)) maxcyc = 20000000;
        fo = $fopen(outname, "w"); fc = $fopen(cmdname, "r");
        repeat (400) @(posedge clk);
        while (!$feof(fc)) begin
            r = $fscanf(fc, "%c %h\n", tag, n);
            if (r == 2) begin
                if (tag == "B") send_byte(n[7:0]);
                else if (tag == "D") repeat (n) @(posedge clk);
            end
        end
        $display("model errors: %0d", mdl.errors);
        $fclose(fo); $finish;
    end
endmodule
