`timescale 1ns/1ps
// Generic serial-link testbench for a board top: plays a byte script over the UART (CLKDIV 8) and prints what the top answers. +script=FILE, one item per line: 'S hh' = send byte hh (hex); 'R n' = receive n bytes and print them as 'R hh hh ...'.
// Compile with the top's defines (-DLATMOD=... -DNCLS=... -DNCELL=... -DCLKDIV=8) and -DTOP=<top module name>.
`ifndef CLKDIV
`define CLKDIV 8
`endif
module tb_hexn_bytes_v1;
    localparam CD = `CLKDIV;
    reg clk = 0, rxd = 1; wire txd; wire [5:0] led;
    `TOP dut(.clk(clk), .uart_rx(rxd), .uart_tx(txd), .led(led));
    always #5 clk = ~clk;
    integer fd, n, i, cnt; reg [1023:0] fn; reg [7:0] b; reg [7:0] ch; reg [7:0] line [0:0];
    task sendb(input [7:0] d); integer j; begin
        rxd = 0; repeat (CD) @(posedge clk);
        for (j = 0; j < 8; j = j + 1) begin rxd = d[j]; repeat (CD) @(posedge clk); end
        rxd = 1; repeat (CD) @(posedge clk);
    end endtask
    task recvb(output [7:0] d); integer j; begin
        while (txd !== 1'b0) @(posedge clk);
        repeat (CD + CD/2) @(posedge clk);
        for (j = 0; j < 8; j = j + 1) begin d[j] = txd; repeat (CD) @(posedge clk); end
    end endtask
    reg [7:0] kind; reg [7:0] val;
    initial begin
        if (!$value$plusargs("script=%s", fn)) begin $display("need +script=FILE"); $finish; end
        fd = $fopen(fn, "r"); repeat (400) @(posedge clk);
        while (!$feof(fd)) begin
            n = $fscanf(fd, " %c", kind);
            if (n == 1) begin
                if (kind == "S") begin n = $fscanf(fd, " %h", val); sendb(val); end
                else if (kind == "R") begin n = $fscanf(fd, " %d", cnt); $write("R"); for (i = 0; i < cnt; i = i + 1) begin recvb(b); $write(" %0h", b); end $write("\n"); end
            end
        end
        $finish;
    end
endmodule
