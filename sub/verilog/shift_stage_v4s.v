// shift_stage_v4s.v -- points.md #899 experiment: a shift amount FIXED AT BUILD
// TIME (a real Verilog parameter, not a runtime cfg_data field), per Alan's own
// idea (limit each cell to a small range, chain for larger totals) pushed to its
// logical extreme: if the amount is baked into the cell at synthesis time, there
// is nothing left to select at runtime, and the whole mux/compare tree that made
// shift_cell_v4s expensive (1,686 LUT4 for the coarse mux ALONE, measured) can be
// optimized away entirely. This is the same "physics, not control" principle
// applied one level deeper: not just no runtime ROUTING decision, no runtime
// FUNCTION-SELECTION decision either -- the topology of what this cell computes
// is fixed the moment it's built, not the moment it's configured.
//
// Chain several of these (each a different power-of-2 amount, or 0=passthrough)
// to compose any total shift, matching the shift_amt values the original sparse
// table already supported (1,2,4,8,12,16,20,24,28 all being achievable by
// combinations of 1/2/4/8/16, an exact classic log-depth barrel-shifter
// decomposition, not an approximation).
`default_nettype none
`timescale 1ns / 1ps

module shift_stage_v4s #(
    parameter [15:0] CELL_ID   = 16'h0000,
    parameter [4:0]  SHIFT_AMT = 5'd0,     // FIXED at build time: 0=passthrough, else the amount
    parameter        DIRECTION = 1'b0      // FIXED at build time: 0=left, 1=right
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,   // arms the cell; no function config left to load
    input  wire [31:0]  cfg_data,    // unused; kept for a uniform port shape

    input  wire [31:0]  data_in,
    input  wire         valid_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg        armed       = 1'b0;
    reg [31:0] out_buffer  = 32'h0;
    reg        valid_out_r = 1'b0;

    // Build-time-fixed shift -- a real Verilog generate/parameter case, not a
    // runtime mux. Yosys sees SHIFT_AMT/DIRECTION as compile-time constants and
    // reduces this to plain wiring for whichever single case is actually chosen.
    wire [31:0] shifted = (SHIFT_AMT == 5'd0) ? data_in :
                          (DIRECTION == 1'b0) ? (data_in << SHIFT_AMT) :
                                                (data_in >> SHIFT_AMT);

    assign data_out  = out_buffer;
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            armed       <= 1'b0;
            out_buffer  <= 32'h0;
            valid_out_r <= 1'b0;
        end else if (cfg_valid) begin
            armed       <= 1'b1;
            valid_out_r <= 1'b0;
        end else begin
            out_buffer  <= shifted;
            valid_out_r <= armed && valid_in;
        end
    end

endmodule
