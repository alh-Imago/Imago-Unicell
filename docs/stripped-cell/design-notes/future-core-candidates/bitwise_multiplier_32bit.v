// 32-bit Single-Stage Combinational Array Multiplier
// Designed for FPGA deployment with zero clock cycles of latency.
// Fully parallelized logic using standard structural bitmasks and shifts.

module bitwise_multiplier_32bit (
    input  wire [31:0] A,
    input  wire [31:0] B,
    output wire [63:0] Product
);

    // Step 1: Generate all 32 partial products in parallel.
    // Each partial product is 64 bits wide to prevent overflow.
    // If bit B[i] is 1, the partial product is A shifted left by i.
    // If bit B[i] is 0, the partial product is 0.
    wire [63:0] pp [31:0];

    assign pp[0]  = B[0]  ? {32'b0, A} : 64'b0;
    assign pp[1]  = B[1]  ? ({32'b0, A} << 1) : 64'b0;
    assign pp[2]  = B[2]  ? ({32'b0, A} << 2) : 64'b0;
    assign pp[3]  = B[3]  ? ({32'b0, A} << 3) : 64'b0;
    assign pp[4]  = B[4]  ? ({32'b0, A} << 4) : 64'b0;
    assign pp[5]  = B[5]  ? ({32'b0, A} << 5) : 64'b0;
    assign pp[6]  = B[6]  ? ({32'b0, A} << 6) : 64'b0;
    assign pp[7]  = B[7]  ? ({32'b0, A} << 7) : 64'b0;
    assign pp[8]  = B[8]  ? ({32'b0, A} << 8) : 64'b0;
    assign pp[9]  = B[9]  ? ({32'b0, A} << 9) : 64'b0;
    assign pp[10] = B[10] ? ({32'b0, A} << 10) : 64'b0;
    assign pp[11] = B[11] ? ({32'b0, A} << 11) : 64'b0;
    assign pp[12] = B[12] ? ({32'b0, A} << 12) : 64'b0;
    assign pp[13] = B[13] ? ({32'b0, A} << 13) : 64'b0;
    assign pp[14] = B[14] ? ({32'b0, A} << 14) : 64'b0;
    assign pp[15] = B[15] ? ({32'b0, A} << 15) : 64'b0;
    assign pp[16] = B[16] ? ({32'b0, A} << 16) : 64'b0;
    assign pp[17] = B[17] ? ({32'b0, A} << 17) : 64'b0;
    assign pp[18] = B[18] ? ({32'b0, A} << 18) : 64'b0;
    assign pp[19] = B[19] ? ({32'b0, A} << 19) : 64'b0;
    assign pp[20] = B[20] ? ({32'b0, A} << 20) : 64'b0;
    assign pp[21] = B[21] ? ({32'b0, A} << 21) : 64'b0;
    assign pp[22] = B[22] ? ({32'b0, A} << 22) : 64'b0;
    assign pp[23] = B[23] ? ({32'b0, A} << 23) : 64'b0;
    assign pp[24] = B[24] ? ({32'b0, A} << 24) : 64'b0;
    assign pp[25] = B[25] ? ({32'b0, A} << 25) : 64'b0;
    assign pp[26] = B[26] ? ({32'b0, A} << 26) : 64'b0;
    assign pp[27] = B[27] ? ({32'b0, A} << 27) : 64'b0;
    assign pp[28] = B[28] ? ({32'b0, A} << 28) : 64'b0;
    assign pp[29] = B[29] ? ({32'b0, A} << 29) : 64'b0;
    assign pp[30] = B[30] ? ({32'b0, A} << 30) : 64'b0;
    assign pp[31] = B[31] ? ({32'b0, A} << 31) : 64'b0;

    // Step 2: Sum all partial products instantly via an adder tree.
    // The synthesiser collapses this tree into an optimised look-up table (LUT) routing structure.
    assign Product = pp[0]  + pp[1]  + pp[2]  + pp[3]  + pp[4]  + pp[5]  + pp[6]  + pp[7]  +
                     pp[8]  + pp[9]  + pp[10] + pp[11] + pp[12] + pp[13] + pp[14] + pp[15] +
                     pp[16] + pp[17] + pp[18] + pp[19] + pp[20] + pp[21] + pp[22] + pp[23] +
                     pp[24] + pp[25] + pp[26] + pp[27] + pp[28] + pp[29] + pp[30] + pp[31];

endmodule
