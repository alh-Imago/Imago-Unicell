// tb_mul_cell_v4s_dsp2_stub.v -- points.md #901: SIMULATION-ONLY behavioural
// stand-in for the real MULT36X36 blackbox, used only because yosys's own
// cells_sim.v ships no functional model for it (confirmed by inspection). This
// module is NEVER used for synthesis -- real synthesis reads mul_cell_v4s_dsp2.v
// directly against yosys's own real MULT36X36 blackbox declaration. This stub
// exists purely so iverilog has something to execute while checking that this
// file's own wiring (zero-extension, output bit selection) is correct; its
// internal behaviour (unsigned A*B, unregistered, matching AREG=BREG=OUT0_REG=0)
// is asserted to match the real primitive's documented behaviour, not verified
// against Gowin's own silicon or any vendor simulation model.
module MULT36X36 #(
    parameter AREG = 1'b0, parameter BREG = 1'b0,
    parameter OUT0_REG = 1'b0, parameter OUT1_REG = 1'b0,
    parameter PIPE_REG = 1'b0, parameter ASIGN_REG = 1'b0, parameter BSIGN_REG = 1'b0,
    parameter MULT_RESET_MODE = "SYNC"
) (
    input  wire [35:0] A,
    input  wire [35:0] B,
    input  wire        ASIGN, BSIGN,
    input  wire        CE,
    input  wire        CLK,
    input  wire        RESET,
    output wire [71:0] DOUT
);
    // Unregistered (AREG=BREG=OUT0_REG=0 in every real use in this file): a
    // plain combinational multiply, matching the primitive's own documented
    // default behaviour for that configuration.
    assign DOUT = A * B;
endmodule

`timescale 1ns/1ps
module tb_mul_cell_v4s_dsp2;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] in_a = 0, in_b = 0;
    reg valid_in = 0;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    mul_cell_v4s_dsp2 dut (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(32'h0),
        .in_a(in_a), .in_b(in_b), .valid_in(valid_in),
        .data_out(data_out), .valid_out(valid_out)
    );

    integer errors = 0;
    task check(input [31:0] expected, input [255:0] label);
        begin
            if (data_out !== expected) begin
                $display("FAIL [%0s]: expected %h got %h", label, expected, data_out);
                errors = errors + 1;
            end else $display("PASS [%0s]: %h", label, data_out);
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;

        in_a = 32'd6; in_b = 32'd7; valid_in = 1;
        @(posedge clk); #1; check(32'd42, "6*7=42");

        in_a = 32'hFFFFFFFF; in_b = 32'hFFFFFFFF;
        @(posedge clk); #1; check(32'h00000001, "truncated low32, matches mul_cell_v4s exactly");

        in_a = 32'd100; in_b = 32'd0;
        @(posedge clk); #1; check(32'd0, "100*0=0");
        valid_in = 0;

        if (errors == 0) $display("ALL PASS (wiring verified against a stub -- NOT Gowin's own model)");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
