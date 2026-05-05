// top_debug.v — Minimal debug top level
// Identical to uart_hello but in the full module structure.
// No unicell_array, no uart_bridge — just HFOSC + TX.
// If HELLO appears: HFOSC and TX work in this build context.
// If nothing: something in the build/synthesis is breaking TX output.

`default_nettype none

module top (
    input  wire BTN_N,
    input  wire RX,
    output reg  TX,
    output wire LEDR_N,
    output wire LEDG_N
);

wire CLK;
SB_HFOSC #(.CLKHF_DIV("0b00")) osc (
    .CLKHFPU(1'b1),
    .CLKHFEN(1'b1),
    .CLKHF(CLK)
);

assign LEDR_N = 1'b0;   // Red always on
assign LEDG_N = TX;     // Green mirrors TX

localparam CLKS_PER_BIT = 415; // 48MHz / 115200

reg [2:0]  msg_idx = 0;
reg [9:0]  shift   = 10'h3FF;
reg [3:0]  bit_cnt = 0;
reg [15:0] clk_cnt = 0;
reg [23:0] gap     = 0;
reg [1:0]  state   = 2'd0;

reg [7:0] cur_byte;
always @(*) begin
    case (msg_idx)
        3'd0: cur_byte = 8'h48; // H
        3'd1: cur_byte = 8'h45; // E
        3'd2: cur_byte = 8'h4C; // L
        3'd3: cur_byte = 8'h4C; // L
        3'd4: cur_byte = 8'h4F; // O
        3'd5: cur_byte = 8'h0D; // \r
        default: cur_byte = 8'h0A; // \n
    endcase
end

always @(posedge CLK) begin
    case (state)
        2'd0: begin TX <= 1'b1; gap <= gap + 1; if (&gap) begin msg_idx <= 0; state <= 2'd1; end end
        2'd1: begin shift <= {1'b1, cur_byte, 1'b0}; bit_cnt <= 0; clk_cnt <= 0; state <= 2'd2; end
        2'd2: begin
            clk_cnt <= clk_cnt + 1;
            if (clk_cnt == CLKS_PER_BIT - 1) begin
                clk_cnt <= 0; TX <= shift[0];
                shift <= {1'b1, shift[9:1]}; bit_cnt <= bit_cnt + 1;
                if (bit_cnt == 9) state <= 2'd3;
            end
        end
        2'd3: begin if (msg_idx == 6) state <= 2'd0; else begin msg_idx <= msg_idx + 1; state <= 2'd1; end end
    endcase
end

endmodule
