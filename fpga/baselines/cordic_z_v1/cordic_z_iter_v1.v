// cordic_z_iter_v1.v -- HAND-WRITTEN baseline, same function, the SMALLEST form: ONE add/subtract unit reused for the four iterations (a loop),
// constants from a tiny table. Takes one item at a time (valid / ack), result after 4 clock cycles of work. Shows what plain hardware costs when
// throughput is traded for area; UniCell's design holds items in a pipeline of cells.
`default_nettype none
module cordic_z_iter_v1 (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] in_data,
    input  wire        in_valid,
    output wire        in_ack,
    output wire [31:0] out_data,
    output wire        out_valid,
    input  wire        out_ack
);
    reg signed [31:0] z;
    reg [2:0] n;           // 0 = idle, 1..4 = iteration number being done next, 5 = result waiting
    wire signed [31:0] k = (n == 3'd1) ? 32'sd45000 : (n == 3'd2) ? 32'sd26565 : (n == 3'd3) ? 32'sd14036 : 32'sd7125;
    assign in_ack = (n == 3'd0);
    assign out_valid = (n == 3'd5);
    assign out_data = z;
    always @(posedge clk) begin
        if (rst) n <= 0;
        else if (n == 3'd0) begin if (in_valid) begin z <= $signed(in_data); n <= 3'd1; end end
        else if (n == 3'd5) begin if (out_ack) n <= 3'd0; end
        else begin z <= z + ((~z[31] & (|z[30:0])) ? -k : k); n <= n + 3'd1; end
    end
endmodule
