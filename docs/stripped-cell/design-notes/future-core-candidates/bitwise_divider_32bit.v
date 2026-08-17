// 32-Bit Combinational Array Divider (Single-Stage / No Clock)
// Implements a completely unrolled combinational division algorithm.
// Output contains both the quotient and the remainder.
// Warning: This creates a very long propagation delay (critical path).

module bitwise_divider_32bit (
    input  wire [31:0] dividend,
    input  wire [31:0] divisor,
    output wire [31:0] quotient,
    output wire [31:0] remainder
);

    // Intermediate wires to pass the running partial remainder and quotient down the chain
    // Each index i represents the state BEFORE calculating bit i of the quotient (from 31 down to 0)
    wire [31:0] r [0:32];
    wire [31:0] q;

    // Initial state: The first remainder starts as zero
    assign r[32] = 32'b0;

    // Unrolled Array Structure (32 stages of combinational subtract-and-shift)
    genvar i;
    generate
        for (i = 31; i >= 0; i = i - 1) begin : div_stage
            // Left shift the running remainder by 1, bringing in the next bit of the dividend
            wire [32:0] shifted_rem = {r[i+1][30:0], dividend[i]};
            
            // Perform trial subtraction
            wire [32:0] sub_res = shifted_rem - {1'b0, divisor};
            
            // If the subtraction results in a positive value (MSB/borrow bit is 0), 
            // the divisor fits, the quotient bit is 1, and the new remainder is the subtraction result.
            // Otherwise, the divisor doesn't fit, the quotient bit is 0, and we keep the shifted remainder.
            assign q[i]    = ~sub_res[32];
            assign r[i]    = q[i] ? sub_res[31:0] : shifted_rem[31:0];
        end
    </generate>

    // Assign final outputs
    assign quotient  = q;
    assign remainder = r[0];

endmodule
