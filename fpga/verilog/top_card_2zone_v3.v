// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// top_card_2zone_v3.v — first 2-zone card: BRAM in its SECOND role. The
// loader test proved BRAM as program store; this proves BRAM as the actual
// inter-zone DATA channel (sessions/latest.md "BRAM as universal primitive" —
// same memory, different job, distinguished only by which port is driving).
//
// Zone 0's cell fires and its result is captured into bram_dp_v3 (NOT sent
// over the zones' own direct wired bridge — those bridge ports are tied off
// here on purpose, to isolate and prove the BRAM path specifically). A small
// autonomous bridge FSM watches the buffer for new data and, with no host
// involvement, injects it into Zone 1's cell, whose result is captured into a
// second BRAM region — the "repository" a host/PCIe read would pull from
// (this session's PCIe stand-in already proved that side separately).
//
// Deliberately ONE cell per zone (smallest-test-first) — proves the mechanism
// before scaling cell count or zone count.
`default_nettype none
`timescale 1ns / 1ps

module top_card_2zone_v3 #(
    parameter NUM_CELLS = 4   // per zone -- small for a fast sim; real card uses more
) (
    input  wire clk,
    input  wire rst,
    input  wire start_load,          // pulse: begin the loader FSM

    // Host-facing run-phase stimulus (e.g. preload/inject Zone 0's operands --
    // the loader only configures cells, it doesn't drive a computation).
    // Ignored while the loader is still running; yields to the bridge FSM on
    // any cycle the bridge itself has something to send (brief, one cycle).
    input  wire [31:0] host_cmd_bus,
    input  wire [31:0] host_cmd_data,
    input  wire        host_cmd_valid,

    // Repository read-out (the "host/PCIe" side) -- results BRAM port B, exposed
    output wire [31:0] results_rdata,
    output wire        loader_done,
    output wire [15:0] bridge_hops    // count of buffer->inject events (debug)
);

    // ── shared transport (broadcast to both zones) ────────────────────────
    // Priority while loading: the loader FSM owns the bus exclusively. After
    // loader_done: the bridge FSM (buffer->Zone1 injection) takes priority on
    // any cycle it's actively sending; otherwise the host stimulus port drives
    // (used to preload/inject Zone 0's operands and kick off the computation).
    //
    // Structured as ONE raw-signal mux (bus/data/valid) followed by the SAME
    // cmd_valid_w / cpu_addr_w derivation top_arria10_zone1_v3.v uses, rather
    // than duplicating that derivation per source -- a DATA_WRITE (opcode 1)
    // from ANY source must never reach the cells' cmd_valid port (only
    // cpu_valid), exactly the fix from this session's addressing bug.
    wire [31:0] ldr_cmd_bus, ldr_cmd_data; wire ldr_cmd_valid;
    wire [15:0] ldr_cpu_addr; wire ldr_cpu_valid;
    reg  [31:0] brg_cmd_bus, brg_cmd_data; reg brg_active;

    wire [31:0] raw_bus   = !loader_done ? ldr_cmd_bus  : (brg_active ? brg_cmd_bus  : host_cmd_bus);
    wire [31:0] raw_data  = !loader_done ? ldr_cmd_data : (brg_active ? brg_cmd_data : host_cmd_data);
    wire        raw_valid = !loader_done ? ldr_cpu_valid: (brg_active ? brg_active   : host_cmd_valid);

    // The loader already emits its own opcodes pre-filtered correctly (it
    // never sends DATA_WRITE), so while it's driving, cmd_valid == its own
    // cmd_valid directly; after handoff, apply the standard filter.
    wire preload_act = (raw_bus[18:17] != 2'b00);
    wire cmd_valid_w = !loader_done ? ldr_cmd_valid
                     : raw_valid && (raw_bus[7:0] != 8'd1) && ((raw_bus[7:0] != 8'd0) || preload_act);
    wire [15:0] cpu_addr_w = (raw_bus[7:0]==8'd1) ? raw_data[31:16]
                           : !loader_done          ? ldr_cpu_addr
                                                    : raw_data[15:0];

    wire [31:0] cmd_bus   = raw_bus;
    wire [31:0] cmd_data  = raw_data;
    wire        cmd_valid = cmd_valid_w;
    wire [15:0] cpu_addr  = cpu_addr_w;
    wire        cpu_valid = raw_valid;

    // ── zones ──────────────────────────────────────────────────────────────
    wire [1:0] tie_v=0; wire [31:0] tie_a=0, tie_d=0;
    wire [15:0] z0_out_addr, z1_out_addr; wire [31:0] z0_out_data, z1_out_data;
    wire z0_out_valid, z1_out_valid;
    wire [15:0] z0_emit, z1_emit;

    unicell_zone64_v3 #(.NUM_CELLS(NUM_CELLS), .NUM_BRIDGES(2), .ZONE_ID(0)) zone0 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z0_out_addr), .out_data(z0_out_data), .out_valid(z0_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z0_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_in_valid(tie_v), .bridge_n_in_addr(tie_a), .bridge_n_in_data(tie_d),
        .bridge_n_out_valid(), .bridge_n_out_addr(), .bridge_n_out_data(),
        .bridge_s_in_valid(tie_v), .bridge_s_in_addr(tie_a), .bridge_s_in_data(tie_d),
        .bridge_s_out_valid(), .bridge_s_out_addr(), .bridge_s_out_data(),
        .bridge_e_in_valid(tie_v), .bridge_e_in_addr(tie_a), .bridge_e_in_data(tie_d),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_w_in_valid(tie_v), .bridge_w_in_addr(tie_a), .bridge_w_in_data(tie_d),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data()
        // NOTE: direct bridge ports tied off deliberately -- BRAM is the
        // inter-zone channel in this build, not the wired bridge network.
    );

    unicell_zone64_v3 #(.NUM_CELLS(NUM_CELLS), .NUM_BRIDGES(2), .ZONE_ID(1)) zone1 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z1_out_addr), .out_data(z1_out_data), .out_valid(z1_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z1_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_in_valid(tie_v), .bridge_n_in_addr(tie_a), .bridge_n_in_data(tie_d),
        .bridge_n_out_valid(), .bridge_n_out_addr(), .bridge_n_out_data(),
        .bridge_s_in_valid(tie_v), .bridge_s_in_addr(tie_a), .bridge_s_in_data(tie_d),
        .bridge_s_out_valid(), .bridge_s_out_addr(), .bridge_s_out_data(),
        .bridge_e_in_valid(tie_v), .bridge_e_in_addr(tie_a), .bridge_e_in_data(tie_d),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_w_in_valid(tie_v), .bridge_w_in_addr(tie_a), .bridge_w_in_data(tie_d),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data()
    );

    // ── loader FSM: one cell in each zone ─────────────────────────────────
    // Zone0 cell (flat addr 0): topology=XOR(0x0BC), armed (start_flag bit11=1),
    //   output_address -> BUFFER_WRITE_ADDR (captured into the buffer BRAM below).
    // Zone1 cell (flat addr 32, ZONE_ID1<<5): topology=PASS_B|LATCH_IN (0x02C |
    //   latch_in via cmd_data[17]), armed, output_address -> RESULTS_ADDR. Fires
    //   on a SINGLE arrival (latch_in) -- no preload needed, it just relays
    //   whatever the bridge FSM injects straight to the results capture.
    localparam [15:0] BUFFER_WRITE_ADDR = 16'h2000;
    localparam [15:0] RESULTS_ADDR      = 16'h3000;
    localparam [7:0]  OP_LOAD_AT        = 8'd23;
    localparam [7:0]  OP_SET_OUTPUT     = 8'd3;
    localparam [7:0]  METH_SET_LANE     = 8'd33;

    wire [15:0] cfg_target  [0:1];
    wire [31:0] cfg_c1_bus  [0:1];
    wire [31:0] cfg_c1_data [0:1];
    wire [31:0] cfg_c2_bus  [0:1];
    wire [31:0] cfg_c2_data [0:1];
    wire        cfg_zsel    [0:1];

    // Cell 0 (zone0, flat addr 0): SET_OUTPUT_ADDR then LOAD_AT would be 2 real
    // steps, but the loader FSM's cycle-1 slot is CMD_LOAD_AT only -- so output
    // address here is folded into the SAME cell's config by using LOAD_AT's
    // own topology+flags word (start_flag) and driving SET_OUTPUT_ADDR as an
    // EXTRA step is not supported by this first loader_fsm_v3 (it's fixed at
    // target+c1+c2+done). For this first card, park the output address at the
    // cell's own default (CELL_ID+1) and instead have the BUFFER WRITER key
    // off that default address directly -- see below. (Extending loader_fsm_v3
    // with an explicit SET_OUTPUT_ADDR step is the natural next widening, not
    // needed to prove the BRAM-buffer mechanism itself.)
    assign cfg_target[0]  = 16'h0000;                         // zone0 cell, flat addr 0
    assign cfg_c1_bus[0]  = {24'h0, OP_LOAD_AT};
    assign cfg_c1_data[0] = 32'h0000_0800 | 32'h0000_00BC;    // start_flag=1, topology=XOR
    assign cfg_c2_bus[0]  = {24'h0, METH_SET_LANE};
    assign cfg_c2_data[0] = 32'h0;
    assign cfg_zsel[0]    = 1'b0;                              // zone0's emit_count

    assign cfg_target[1]  = 16'h0020;                          // zone1 cell, flat addr 32 (ZONE_ID1<<5)
    assign cfg_c1_bus[1]  = {24'h0, OP_LOAD_AT};
    // topology=PASS_B(0x02C) | latch_in (cmd_data[17]) | start_flag (cmd_data[11])
    assign cfg_c1_data[1] = 32'h0000_0800 | 32'h0002_0000 | 32'h0000_002C;
    assign cfg_c2_bus[1]  = {24'h0, METH_SET_LANE};
    assign cfg_c2_data[1] = 32'h0;
    assign cfg_zsel[1]    = 1'b1;                              // zone1's emit_count

    loader_fsm_v3 #(.NCELLS(2)) loader (
        .clk(clk), .rst(rst), .start(start_load),
        .config_target(cfg_target), .config_c1_bus(cfg_c1_bus), .config_c1_data(cfg_c1_data),
        .config_c2_bus(cfg_c2_bus), .config_c2_data(cfg_c2_data), .config_zone_sel(cfg_zsel),
        .cmd_bus(ldr_cmd_bus), .cmd_data(ldr_cmd_data), .cmd_valid(ldr_cmd_valid),
        .cpu_addr(ldr_cpu_addr), .cpu_valid(ldr_cpu_valid),
        .emit_count_z0(z0_emit), .emit_count_z1(z1_emit),
        .done(loader_done), .cells_confirmed()
    );

    // ── buffer BRAM: zone0's fired result lands here (its default output ────
    // address is CELL_ID+1 = 1, since this first card doesn't extend the
    // loader to also drive SET_OUTPUT_ADDR -- see note above). Port B is read
    // CONTINUOUSLY at address 0 by the bridge FSM below -- this is a genuine
    // BRAM-mediated hop, not a shortcut: the bridge only ever sees what port B
    // reports, never zone0's live output directly.
    wire [31:0] buf_rdata;
    bram_dp_v3 #(.ADDR_W(4), .DATA_W(32)) buffer_bram (
        .clk(clk),
        .a_addr(4'h0), .a_wdata(z0_out_data), .a_we(z0_out_valid && (z0_out_addr==16'h0001)), .a_rdata(),
        .b_addr(4'h0), .b_wdata(32'h0), .b_we(1'b0), .b_rdata(buf_rdata)
    );

    reg  [15:0] buffer_write_count;
    always @(posedge clk) begin
        if (rst) buffer_write_count <= 16'h0;
        else if (z0_out_valid && (z0_out_addr==16'h0001)) buffer_write_count <= buffer_write_count + 1'b1;
    end

    // ── autonomous bridge FSM: buffer -> Zone1 injection (DATA_WRITE) ───────
    // No host involvement -- purely dataflow-triggered, watching the buffer
    // write count against its own read count. Port B's registered read means
    // buf_rdata reflects a write 2 cycles after it happens (1 cycle for the
    // memory array itself, 1 more for the registered output) -- BS_READWAIT
    // below budgets that, the same "don't time it, wait for it" discipline as
    // the bridge-out-triggered read pipeline from last session, just applied
    // with a fixed settle count here since this first pass reads a known-fixed
    // single slot rather than a streamed sequence.
    reg [15:0] bridge_read_count;
    reg [2:0]  brg_state;
    localparam BS_IDLE=0, BS_READWAIT=1, BS_INJECT=2, BS_SETTLE=3;
    reg [1:0] readwait_ctr;
    reg [31:0] buffered_value;

    always @(posedge clk) begin
        if (rst) begin
            bridge_read_count <= 16'h0; brg_state <= BS_IDLE;
            brg_cmd_bus <= 32'h0; brg_cmd_data <= 32'h0; brg_active <= 1'b0;
            buffered_value <= 32'h0; readwait_ctr <= 2'h0;
        end else begin
            brg_active <= 1'b0;
            case (brg_state)
                BS_IDLE: begin
                    if (loader_done && (buffer_write_count != bridge_read_count)) begin
                        readwait_ctr <= 2'h0;
                        brg_state <= BS_READWAIT;
                    end
                end
                BS_READWAIT: begin
                    readwait_ctr <= readwait_ctr + 1'b1;
                    if (readwait_ctr == 2'h2) begin
                        buffered_value <= buf_rdata; // genuinely read off BRAM port B
                        brg_state <= BS_INJECT;
                    end
                end
                BS_INJECT: begin
                    // DATA_WRITE (opcode1): address rides cmd_data[31:16], value IS
                    // cmd_data (whole word) -- existing convention (tb_pcie_bram_v3.v).
                    // Target zone1 cell's input_address (default = CELL_ID = 32).
                    brg_cmd_bus  <= {24'h0, 8'h01};
                    brg_cmd_data <= {16'h0020, buffered_value[15:0]};
                    brg_active <= 1'b1;
                    bridge_read_count <= bridge_read_count + 1'b1;
                    brg_state <= BS_SETTLE;
                end
                BS_SETTLE: brg_state <= BS_IDLE;
                default: brg_state <= BS_IDLE;
            endcase
        end
    end
    assign bridge_hops = bridge_read_count;

    // ── results capture: zone1's fired output (its default output address = ─
    // CELL_ID+1 = 33) lands here -- the repository a host/PCIe read pulls from
    bram_dp_v3 #(.ADDR_W(4), .DATA_W(32)) results_bram (
        .clk(clk),
        .a_addr(4'h0), .a_wdata(z1_out_data), .a_we(z1_out_valid && (z1_out_addr==16'h0021)), .a_rdata(),
        .b_addr(4'h0), .b_wdata(32'h0), .b_we(1'b0), .b_rdata(results_rdata)
    );

endmodule
