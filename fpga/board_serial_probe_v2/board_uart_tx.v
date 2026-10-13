// board_uart_tx.v -- 8N1 transmitter, CPB clocks per bit (ledger #1023)
`default_nettype none
module board_uart_tx #(parameter integer CPB = 234) (input wire clk, input wire start, input wire [7:0] data, output reg tx, output wire busy);
    reg [3:0] nbit = 4'd0; reg [15:0] cnt = 16'd0; reg [9:0] sh = 10'h3FF;
    assign busy = (nbit != 4'd0);
    initial tx = 1'b1;
    always @(posedge clk) begin
        if (nbit == 4'd0) begin
            tx <= 1'b1;
            if (start) begin sh <= {1'b1, data, 1'b0}; nbit <= 4'd10; cnt <= CPB - 1; end
        end else begin
            tx <= sh[0];
            if (cnt == 16'd0) begin sh <= {1'b1, sh[9:1]}; nbit <= nbit - 4'd1; cnt <= CPB - 1; end else cnt <= cnt - 16'd1;
        end
    end
endmodule
