// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mem_interface_cell_v1.v — first real RTL draft of the memory-interface
// core (points.md #248 task 3 continuation, following `#253`'s SHELL/
// CORE/ADDON confirmation). DRAFT — sim-verified only, no Quartus data
// yet. Alan's own framing (2026-08-09): a new core that takes a
// counting cell's data AS THE ADDRESS, combines it with a fixed READ or
// WRITE command, and either the data pops out (READ) or is taken
// (WRITE) — with each cell's own ACK acting as the control, so a
// counter driven by this cell's ack naturally stays synced to real
// read/write completion. Same SHELL (cardinal ports, ready/ack
// handshake, offer/drain) as ram_cell_v1.v/adder_cell_v1.v — the CORE
// here is bram_controller_v1.v instead of a latch or an adder. Alan's
// own note: this may generalize to a "device interface" core beyond
// memory if a future device follows the same pattern — not built here,
// flagged for later.
//
// cfg_data[63:0] field map (first proposal, same convention as the
// other two cores — NOT frozen):
//   [3:0]   downstream_mask  — READ mode only: where the result offers
//   [7:4]   upstream_mask    — address source (READ), address+data
//                              source (WRITE) — direction-agnostic,
//                              same two-arrival convention adder_cell_v1
//                              uses (whichever direction arrives becomes
//                              A, then B, regardless of which port)
//   [8]     op_mode          — 0=READ, 1=WRITE (matches
//                              bram_controller_v1's own OP_READ/OP_WRITE)
//   [63:9]  reserved
//
// READ MODE: single arrival -> address. capture_now launches the real
// bram_controller_v1 READ command COMBINATIONALLY the same cycle
// (cmd_valid/cmd_addr wired straight from this cycle's capture_now/
// upstream_val — bram_controller_v1 samples them at that same edge).
// The controller's own single-stage synchronous read (#255) makes the
// result available exactly one edge later; this core's own
// `read_pending` flag tracks that one-cycle wait and moves the result
// into `out_buffer`/`data_valid` the moment `bram_rdata_valid` arrives,
// then offers it downstream through the ordinary offer/drain mechanism
// — genuinely "pops out" the normal way, no new downstream protocol.
// `ready_out` stays low the whole time addr_captured is held (covers
// the wait), so ONE read is in flight at a time in this first draft —
// no pipelining yet, deliberately, per "smallest test first."
//
// WRITE MODE: two arrivals -> address then data, same two-arrival shape
// unicell_stripped_v1.v/adder_cell_v1.v already use. The second arrival
// fires the WRITE command immediately (no wait state needed — writes
// are single-cycle in bram_controller_v1.v). Nothing "pops out" for a
// write in this first draft — downstream_mask is unused/left zero for
// a pure write-sink cell; a write-completion echo could be added later
// if a use for it appears.
//
// THE SYNC CLAIM (Alan's own framing, to be proven directly by a
// dedicated integration testbench, not just asserted): each direction's
// `ack_out` fires exactly at capture (same convention every other cell
// here uses) — so wiring `addr_counter_v1.v`'s `advance_en` straight to
// THIS cell's own address-direction ack means the counter only steps to
// the next address once this cell has genuinely captured (and, for
// READ, is correctly gated from re-capturing until the prior read
// drains via `ready_out`) — no separate synchronization mechanism
// needed, the existing per-cell ack fabric IS the control.
`default_nettype none
`timescale 1ns / 1ps

module mem_interface_cell_v1 #(
    parameter [15:0] CELL_ID    = 16'h0000,
    parameter        ADDR_WIDTH = 16
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    output wire         status_data_valid,
    output wire         status_addr_captured
);

    // ── State ───────────────────────────────────────────────────────────
    reg [31:0] addr_reg        = 32'h0;
    reg        addr_captured   = 1'b0;
    reg        read_pending    = 1'b0;
    reg [31:0] out_buffer      = 32'h0;
    reg        data_valid      = 1'b0;
    reg [3:0]  downstream_mask = 4'h0;
    reg [3:0]  upstream_mask   = 4'h0;
    reg        op_mode         = 1'b0;   // 0=READ, 1=WRITE
    reg [3:0]  pending_ack     = 4'h0;

    wire effective_freeze = freeze_in;

    // ── Upstream arrival selection — same convention as ram_cell_v1.v/
    // adder_cell_v1.v. ──
    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    // First arrival -> address, both modes. READ mode also requires
    // !data_valid — the "doubly full" gate ram_cell_v1.v/adder_cell_v1.v
    // both already use, applied here for the same reason: without it, a
    // second READ could complete and overwrite out_buffer/data_valid
    // while a PREVIOUS un-drained result is still waiting on the
    // downstream consumer, silently losing it. The header already
    // stated "no pipelining yet, deliberately" but an earlier draft of
    // this logic didn't actually enforce that — caught before any
    // integration testing exercised back-to-back reads, not found via
    // a failing test. WRITE mode never sets data_valid/out_buffer at
    // all, so this extra term is inert (always true) for WRITE.
    wire capture_now = any_upstream_arrived && !addr_captured && !effective_freeze &&
                        !((op_mode == 1'b0) && data_valid);

    // WRITE mode's second arrival -> data, fires the write.
    wire can_fire_write = any_upstream_arrived && addr_captured &&
                           (op_mode == 1'b1) && !effective_freeze;

    assign ack_out_n = (capture_now || can_fire_write) && sel_n;
    assign ack_out_s = (capture_now || can_fire_write) && sel_s;
    assign ack_out_e = (capture_now || can_fire_write) && sel_e;
    assign ack_out_w = (capture_now || can_fire_write) && sel_w;

    // ── The real memory core — bram_controller_v1.v, not a latch or an
    // adder (points.md #253/#255). READ command launches combinationally
    // at the SAME edge address arrives; WRITE command launches at the
    // SAME edge the data (second arrival) arrives. ──
    wire                    bram_cmd_valid = (capture_now && (op_mode == 1'b0)) || can_fire_write;
    wire                    bram_cmd_op    = op_mode;   // matches bram_controller_v1's OP_READ=0/OP_WRITE=1
    wire [ADDR_WIDTH-1:0]   bram_cmd_addr  = (op_mode == 1'b0) ? upstream_val[ADDR_WIDTH-1:0]
                                                                : addr_reg[ADDR_WIDTH-1:0];
    wire [31:0]             bram_cmd_wdata = upstream_val;   // only meaningful on the can_fire_write cycle

    wire        bram_rdata_valid;
    wire [31:0] bram_rdata;
    wire        bram_write_done;   // unused for now — no completion echo yet, see header

    bram_controller_v1 #(.ADDR_WIDTH(ADDR_WIDTH), .DATA_WIDTH(32)) CORE (
        .clk(clk), .rst(rst),
        .cmd_valid(bram_cmd_valid), .cmd_op(bram_cmd_op),
        .cmd_addr(bram_cmd_addr), .cmd_wdata(bram_cmd_wdata),
        .rdata_valid(bram_rdata_valid), .rdata(bram_rdata), .write_done(bram_write_done)
    );

    // ── Downstream offering — READ mode only, identical shape to
    // ram_cell_v1.v/adder_cell_v1.v. ──
    wire want_to_offer = data_valid && !effective_freeze;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    // Ready for a NEW address only when not currently holding one, AND
    // (READ mode) not still holding an undrained previous result —
    // same "doubly full" reasoning as capture_now above, kept in sync
    // with it deliberately.
    assign ready_out = !effective_freeze && !addr_captured &&
                        !((op_mode == 1'b0) && data_valid);
    assign status_data_valid    = data_valid;
    assign status_addr_captured = addr_captured;

    always @(posedge clk) begin
        if (rst) begin
            addr_reg        <= 32'h0;
            addr_captured   <= 1'b0;
            read_pending    <= 1'b0;
            out_buffer      <= 32'h0;
            data_valid      <= 1'b0;
            downstream_mask <= 4'h0;
            upstream_mask   <= 4'h0;
            op_mode         <= 1'b0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[3:0];
            upstream_mask   <= cfg_data[7:4];
            op_mode         <= cfg_data[8];
            addr_captured   <= 1'b0;
            read_pending    <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else begin
            // Independent if-blocks throughout (not else-if chained) —
            // points.md #252's own lesson: verified by construction that
            // no two of these can genuinely coincide in the same cycle
            // (capture_now requires !addr_captured; can_fire_write
            // requires addr_captured&&WRITE; the read-complete block
            // requires addr_captured already set from a PRIOR cycle's
            // READ capture, mutually exclusive with a fresh capture_now
            // this same cycle) rather than assumed safe by priority.
            if (capture_now) begin
                addr_reg      <= upstream_val;
                addr_captured <= 1'b1;
                if (op_mode == 1'b0) read_pending <= 1'b1;
            end else if (can_fire_write) begin
                addr_captured <= 1'b0;
            end

            if (read_pending && bram_rdata_valid) begin
                out_buffer    <= bram_rdata;
                data_valid    <= 1'b1;
                addr_captured <= 1'b0;
                read_pending  <= 1'b0;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
