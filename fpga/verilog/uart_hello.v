// uart_hello.v — UART TX test for iCEBreaker
// Sends "HELLO\r\n" repeatedly.
// Red LED always on = design is running.
// If you see HELLO in terminal: TX pin and baud rate are correct.

`default_nettype none

module top (
    input  wire CLK,
    output reg  TX,
    output wire LEDR_N,
    output wire LEDG_N
);

localparam CLKS_PER_BIT = 1250; // 12MHz / 9600

reg [7:0] msg0 = 8'h48; // H
reg [7:0] msg1 = 8'h45; // E
reg [7:0] msg2 = 8'h4C; // L
reg [7:0] msg3 = 8'h4C; // L
reg [7:0] msg4 = 8'h4F; // O
reg [7:0] msg5 = 8'h0D; // \r
reg [7:0] msg6 = 8'h0A; // \n

assign LEDR_N = 1'b0;   // Red always on = design running
assign LEDG_N = TX;     // Green mirrors TX

reg [2:0]  msg_idx = 0;
reg [9:0]  shift   = 10'h3FF;
reg [3:0]  bit_cnt = 0;
reg [15:0] clk_cnt = 0;
reg [23:0] gap     = 0;
reg [1:0]  state   = 2'd0;

reg [7:0] cur_byte;
always @(*) begin
    case (msg_idx)
        3'd0: cur_byte = msg0;
        3'd1: cur_byte = msg1;
        3'd2: cur_byte = msg2;
        3'd3: cur_byte = msg3;
        3'd4: cur_byte = msg4;
        3'd5: cur_byte = msg5;
        default: cur_byte = msg6;
    endcase
end

always @(posedge CLK) begin
    case (state)
        2'd0: begin // gap
            TX    <= 1'b1;
            gap   <= gap + 1;
            if (&gap) begin
                msg_idx <= 0;
                state   <= 2'd1;
            end
        end
        2'd1: begin // load byte
            shift   <= {1'b1, cur_byte, 1'b0};
            bit_cnt <= 0;
            clk_cnt <= 0;
            state   <= 2'd2;
        end
        2'd2: begin // send bits
            clk_cnt <= clk_cnt + 1;
            if (clk_cnt == CLKS_PER_BIT - 1) begin
                clk_cnt <= 0;
                TX      <= shift[0];
                shift   <= {1'b1, shift[9:1]};
                bit_cnt <= bit_cnt + 1;
                if (bit_cnt == 9) begin
                    state <= 2'd3;
                end
            end
        end
        2'd3: begin // next byte or gap
            if (msg_idx == 6) begin
                state <= 2'd0;
            end else begin
                msg_idx <= msg_idx + 1;
                state   <= 2'd1;
            end
        end
    endcase
end

endmodule
