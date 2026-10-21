`default_nettype none
// hexn_sdiv_v1.v -- small serial restoring divider (one quotient bit per clock), used once per detector by the training bank to form the midpoint threshold.
module hexn_sdiv_v1 #(parameter NW = 24, parameter DW = 12) (
    input  wire clk, input wire rst, input wire start,
    input  wire [NW-1:0] num, input wire [DW-1:0] den,
    output reg  busy, output reg done,
    output reg  [NW-1:0] q, output wire [DW-1:0] r);
    reg [NW-1:0] n_sh; reg [DW:0] rem; reg [$clog2(NW+1)-1:0] i;
    wire [DW:0] rem2 = {rem[DW-1:0], n_sh[NW-1]};
    assign r = rem[DW-1:0];
    wire        ge   = (rem2 >= {1'b0, den});
    always @(posedge clk) begin
        done <= 1'b0;
        if (rst) begin busy <= 0; done <= 0; q <= 0; end
        else if (start && !busy) begin busy <= 1; n_sh <= num; rem <= 0; q <= 0; i <= 0; end
        else if (busy) begin
            rem  <= ge ? rem2 - {1'b0, den} : rem2;
            q    <= {q[NW-2:0], ge};
            n_sh <= {n_sh[NW-2:0], 1'b0};
            i    <= i + 1'b1;
            if (i == NW - 1) begin busy <= 0; done <= 1; end
        end
    end
endmodule
`default_nettype wire
