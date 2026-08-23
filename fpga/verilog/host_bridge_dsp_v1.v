// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// host_bridge_dsp_v1.v — points.md #466/#467's own queue: the first
// real JTAG bridge for a DSP wrapper. Same proven ISSP protocol shape
// as `host_bridge_bram_icm_v1.v` (#441/#442, real-hardware-confirmed
// first try) -- a SOURCE register with an opcode + cmd_go rising-edge
// injection, a PROBE register latched on snap_req.
//
// REAL, DELIBERATE SCOPE, per this project's own "smallest
// reproducible case first" discipline: this bridge talks DIRECTLY to
// one `dsp_arith_wrapper_v1.v` instance's own cardinal-style ports --
// it does NOT stage through real RAM cells first, even though #453's
// own full architecture eventually wants the wrapper sitting between
// two ordinary RAM-configured `unicell_super_v1` instances. That real
// staging layer is separate, later work -- the real, immediate goal
// here is proving the DSP hard IP itself computes correctly on real
// silicon, driven by a real host, before adding the extra fabric-
// staging layer on top of an unconfirmed foundation. Matches this
// session's own exact precedent: the single-cell BRAM/ICM bridge
// proved its two raw channels in isolation before the full 3-chain
// mechanism was ever attempted.
//
// SOURCE word (host -> fabric), 37 bits:
//   source[31:0]   data      -- LOAD_A/LOAD_B: the real 32-bit operand.
//                                WD_SET: low 16 bits are the real
//                                watchdog threshold.
//   source[34:32]  opcode    -- 0=NOP 1=LOAD_A 2=LOAD_B 3=WD_SET 4=ACK
//   source[35]     cmd_go    -- rising edge = issue (1-cycle pulse)
//   source[36]     snap_req  -- rising edge = latch a readback snapshot
//
// PROBE word (fabric -> host), 114 bits:
//   probe[31:0]    result       -- the wrapper's own real `data_out`,
//                                   captured continuously, live.
//   probe[32]      fire         -- the wrapper's own real, LIVE `fire`
//                                   level signal (not sticky) -- stays
//                                   high exactly as long as the real
//                                   wrapper itself holds a ready,
//                                   unacked result. The host polls
//                                   this directly, reads `result`, then
//                                   issues ACK to consume it and let
//                                   the wrapper re-arm -- matching the
//                                   wrapper's own real semantics
//                                   exactly, no extra sticky layer
//                                   needed on top.
//   probe[33]      wd_timeout_err -- the real watchdog's own live
//                                   timeout flag, direct passthrough.
//   probe[49:34]   wd_count_out -- the real watchdog's own live count,
//                                   for debug.
//   probe[81:50]   cmd_count    -- 32-bit free-running command count,
//                                   same channel-alive convention as
//                                   every ISSP bridge in this project.
//   probe[113:82]  free_cycle   -- 32-bit free-running debug cycle
//                                   counter, same convention.
`default_nettype none
`timescale 1ns / 1ps

module host_bridge_dsp_v1 #(
    parameter SRC_W          = 37,
    parameter PRB_W          = 114,
    parameter WATCHDOG_WIDTH = 16
) (
    input  wire clk,
    input  wire rst,

    // ── The one driven DSP wrapper's own real cardinal-style ports ──
    output reg  [31:0]               dsp_data_in_a,
    output reg                       dsp_arrived_a,
    input  wire                      dsp_ack_out_a,

    output reg  [31:0]               dsp_data_in_b,
    output reg                       dsp_arrived_b,
    input  wire                      dsp_ack_out_b,

    input  wire [31:0]               dsp_data_out,
    input  wire                      dsp_fire,
    output reg                       dsp_ack_in,

    output reg                       dsp_wd_cfg_valid,
    output reg  [WATCHDOG_WIDTH-1:0] dsp_wd_cfg_threshold,
    input  wire                      dsp_wd_timeout_err,
    input  wire [WATCHDOG_WIDTH-1:0] dsp_wd_count_out
);

    wire [SRC_W-1:0] source;
    reg  [PRB_W-1:0] probe;

    // ── The real ISSP IP instance -- must be generated locally per
    // this file's own header instructions before any real Quartus
    // build. `issp_dsp` is a simulation-only stand-in with matching
    // port widths (`tb_stub_issp_dsp_v1.v`) for iverilog elaboration. ──
    issp_dsp issp_inst (
        .source     (source),
        .probe      (probe),
        .source_clk (clk)
    );

    wire [31:0] src_data     = source[31:0];
    wire [2:0]  src_opcode   = source[34:32];
    wire        src_cmd_go   = source[35];
    wire        src_snap_req = source[36];

    localparam [2:0] OP_NOP    = 3'd0;
    localparam [2:0] OP_LOAD_A = 3'd1;
    localparam [2:0] OP_LOAD_B = 3'd2;
    localparam [2:0] OP_WD_SET = 3'd3;
    localparam [2:0] OP_ACK    = 3'd4;

    reg cmd_go_d;
    always @(posedge clk) cmd_go_d <= src_cmd_go;
    wire cmd_go_pulse = src_cmd_go & ~cmd_go_d;

    reg snap_req_d;
    always @(posedge clk) snap_req_d <= src_snap_req;
    wire snap_req_pulse = src_snap_req & ~snap_req_d;

    reg [31:0] cmd_count  = 32'h0;
    reg [31:0] free_cycle = 32'h0;

    always @(posedge clk) begin
        free_cycle <= free_cycle + 32'd1;

        // Defaults -- one-cycle pulses on the driven interfaces.
        dsp_arrived_a    <= 1'b0;
        dsp_arrived_b    <= 1'b0;
        dsp_ack_in       <= 1'b0;
        dsp_wd_cfg_valid <= 1'b0;

        if (rst) begin
            dsp_data_in_a         <= 32'h0;
            dsp_arrived_a         <= 1'b0;
            dsp_data_in_b         <= 32'h0;
            dsp_arrived_b         <= 1'b0;
            dsp_ack_in            <= 1'b0;
            dsp_wd_cfg_valid      <= 1'b0;
            dsp_wd_cfg_threshold  <= {WATCHDOG_WIDTH{1'b0}};
            cmd_count             <= 32'h0;
            free_cycle            <= 32'h0;
        end else begin
            if (cmd_go_pulse) begin
                cmd_count <= cmd_count + 32'd1;

                case (src_opcode)
                    OP_LOAD_A: begin
                        dsp_data_in_a <= src_data;
                        dsp_arrived_a <= 1'b1;
                    end
                    OP_LOAD_B: begin
                        dsp_data_in_b <= src_data;
                        dsp_arrived_b <= 1'b1;
                    end
                    OP_WD_SET: begin
                        dsp_wd_cfg_threshold <= src_data[WATCHDOG_WIDTH-1:0];
                        dsp_wd_cfg_valid     <= 1'b1;
                    end
                    OP_ACK: begin
                        dsp_ack_in <= 1'b1;
                    end
                    default: ; // OP_NOP
                endcase
            end

            // Snapshot the probe on snap_req -- an atomic, consistent
            // view even though the wrapper's own real signals keep
            // changing between polls, same discipline as every other
            // ISSP bridge in this project. `result`/`fire`/
            // `wd_timeout_err`/`wd_count_out` are all real, LIVE
            // signals here (not internally latched first) -- the
            // wrapper itself already holds `fire`/`data_out` stable
            // until acked, so there's no risk of missing a single-
            // cycle pulse the way `#441`'s own BRAM read-valid pulse
            // needed continuous capture for.
            if (snap_req_pulse) begin
                probe <= {free_cycle, cmd_count, dsp_wd_count_out,
                          dsp_wd_timeout_err, dsp_fire, dsp_data_out};
            end
        end
    end

endmodule
