// unicell_array_stub.v — empty stub for TX debug build
// Replaces full unicell_array to isolate TX path issue
module unicell_array #(
    parameter NUM_CELLS    = 8,
    parameter BASE_ADDRESS = 0
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze,
    input  wire [31:0] cpu_addr,
    input  wire [31:0] cpu_data,
    input  wire        cpu_valid,
    input  wire        cpu_inject,
    output wire [31:0] out_addr,
    output wire [31:0] out_data,
    output wire        out_valid,
    output wire [15:0] armed_count,
    output wire [31:0] cycle_count
);
    assign out_addr    = 32'h0;
    assign out_data    = 32'h0;
    assign out_valid   = 1'b0;
    assign armed_count = 16'h0;
    assign cycle_count = 32'h0;
endmodule
