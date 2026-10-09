// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// bram_controller_v2.v — a deliberate CLONE of `bram_controller_v1.v`
// (never modify a proven file in place), fixing a real Quartus RAM-
// inference failure confirmed on real hardware (points.md #284).
//
// THE REAL PROBLEM, confirmed via a real Quartus build, not predicted:
// `top_full_tree_system_v1.v` (3 hierarchy levels deep: top ->
// `mem_read_splitter_v1_test.v` -> `bram_controller_v1.v`) reported
// `Info (276007): RAM logic ... is uninferred due to asynchronous read
// logic` and synthesized the entire 65536-deep array as 655,712 plain
// registers instead of real M20K — a documented Intel/Altera Quartus
// limitation: the exact same unmodified RTL that inferred correctly as
// real M20K when close to the top of the hierarchy (`#265`, 2 levels:
// top -> `bram_controller_v1.v` directly) can fail once wrapped several
// levels deeper, even with no functional change to the module itself.
//
// THE FIX, matching Quartus's own documented canonical RAM template:
// the READ ADDRESS is now REGISTERED inside this module (a genuine
// design change, not cosmetic) before indexing `mem`, rather than
// combinationally read straight from the `cmd_addr` input port. This
// is the standard, most robust inference pattern precisely because it
// doesn't rely on Quartus tracing a combinational address through
// multiple hierarchy levels to recognize the RAM pattern — the address
// register lives in the SAME module as the memory array.
//
// REAL CONSEQUENCE, confirmed correct not to require any change
// elsewhere: this makes the read TWO-STAGE instead of `#255`'s
// original single-stage (`rdata_valid` now pulses one cycle LATER
// than before). Every consumer in this project (`mem_read_splitter_
// v1.v`/`_test.v`/`_ext.v`, `mem_interface_cell_v1.v`) already waits
// on `rdata_valid` as a genuine EVENT, never assuming a fixed cycle
// count anywhere — confirmed by direct inspection AND by full
// regression (points.md #284) — so this change needed ZERO edits to
// any consumer. Exactly the layered-latency discipline Alan's own
// framing described: each level only ever sees "wait for the valid
// signal from the layer above," regardless of how many cycles that
// takes internally, no matter how deep the real hierarchy is.
`default_nettype none
`timescale 1ns / 1ps

module bram_controller_v2 #(
    parameter ADDR_WIDTH = 16,
    parameter DATA_WIDTH = 40,
    parameter DEPTH       = (1 << ADDR_WIDTH)
) (
    input  wire                     clk,
    input  wire                     rst,

    input  wire                     cmd_valid,
    input  wire                     cmd_op,      // 0=READ, 1=WRITE
    input  wire [ADDR_WIDTH-1:0]    cmd_addr,
    input  wire [DATA_WIDTH-1:0]    cmd_wdata,

    output reg                      rdata_valid, // pulses 1 cycle after the REGISTERED address is captured (2 cycles after cmd_valid)
    output reg  [DATA_WIDTH-1:0]    rdata,
    output reg                      write_done   // pulses the same cycle a WRITE lands (unchanged from v1 — writes stay single-cycle)
);

    localparam OP_READ  = 1'b0;
    localparam OP_WRITE = 1'b1;

    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    // ── THE FIX: registered read address ────────────────────────────
    reg                     read_req_reg  = 1'b0;
    reg [ADDR_WIDTH-1:0]    read_addr_reg = {ADDR_WIDTH{1'b0}};

    always @(posedge clk) begin
        rdata_valid  <= 1'b0;
        write_done   <= 1'b0;
        read_req_reg <= 1'b0;

        if (rst) begin
            rdata_valid  <= 1'b0;
            write_done   <= 1'b0;
            read_req_reg <= 1'b0;
        end else begin
            // Stage 1: capture the command, register the address for
            // a READ (this is the change from v1 — the address is
            // stored here, not used to index `mem` this same cycle).
            if (cmd_valid) begin
                if (cmd_op == OP_READ) begin
                    read_addr_reg <= cmd_addr;
                    read_req_reg  <= 1'b1;
                end else begin // OP_WRITE — unchanged, still single-cycle
                    mem[cmd_addr] <= cmd_wdata;
                    write_done    <= 1'b1;
                end
            end

            // Stage 2: the REGISTERED address indexes `mem` here —
            // this is the canonical, Quartus-documented pattern.
            if (read_req_reg) begin
                rdata       <= mem[read_addr_reg];
                rdata_valid <= 1'b1;
            end
        end
    end

endmodule
