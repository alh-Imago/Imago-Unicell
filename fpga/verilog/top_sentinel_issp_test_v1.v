// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_sentinel_issp_test_v1.v — points.md #288 continuation: minimal
// real-hardware wrapper around `sentinel_issp_bridge_v1.v` for
// standalone testing over real JTAG, before this gets folded into the
// full tree system. NOT YET BUILT — prepared project.
//
// No self-test FSM here, deliberately — unlike every other top-level
// in this project, this one is driven LIVE from the host side via
// `sentinel_issp.tcl` (feed_pulse/collect_pulse/out_wrap_pulse/host_
// unfreeze_pulse/set-chain_length commands, snapshot readback), not a
// fixed on-chip sequence. LED0 is a simple clock-alive heartbeat,
// independent confirmation the fabric is running even before the JTAG
// channel itself is exercised (the Tcl script's own "channel-alive"
// check is the real confirmation of the JTAG path specifically).
`default_nettype none
`timescale 1ns / 1ps

module top_sentinel_issp_test_v1 (
    input  wire CLK_100M,
    output wire LED0_N
);

// ── Clock/reset — same convention as every other project here ──────────
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

sentinel_issp_bridge_v1 #(.DIFF_WIDTH(16)) BRIDGE (
    .clk(clk), .rst(rst)
);

reg [23:0] heartbeat = 0;
always @(posedge clk) heartbeat <= heartbeat + 24'h1;
assign LED0_N = ~heartbeat[21];   // steady heartbeat while alive

endmodule
