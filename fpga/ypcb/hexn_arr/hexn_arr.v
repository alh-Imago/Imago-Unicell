`default_nettype none
// hexn_arr on the YPCB-00338-1P1: JTAG bridge on USER2 (IR 0x03) + hexn_arr_core (frame v4 around one hex pattern). Same for every pattern. Written by tools/hexn_kxarr_v1.py top; do not edit.
module hexn_arr (input SYS_CLK, output [2:0] led);
    reg [31:0] count = 0; always @(posedge SYS_CLK) count <= count + 1;
    wire [7:0] rx_d, tx_d; wire rx_v, tx_s, tx_b; wire [5:0] cled;
    hexn_jtag_bridge_v1 #(.CHAIN(2), .FSPACING(128)) br (.clk(SYS_CLK), .rst(1'b0), .rx_d(rx_d), .rx_v(rx_v), .tx_d(tx_d), .tx_s(tx_s), .tx_b(tx_b));
    hexn_arr_core core (.clk(SYS_CLK), .rx_d(rx_d), .rx_v(rx_v), .tx_dout(tx_d), .tx_s(tx_s), .tx_b(tx_b), .led(cled));
    reg txseen = 0; always @(posedge SYS_CLK) if (tx_s) txseen <= ~txseen;
    assign led = {txseen, ~&cled[2:0], count[25]};
endmodule
