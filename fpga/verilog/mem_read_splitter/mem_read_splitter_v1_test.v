// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mem_read_splitter_v1_test.v — a deliberate CLONE of
// `mem_read_splitter_v1.v` (never modify a proven file in place), for
// ONE purpose only: real-hardware Quartus testing of `#273`'s full tree
// system needs a way to seed known A/B/C values into this module's own
// internal BRAM before the self-test runs. The proven simulation
// testbench (`tb_full_tree_system_v1.v`) did this via a hierarchical
// backdoor (`SPLITTER.CORE.mem[addr] = value`) — a real simulation-only
// construct, not synthesizable. This clone adds a genuine debug write
// port (`dbg_wr_*`), muxed into the internal `bram_controller_v1.v`
// core's own command port ahead of the normal read path, so a
// synthesizable self-test FSM can load real values through real logic
// instead.
//
// NOT a general-purpose write capability — `mem_read_splitter_v1.v`
// itself stays READ-only by design (points.md #257/#260); this is a
// test-harness-only extension, isolated to its own file, never touching
// the proven original. Debug writes are expected ONLY during a brief
// power-on seeding phase before normal operation begins — no attempt
// is made to arbitrate a debug write against an in-flight normal read
// beyond simple priority (debug wins), since the self-test FSM that
// drives this is expected to keep `dbg_wr_valid` and normal address
// arrivals mutually exclusive in time by construction.
`default_nettype none
`timescale 1ns / 1ps

module mem_read_splitter_v1_test #(
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

    output wire [7:0]   routing_out,

    output wire         status_data_valid,
    output wire         status_addr_captured,

    // ── Debug write port — test-harness only, see header ──────────────
    input  wire                   dbg_wr_valid,
    input  wire [ADDR_WIDTH-1:0]  dbg_wr_addr,
    input  wire [39:0]            dbg_wr_wdata,
    output wire                   dbg_wr_done
);

    // ── State — identical to mem_read_splitter_v1.v ────────────────────
    reg [31:0] addr_reg        = 32'h0;
    reg        addr_captured   = 1'b0;
    reg        read_pending    = 1'b0;
    reg [31:0] out_buffer      = 32'h0;
    reg [7:0]  routing_reg     = 8'h0;
    reg        data_valid      = 1'b0;
    reg [3:0]  downstream_mask = 4'h0;
    reg [3:0]  upstream_mask   = 4'h0;
    reg [3:0]  pending_ack     = 4'h0;

    wire effective_freeze = freeze_in;

    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    wire capture_now = any_upstream_arrived && !addr_captured && !effective_freeze &&
                        !data_valid && !dbg_wr_valid;   // debug write takes priority

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    // ── The real memory core, with the command port now MUXED between
    // the normal read path and the debug write path. ──
    wire                  bram_cmd_valid = capture_now || dbg_wr_valid;
    wire                  bram_cmd_op    = dbg_wr_valid;   // 0=READ, 1=WRITE — debug write wins priority
    wire [ADDR_WIDTH-1:0] bram_cmd_addr  = dbg_wr_valid ? dbg_wr_addr : upstream_val[ADDR_WIDTH-1:0];
    wire [39:0]           bram_cmd_wdata = dbg_wr_wdata;

    wire        bram_rdata_valid;
    wire [39:0] bram_rdata;
    wire        bram_write_done;

    // NOTE (points.md #284): uses bram_controller_v2.v, NOT v1 --
    // a real Quartus build revealed v1's memory failed to infer as
    // real M20K when instantiated this deep in the hierarchy (3
    // levels: top -> this module -> the memory core), synthesizing as
    // 655,712 plain registers instead. v2's registered read address
    // fixes this. The consequence -- read is now genuinely 2-stage,
    // not 1 -- requires NO changes to this module's own logic below,
    // since it already waits on `bram_rdata_valid` as a genuine event
    // rather than assuming a fixed cycle count (confirmed directly,
    // not assumed).
    bram_controller_v2 #(.ADDR_WIDTH(ADDR_WIDTH), .DATA_WIDTH(40)) CORE (
        .clk(clk), .rst(rst),
        .cmd_valid(bram_cmd_valid), .cmd_op(bram_cmd_op),
        .cmd_addr(bram_cmd_addr), .cmd_wdata(bram_cmd_wdata),
        .rdata_valid(bram_rdata_valid), .rdata(bram_rdata), .write_done(bram_write_done)
    );

    assign dbg_wr_done = bram_write_done;

    // ── Downstream DATA offering — identical to mem_read_splitter_v1.v ──
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

    assign routing_out = routing_reg;

    assign ready_out = !effective_freeze && !addr_captured && !data_valid;
    assign status_data_valid    = data_valid;
    assign status_addr_captured = addr_captured;

    always @(posedge clk) begin
        if (rst) begin
            addr_reg        <= 32'h0;
            addr_captured   <= 1'b0;
            read_pending    <= 1'b0;
            out_buffer      <= 32'h0;
            routing_reg     <= 8'h0;
            data_valid      <= 1'b0;
            downstream_mask <= 4'h0;
            upstream_mask   <= 4'h0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[3:0];
            upstream_mask   <= cfg_data[7:4];
            addr_captured   <= 1'b0;
            read_pending    <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else begin
            if (capture_now) begin
                addr_reg      <= upstream_val;
                addr_captured <= 1'b1;
                read_pending  <= 1'b1;
            end

            if (read_pending && bram_rdata_valid) begin
                out_buffer    <= bram_rdata[31:0];
                routing_reg   <= bram_rdata[39:32];
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
