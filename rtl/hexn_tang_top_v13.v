`default_nettype none
// hexn_tang_top_v13.v -- Board top for core v9 (store v5) (new file; earlier tops untouched): the serial port (USB serial through the BL616, 8N1, 115200 at 27 MHz) around hexn_core_v9, which holds the command interpreter, the lattice bank, the hold counter and the layer 2 store with reward values.
`ifndef CLKDIV
`define CLKDIV 234
`endif
module hexn_tang_top_v13 (input wire clk, input wire uart_rx, output wire uart_tx, output wire [5:0] led);
    reg [7:0] por = 0; wire rst = ~&por; always @(posedge clk) if (~&por) por <= por + 1'b1;
    wire [7:0] rx_d, tx_d; wire rx_v, tx_s, tx_b;
    hexn_uart_rx_v1 #(.CLKDIV(`CLKDIV)) urx(.clk(clk), .rst(rst), .rxd(uart_rx), .data(rx_d), .valid(rx_v));
    hexn_uart_tx_v1 #(.CLKDIV(`CLKDIV)) utx(.clk(clk), .rst(rst), .data(tx_d), .send(tx_s), .txd(uart_tx), .busy(tx_b));
    hexn_core_v9 core(.clk(clk), .rx_d(rx_d), .rx_v(rx_v), .tx_d(tx_d), .tx_s(tx_s), .tx_b(tx_b), .led(led));
endmodule
`default_nettype wire
