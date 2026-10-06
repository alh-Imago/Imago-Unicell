module adder_v4sa_top_single (
    input  wire BOARD_CLK,
    input  wire BTN_RST_N,
    input  wire BTN_ENTRY,
    output wire LED0_N,
    output wire LED1_N,
    output wire LED2_N
);
reg [3:0] rst_sr = 4'hF;
always @(posedge BOARD_CLK) rst_sr <= {rst_sr[2:0], ~BTN_RST_N};
wire rst = rst_sr[3] | ~BTN_RST_N;

reg [3:0] cfg_sr = 4'hF;
always @(posedge BOARD_CLK) if (!rst) cfg_sr <= {cfg_sr[2:0], 1'b0};
wire cfg_valid = !rst && cfg_sr[3] && !cfg_sr[2];

// real, genuinely-not-provably-constant stimulus (LFSR mixed with the button,
// matching #889's own proven anti-collapse pattern)
reg [31:0] lfsr = 32'hACE1_1234;
always @(posedge BOARD_CLK) lfsr <= {lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]^BTN_ENTRY};

// a slow, real consumer tick -- without SOME periodic ack, the single cell
// fills once and then permanently stalls, which would prove nothing about
// real operation at speed.
reg [3:0] tick_cnt = 0;
always @(posedge BOARD_CLK) tick_cnt <= tick_cnt + 4'd1;
wire consumer_ack = (tick_cnt == 4'hF);

wire [31:0] result;
wire valid, ack_out;

adder_cell_v4sa DUT (
    .clk(BOARD_CLK), .rst(rst), .freeze_in(1'b0),
    .cfg_valid(cfg_valid), .cfg_data(32'h0),
    .in_a(lfsr), .in_b(~lfsr), .valid_in(1'b1), .ack_out(ack_out),
    .data_out(result), .valid_out(valid), .ack_in(consumer_ack), .ack_in_c(1'b1)
);

assign LED0_N = ~valid;
assign LED1_N = ~ack_out;
assign LED2_N = ~(^result);
endmodule
