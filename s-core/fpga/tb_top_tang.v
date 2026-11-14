`timescale 1ns/1ps
// Whole-board simulation of sc_top_tang through its UART pins.
//   +cmds=<file>: lines "B xx" (send one byte, hex) and "D n" (idle n clocks).  +out=<file>: received bytes, hex per line.
//   +maxcyc=<n>: stop after n clocks.
module tb_top_tang;
    parameter S = 8, QD = 16, IMW = 256, DMW = 64, PROF = 64, DIV = 8, LONGEST = 1, FINE = 0;
    reg clk = 0; always #5 clk = ~clk;
    reg rx = 1'b1;
    wire tx; wire [5:0] led_n;
    `ifdef POOL8TOP sc_top_pool8 `elsif POOL7TOP sc_top_pool7 `elsif POOL6TOP sc_top_pool6 `elsif POOLTOP sc_top_pool `else sc_top_tang `endif #(.S(S), .QD(QD), .IMEM_WORDS(IMW), .DMW(DMW), .PROF(PROF), .BAUD_DIV(DIV), .LONGEST(LONGEST), .FINE(FINE)) dut (
        .clk(clk), .uart_rx(rx), .uart_tx(tx), .led_n(led_n));

    task send_byte(input [7:0] b);
        integer k;
        begin
            rx <= 1'b0; repeat (DIV) @(posedge clk);
            for (k = 0; k < 8; k = k + 1) begin rx <= b[k]; repeat (DIV) @(posedge clk); end
            rx <= 1'b1; repeat (DIV) @(posedge clk);
        end
    endtask

    // receiver monitor
    integer fo; reg [1023:0] cmdname, outname;
    integer rcount = 0;
    initial begin
        forever begin
            @(negedge tx);
            repeat (DIV + DIV/2) @(posedge clk);
            begin : rxb
                reg [7:0] v; integer k;
                for (k = 0; k < 8; k = k + 1) begin v[k] = tx; repeat (DIV) @(posedge clk); end
                $fdisplay(fo, "%02x", v); rcount = rcount + 1;
            end
        end
    end

    integer fc, r, n; reg [7:0] cb; reg [7:0] tag; integer maxcyc;
    initial begin
        if (!$value$plusargs("cmds=%s", cmdname)) begin $display("need +cmds"); $finish; end
        if (!$value$plusargs("out=%s", outname))  begin $display("need +out");  $finish; end
        if (!$value$plusargs("maxcyc=%d", maxcyc)) maxcyc = 50000000;
        fo = $fopen(outname, "w"); fc = $fopen(cmdname, "r");
        repeat (400) @(posedge clk);                       // power-on reset
        while (!$feof(fc)) begin
            r = $fscanf(fc, "%c %h\n", tag, n);
            if (r == 2) begin
                if (tag == "B") send_byte(n[7:0]);
                else if (tag == "D") begin
                    // decimal wait given as hex field is awkward: D lines hold hex clocks
                    repeat (n) @(posedge clk);
                end
            end
        end
        $fclose(fo); $finish;
    end
    initial begin #1; end
endmodule
