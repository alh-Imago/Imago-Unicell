// top_icebreaker.v — DEBUG: uart_hello + stub array
// Stripped back to exactly what worked in uart_hello,
// plus unicell_array_stub instantiation.

`default_nettype none

module top (
    input  wire BTN_N,
    input  wire RX,
    output reg  TX,
    output wire LEDR_N,
    output wire LEDG_N
);

// Internal 48MHz oscillator
wire CLK;
SB_HFOSC #(.CLKHF_DIV("0b00")) osc (
    .CLKHFPU(1'b1),
    .CLKHFEN(1'b1),
    .CLKHF(CLK)
);

assign LEDR_N = 1'b0;  // Red always on
assign LEDG_N = 1'b0;  // Green always on

// Stub array — just to confirm it doesn't kill TX
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

unicell_array #(
    .NUM_CELLS(8),
    .BASE_ADDRESS(32'h00001000)
) array (
    .clk        (CLK),
    .rst        (1'b0),
    .freeze     (1'b0),
    .cpu_addr   (32'h0),
    .cpu_data   (32'h0),
    .cpu_valid  (1'b0),
    .cpu_inject (1'b0),
    .out_addr   (out_addr),
    .out_data   (out_data),
    .out_valid  (out_valid),
    .armed_count(armed_count),
    .cycle_count(cycle_count)
);

// Exact uart_hello transmitter
localparam CLKS_PER_BIT = 415;

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
