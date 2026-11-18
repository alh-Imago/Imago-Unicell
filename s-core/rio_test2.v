// rio_test2.v - rio16 again with the write written per bit and the read per output lane (ledger #1365); rio1 is in rio_test.v.
module rio16b (input clk, input [31:0] word, input [4:0] k, input [15:0] wd, input [2:0] lw, input we, output [15:0] rd, output reg [31:0] acc);
    // digit index for width 2^lw is k (0..32>>lw-1).  Bit i belongs to digit i>>lw, lane i&(2^lw-1).
    wire [4:0] kk = k;
    // write: bit i updates when k equals its digit index under the chosen width
    wire [31:0] upd;
    wire [31:0] val;
    genvar i, l;
    generate for (i = 0; i < 32; i = i + 1) begin : wb
        assign upd[i] = we & ((lw == 3'd0) ? (kk == i) :
                              (lw == 3'd1) ? (kk == (i >> 1)) :
                              (lw == 3'd2) ? (kk == (i >> 2)) :
                              (lw == 3'd3) ? (kk == (i >> 3)) : (kk == (i >> 4)));
        assign val[i] = (lw == 3'd0) ? wd[0] : (lw == 3'd1) ? wd[i & 1] : (lw == 3'd2) ? wd[i & 3] : (lw == 3'd3) ? wd[i & 7] : wd[i & 15];
        always @(posedge clk) if (upd[i]) acc[i] <= val[i];
    end endgenerate
    // read: lane l of the output = word bit (l + W*k) for l < W
    generate for (l = 0; l < 16; l = l + 1) begin : rl
        wire [31:0] w = word;
        reg o;
        always @* begin
            o = 1'b0;
            case (lw)
                3'd0: if (l < 1)  o = w[kk];
                3'd1: if (l < 2)  o = w[{kk[3:0],1'b0} + l];
                3'd2: if (l < 4)  o = w[{kk[2:0],2'b0} + l];
                3'd3: if (l < 8)  o = w[{kk[1:0],3'b0} + l];
                default: o = kk[0] ? w[16 + l] : w[l];
            endcase
        end
        assign rd[l] = o;
    end endgenerate
endmodule
