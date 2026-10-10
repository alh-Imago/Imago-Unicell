// cordic_z_hs_frz_v1.v -- cordic_z_hs_v1.v (unchanged) plus a FREEZE input and a SCAN CHAIN, plain Verilog, no cells (ledger #1036 addendum 65).
// freeze = 1: every register holds, in_ack and out_valid are forced low so nothing outside can give or take an item. scan_en = 1: all 132 state bits
// (d0, d1, d2, d3, v0, v1, v2, v3) form one shift register, one bit per clock, bit 0 (v3) out first. Priority: rst, scan_en, freeze, normal.
`default_nettype none
module cordic_z_hs_frz_v1 (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze,
    input  wire        scan_en,
    input  wire        scan_in,
    output wire        scan_out,
    input  wire [31:0] in_data,
    input  wire        in_valid,
    output wire        in_ack,
    output wire [31:0] out_data,
    output wire        out_valid,
    input  wire        out_ack
);
    localparam signed [31:0] K0 = 32'sd45000, K1 = 32'sd26565, K2 = 32'sd14036, K3 = 32'sd7125;
    function signed [31:0] step(input signed [31:0] z, input signed [31:0] k);
        reg pos;
        begin
            pos = ~z[31] & (|z[30:0]);
            step = z + (pos ? -k : k);
        end
    endfunction
    reg signed [31:0] d0, d1, d2, d3;
    reg v0, v1, v2, v3;
    wire r3 = !v3 | out_ack;
    wire r2 = !v2 | r3;
    wire r1 = !v1 | r2;
    wire r0 = !v0 | r1;
    assign in_ack = r0 & ~freeze;
    assign out_data = d3;
    assign out_valid = v3 & ~freeze;
    wire [131:0] st = {d0, d1, d2, d3, v0, v1, v2, v3};
    assign scan_out = st[0];
    always @(posedge clk) begin
        if (rst) begin v0 <= 0; v1 <= 0; v2 <= 0; v3 <= 0; end
        else if (scan_en) {d0, d1, d2, d3, v0, v1, v2, v3} <= {scan_in, st[131:1]};
        else if (!freeze) begin
            if (r0) begin v0 <= in_valid; if (in_valid) d0 <= step($signed(in_data), K0); end
            if (r1) begin v1 <= v0;       if (v0)       d1 <= step(d0, K1); end
            if (r2) begin v2 <= v1;       if (v1)       d2 <= step(d1, K2); end
            if (r3) begin v3 <= v2;       if (v2)       d3 <= step(d2, K3); end
        end
    end
endmodule
