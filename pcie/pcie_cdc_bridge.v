// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// pcie_cdc_bridge.v -- clock-domain-crossing bridge between the PCIe Hard
// IP's fast application clock (coreclkout_hip, 250MHz for the currently
// selected Gen2x8/128-bit mode) and the fabric's slow clock (CLK, currently
// 25MHz via CLK_100M/4, with a stated target of 50MHz -- see points.md #46).
//
// Sits directly in front of pcie_unicell_bridge.v, translating its avs_*
// slave interface across the clock boundary. pcie_unicell_bridge.v itself
// is completely unchanged -- it already only cares about a stable,
// single-outstanding-transaction Avalon-MM slave interface in its own
// (slow) clock domain, which is exactly what this bridge's slow-side ports
// present to it.
//
// DESIGN: standard two-phase toggle request/acknowledge handshake, chosen
// over a dual-clock FIFO because the traffic pattern here is genuinely
// single-outstanding (PIO-style, one transaction at a time, matching
// pio_bridge_0's own non-bursting behaviour) -- a FIFO's full/empty
// bookkeeping would add complexity this traffic pattern doesn't need.
//
// FREQUENCY-RATIO-INDEPENDENT BY CONSTRUCTION: nothing here is sized or
// timed for a specific fast:slow ratio. Two-flop synchronizers on the
// toggle signals work correctly for any ratio comfortably above the
// standard ~2x minimum (both currently plausible ratios -- 250:25 = 10x,
// 250:50 = 5x -- are well past that). If the fabric clock is later
// retuned (e.g. clk_div's /4 tightened to /2 for 50MHz), NOTHING in this
// module needs to change -- only SDC timing constraints need updating to
// reflect the new relationship. Verified directly, not just claimed: see
// tb_pcie_cdc_bridge.v, which runs the identical test sequence at both a
// 25MHz-equivalent and a 50MHz-equivalent slow clock period.
//
// Multi-bit buses (address/byteenable/writedata/readdata) are NOT
// separately synchronized -- only the single-bit toggle signals go
// through flip-flop synchronizers. This is the standard, correct pattern:
// each bus is latched in its OWN domain before its corresponding toggle
// changes, and held stable throughout the entire handshake (which spans
// several clock periods on both sides while the toggle propagates) -- by
// the time the toggle's synchronized value is observed as changed on the
// receiving side, the associated bus has been stable for multiple cycles
// already, so sampling it directly is safe.

`timescale 1ns / 1ps
`default_nettype none

module pcie_cdc_bridge (
    // ── Fast domain (PCIe Hard IP / pio_bridge_0 side) ──────────────────────
    input  wire         fast_clk,
    input  wire         fast_rst,

    input  wire [15:0]  fast_address,
    input  wire [3:0]   fast_byteenable,
    input  wire [31:0]  fast_writedata,
    input  wire         fast_write,
    input  wire         fast_read,
    output reg  [31:0]  fast_readdata,
    output reg          fast_readdatavalid,
    output wire         fast_waitrequest,

    // ── Slow domain (fabric side -- connects directly to
    //    pcie_unicell_bridge.v's avs_* ports, unchanged) ─────────────────────
    input  wire         slow_clk,
    input  wire         slow_rst,

    output reg  [15:0]  slow_address,
    output reg  [3:0]   slow_byteenable,
    output reg  [31:0]  slow_writedata,
    output reg          slow_write,
    output reg          slow_read,
    input  wire [31:0]  slow_readdata,
    input  wire         slow_readdatavalid,
    input  wire         slow_waitrequest    // honoured for correctness/generality,
                                             // even though pcie_unicell_bridge.v
                                             // currently ties this to 0 always
);

// ── Fast domain: capture the request, stall the master until acked ─────────
reg         fast_busy;
reg         fast_req_toggle;
reg  [15:0] fast_address_r;
reg  [3:0]  fast_byteenable_r;
reg  [31:0] fast_writedata_r;
reg         fast_is_write_r;

assign fast_waitrequest = fast_busy;

// Synchronize the slow domain's ack_toggle into the fast domain (2-flop)
reg fast_ack_sync_0, fast_ack_sync_1, fast_ack_sync_1_prev;
wire fast_ack_edge = (fast_ack_sync_1 != fast_ack_sync_1_prev);

always @(posedge fast_clk) begin
    if (fast_rst) begin
        fast_ack_sync_0      <= 1'b0;
        fast_ack_sync_1      <= 1'b0;
        fast_ack_sync_1_prev <= 1'b0;
    end else begin
        fast_ack_sync_0      <= slow_ack_toggle;   // slow_ack_toggle is a slow-domain
                                                    // reg, sampled here as an ordinary
                                                    // asynchronous input -- this is the
                                                    // actual metastability-prone crossing
                                                    // point, resolved by the two flops.
        fast_ack_sync_1      <= fast_ack_sync_0;
        fast_ack_sync_1_prev <= fast_ack_sync_1;
    end
end

always @(posedge fast_clk) begin
    if (fast_rst) begin
        fast_busy           <= 1'b0;
        fast_req_toggle      <= 1'b0;
        fast_address_r       <= 16'h0;
        fast_byteenable_r    <= 4'h0;
        fast_writedata_r     <= 32'h0;
        fast_is_write_r      <= 1'b0;
        fast_readdata        <= 32'h0;
        fast_readdatavalid   <= 1'b0;
    end else begin
        fast_readdatavalid <= 1'b0;   // default: one-cycle pulse, matches
                                       // pcie_unicell_bridge.v's own convention

        if (!fast_busy && (fast_write || fast_read)) begin
            // New request: latch everything, flip the request toggle, stall
            // the master (via fast_waitrequest = fast_busy) until acked.
            fast_address_r    <= fast_address;
            fast_byteenable_r <= fast_byteenable;
            fast_writedata_r  <= fast_writedata;
            fast_is_write_r   <= fast_write;
            fast_req_toggle   <= ~fast_req_toggle;
            fast_busy         <= 1'b1;
        end else if (fast_busy && fast_ack_edge) begin
            // Slow domain has completed the transaction.
            fast_busy <= 1'b0;
            if (!fast_is_write_r) begin
                fast_readdata      <= slow_readdata_captured;
                fast_readdatavalid <= 1'b1;
            end
        end
    end
end

// ── Slow domain: detect the request, drive avs_*, ack when done ────────────
reg slow_req_sync_0, slow_req_sync_1, slow_req_sync_1_prev;
wire slow_req_edge = (slow_req_sync_1 != slow_req_sync_1_prev);

reg        slow_ack_toggle;
reg [31:0] slow_readdata_captured;   // sampled once, held stable across the
                                     // entire ack handshake -- this is the
                                     // value fast_readdata copies on ack_edge

// Small state machine: IDLE -> (write completes same-cycle) -> ACK, or
// IDLE -> WAIT_READ (waiting for slow_readdatavalid) -> ACK
localparam S_IDLE      = 2'h0;
localparam S_DRIVE      = 2'h1;   // drive slow_write/slow_read for one cycle
localparam S_WAIT_READ  = 2'h2;   // waiting for slow_readdatavalid (reads only)
reg [1:0] slow_state;

always @(posedge slow_clk) begin
    if (slow_rst) begin
        slow_req_sync_0      <= 1'b0;
        slow_req_sync_1      <= 1'b0;
        slow_req_sync_1_prev <= 1'b0;
    end else begin
        slow_req_sync_0      <= fast_req_toggle;   // the actual crossing point
                                                    // for this direction
        slow_req_sync_1      <= slow_req_sync_0;
        slow_req_sync_1_prev <= slow_req_sync_1;
    end
end

always @(posedge slow_clk) begin
    if (slow_rst) begin
        slow_state             <= S_IDLE;
        slow_ack_toggle         <= 1'b0;
        slow_address            <= 16'h0;
        slow_byteenable          <= 4'h0;
        slow_writedata           <= 32'h0;
        slow_write               <= 1'b0;
        slow_read                <= 1'b0;
        slow_readdata_captured   <= 32'h0;
    end else begin
        slow_write <= 1'b0;   // defaults: one-cycle pulses, matching
        slow_read  <= 1'b0;   // pcie_unicell_bridge.v's own expected timing

        case (slow_state)
            S_IDLE: begin
                if (slow_req_edge) begin
                    // fast_address_r/byteenable_r/writedata_r/is_write_r have
                    // been stable in the fast domain since well before this
                    // toggle edge propagated through both synchronizer flops
                    // -- safe to sample directly here, no separate bus
                    // synchronizer needed (see module header).
                    slow_address    <= fast_address_r;
                    slow_byteenable <= fast_byteenable_r;
                    slow_writedata  <= fast_writedata_r;
                    if (fast_is_write_r) begin
                        slow_write <= 1'b1;
                        slow_state <= S_DRIVE;
                    end else begin
                        slow_read  <= 1'b1;
                        slow_state <= S_WAIT_READ;
                    end
                end
            end

            S_DRIVE: begin
                // Write completes the same cycle it's presented in
                // pcie_unicell_bridge.v (no waitrequest stall on writes) --
                // safe to ack immediately, one cycle after driving slow_write.
                if (!slow_waitrequest) begin
                    slow_ack_toggle <= ~slow_ack_toggle;
                    slow_state      <= S_IDLE;
                end
            end

            S_WAIT_READ: begin
                if (slow_readdatavalid) begin
                    slow_readdata_captured <= slow_readdata;
                    slow_ack_toggle         <= ~slow_ack_toggle;
                    slow_state              <= S_IDLE;
                end
            end

            default: slow_state <= S_IDLE;
        endcase
    end
end

endmodule

`default_nettype wire
