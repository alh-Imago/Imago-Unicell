// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// host_bridge_sentinel_gather_v1.v — extends #441/#442's own proven
// single-cell JTAG bridge pattern to the FULL v2 sentinel+gather
// mechanism (`top_sentinel_gather_shared_bram_v2.v`'s own 3-chain
// round-robin, real Quartus-confirmed at #437). Real, host-driven
// operation of the mechanism, replacing v2's own self-test FSM
// entirely -- the natural next step per #441/#442's own stated
// "wiring into the full mechanism is separate, later work."
//
// A REAL ARCHITECTURAL FACT this bridge is built around, confirmed
// directly against v2's own RTL before writing this (not assumed):
// the round-robin mechanism does NOT free-run once armed --
// `round_start_pulse` is a direct registered copy of `advance_trigger`
// (NOT derived from `round_complete_pulse`), so a real host must issue
// one ADVANCE per round, not just once at startup. Given real JTAG
// round-trip latency (milliseconds) vastly exceeds the fabric's own
// round completion time (nanoseconds at 25MHz), one ADVANCE per real
// JTAG interaction is naturally safe -- the previous round will have
// long since completed by the time a human/script issues the next
// command -- but this is a REAL, STATED PROTOCOL DISCIPLINE the host
// must respect, not something enforced in hardware.
//
// A SECOND real protocol discipline, matching v2's own self-test FSM's
// real behavior exactly (it preloaded BEFORE ever unfreezing/starting
// rounds too): the host must ICM_LOAD all 4 cells, BRAM_WRITE all
// preload data, and UNFREEZE all 3 chains BEFORE the first ADVANCE.
// The shared BRAM command channel is a simple OR-arbitration between
// this bridge's own host-issued BRAM commands and the mechanism's own
// internal automatic reads (`shared_read_trigger`) -- IDENTICAL in
// structure to v2's own already-proven preload/internal-read muxing,
// not a new, more elaborate scheme. This is safe as long as the host
// follows the stated discipline (preload/configure before starting);
// it is NOT a formally arbitrated, collision-proof design if the host
// issues a BRAM command the same cycle an active round needs its own
// read -- a real, low-probability, stated limitation, not glossed
// over.
//
// SOURCE word (host -> fabric), 91 bits -- SAME LAYOUT as
// `host_bridge_bram_icm_v1.v` (#441), `target` now genuinely used:
//   source[79:0]   data      -- BRAM_WRITE: low 40 bits. ICM_LOAD: full
//                                80-bit SUPER_LATCH value.
//   source[83:80]  addr      -- BRAM address (4 bits).
//   source[85:84]  target    -- ICM_LOAD: 0=H1 1=H2 2=H3 3=QUEUE.
//                                UNFREEZE: 0=H1 1=H2 2=H3 (3 unused).
//                                Ignored by all other opcodes.
//   source[88:86]  opcode    -- 0=NOP 1=BRAM_READ 2=BRAM_WRITE
//                                3=ICM_LOAD 4=UNFREEZE 5=ADVANCE
//   source[89]     cmd_go    -- rising edge = issue
//   source[90]     snap_req  -- rising edge = latch a readback snapshot
//
// PROBE word (fabric -> host), 158 bits:
//   probe[39:0]    bram_rdata
//   probe[40]      bram_read_valid   -- sticky, cleared on next cmd_go
//   probe[41]      bram_write_done   -- sticky
//   probe[42]      icm_load_done     -- sticky
//   probe[43]      unfreeze_done     -- sticky
//   probe[44]      advance_done      -- sticky
//   probe[49:45]   status_core_select -- muxed: the LAST ICM_LOAD
//                                        target's own real readback,
//                                        same confirmation discipline
//                                        as #441's own proven bridge.
//   probe[53:50]   h1_flags  -- {err,safe,results_ready,need_data}
//   probe[57:54]   h2_flags  -- same bit order
//   probe[61:58]   h3_flags  -- same bit order
//   probe[93:62]   q_data_out_n -- QUEUE's own real, live collected
//                                  value -- the actual mechanism
//                                  RESULT, directly readable.
//   probe[125:94]  cmd_count
//   probe[157:126] free_cycle
`default_nettype none
`timescale 1ns / 1ps

module host_bridge_sentinel_gather_v1 #(
    parameter SRC_W       = 91,
    parameter PRB_W       = 158,
    parameter BRAM_ADDR_W = 4,
    parameter BRAM_DATA_W = 40
) (
    input  wire clk,
    input  wire rst,

    // ── Shared BRAM channel ──
    output reg                       bram_cmd_valid,
    output reg                       bram_cmd_op,
    output reg  [BRAM_ADDR_W-1:0]    bram_cmd_addr,
    output reg  [BRAM_DATA_W-1:0]    bram_cmd_wdata,
    input  wire                      bram_rdata_valid,
    input  wire [BRAM_DATA_W-1:0]    bram_rdata,
    input  wire                      bram_write_done,

    // ── ICM (SUPER_LATCH) load -- one shared data bus, 4 target valids ──
    output reg  [79:0]               icm_cfg_data,
    output reg                       icm_cfg_valid_h1,
    output reg                       icm_cfg_valid_h2,
    output reg                       icm_cfg_valid_h3,
    output reg                       icm_cfg_valid_q,

    // ── Per-chain unfreeze, and the mechanism's own per-round advance ──
    output reg                       unfreeze_h1,
    output reg                       unfreeze_h2,
    output reg                       unfreeze_h3,
    output reg                       advance_trigger,

    // ── Status readback ──
    input  wire [4:0]                status_core_select_h1,
    input  wire [4:0]                status_core_select_h2,
    input  wire [4:0]                status_core_select_h3,
    input  wire [4:0]                status_core_select_q,
    input  wire                      h1_need_data, h1_results_ready, h1_safe, h1_err,
    input  wire                      h2_need_data, h2_results_ready, h2_safe, h2_err,
    input  wire                      h3_need_data, h3_results_ready, h3_safe, h3_err,
    input  wire [31:0]               q_data_out_n
);

    wire [SRC_W-1:0] source;
    reg  [PRB_W-1:0] probe;

    issp_sentinel_gather issp_inst (
        .source     (source),
        .probe      (probe),
        .source_clk (clk)
    );

    wire [79:0] src_data     = source[79:0];
    wire [3:0]  src_addr     = source[83:80];
    wire [1:0]  src_target   = source[85:84];
    wire [2:0]  src_opcode   = source[88:86];
    wire        src_cmd_go   = source[89];
    wire        src_snap_req = source[90];

    localparam [2:0] OP_NOP        = 3'd0;
    localparam [2:0] OP_BRAM_READ  = 3'd1;
    localparam [2:0] OP_BRAM_WRITE = 3'd2;
    localparam [2:0] OP_ICM_LOAD   = 3'd3;
    localparam [2:0] OP_UNFREEZE   = 3'd4;
    localparam [2:0] OP_ADVANCE    = 3'd5;

    reg cmd_go_d;
    always @(posedge clk) cmd_go_d <= src_cmd_go;
    wire cmd_go_pulse = src_cmd_go & ~cmd_go_d;

    reg snap_req_d;
    always @(posedge clk) snap_req_d <= src_snap_req;
    wire snap_req_pulse = src_snap_req & ~snap_req_d;

    reg [BRAM_DATA_W-1:0] last_bram_rdata      = {BRAM_DATA_W{1'b0}};
    reg                   last_bram_read_valid = 1'b0;
    reg                   last_bram_write_done = 1'b0;
    reg                   last_icm_load_done   = 1'b0;
    reg                   last_unfreeze_done   = 1'b0;
    reg                   last_advance_done    = 1'b0;
    reg [4:0]             last_core_select     = 5'h0;   // muxed by last ICM_LOAD target
    reg [31:0]            cmd_count            = 32'h0;
    reg [31:0]            free_cycle           = 32'h0;

    always @(posedge clk) begin
        free_cycle <= free_cycle + 32'd1;

        bram_cmd_valid   <= 1'b0;
        icm_cfg_valid_h1 <= 1'b0;
        icm_cfg_valid_h2 <= 1'b0;
        icm_cfg_valid_h3 <= 1'b0;
        icm_cfg_valid_q  <= 1'b0;
        unfreeze_h1      <= 1'b0;
        unfreeze_h2      <= 1'b0;
        unfreeze_h3      <= 1'b0;
        advance_trigger  <= 1'b0;

        if (rst) begin
            bram_cmd_valid        <= 1'b0;
            bram_cmd_op           <= 1'b0;
            bram_cmd_addr         <= {BRAM_ADDR_W{1'b0}};
            bram_cmd_wdata        <= {BRAM_DATA_W{1'b0}};
            icm_cfg_data          <= 80'h0;
            icm_cfg_valid_h1      <= 1'b0;
            icm_cfg_valid_h2      <= 1'b0;
            icm_cfg_valid_h3      <= 1'b0;
            icm_cfg_valid_q       <= 1'b0;
            unfreeze_h1           <= 1'b0;
            unfreeze_h2           <= 1'b0;
            unfreeze_h3           <= 1'b0;
            advance_trigger       <= 1'b0;
            last_bram_rdata       <= {BRAM_DATA_W{1'b0}};
            last_bram_read_valid  <= 1'b0;
            last_bram_write_done  <= 1'b0;
            last_icm_load_done    <= 1'b0;
            last_unfreeze_done    <= 1'b0;
            last_advance_done     <= 1'b0;
            last_core_select      <= 5'h0;
            cmd_count             <= 32'h0;
            free_cycle            <= 32'h0;
        end else begin
            if (cmd_go_pulse) begin
                cmd_count            <= cmd_count + 32'd1;
                last_bram_read_valid <= 1'b0;
                last_bram_write_done <= 1'b0;
                last_icm_load_done   <= 1'b0;
                last_unfreeze_done   <= 1'b0;
                last_advance_done    <= 1'b0;

                case (src_opcode)
                    OP_BRAM_READ: begin
                        bram_cmd_valid <= 1'b1;
                        bram_cmd_op    <= 1'b0;
                        bram_cmd_addr  <= src_addr;
                    end
                    OP_BRAM_WRITE: begin
                        bram_cmd_valid <= 1'b1;
                        bram_cmd_op    <= 1'b1;
                        bram_cmd_addr  <= src_addr;
                        bram_cmd_wdata <= src_data[BRAM_DATA_W-1:0];
                    end
                    OP_ICM_LOAD: begin
                        icm_cfg_data     <= src_data;
                        icm_cfg_valid_h1 <= (src_target == 2'd0);
                        icm_cfg_valid_h2 <= (src_target == 2'd1);
                        icm_cfg_valid_h3 <= (src_target == 2'd2);
                        icm_cfg_valid_q  <= (src_target == 2'd3);
                    end
                    OP_UNFREEZE: begin
                        unfreeze_h1 <= (src_target == 2'd0);
                        unfreeze_h2 <= (src_target == 2'd1);
                        unfreeze_h3 <= (src_target == 2'd2);
                    end
                    OP_ADVANCE: begin
                        advance_trigger <= 1'b1;
                    end
                    default: ; // OP_NOP
                endcase
            end

            // Continuous capture, independent of snap_req timing.
            if (bram_rdata_valid) begin
                last_bram_rdata      <= bram_rdata;
                last_bram_read_valid <= 1'b1;
            end
            if (bram_write_done) last_bram_write_done <= 1'b1;
            if (icm_cfg_valid_h1 || icm_cfg_valid_h2 || icm_cfg_valid_h3 || icm_cfg_valid_q) begin
                last_icm_load_done <= 1'b1;
                last_core_select   <= icm_cfg_valid_h1 ? status_core_select_h1 :
                                       icm_cfg_valid_h2 ? status_core_select_h2 :
                                       icm_cfg_valid_h3 ? status_core_select_h3 :
                                                           status_core_select_q;
            end
            if (unfreeze_h1 || unfreeze_h2 || unfreeze_h3) last_unfreeze_done <= 1'b1;
            if (advance_trigger) last_advance_done <= 1'b1;

            if (snap_req_pulse) begin
                probe <= {free_cycle, cmd_count, q_data_out_n,
                          {h3_err, h3_safe, h3_results_ready, h3_need_data},
                          {h2_err, h2_safe, h2_results_ready, h2_need_data},
                          {h1_err, h1_safe, h1_results_ready, h1_need_data},
                          last_core_select,
                          last_advance_done, last_unfreeze_done, last_icm_load_done,
                          last_bram_write_done, last_bram_read_valid, last_bram_rdata};
            end
        end
    end

endmodule
