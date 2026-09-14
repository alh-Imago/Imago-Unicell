// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// shared_bram_arbiter_v1.v — real RTL for the shared-memory piece Alan
// asked for directly: ONE `bram_controller_v1.v` instance serving BOTH
// a read request (`mem_read_splitter_v1_ext.v`) and a write request
// (`combiner_cell_v1.v`/`v2.v`), instead of the two SEPARATE instances
// every prior full-system build used (`#257`'s own "two independent
// regions" design). DRAFT — sim-verified only, no Quartus data yet.
//
// POLICY: write has priority — a write represents a real result that
// needs to land promptly, and delaying/losing one risks backpressure
// cascading upstream through the whole combiner chain. A read that
// loses the arbitration for a cycle is NOT dropped: `mem_read_
// splitter_v1_ext.v`'s own `ext_cmd_valid` is a single-cycle pulse, so
// if it isn't serviced that exact cycle, the request would otherwise
// be silently lost forever (the splitter's own internal state has
// already latched as if the read was issued, with no retry mechanism
// of its own). This arbiter QUEUES a blocked read (one outstanding
// request, address latched) and re-issues it on the first subsequent
// cycle no write is contending.
//
// Safe by construction, not just by policy: `mem_read_splitter_v1_
// ext.v`'s own doubly-full guard (`!addr_captured && !data_valid`)
// already prevents it from ever issuing a SECOND `ext_cmd_valid` while
// a first is still outstanding — regardless of whether that outstanding
// wait is normal 1-cycle BRAM latency or extra arbiter queuing delay,
// the splitter just waits for `ext_rdata_valid`. So this arbiter never
// needs to handle more than one queued read at a time.
`default_nettype none
`timescale 1ns / 1ps

module shared_bram_arbiter_v1 #(
    parameter ADDR_WIDTH = 16
) (
    input  wire        clk,
    input  wire        rst,

    // ── Read side (mem_read_splitter_v1_ext.v) ─────────────────────────
    input  wire                    rd_cmd_valid,
    input  wire [ADDR_WIDTH-1:0]   rd_cmd_addr,
    output wire                    rd_rdata_valid,
    output wire [39:0]             rd_rdata,

    // ── Write side (combiner_cell_v1.v/v2.v) ───────────────────────────
    input  wire                    wr_cmd_valid,
    input  wire [ADDR_WIDTH-1:0]   wr_cmd_addr,
    input  wire [39:0]             wr_cmd_wdata,
    output wire                    wr_write_done,

    // ── Real memory command port (to ONE bram_controller_v1.v) ─────────
    output wire                    mem_cmd_valid,
    output wire                    mem_cmd_op,
    output wire [ADDR_WIDTH-1:0]   mem_cmd_addr,
    output wire [39:0]             mem_cmd_wdata,
    input  wire                    mem_rdata_valid,
    input  wire [39:0]             mem_rdata,
    input  wire                    mem_write_done,

    output wire                    status_queued   // debug: a read is currently queued behind a write
);

    reg                    pending_rd      = 1'b0;
    reg [ADDR_WIDTH-1:0]   pending_rd_addr = {ADDR_WIDTH{1'b0}};

    // A brand-new read request that loses arbitration THIS cycle gets
    // queued; a previously-queued read gets serviced the first cycle
    // no write contends.
    wire do_write       = wr_cmd_valid;
    wire do_read_new     = rd_cmd_valid && !pending_rd && !wr_cmd_valid;
    wire do_read_queued  = pending_rd && !wr_cmd_valid;
    wire do_read         = do_read_new || do_read_queued;

    assign mem_cmd_valid = do_write || do_read;
    assign mem_cmd_op    = do_write;   // 0=READ, 1=WRITE
    assign mem_cmd_addr  = do_write ? wr_cmd_addr :
                            do_read_queued ? pending_rd_addr : rd_cmd_addr;
    assign mem_cmd_wdata = wr_cmd_wdata;

    assign wr_write_done = mem_write_done;
    assign rd_rdata_valid = mem_rdata_valid;
    assign rd_rdata        = mem_rdata;

    assign status_queued = pending_rd;

    always @(posedge clk) begin
        if (rst) begin
            pending_rd      <= 1'b0;
            pending_rd_addr <= {ADDR_WIDTH{1'b0}};
        end else begin
            if (rd_cmd_valid && !pending_rd && wr_cmd_valid) begin
                // New read request arrives the SAME cycle a write wins
                // -- queue it rather than lose it.
                pending_rd      <= 1'b1;
                pending_rd_addr <= rd_cmd_addr;
            end else if (pending_rd && !wr_cmd_valid) begin
                // Queued read just got serviced this cycle (do_read_queued
                // was true combinationally above) — clear the queue.
                pending_rd <= 1'b0;
            end
        end
    end

endmodule
