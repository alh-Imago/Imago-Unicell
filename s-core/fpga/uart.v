// uart.v - 8N1 UART receiver and transmitter, one start bit, 8 data bits LSB first, one stop bit.
// DIV = clock cycles per bit (27 MHz / 115200 = 234).
module uart_rx #(parameter DIV = 234) (
    input  wire       clk,
    input  wire       rx,
    output reg  [7:0] data,
    output reg        valid          // one-clock pulse
);
    reg [1:0]  sync = 2'b11;
    reg [15:0] cnt  = 0;
    reg [3:0]  nbit = 0;
    reg        busy = 0;
    reg [7:0]  sh   = 0;
    always @(posedge clk) begin
        sync  <= {sync[0], rx};
        valid <= 1'b0;
        if (!busy) begin
            if (!sync[1]) begin            // start edge: wait half a bit to sample in the middle
                busy <= 1'b1; cnt <= DIV/2; nbit <= 0;
            end
        end else if (cnt != 0) cnt <= cnt - 1'b1;
        else begin
            cnt <= DIV - 1;
            if (nbit == 0) begin
                if (sync[1]) busy <= 1'b0;                 // false start
                else nbit <= 1;
            end else if (nbit <= 8) begin
                sh <= {sync[1], sh[7:1]}; nbit <= nbit + 1'b1;
            end else begin                                  // stop bit
                busy <= 1'b0;
                if (sync[1]) begin data <= sh; valid <= 1'b1; end
            end
        end
    end
endmodule

module uart_tx #(parameter DIV = 234) (
    input  wire       clk,
    input  wire [7:0] data,
    input  wire       send,          // pulse; ignored while busy
    output reg        tx = 1'b1,
    output wire       busy
);
    reg [15:0] cnt  = 0;
    reg [3:0]  nbit = 0;
    reg [9:0]  sh   = 10'h3FF;
    reg        act  = 0;
    assign busy = act;
    always @(posedge clk) begin
        if (!act) begin
            if (send) begin sh <= {1'b1, data, 1'b0}; act <= 1'b1; cnt <= DIV - 1; nbit <= 0; tx <= 1'b0; end
        end else if (cnt != 0) cnt <= cnt - 1'b1;
        else begin
            cnt <= DIV - 1;
            if (nbit == 9) begin act <= 1'b0; tx <= 1'b1; end
            else begin nbit <= nbit + 1'b1; tx <= sh[nbit + 1]; end
        end
    end
endmodule
