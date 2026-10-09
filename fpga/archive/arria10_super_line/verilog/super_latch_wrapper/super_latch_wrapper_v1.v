// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// super_latch_wrapper_v1.v — points.md #562: Alan's own real,
// explicitly-experimental idea. Extract the SUPER_LATCH register and
// all per-core config-distribution logic (currently inline inside
// unicell_super_v3.v) into its own separate, standalone module — a
// single, real, isolated structural change, with everything else
// about the shell (the 8 core instantiations, the output mux) left
// completely untouched, so any real difference in Quartus's own ALM
// result can be attributed specifically to THIS change.
//
// THE REAL, HONEST QUESTION THIS TESTS, not assumed either way:
// Quartus flattens module hierarchy before Boolean-level optimization
// in principle, so where a register lives in the source SHOULDN'T
// change what optimizations are legally available. But real synthesis
// tools are heuristic-driven, not globally-optimal solvers -- a
// different structural presentation of the same logic CAN, in
// practice, put a real tool on a different optimization path even
// when the theoretical best result is identical either way. The only
// honest way to know is to build this and measure it for real.
//
// Zero change to the 8 existing core files -- adder_cell_v1.v,
// accumulator_cell_v1.v, etc. are used completely unmodified. This is
// the real reason this specific restructuring was chosen over
// modifying the cores directly (the experimental_shared_buffer_v1/
// README's own "Option A") -- it doesn't touch anything already
// silicon-proven and used standalone elsewhere.
`default_nettype none
`timescale 1ns / 1ps

module super_latch_wrapper_v1 (
    input  wire         clk,
    input  wire         rst,
    input  wire         cfg_valid,
    input  wire [79:0]  cfg_data,

    output wire [4:0]   core_select,
    output wire [41:0]  core_config,
    output wire [19:0]  addon_config,

    output wire         cfg_valid_nano,  cfg_valid_ram,   cfg_valid_adder, cfg_valid_acc,
    output wire         cfg_valid_cmp,   cfg_valid_latch, cfg_valid_seq,   cfg_valid_branch,

    output wire         sel_active_nano,  sel_active_ram,   sel_active_adder, sel_active_acc,
    output wire         sel_active_cmp,   sel_active_latch, sel_active_seq,   sel_active_branch
);

    // ── Identical logic to unicell_super_v3.v's own real, original
    // inline version -- a pure extraction, zero behavioral change. ──
    reg [79:0] super_latch = 80'h0;
    always @(posedge clk) begin
        if (rst) super_latch <= 80'h0;
        else if (cfg_valid) super_latch <= cfg_data;
    end

    assign core_select  = super_latch[4:0];
    assign core_config  = super_latch[46:5];
    assign addon_config = super_latch[66:47];

    wire [4:0] incoming_select = cfg_data[4:0];

    localparam [4:0] SEL_NANO = 5'd0, SEL_RAM = 5'd1, SEL_ADDER = 5'd2,
                      SEL_ACC = 5'd3, SEL_CMP = 5'd4, SEL_LATCH = 5'd5,
                      SEL_SEQ = 5'd6, SEL_BRANCH = 5'd7;

    assign cfg_valid_nano   = cfg_valid && (incoming_select == SEL_NANO);
    assign cfg_valid_ram    = cfg_valid && (incoming_select == SEL_RAM);
    assign cfg_valid_adder  = cfg_valid && (incoming_select == SEL_ADDER);
    assign cfg_valid_acc    = cfg_valid && (incoming_select == SEL_ACC);
    assign cfg_valid_cmp    = cfg_valid && (incoming_select == SEL_CMP);
    assign cfg_valid_latch  = cfg_valid && (incoming_select == SEL_LATCH);
    assign cfg_valid_seq    = cfg_valid && (incoming_select == SEL_SEQ);
    assign cfg_valid_branch = cfg_valid && (incoming_select == SEL_BRANCH);

    assign sel_active_nano   = (core_select == SEL_NANO);
    assign sel_active_ram    = (core_select == SEL_RAM);
    assign sel_active_adder  = (core_select == SEL_ADDER);
    assign sel_active_acc    = (core_select == SEL_ACC);
    assign sel_active_cmp    = (core_select == SEL_CMP);
    assign sel_active_latch  = (core_select == SEL_LATCH);
    assign sel_active_seq    = (core_select == SEL_SEQ);
    assign sel_active_branch = (core_select == SEL_BRANCH);

endmodule
