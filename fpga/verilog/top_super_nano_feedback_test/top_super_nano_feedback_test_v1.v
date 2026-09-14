// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_super_nano_feedback_test_v1.v — first real Quartus attempt for
// nano's newly-exposed hold_in/fb_internal_in ports through the super
// carrier shell (points.md #522) -- sim-verified clean (tb_super_
// nano_feedback_v1.v) but never yet touched real silicon. Through the
// REAL shell (unicell_super_v1.v), not standalone -- this is genuinely
// only reachable via the shell's own core_config, so testing it any
// other way wouldn't reflect real deployed use.
//
// THE REAL SHAPE, exactly matching tb_super_nano_feedback_v1.v's own
// three-pass sequence: (1) hold=0,fb=0, load threshold 0xAAAA0000 via
// a real external arrival; (2) hold=1,fb=0, kick with one external
// value (0x11110000) -- must compute NOR(threshold,kick)=0x4444FFFF;
// (3) hold=1,fb=1 -- starts the real internal feedback loop. Confirmed
// in simulation that this reconfigure resets out_buffer, so the loop
// settles into the SAME real 0x00000000<->0x5555FFFF oscillation
// tb_super_nano_feedback_v1.v already proved (NOT the standalone
// module's own 0x4444FFFF<->0x11110000) -- checked here for exactly
// that real, honest sequence, at whichever phase this FSM's own
// settle timing happens to land on first (confirmed directly via
// simulation, not assumed).
`default_nettype none
`timescale 1ns / 1ps

module top_super_nano_feedback_test_v1 (
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
reg  [79:0] cfg_data  = 0;
reg  [31:0] data_in_n = 0;
reg         arrived_n = 0;

wire [31:0] data_out_n;

unicell_super_v1 DUT (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(data_out_n), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

function [79:0] pack(input [4:0] sel, input [41:0] core_cfg);
    pack = {13'b0, 20'h0, core_cfg, sel};
endfunction

localparam [9:0] TOPO_NOR = 10'h004;

// core_config for nano: topology[9:0], ready[10] (RTL forces this to 1
// unconditionally, included only for bit alignment), routing_mask
// [16:11], cardinal_edge[22:17], hold_in[23], fb_internal_in[24].
function [41:0] nano_cfg(input hold, input fb_internal);
    nano_cfg = {17'h0, fb_internal, hold, 6'h0, 6'h0, 1'h0, TOPO_NOR};
endfunction

localparam [4:0] SETTLE = 5'd16;
localparam [4:0]
    S_CFG1=0, S_SEED=1, S_WAIT1=2,
    S_CFG2=3, S_KICK=4, S_WAIT2=5, S_CHECK_KICK=6,
    S_CFG3=7, S_WATCH=8, S_DONE=9;

reg [4:0] state = S_CFG1;
reg [4:0] settle_cnt = 0;
reg       err_sticky = 1'b0;
reg       saw_zero = 1'b0, saw_alt = 1'b0;
reg [5:0] osc_watch_cnt = 0;

always @(posedge clk) begin
    if (rst) begin
        state <= S_CFG1;
        cfg_valid <= 0; cfg_data <= 80'h0;
        arrived_n <= 0; data_in_n <= 0;
        settle_cnt <= 0;
        err_sticky <= 1'b0;
        saw_zero <= 1'b0; saw_alt <= 1'b0; osc_watch_cnt <= 0;
    end else begin
        cfg_valid <= 1'b0;
        arrived_n <= 1'b0;
        settle_cnt <= settle_cnt + 5'd1;

        case (state)
            // ═══ Pass 1: hold=0, fb=0 -- load threshold ═══
            S_CFG1: begin
                cfg_valid <= 1'b1; cfg_data <= pack(5'd0, nano_cfg(1'b0, 1'b0));
                settle_cnt <= 0; state <= S_SEED;
            end
            S_SEED: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'hAAAA0000; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_WAIT1;
            end
            S_WAIT1: if (settle_cnt >= SETTLE) begin
                settle_cnt <= 0; state <= S_CFG2;
            end
            // ═══ Pass 2: hold=1, fb=0 -- kick, confirming threshold
            // genuinely survived the reconfigure ═══
            S_CFG2: begin
                cfg_valid <= 1'b1; cfg_data <= pack(5'd0, nano_cfg(1'b1, 1'b0));
                settle_cnt <= 0; state <= S_KICK;
            end
            S_KICK: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'h11110000; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_WAIT2;
            end
            S_WAIT2: if (settle_cnt >= SETTLE) begin
                settle_cnt <= 0; state <= S_CHECK_KICK;
            end
            S_CHECK_KICK: if (settle_cnt >= SETTLE) begin
                if (data_out_n !== 32'h4444FFFF) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_CFG3;
            end
            // ═══ Pass 3: hold=1, fb=1 -- real internal feedback loop.
            // Reconfigure resets out_buffer (confirmed in sim), so this
            // genuinely, correctly settles at 0<->0x5555FFFF, not the
            // standalone module's own 0x4444FFFF<->0x11110000. Checked
            // robustly (both real values seen across a real window),
            // not by exact per-cycle phase -- the oscillation's own
            // exact phase alignment depends on this FSM's own
            // transition-cycle overhead, not a meaningful hardware
            // property; the real claim is that BOTH values genuinely
            // appear, proving a real, correctly-computed 2-value
            // oscillation, not a stuck or corrupted result. ═══
            S_CFG3: begin
                cfg_valid <= 1'b1; cfg_data <= pack(5'd0, nano_cfg(1'b1, 1'b1));
                settle_cnt <= 0; saw_zero <= 1'b0; saw_alt <= 1'b0;
                osc_watch_cnt <= 0; state <= S_WATCH;
            end
            S_WATCH: begin
                if (data_out_n == 32'h00000000) saw_zero <= 1'b1;
                if (data_out_n == 32'h5555FFFF) saw_alt  <= 1'b1;
                osc_watch_cnt <= osc_watch_cnt + 6'd1;
                if (osc_watch_cnt >= 6'd32) begin
                    if (!saw_zero || !saw_alt) err_sticky <= 1'b1;
                    state <= S_DONE;
                end
            end
            S_DONE: begin
                // test complete, result latched in err_sticky, stays here
            end
            default: state <= S_CFG1;
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
