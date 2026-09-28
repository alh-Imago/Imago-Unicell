// unicell_tang_nano_20k_diag_v1.v -- points.md #894: real-hardware bisection diagnostic.
//
// The v1 smoke test (#892) is dark on LED1/LED2 on real silicon despite passing simulation and a
// pull-up fix (#893) making no difference even with the reset button held for several seconds. This
// variant exposes internal signals directly, LATCHED STICKY (once true, stays true forever until reset),
// so a signal that only pulses briefly still shows as a steady, unmistakable LED rather than something
// easy to miss:
//   LED0 = heartbeat (unchanged from v1 -- already confirmed working: clock is alive)
//   LED1 = sticky: cfg_valid has fired at least once (proves the config-load pulse generator works)
//   LED2 = sticky: armed has become 1 at least once (proves the sequencer core itself latched cfg_valid)
//   LED3 = sticky: fire_n has asserted at least once (proves any_fire triggered -- the full handshake
//          decode chain: want_to_offer, downstream_mask, targets_all_ready, all real and all working)
// If ALL FOUR light up (and stay lit) shortly after flashing, the whole chain up to "ready to advance" is
// proven working on real silicon, and the only remaining question is the tick/ack loopback timing itself.
// If LED1 never lights, the config pulse generator itself is the problem. If LED1 lights but LED2 doesn't,
// the sequencer core isn't latching cfg_valid despite receiving it -- a genuine RTL/synthesis mismatch.
`default_nettype none
`timescale 1ns / 1ps

module unicell_tang_nano_20k_diag_v1 (
    input  wire BOARD_CLK,
    input  wire BTN_RST_N,
    output wire LED0_N,
    output wire LED1_N,
    output wire LED2_N,
    output wire LED3_N
);

wire clk = BOARD_CLK;
reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], ~BTN_RST_N};
wire rst = rst_sr[3] | ~BTN_RST_N;

reg [3:0] cfg_pulse_sr = 4'hF;
always @(posedge clk) if (!rst) cfg_pulse_sr <= {cfg_pulse_sr[2:0], 1'b0};
wire cfg_valid = !rst && cfg_pulse_sr[3] && !cfg_pulse_sr[2];

localparam [63:0] CFG_DATA = {24'h0, 6'b00_0001, 2'd3, 8'h04, 8'h03, 8'h02, 8'h01};

wire [31:0] dout_n;
wire fire_n;
wire ready_out_w;   // = armed && active (this core's own real definition) -- a real port, not a hierarchical peek
wire [1:0] seq_index;

// No tick/ack gating at all in this diagnostic -- ack_in_n tied directly to fire_n, so if the handshake
// chain works at all, seq_index will free-run as fast as the FSM allows (irrelevant here; we're only
// checking whether cfg_valid/armed/fire_n ever assert, not watching seq_index in this build).
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

// Sticky latches: once set, stay set until reset. This is the whole point -- a signal that pulses for a
// single cycle (37ns) would otherwise be completely invisible to the human eye.
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
