// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// sentinel_issp_bridge_v1.v — JTAG host bridge for sentinel_counter_v1.v,
// via In-System Sources & Probes (altsource_probe).
//
// Alan's own ask, directly: a way to READ the sentinel's status/error
// state over the real host connection (the USB-Blaster carrying JTAG),
// same discipline as this project's existing `unicell_issp_bridge.v`
// (`pcie/unicell_issp_bridge.v`) -- same 66-bit SOURCE / 113-bit PROBE
// width and cmd_go/snap_req protocol shape, deliberately reused for
// consistency (and so this bridge can reuse the SAME simulation stub,
// `tb_stub_issp_sim_only.v`, without needing a new one).
//
// NOT a modification of the existing bridge -- that one is wired to
// the OLD full-cell architecture's own debug signals (cell-0 latch
// view, cardinal bridge sticky captures) and stays untouched. This is
// a separate, purpose-built bridge for the sentinel system specifically
// (points.md #279/#281/#287), wired to `sentinel_counter_v1.v` directly.
//
// CRITICAL — GENERATE THE IP CORRECTLY (same instructions as the
// existing bridge's own header): IP Catalog -> In-System Sources and
// Probes, name it `issp` -- Source width = 66, Probe width = 113,
// ENABLE "Source Clock" (connect to the real fabric clock), ENABLE the
// source synchronization registers. `issp.qsys` is deliberately NOT
// committed to git (per `docs/HARDWARE_SETUP.md`) -- regenerate locally
// before any real Quartus build. `tb_stub_issp_sim_only.v` stands in
// during iverilog simulation.
//
// SOURCE word (host -> fabric), same shape as the existing bridge:
//   source[31:0]   cpu_data   payload -- ONLY meaningful for opcode 5
//                             (set chain_length): the new value
//   source[63:32]  cpu_bus    command word, opcode in [7:0]:
//                               0 = nop
//                               1 = inject one feed_pulse
//                               2 = inject one collect_pulse
//                               3 = inject one out_wrap_pulse
//                               4 = inject one host_unfreeze_pulse
//                               5 = set chain_length := cpu_data
//   source[64]     cmd_go     rising edge = inject the above command
//                             (1-cycle pulse of whichever signal)
//   source[65]     snap_req   rising edge = latch a readback snapshot
//
// PROBE word (fabric -> host), all from the last snapshot:
//   probe[31:0]    snap_cycle        free-running debug cycle counter
//                                    (channel-alive check, same
//                                    convention as the existing bridge)
//   probe[40:32]   snap_flags        {out_frozen, err_overflow,
//                                     err_negative, err_flag,
//                                     freeze_in, freeze_out,
//                                     safe_to_intervene,
//                                     results_ready_flag,
//                                     need_data_flag} (9 bits, [0]=LSB)
//   probe[72:41]   snap_diff         sentinel_counter_v1's own signed
//                                    diff value (32 bits, sign-extended)
//   probe[88:73]   snap_chain_length currently configured chain_length
//   probe[104:89]  snap_cmd_count    total commands injected since
//                                    reset -- confirms the command
//                                    channel is genuinely working, same
//                                    spirit as the existing bridge's
//                                    own out_count
//   probe[112:105] reserved
`default_nettype none
`timescale 1ns / 1ps

module sentinel_issp_bridge_v1 #(
    parameter SRC_W      = 66,
    parameter PRB_W      = 113,
    parameter DIFF_WIDTH = 16
) (
    input  wire clk,
    input  wire rst
);

    // ── ISSP source/probe nets ────────────────────────────────────────
    wire [SRC_W-1:0] source;
    reg  [PRB_W-1:0] probe;

    wire [31:0] src_cpu_data = source[31:0];
    wire [31:0] src_cpu_bus  = source[63:32];
    wire        src_cmd_go   = source[64];
    wire        src_snap_req = source[65];

    // ── Command injection: edge-detect cmd_go -> 1-cycle pulse of
    // whichever sentinel input the opcode selects ──────────────────────
    reg cmd_go_d;
    always @(posedge clk) cmd_go_d <= src_cmd_go;
    wire cmd_go_pulse = src_cmd_go & ~cmd_go_d;

    wire [7:0] opcode = src_cpu_bus[7:0];

    wire feed_pulse          = cmd_go_pulse && (opcode == 8'd1);
    wire collect_pulse       = cmd_go_pulse && (opcode == 8'd2);
    wire out_wrap_pulse      = cmd_go_pulse && (opcode == 8'd3);
    wire host_unfreeze_pulse = cmd_go_pulse && (opcode == 8'd4);
    wire set_chain_length    = cmd_go_pulse && (opcode == 8'd5);

    reg [DIFF_WIDTH-1:0] chain_length_reg = {DIFF_WIDTH{1'b0}};
    reg [15:0]           cmd_count        = 16'h0;

    always @(posedge clk) begin
        if (rst) begin
            chain_length_reg <= {DIFF_WIDTH{1'b0}};
            cmd_count         <= 16'h0;
        end else begin
            if (set_chain_length) chain_length_reg <= src_cpu_data[DIFF_WIDTH-1:0];
            if (cmd_go_pulse)     cmd_count         <= cmd_count + 16'h1;
        end
    end

    // ── The real sentinel core ──────────────────────────────────────────
    // NOTE: uses sentinel_counter_v2.v, NOT v1 -- a real Quartus build
    // confirmed v1's hierarchical-reference debug signals (SENTINEL.
    // out_frozen, SENTINEL.err_negative, SENTINEL.err_overflow) are
    // NOT synthesizable (`Error (10207): can't resolve reference to
    // object "out_frozen"` -- a universal EDA limitation, hierarchical
    // references only work in simulation). v2 exposes the two
    // individual error causes as real ports instead. `out_frozen`
    // itself needed no new port -- it's already exactly `need_data_
    // flag` (a genuine alias in the original design), used directly
    // below instead of a separate reference.
    wire freeze_out, freeze_in, need_data_flag, results_ready_flag,
         safe_to_intervene, err_flag, err_negative_flag, err_overflow_flag;
    wire signed [DIFF_WIDTH:0] diff_out;

    sentinel_counter_v2 #(.DIFF_WIDTH(DIFF_WIDTH)) SENTINEL (
        .clk(clk), .rst(rst),
        .feed_pulse(feed_pulse), .collect_pulse(collect_pulse),
        .chain_length(chain_length_reg),
        .out_wrap_pulse(out_wrap_pulse), .host_unfreeze_pulse(host_unfreeze_pulse),
        .freeze_out(freeze_out), .freeze_in(freeze_in),
        .need_data_flag(need_data_flag), .results_ready_flag(results_ready_flag),
        .safe_to_intervene(safe_to_intervene), .err_flag(err_flag),
        .err_negative_flag(err_negative_flag), .err_overflow_flag(err_overflow_flag),
        .diff_out(diff_out)
    );

    // out_frozen is exactly need_data_flag (a genuine alias in the
    // sentinel's own design) -- no separate reference needed.
    wire out_frozen_dbg   = need_data_flag;
    wire err_negative_dbg = err_negative_flag;
    wire err_overflow_dbg = err_overflow_flag;

    // ── Snapshot: freeze readback into a static word on snap_req rising
    // edge -- identical protocol to the existing bridge. ──
    reg snap_d;
    always @(posedge clk) snap_d <= src_snap_req;
    wire snap_pulse = src_snap_req & ~snap_d;

    (* preserve *) reg [31:0]              snap_cycle = 32'h0;
    (* preserve *) reg [8:0]               snap_flags = 9'h0;
    (* preserve *) reg signed [31:0]       snap_diff  = 32'h0;
    (* preserve *) reg [DIFF_WIDTH-1:0]    snap_chain_length = {DIFF_WIDTH{1'b0}};
    (* preserve *) reg [15:0]              snap_cmd_count = 16'h0;

    reg [31:0] free_cycle = 32'h0;
    always @(posedge clk) free_cycle <= free_cycle + 32'h1;

    always @(posedge clk) if (snap_pulse) begin
        snap_cycle        <= free_cycle;
        snap_flags        <= {out_frozen_dbg, err_overflow_dbg, err_negative_dbg,
                               err_flag, freeze_in, freeze_out, safe_to_intervene,
                               results_ready_flag, need_data_flag};
        snap_diff         <= {{(31-DIFF_WIDTH){diff_out[DIFF_WIDTH]}}, diff_out};
        snap_chain_length <= chain_length_reg;
        snap_cmd_count    <= cmd_count;
    end

    always @(*) probe = { 8'h0,              // [112:105] reserved
                          snap_cmd_count,     // [104:89]
                          snap_chain_length,  // [88:73]
                          snap_diff,          // [72:41]
                          snap_flags,         // [40:32]
                          snap_cycle };       // [31:0]

    // ── In-System Sources & Probes IP instance — see header for real
    // generation instructions. ──
    issp issp_inst (
        .source     (source),
        .probe      (probe),
        .source_clk (clk)
    );

endmodule
