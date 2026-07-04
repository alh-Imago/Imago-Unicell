// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// zone_watchdog_v3.v — the backpressure design from this session, built as RTL
// (not fabric cells) per Alan's call: putting the watch/level/command-cell
// triad in-fabric would cost 8 cells/channel x 2 channels = 16 cells PER ZONE
// just for I/O plumbing (128 cells across 16 zones -- ~29% of the 448-cell
// budget spent before a single model runs), and the only escape from that
// cost inside the fabric (one shared, time-multiplexed instance) trades it
// for a 32x serialization penalty that defeats the parallel design outright.
// RTL sidesteps the tradeoff instead of picking a side of it: ALMs are a
// different resource pool from the 448-cell budget, so one independent,
// full-speed instance per zone costs the fabric nothing and needs no sharing.
//
// This ALSO resolves the per-cell CMD_FREEZE/CMD_RELEASE targeting problem
// (the 3-stage command-emit pipeline extension that was mid-build): since
// this drives its OWN zone's cmd_valid line directly, FREEZE/RELEASE scope to
// that zone by construction -- no in-cell address-lane targeting needed. Zone
// granularity, not per-cell -- matches "at least per-zone" from this session,
// not the finer (harder, cell-internal) per-cell case.
//
// Level = write_count - read_count, ordinary 16-bit RTL arithmetic (no NOR-
// tile comparator needed here at all -- that 518-cell INT32_LT_U from the
// earlier VM prototype was the right proof-of-concept but the wrong scale;
// this replaces it for the real build). Genuine hysteresis: HIGH freezes,
// LOW releases, with a real stateful latch this time (the earlier VM
// prototype proved only the combinational "raw" trigger signals, explicitly
// flagged as not-yet-stateful) -- FREEZE/RELEASE emit as ONE-SHOT pulses on
// the transition edge only, not held continuously.
`default_nettype none
`timescale 1ns / 1ps

module zone_watchdog_v3 #(
    parameter [15:0] HIGH = 16'd12,   // freeze when level >= HIGH
    parameter [15:0] LOW  = 16'd4,    // release when level <= LOW
    parameter [7:0]  OP_CMD_FREEZE  = 8'd5,
    parameter [7:0]  OP_CMD_RELEASE = 8'd6,
    parameter [10:0] AUTH = 11'h0    // this zone's cells' auth_mask (0 = open/
                                     // never-booted cells only; a real
                                     // deployment sets this to match whatever
                                     // CMD_BOOT_COMMIT gave the target zone)
) (
    input  wire        clk,
    input  wire        rst,

    input  wire [15:0] write_count,
    input  wire [15:0] read_count,

    // Drives this zone's OWN cmd_valid line (see top-level integration note:
    // each zone needs its own cmd_valid qualifier for this to actually scope
    // to one zone -- a shared/broadcast cmd_valid across all zones, as in
    // top_card_2zone_v3.v today, would freeze every zone at once).
    output reg  [31:0] cmd_bus,
    output reg  [31:0] cmd_data,
    output reg         cmd_valid,

    output wire        frozen         // debug/status: current hysteresis state
);

    wire [15:0] level = write_count - read_count; // unsigned wraparound is fine
                                                    // and correct here, same as
                                                    // the VM prototype's sweep
                                                    // (a stepper never legitimately
                                                    // runs ahead of the writer in
                                                    // normal operation, but the
                                                    // arithmetic doesn't need to
                                                    // special-case it either way)

    reg frozen_r;
    assign frozen = frozen_r;

    wire freeze_raw  = (level >= HIGH);
    wire release_raw = (level <= LOW);

    always @(posedge clk) begin
        if (rst) begin
            frozen_r  <= 1'b0;
            cmd_valid <= 1'b0;
            cmd_bus   <= 32'h0;
            cmd_data  <= 32'h0;
        end else begin
            cmd_valid <= 1'b0; // default: no pulse this cycle
            if (!frozen_r && freeze_raw) begin
                frozen_r  <= 1'b1;
                cmd_bus   <= {2'b0, AUTH, 11'h0, OP_CMD_FREEZE};
                cmd_data  <= 32'h0;
                cmd_valid <= 1'b1; // one-shot pulse, only on the transition
            end else if (frozen_r && release_raw) begin
                frozen_r  <= 1'b0;
                cmd_bus   <= {2'b0, AUTH, 11'h0, OP_CMD_RELEASE};
                cmd_data  <= 32'h0;
                cmd_valid <= 1'b1;
            end
            // else: hold state, no re-send -- avoids redundant FREEZE/RELEASE
            // traffic and matches "one-shot pulse on the edge" from the design.
        end
    end

endmodule
