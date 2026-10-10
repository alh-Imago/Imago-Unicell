// cordic_z_pipe_v1.v -- HAND-WRITTEN baseline for the UniCell CORDIC z-convergence example (ledger #1036 addendum 58).
// Same function as nano/examples/cordic_z_convergence.icm-hier.json, 32-bit signed, 4 stages: each stage does
//   z > 0 (signed, non-zero)  ->  z - K_i     else (z < 0 or z == 0) -> z + K_i
// with K = 45000, 26565, 14036, 7125 (atan(2^-i) in degrees x 1000). Note z == 0 takes the ADD side, as the UniCell branch cell's route_equal does.
// This version is the plainest hardware: one register per stage and a valid bit; NO back-pressure (the consumer must always take a result).
`default_nettype none
module cordic_z_pipe_v1 (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] in_data,
    input  wire        in_valid,
    output reg  [31:0] out_data,
    output reg         out_valid
);
    localparam signed [31:0] K0 = 32'sd45000, K1 = 32'sd26565, K2 = 32'sd14036, K3 = 32'sd7125;
    // one adder per stage: pick +K or -K from the sign/zero test, then add. z > 0 means "not negative and not zero".
    function signed [31:0] step(input signed [31:0] z, input signed [31:0] k);
        reg pos;
        begin
            pos = ~z[31] & (|z[30:0]);
            step = z + (pos ? -k : k);
        end
    endfunction
    reg signed [31:0] z1, z2, z3;
    reg v1, v2, v3;
    always @(posedge clk) begin
        if (rst) begin v1 <= 0; v2 <= 0; v3 <= 0; out_valid <= 0; end
        else begin
            v1 <= in_valid; v2 <= v1; v3 <= v2; out_valid <= v3;
        end
        z1 <= step($signed(in_data), K0);
        z2 <= step(z1, K1);
        z3 <= step(z2, K2);
        out_data <= step(z3, K3);
    end
endmodule
