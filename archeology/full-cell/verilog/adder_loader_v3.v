// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// adder_loader_v3.v — purpose-built loader for the 45-cell packed shift-
// adder (docs/design-notes/packed_adder_cluster_mesh.md). NOT a general
// reusable component (that's loader_fsm_v3.v's job for the simpler 3-cycle
// case) -- this one is wider because this specific design needs two things
// loader_fsm_v3.v doesn't have:
//   1. SET_INPUT_ADDR + SET_OUTPUT_ADDR as explicit per-cell steps (every
//      cell here needs a specific, non-default output target; two cells
//      also need a non-default input target). Applied uniformly to all
//      cells (even where the value equals the existing default) rather
//      than conditionally skipped, to keep the FSM's per-cell sequence a
//      single fixed shape -- a few redundant writes, much simpler FSM.
//   2. A PRIMING phase after the main load: every relay/shift-role cell
//      (PASS_B + latch_in) needs CMD_SWAP_AB before it can fire correctly
//      on its first-ever value (tb_v3_shl_cell.v, this session -- a cold
//      one-shot cell's first value can't self-trigger). No completion
//      pulse exists for CMD_SWAP_AB, so this phase uses a fixed settle
//      count instead of an event wait -- acceptable for a one-time setup
//      step whose timing is already known from the main load's own
//      SET_TARGET settle requirement.
//
// Supports up to 16 clusters (NCLUSTERS param, zone_sel width fixed at 4
// bits) -- this build uses 9.
`default_nettype none
`timescale 1ns / 1ps

module adder_loader_v3 #(
    parameter NCELLS  = 85,
    parameter NPRIME  = 68,
    parameter NCLUSTERS = 18
) (
    input  wire clk,
    input  wire rst,
    input  wire start,

    // Per-cell config table (driven combinationally by whoever owns it --
    // a plain array in the top file for this build).
    input  wire [15:0] cfg_target     [0:NCELLS-1],
    input  wire [15:0] cfg_input_addr [0:NCELLS-1],
    input  wire [15:0] cfg_output_addr[0:NCELLS-1],
    input  wire [31:0] cfg_c1_bus     [0:NCELLS-1], // CMD_LOAD_AT word
    input  wire [31:0] cfg_c1_data    [0:NCELLS-1],
    input  wire [31:0] cfg_c2_bus     [0:NCELLS-1], // cycle-2 methodology word
    input  wire [31:0] cfg_c2_data    [0:NCELLS-1],
    input  wire [7:0]  cfg_cluster    [0:NCELLS-1], // which cluster's emit_count to watch

    // Priming table: which cell IDs need CMD_SWAP_AB after the main load
    input  wire [15:0] prime_target   [0:NPRIME-1],

    // Zone-facing transport (broadcast to every cluster)
    output reg  [31:0] cmd_bus,
    output reg  [31:0] cmd_data,
    output reg         cmd_valid,
    output wire [15:0] cpu_addr,
    output reg         cpu_valid,

    input  wire [15:0] emit_count [0:NCLUSTERS-1],

    output reg done  // sticky: main load AND priming both complete
);

    localparam [7:0] OP_SET_TARGET      = 8'd24;
    localparam [7:0] OP_SET_INPUT_ADDR  = 8'd2;
    localparam [7:0] OP_SET_OUTPUT_ADDR = 8'd3;
    localparam [7:0] OP_LOAD_AT         = 8'd23;
    localparam [7:0] OP_LOAD_DONE       = 8'd27;
    localparam [7:0] OP_SWAP_AB         = 8'd18;

    // ── SET_TARGET latch + address-lane mux (same transport as the rest ────
    // of this session's work; includes 30-33 from the earlier bug fix)
    reg [15:0] load_target;
    wire is_target_opcode = (cmd_bus[7:0]==OP_LOAD_AT)
                          || (cmd_bus[7:0]==OP_SET_INPUT_ADDR)
                          || (cmd_bus[7:0]==OP_SET_OUTPUT_ADDR)
                          || (cmd_bus[7:0]==8'd30) || (cmd_bus[7:0]==8'd31)
                          || (cmd_bus[7:0]==8'd32) || (cmd_bus[7:0]==8'd33)
                          || (cmd_bus[7:0]==OP_LOAD_DONE)
                          || (cmd_bus[7:0]==OP_SWAP_AB);
    assign cpu_addr = is_target_opcode ? load_target : cmd_data[15:0];

    always @(posedge clk) begin
        if (rst) load_target <= 16'h0;
        else if (cpu_valid && cmd_bus[7:0]==OP_SET_TARGET) load_target <= cmd_data[15:0];
    end

    // ── FSM ───────────────────────────────────────────────────────────────
    localparam S_IDLE=0, S_TARGET=1, S_SETTLE=2, S_INADDR=3, S_OUTADDR=4,
               S_C1=5, S_C2=6, S_C3=7, S_WAIT=8,
               S_PRIME_TARGET=9, S_PRIME_SETTLE=10, S_PRIME_SWAP=11, S_PRIME_WAIT=12,
               S_DONE=13;
    reg [4:0] state;
    reg [$clog2(NCELLS+1)-1:0] cell_idx;
    reg [$clog2(NPRIME+1)-1:0] prime_idx;
    reg [15:0] emit_before;
    reg [2:0]  prime_settle_ctr;
    wire [15:0] emit_sel = emit_count[cfg_cluster[cell_idx]];

    always @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE; cell_idx <= 0; prime_idx <= 0; done <= 1'b0;
            cmd_bus <= 32'h0; cmd_data <= 32'h0; cmd_valid <= 1'b0; cpu_valid <= 1'b0;
            emit_before <= 16'h0; prime_settle_ctr <= 3'h0;
        end else begin
            cmd_valid <= 1'b0; cpu_valid <= 1'b0;
            case (state)
                S_IDLE: if (start) begin cell_idx<=0; done<=1'b0; state<=S_TARGET; end

                S_TARGET: begin
                    cmd_bus <= {24'h0, OP_SET_TARGET}; cmd_data <= {16'h0, cfg_target[cell_idx]};
                    cmd_valid<=1'b1; cpu_valid<=1'b1; state<=S_SETTLE;
                end
                S_SETTLE: state <= S_INADDR; // idle cycle -- bus_addr_r catch-up

                S_INADDR: begin
                    cmd_bus <= {24'h0, OP_SET_INPUT_ADDR}; cmd_data <= {16'h0, cfg_input_addr[cell_idx]};
                    cmd_valid<=1'b1; cpu_valid<=1'b1; state<=S_OUTADDR;
                end
                S_OUTADDR: begin
                    cmd_bus <= {24'h0, OP_SET_OUTPUT_ADDR}; cmd_data <= {16'h0, cfg_output_addr[cell_idx]};
                    cmd_valid<=1'b1; cpu_valid<=1'b1; state<=S_C1;
                end
                S_C1: begin
                    cmd_bus <= cfg_c1_bus[cell_idx]; cmd_data <= cfg_c1_data[cell_idx];
                    cmd_valid<=1'b1; cpu_valid<=1'b1; state<=S_C2;
                end
                S_C2: begin
                    cmd_bus <= cfg_c2_bus[cell_idx]; cmd_data <= cfg_c2_data[cell_idx];
                    cmd_valid<=1'b1; cpu_valid<=1'b1; state<=S_C3;
                end
                S_C3: begin
                    cmd_bus <= {24'h0, OP_LOAD_DONE}; cmd_data <= 32'h0;
                    cmd_valid<=1'b1; cpu_valid<=1'b1;
                    emit_before <= emit_sel; state<=S_WAIT;
                end
                S_WAIT: begin
                    if (emit_sel != emit_before) begin
                        if (cell_idx == NCELLS-1) begin
                            prime_idx <= 0; state <= S_PRIME_TARGET;
                        end else begin
                            cell_idx <= cell_idx + 1'b1; state <= S_TARGET;
                        end
                    end
                end

                // ── Priming phase: fixed-settle, no completion event ───────
                S_PRIME_TARGET: begin
                    cmd_bus <= {24'h0, OP_SET_TARGET}; cmd_data <= {16'h0, prime_target[prime_idx]};
                    cmd_valid<=1'b1; cpu_valid<=1'b1; state<=S_PRIME_SETTLE;
                end
                S_PRIME_SETTLE: state <= S_PRIME_SWAP;
                S_PRIME_SWAP: begin
                    cmd_bus <= {24'h0, OP_SWAP_AB}; cmd_data <= 32'h0;
                    cmd_valid<=1'b1; cpu_valid<=1'b1;
                    prime_settle_ctr <= 3'h0; state<=S_PRIME_WAIT;
                end
                S_PRIME_WAIT: begin
                    prime_settle_ctr <= prime_settle_ctr + 1'b1;
                    if (prime_settle_ctr == 3'h3) begin
                        if (prime_idx == NPRIME-1) state <= S_DONE;
                        else begin prime_idx <= prime_idx + 1'b1; state <= S_PRIME_TARGET; end
                    end
                end

                S_DONE: done <= 1'b1;
                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
