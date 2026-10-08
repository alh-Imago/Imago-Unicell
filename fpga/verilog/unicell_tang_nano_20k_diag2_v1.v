// unicell_tang_nano_20k_diag2_v1.v -- points.md #895: same three sticky diagnostics as diag_v1, but with
// BTN_RST_N removed from the reset path ENTIRELY. Reset now comes only from a power-on counter that
// releases automatically ~1us after configuration, with zero dependency on any button or external pin.
// This isolates one specific question: does the reset BUTTON/pin explain diag_v1's all-dark result, or
// does the problem lie somewhere else even with reset completely out of the picture?
`default_nettype none
`timescale 1ns / 1ps

module unicell_tang_nano_20k_diag2_v1 (
    input  wire BOARD_CLK,
    output wire LED0_N,
    output wire LED1_N,
    output wire LED2_N,
    output wire LED3_N
);

wire clk = BOARD_CLK;

// Pure power-on reset: counts up once and never again touches rst after that. No button, no external pin,
// nothing but the clock itself.
reg [7:0] por_cnt = 8'h00;
wire rst = (por_cnt != 8'hFF);
always @(posedge clk) if (rst) por_cnt <= por_cnt + 8'd1;

reg [3:0] cfg_pulse_sr = 4'hF;
always @(posedge clk) if (!rst) cfg_pulse_sr <= {cfg_pulse_sr[2:0], 1'b0};
wire cfg_valid = !rst && cfg_pulse_sr[3] && !cfg_pulse_sr[2];

localparam [63:0] CFG_DATA = {24'h0, 6'b00_0001, 2'd3, 8'h04, 8'h03, 8'h02, 8'h01};

wire [31:0] dout_n;
wire fire_n;
wire ready_out_w;
wire [1:0] seq_index;
wire ack_in_n = fire_n;

sequencer_shell_v1c #(.CELL_ID(16'h0001)) SEQ (
    .clk(clk), .rst(rst),
    .active_in_n(1'b1), .active_in_s(1'b0), .active_in_e(1'b0), .active_in_w(1'b0),
    .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),
    .cfg_valid(cfg_valid), .cfg_data(CFG_DATA),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(fire_n), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(ready_out_w), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(ack_in_n), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
    .status_seq_index(seq_index)
);

reg cfg_valid_seen = 1'b0;
reg armed_seen = 1'b0;
reg fire_seen = 1'b0;
always @(posedge clk) begin
    if (rst) begin
        cfg_valid_seen <= 1'b0;
        armed_seen <= 1'b0;
        fire_seen <= 1'b0;
    end else begin
        if (cfg_valid) cfg_valid_seen <= 1'b1;
        if (ready_out_w) armed_seen <= 1'b1;
        if (fire_n) fire_seen <= 1'b1;
    end
end

reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;

assign LED0_N = ~hb_cnt[23];
assign LED1_N = ~cfg_valid_seen;
assign LED2_N = ~armed_seen;
assign LED3_N = ~fire_seen;

endmodule
