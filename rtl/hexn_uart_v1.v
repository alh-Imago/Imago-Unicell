`default_nettype none
// hexn_uart_v1.v -- 8N1 serial receiver and transmitter, CLKDIV clocks per bit (27 MHz / 115200 = 234).
module hexn_uart_rx_v1 #(parameter CLKDIV = 234) (input wire clk, input wire rst, input wire rxd, output reg [7:0] data, output reg valid);
    reg [2:0] sync; reg [15:0] cnt; reg [3:0] nbit; reg busy; reg [7:0] sh;
    always @(posedge clk) begin
        sync <= {sync[1:0], rxd}; valid <= 1'b0;
        if (rst) begin busy <= 0; cnt <= 0; nbit <= 0; end
        else if (!busy) begin
            if (sync[2] == 1'b1 && sync[1] == 1'b0) begin busy <= 1; cnt <= CLKDIV + CLKDIV/2 - 1; nbit <= 0; end   // start edge: next sample in the middle of data bit 0
        end else if (cnt != 0) cnt <= cnt - 1'b1;
        else begin
            cnt <= CLKDIV - 1;
            if (nbit < 8) begin sh <= {sync[1], sh[7:1]}; nbit <= nbit + 1'b1; end
            else begin busy <= 0; if (sync[1]) begin data <= sh; valid <= 1'b1; end end   // stop bit must be 1
        end
    end
endmodule
module hexn_uart_tx_v1 #(parameter CLKDIV = 234) (input wire clk, input wire rst, input wire [7:0] data, input wire send, output reg txd, output wire busy);
    reg [15:0] cnt; reg [3:0] nbit; reg [9:0] sh; reg act;
    assign busy = act;
    always @(posedge clk) begin
        if (rst) begin act <= 0; txd <= 1; cnt <= 0; nbit <= 0; end
        else if (!act) begin
            txd <= 1;
            if (send) begin sh <= {1'b1, data, 1'b0}; act <= 1; cnt <= CLKDIV - 1; nbit <= 0; txd <= 1'b0; end
        end else if (cnt != 0) cnt <= cnt - 1'b1;
        else begin
            cnt <= CLKDIV - 1;
            if (nbit == 9) begin act <= 0; txd <= 1; end
            else begin nbit <= nbit + 1'b1; txd <= sh[nbit + 1]; end
        end
    end
endmodule
`default_nettype wire
