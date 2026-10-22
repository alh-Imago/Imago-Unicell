// Hex-N on the Kintex-7 card (YPCB-00338, xc7k480tffg1156): SIZE / TIMING TOP ONLY. The card has no UART pins and the JTAG command path is not built yet, so this top has no host link:
// a free-running LFSR drives the serial command input of the Tang top (rtl/hexn_tang_top_v11.v) with random bytes, so every command (train, run, cell, memory) is exercised and nothing is optimised away; the LEDs show response activity.
// It measures how large the design is on this chip and how fast it clocks (nextpnr-xilinx max frequency). It does NOT test function. Ports and pins are those of archeology/full-cell/verilog/top_kintex7.xdc (CLK 50 MHz, BTN_RST_N, LED0-2).
// Needs the same defines as the Tang build: -DLATMOD=hexn_lattice_<shape>_v14 -DNBW=18 -DAWB=7 -DNCLS=<K> -DNCELL=<N> -DACCMODE=0 -DCLKDIV=<clock/baud>.
module top (input wire CLK, input wire BTN_RST_N, output wire LED0, output wire LED1, output wire LED2);
    localparam BIT = `CLKDIV;
    reg [15:0] cnt = 0; reg [31:0] lf = 32'hACE1_2345; reg line = 1'b1; reg [7:0] por = 0;
    wire go = &por; always @(posedge CLK) begin if (~&por) por <= por + 1'b1; end
    always @(posedge CLK) begin
        if (cnt == BIT - 1) begin cnt <= 0; lf <= {lf[30:0], lf[31] ^ lf[21] ^ lf[1] ^ lf[0]}; line <= go ? lf[0] : 1'b1; end else cnt <= cnt + 1'b1;
    end
    wire tx; wire [5:0] led;
    hexn_tang_top_v11 dut (.clk(CLK), .uart_rx(line & BTN_RST_N), .uart_tx(tx), .led(led));
    reg act = 0, seen = 0; always @(posedge CLK) begin act <= tx; if (act & ~tx) seen <= ~seen; end
    assign LED0 = seen; assign LED1 = ^led; assign LED2 = |led;
endmodule
