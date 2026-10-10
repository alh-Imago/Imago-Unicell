// cordic_z_pipe_frz_v1.v -- cordic_z_pipe_v1.v (unchanged) plus a FREEZE input and a SCAN CHAIN, plain Verilog, no cells (ledger #1036 addendum 65).
// freeze = 1: every register holds (a clock enable). scan_en = 1: all 132 state bits form one shift register (z1, z2, z3, out_data, v1, v2, v3, out_valid; bit 0 =
// out_valid is shifted out first); one bit per clock; scan_in enters at the top. Priority: rst, then scan_en, then freeze, then normal operation.
// This pipeline has NO back-pressure, so the freeze must also stop whatever feeds it and takes from it (the environment holds in_valid and ignores out_valid).
`default_nettype none
module cordic_z_pipe_frz_v1 (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze,
    input  wire        scan_en,
    input  wire        scan_in,
    output wire        scan_out,
    input  wire [31:0] in_data,
    input  wire        in_valid,
    output reg  [31:0] out_data,
    output reg         out_valid
);
    localparam signed [31:0] K0 = 32'sd45000, K1 = 32'sd26565, K2 = 32'sd14036, K3 = 32'sd7125;
    function signed [31:0] step(input signed [31:0] z, input signed [31:0] k);
        reg pos;
        begin
            pos = ~z[31] & (|z[30:0]);
            step = z + (pos ? -k : k);
        end
    endfunction
    reg signed [31:0] z1, z2, z3;
    reg v1, v2, v3;
    wire [131:0] st = {z1, z2, z3, out_data, v1, v2, v3, out_valid};
    assign scan_out = st[0];
    always @(posedge clk) begin
        if (rst) begin v1 <= 0; v2 <= 0; v3 <= 0; out_valid <= 0; end
        else if (scan_en) {z1, z2, z3, out_data, v1, v2, v3, out_valid} <= {scan_in, st[131:1]};
        else if (!freeze) begin
            v1 <= in_valid; v2 <= v1; v3 <= v2; out_valid <= v3;
            z1 <= step($signed(in_data), K0);
            z2 <= step(z1, K1);
            z3 <= step(z2, K2);
            out_data <= step(z3, K3);
        end
    end
endmodule
