// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// loader_fsm_v3.v — synthesizable icmP loader. Walks a small config table into
// the fabric using the exact same wire protocol proved in sim this session
// (tb_bram_loader_v3.v, tb_pcie_bram_v3.v): per cell, SET_TARGET (opcode 24,
// held on the address lane) -> CYCLE 1 (topology + optional methodology-1,
// CMD_LOAD_AT) -> CYCLE 2 (methodology 2+3, or a METH_SET_LANE(0) pad if the
// cell needs neither) -> CYCLE 3 (CMD_LOAD_DONE) -> wait for the REAL
// completion pulse (this cell's zone's emit_count incrementing) before moving
// to the next cell. Also folds in the SET_TARGET-latch / cpu_addr_w transport
// mux that lives in top_arria10_zone1_v3.v, so a top file just wires this
// module's outputs straight to every zone's cmd_bus/cmd_data/cmd_valid/
// cpu_addr/cpu_valid ports (broadcast, same pattern as the real top).
//
// SUPPORTS 2 ZONES for now (matches the card build this lands in). The
// current per-cell record includes an explicit zone_sel bit so the FSM knows
// which zone's emit_count to watch for the completion confirm -- derived at
// table-build time from the target's flat address (bit 5, since
// CELL_BASE = ZONE_ID << 5), not re-derived in hardware, to keep this first
// version simple. Widen NUM_ZONES + the emit_count port when a third zone
// is added.
//
// NCELLS is fixed at elaboration (parameter) with the config table wired in
// from outside (config_target/config_c1_bus/config_c1_data/config_c2_bus/
// config_c2_data/config_zone_sel arrays) rather than owned internally, so a
// sim testbench and a real Quartus initial-value ROM can both feed it the
// same way.
`default_nettype none
`timescale 1ns / 1ps

module loader_fsm_v3 #(
    parameter NCELLS = 2
) (
    input  wire clk,
    input  wire rst,
    input  wire start,                       // pulse to begin loading from cell 0

    // Config table (one entry per cell, driven combinationally by whoever
    // owns the table -- a ROM, a BRAM read port, or (in sim) a plain array).
    input  wire [15:0] config_target   [0:NCELLS-1],
    input  wire [31:0] config_c1_bus   [0:NCELLS-1], // CMD_LOAD_AT word (cmd_bus)
    input  wire [31:0] config_c1_data  [0:NCELLS-1], // CMD_LOAD_AT payload (cmd_data)
    input  wire [31:0] config_c2_bus   [0:NCELLS-1], // cycle-2 methodology word (cmd_bus)
    input  wire [31:0] config_c2_data  [0:NCELLS-1], // cycle-2 payload (cmd_data)
    input  wire        config_zone_sel [0:NCELLS-1], // 0 = zone0's emit_count, 1 = zone1's

    // Zone-facing transport (broadcast to every zone instance in the top file)
    output reg  [31:0] cmd_bus,
    output reg  [31:0] cmd_data,
    output reg         cmd_valid,
    output wire [15:0] cpu_addr,
    output reg         cpu_valid,

    // Completion tracking, one emit_count per zone (widen alongside NUM_ZONES)
    input  wire [15:0] emit_count_z0,
    input  wire [15:0] emit_count_z1,

    output reg          done,        // sticky: all NCELLS cells confirmed loaded
    output reg [$clog2(NCELLS+1)-1:0] cells_confirmed
);

    localparam [7:0] OP_SET_TARGET = 8'd24;
    localparam [7:0] OP_LOAD_DONE  = 8'd27;

    // ── SET_TARGET latch + address-lane mux (the top_arria10 transport, ─────
    // folded in here so every zone in the top file just takes this module's
    // outputs directly). See the fixed whitelist from this session's BRAM
    // loader bug: opcodes 30-33 (the real, self-describing cycle-2 opcodes)
    // must be included, or a second cell's cycle-2 word clobbers bus_addr.
    reg [15:0] load_target;
    wire is_target_opcode = (cmd_bus[7:0]==8'd23)  // CMD_LOAD_AT
                          || (cmd_bus[7:0]==8'd2)  // SET_INPUT_ADDR
                          || (cmd_bus[7:0]==8'd3)  // SET_OUTPUT_ADDR
                          || (cmd_bus[7:0]==8'd30) // METH_SET_MASK
                          || (cmd_bus[7:0]==8'd31) // METH_SET_SHIFT_IN
                          || (cmd_bus[7:0]==8'd32) // METH_SET_SHIFT_OUT
                          || (cmd_bus[7:0]==8'd33) // METH_SET_LANE
                          || (cmd_bus[7:0]==OP_LOAD_DONE);
    assign cpu_addr = is_target_opcode ? load_target : cmd_data[15:0];

    always @(posedge clk) begin
        if (rst) load_target <= 16'h0;
        else if (cpu_valid && cmd_bus[7:0]==OP_SET_TARGET) load_target <= cmd_data[15:0];
    end

    // ── FSM ───────────────────────────────────────────────────────────────
    // S_TARGET_SETTLE exists because SET_TARGET's new address takes 2 cycles
    // to reach a cell's config_match (1 cycle: the array's own bus_addr
    // register; 1 more: the cell's own bus_addr_r register). Issuing the very
    // next command with zero gap risks it landing on the STALE address
    // (whichever cell was targeted before) instead of the new one -- exactly
    // the hazard this session's BRAM-loader bug traced back to. The sim-only
    // testbenches didn't catch this here because they either used an explicit
    // settle cycle (tb_bram_loader_v3.v) or happened to target address 0,
    // which needs no settle since it's the reset default (tb_pcie_bram_v3.v's
    // single-cell burst write). A synthesizable loader can't rely on luck.
    localparam S_IDLE=0, S_TARGET=1, S_TARGET_SETTLE=2, S_C1=3, S_C2=4, S_C3=5, S_WAIT=6, S_DONE=7;
    reg [2:0] state;
    reg [$clog2(NCELLS+1)-1:0] cell_idx;
    reg [15:0] emit_before;
    wire [15:0] emit_sel = config_zone_sel[cell_idx] ? emit_count_z1 : emit_count_z0;

    always @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE; cell_idx <= 0; done <= 1'b0; cells_confirmed <= 0;
            cmd_bus <= 32'h0; cmd_data <= 32'h0; cmd_valid <= 1'b0; cpu_valid <= 1'b0;
            emit_before <= 16'h0;
        end else begin
            cmd_valid <= 1'b0; cpu_valid <= 1'b0;
            case (state)
                S_IDLE: if (start) begin cell_idx <= 0; done <= 1'b0; cells_confirmed <= 0; state <= S_TARGET; end
                S_TARGET: begin
                    cmd_bus <= {24'h0, OP_SET_TARGET}; cmd_data <= {16'h0, config_target[cell_idx]};
                    cmd_valid <= 1'b1; cpu_valid <= 1'b1;
                    state <= S_TARGET_SETTLE;
                end
                S_TARGET_SETTLE: state <= S_C1; // no cmd_valid this cycle -- let bus_addr_r catch up
                S_C1: begin
                    cmd_bus <= config_c1_bus[cell_idx]; cmd_data <= config_c1_data[cell_idx];
                    cmd_valid <= 1'b1; cpu_valid <= 1'b1;
                    state <= S_C2;
                end
                S_C2: begin
                    cmd_bus <= config_c2_bus[cell_idx]; cmd_data <= config_c2_data[cell_idx];
                    cmd_valid <= 1'b1; cpu_valid <= 1'b1;
                    state <= S_C3;
                end
                S_C3: begin
                    cmd_bus <= {24'h0, OP_LOAD_DONE}; cmd_data <= 32'h0;
                    cmd_valid <= 1'b1; cpu_valid <= 1'b1;
                    emit_before <= emit_sel;
                    state <= S_WAIT;
                end
                S_WAIT: begin
                    if (emit_sel != emit_before) begin
                        cells_confirmed <= cells_confirmed + 1'b1;
                        if (cell_idx == NCELLS-1) state <= S_DONE;
                        else begin cell_idx <= cell_idx + 1'b1; state <= S_TARGET; end
                    end
                    // else: keep waiting -- no fixed delay, real event only
                end
                S_DONE: begin done <= 1'b1; end // sticky
                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
