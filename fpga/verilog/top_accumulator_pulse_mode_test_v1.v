// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_accumulator_pulse_mode_test_v1.v — first real Quartus attempt for
// accumulator_cell_v1.v's own pulse_mode/threshold reset-after-fire
// mechanism (points.md #515) — sim-verified clean (tb_accumulator_
// cell_v1.v) but never yet touched real silicon. Standalone instance,
// same "SIZE/TIMING CHECK" discipline top_adder_chain50_v1.v already
// established for adder_cell_v1.v — isolates this core's own real
// ALM/Fmax cost, not the shell's.
//
// THE REAL CLAIM BEING CHECKED ON SILICON: threshold=3, step_amount=1,
// inc on N, downstream on E. Feed 3 real pulses -> must fire with the
// crossing value (3) AND the internal total must genuinely reset to 0
// (not just cap at 3) -- checked by feeding 3 MORE pulses and
// confirming a SECOND real fire, also showing 3. A one-shot latch
// would only ever fire once; this proves the real repeat.
//
// Same self-test discipline as every other top-level here: LED0
// heartbeats; LED1 (active-low: LIT=error) should never light on
// correct hardware. Same SDC/clock convention (CLK_100M/4 -> 25 MHz
// fabric clock).
`default_nettype none
`timescale 1ns / 1ps

module top_accumulator_pulse_mode_test_v1 (
    input  wire CLK_100M,
    output wire LED0_N,
    output wire LED1_N
);

reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

reg         cfg_valid = 0;
reg  [63:0] cfg_data  = 0;
reg         arrived_n = 0;
reg         ack_in_e  = 0;

wire [31:0] data_out_e;
wire        fire_e;

accumulator_cell_v1 #(.CELL_ID(16'h0001), .WIDTH(32)) DUT (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_negative()
);

// cfg_data[63:0], per accumulator_cell_v1.v's own real field map:
// {27'h0 reserved, threshold(16), pulse_mode(1), step_amount(8),
// downstream_mask(4), dec_dir(4), inc_dir(4)}.
localparam [63:0] CFG_PULSE = {27'h0, 16'd3, 1'b1, 8'h01, 4'b0100, 4'h0, 4'b0001};

localparam [4:0] SETTLE = 5'd16;
localparam [4:0]
    S_CFG=0, S_F1=1, S_F2=2, S_F3=3, S_CHECK1=4,
    S_F4=5,  S_F5=6, S_F6=7, S_CHECK2=8, S_DONE=9;

reg [4:0] state = S_CFG;
reg [4:0] settle_cnt = 0;
reg       err_sticky = 1'b0;

always @(posedge clk) begin
    if (rst) begin
        state <= S_CFG;
        cfg_valid <= 0; cfg_data <= 64'h0;
        arrived_n <= 0; ack_in_e <= 0;
        settle_cnt <= 0;
        err_sticky <= 1'b0;
    end else begin
        cfg_valid <= 1'b0;
        arrived_n <= 1'b0;
        ack_in_e  <= 1'b0;
        settle_cnt <= settle_cnt + 5'd1;

        case (state)
            S_CFG: begin
                cfg_valid <= 1'b1; cfg_data <= CFG_PULSE;
                settle_cnt <= 0; state <= S_F1;
            end
            // ═══ First 3 pulses -- must cross threshold and fire ═══
            S_F1: if (settle_cnt >= SETTLE) begin
                arrived_n <= 1'b1; settle_cnt <= 0; state <= S_F2;
            end
            S_F2: if (settle_cnt >= SETTLE) begin
                arrived_n <= 1'b1; settle_cnt <= 0; state <= S_F3;
            end
            S_F3: if (settle_cnt >= SETTLE) begin
                arrived_n <= 1'b1; settle_cnt <= 0; state <= S_CHECK1;
            end
            S_CHECK1: if (settle_cnt >= SETTLE) begin
                if (!fire_e || data_out_e !== 32'd3) err_sticky <= 1'b1;
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_F4;
            end
            // ═══ Second round of 3 -- proves the internal total
            // genuinely reset to 0 and this REPEATS, not a one-shot ═══
            S_F4: if (settle_cnt >= SETTLE) begin
                arrived_n <= 1'b1; settle_cnt <= 0; state <= S_F5;
            end
            S_F5: if (settle_cnt >= SETTLE) begin
                arrived_n <= 1'b1; settle_cnt <= 0; state <= S_F6;
            end
            S_F6: if (settle_cnt >= SETTLE) begin
                arrived_n <= 1'b1; settle_cnt <= 0; state <= S_CHECK2;
            end
            S_CHECK2: if (settle_cnt >= SETTLE) begin
                if (!fire_e || data_out_e !== 32'd3) err_sticky <= 1'b1;
                state <= S_DONE;
            end
            S_DONE: begin
                // test complete, result latched in err_sticky, stays here
            end
            default: state <= S_CFG;
        endcase
    end
end

reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;

assign LED0_N = ~hb_cnt[23];
assign LED1_N = ~err_sticky;   // active-low: LIT = error

// points.md #529/#531: same real ISSP debug channel proven on the
// branch cell test -- a JTAG-readable pass/fail that doesn't depend
// on whether LED0_N/LED1_N actually reach a physical LED on this
// board (the still-open real question from #528).
debug_issp_probe_v1 DEBUG_PROBE (
    .err_sticky(err_sticky),
    .heartbeat(hb_cnt[23])
);

endmodule
