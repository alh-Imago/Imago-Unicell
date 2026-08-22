// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// host_bridge_bram_icm_v1.v — points.md #430's own queue item 2: the
// first real JTAG bridge covering BOTH capabilities Alan asked for --
// real BRAM read/write, and real ICM (SUPER_LATCH) loading into the
// substrate. Built via In-System Sources & Probes (altsource_probe),
// same proven protocol shape as `sentinel_issp_bridge_v1.v` (#279/#281,
// real hardware-confirmed at #291) -- a wide SOURCE register with an
// opcode + cmd_go rising-edge injection, and a PROBE register latched
// on snap_req, deliberately reused rather than reinvented.
//
// REAL, DELIBERATE SCOPE (per this project's own "smallest
// reproducible case first" discipline): this bridge drives ONE shared
// `bram_controller_v1.v` instance and ONE `unicell_super_v1.v` instance
// directly -- proving the two raw CHANNELS work on real silicon in
// isolation, before wiring a host bridge into the full 3-chain v2
// sentinel+gather mechanism (`top_sentinel_gather_shared_bram_v2.v`),
// which is separate, later, not-yet-scoped integration work. This is
// the FIRST real host-driven (not self-test-FSM-driven) hardware in
// this whole project line.
//
// SOURCE word (host -> fabric), 91 bits:
//   source[79:0]   data      -- write payload. BRAM_WRITE uses the low
//                                40 bits (bram_controller_v1's own real
//                                DATA_WIDTH); ICM_LOAD uses the full 80
//                                bits (the real SUPER_LATCH width,
//                                confirmed against unicell_super_v1.v's
//                                own cfg_data port).
//   source[83:80]  addr      -- BRAM address (4 bits, matching the
//                                shared BRAM's own real ADDR_WIDTH=4
//                                convention already proven in v2).
//   source[85:84]  target    -- reserved for a future multi-cell
//                                bring-up (0 = the one cell this bridge
//                                drives; other values inert for now,
//                                real headroom, not dead weight -- see
//                                header note below).
//   source[88:86]  opcode    -- 0=NOP 1=BRAM_READ 2=BRAM_WRITE
//                                3=ICM_LOAD
//   source[89]     cmd_go    -- rising edge = issue the above command
//                                (1-cycle pulse of whichever signal)
//   source[90]     snap_req  -- rising edge = latch a readback snapshot
//
// PROBE word (fabric -> host), 107 bits:
//   probe[39:0]    bram_rdata       -- last real BRAM read result
//   probe[40]      bram_read_valid  -- sticky: set when a READ's result
//                                       lands, cleared on the NEXT
//                                       cmd_go (not just on snap_req --
//                                       a real command should never
//                                       silently keep an old result
//                                       looking current)
//   probe[41]      bram_write_done  -- sticky, same discipline
//   probe[42]      icm_load_done    -- sticky: set the cycle
//                                       `cfg_valid` was genuinely
//                                       pulsed for ICM_LOAD. This IS a
//                                       real, accurate confirmation,
//                                       not a guess -- confirmed
//                                       directly against
//                                       `accumulator_cell_v1.v`'s (and
//                                       every other core's) own RTL:
//                                       config application is
//                                       synchronous and immediate on
//                                       `cfg_valid`, with no separate
//                                       internal "done" signal to wait
//                                       for.
//   probe[47:43]   status_core_select -- direct readback of the
//                                       driven cell's own real
//                                       `status_core_select` (#317's
//                                       own debug tap) -- lets the host
//                                       directly confirm an ICM_LOAD's
//                                       own `core_select` field
//                                       genuinely landed, not assumed.
//   probe[79:48]   cmd_count        -- 32-bit free-running count of
//                                       commands issued since reset --
//                                       confirms the command channel is
//                                       genuinely alive, same
//                                       convention as the existing
//                                       sentinel bridge's own cmd_count.
//   probe[111:80]  free_cycle       -- 32-bit free-running debug cycle
//                                       counter, same channel-alive
//                                       convention as every ISSP bridge
//                                       in this project so far.
`default_nettype none
`timescale 1ns / 1ps

module host_bridge_bram_icm_v1 #(
    parameter SRC_W       = 91,
    parameter PRB_W       = 112,
    parameter BRAM_ADDR_W = 4,
    parameter BRAM_DATA_W = 40
) (
    input  wire clk,
    input  wire rst,

    // ── Shared BRAM channel (bram_controller_v1.v's own real interface) ──
    output reg                       bram_cmd_valid,
    output reg                       bram_cmd_op,     // 0=READ 1=WRITE
    output reg  [BRAM_ADDR_W-1:0]    bram_cmd_addr,
    output reg  [BRAM_DATA_W-1:0]    bram_cmd_wdata,
    input  wire                      bram_rdata_valid,
    input  wire [BRAM_DATA_W-1:0]    bram_rdata,
    input  wire                      bram_write_done,

    // ── One driven cell's own real ICM (cfg_valid/cfg_data) port ──
    output reg                       icm_cfg_valid,
    output reg  [79:0]               icm_cfg_data,
    input  wire [4:0]                icm_status_core_select
);

    // ── ISSP source/probe nets ────────────────────────────────────────
    wire [SRC_W-1:0] source;
    reg  [PRB_W-1:0] probe;

    // ── The real ISSP IP instance -- must be generated locally per this
    // file's own header instructions before any real Quartus build.
    // `issp_bram_icm` is a simulation-only stand-in with matching port
    // widths (`tb_stub_issp_bram_icm_v1.v`) for iverilog elaboration. ──
    issp_bram_icm issp_inst (
        .source     (source),
        .probe      (probe),
        .source_clk (clk)
    );

    wire [79:0] src_data     = source[79:0];
    wire [3:0]  src_addr     = source[83:80];
    wire [1:0]  src_target   = source[85:84];   // reserved, unused this build
    wire [2:0]  src_opcode   = source[88:86];
    wire        src_cmd_go   = source[89];
    wire        src_snap_req = source[90];

    localparam [2:0] OP_NOP       = 3'd0;
    localparam [2:0] OP_BRAM_READ  = 3'd1;
    localparam [2:0] OP_BRAM_WRITE = 3'd2;
    localparam [2:0] OP_ICM_LOAD   = 3'd3;

    // ── Command injection: edge-detect cmd_go -> 1-cycle pulse of
    // whichever channel the opcode selects. Same discipline as
    // `sentinel_issp_bridge_v1.v`'s own proven `cmd_go_pulse` pattern. ──
    reg cmd_go_d;
    always @(posedge clk) cmd_go_d <= src_cmd_go;
    wire cmd_go_pulse = src_cmd_go & ~cmd_go_d;

    reg snap_req_d;
    always @(posedge clk) snap_req_d <= src_snap_req;
    wire snap_req_pulse = src_snap_req & ~snap_req_d;

    // ── Internal, continuously-live result state -- captured the
    // instant a real result lands, independent of when the host next
    // polls via snap_req (same "capture continuously, snapshot on
    // demand" pattern as the sentinel bridge; a single-cycle fabric
    // pulse would almost certainly be missed if the host could only
    // observe it exactly at snap_req time). ──
    reg [BRAM_DATA_W-1:0] last_bram_rdata     = {BRAM_DATA_W{1'b0}};
    reg                   last_bram_read_valid = 1'b0;
    reg                   last_bram_write_done = 1'b0;
    reg                   last_icm_load_done   = 1'b0;
    reg [31:0]            cmd_count            = 32'h0;
    reg [31:0]            free_cycle           = 32'h0;

    always @(posedge clk) begin
        free_cycle <= free_cycle + 32'd1;

        // Defaults -- one-cycle pulses on the driven interfaces.
        bram_cmd_valid <= 1'b0;
        icm_cfg_valid  <= 1'b0;

        if (rst) begin
            bram_cmd_valid       <= 1'b0;
            bram_cmd_op          <= 1'b0;
            bram_cmd_addr        <= {BRAM_ADDR_W{1'b0}};
            bram_cmd_wdata       <= {BRAM_DATA_W{1'b0}};
            icm_cfg_valid        <= 1'b0;
            icm_cfg_data         <= 80'h0;
            last_bram_rdata      <= {BRAM_DATA_W{1'b0}};
            last_bram_read_valid <= 1'b0;
            last_bram_write_done <= 1'b0;
            last_icm_load_done   <= 1'b0;
            cmd_count            <= 32'h0;
            free_cycle           <= 32'h0;
        end else begin
            // A NEW command clears all three sticky result flags first
            // -- a real command should never leave a stale result
            // looking current to the host.
            if (cmd_go_pulse) begin
                cmd_count            <= cmd_count + 32'd1;
                last_bram_read_valid <= 1'b0;
                last_bram_write_done <= 1'b0;
                last_icm_load_done   <= 1'b0;

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
                        icm_cfg_valid <= 1'b1;
                        icm_cfg_data  <= src_data;
                    end
                    default: ; // OP_NOP -- no channel driven
                endcase
            end

            // Continuous capture -- independent of cmd_go/snap_req timing.
            if (bram_rdata_valid) begin
                last_bram_rdata      <= bram_rdata;
                last_bram_read_valid <= 1'b1;
            end
            if (bram_write_done) last_bram_write_done <= 1'b1;
            if (icm_cfg_valid)   last_icm_load_done   <= 1'b1;   // fires the
                // SAME cycle icm_cfg_valid is asserted -- a real, accurate
                // confirmation per this file's own header note, not a guess.

            // Snapshot the probe on snap_req -- an atomic, consistent
            // view even though internal state keeps changing between
            // polls, same discipline as `sentinel_issp_bridge_v1.v`.
            if (snap_req_pulse) begin
                probe <= {free_cycle, cmd_count, icm_status_core_select,
                          last_icm_load_done, last_bram_write_done,
                          last_bram_read_valid, last_bram_rdata};
            end
        end
    end

endmodule
