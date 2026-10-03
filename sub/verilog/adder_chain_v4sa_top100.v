module adder_chain_v4sa_top100 (
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

// Real, genuinely-evolving stimulus (not constant) -- the proven anti-collapse
// pattern from #889: an LFSR whose own feedback includes a real board input.
reg [31:0] lfsr = 32'hACE1_1234;
always @(posedge BOARD_CLK) lfsr <= {lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]^BTN_ENTRY};

// A real, periodic consumer at the far end of the 100-stage chain -- without
// this the chain fills once and permanently stalls, proving nothing about
// real sustained operation.
reg [4:0] tick_cnt = 0;
always @(posedge BOARD_CLK) tick_cnt <= tick_cnt + 5'd1;
wire consumer_ack = (tick_cnt == 5'h1F);

wire [31:0] chain_out;
wire chain_valid_out, chain_ack_out;

adder_chain_v4sa #(.NSTAGES(100)) CHAIN (
    .clk(BOARD_CLK), .rst(rst), .freeze_in(1'b0),
    .cfg_valid(cfg_valid),
    .chain_in(lfsr), .chain_valid_in(1'b1), .chain_ack_out(chain_ack_out),
    .chain_out(chain_out), .chain_valid_out(chain_valid_out), .chain_ack_in(consumer_ack),
    .lfsr(lfsr)
);

// Full-width XOR reduction -- NOT a single bit -- per #902's own hard-won lesson.
assign LED0_N = ~chain_valid_out;
assign LED1_N = ~chain_ack_out;
assign LED2_N = ~(^chain_out);
endmodule
