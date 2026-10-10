// cordic_z_hs_v1.v -- HAND-WRITTEN baseline, same function as cordic_z_pipe_v1.v, but with the SAME valid / ack handshake the UniCell flex cells use:
// every stage holds one item and passes it on only when the next stage can take it. (A stage can take a new item when it is empty or its
// own item is leaving this cycle.) Ports match the generated UniCell module apart from the clock, reset and configuration pins.
`default_nettype none
module cordic_z_hs_v1 (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] in_data,
    input  wire        in_valid,
    output wire        in_ack,
    output wire [31:0] out_data,
    output wire        out_valid,
    input  wire        out_ack
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
    reg signed [31:0] d0, d1, d2, d3;
    reg v0, v1, v2, v3;
    wire r3 = !v3 | out_ack;
    wire r2 = !v2 | r3;
    wire r1 = !v1 | r2;
    wire r0 = !v0 | r1;
    assign in_ack = r0;
    assign out_data = d3;
    assign out_valid = v3;
    always @(posedge clk) begin
        if (rst) begin v0 <= 0; v1 <= 0; v2 <= 0; v3 <= 0; end
        else begin
            if (r0) begin v0 <= in_valid; if (in_valid) d0 <= step($signed(in_data), K0); end
            if (r1) begin v1 <= v0;       if (v0)       d1 <= step(d0, K1); end
            if (r2) begin v2 <= v1;       if (v1)       d2 <= step(d1, K2); end
            if (r3) begin v3 <= v2;       if (v2)       d3 <= step(d2, K3); end
        end
    end
endmodule
