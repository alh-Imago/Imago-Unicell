`default_nettype none
// hexn_cell_probe_v1 -- MEASUREMENT PROTOTYPES for the UCC v2 idea (Alan, 2 Nov 2026 05:49 to 05:55): a hex cell whose six faces are the six inputs of a look-up table, data sent bit-serial. Not a design; counts only.
//   hexn_lut6_cell_v1     table of 64 bits held in FLIP-FLOPS (shift-loaded), output registered:  out <= tbl[faces]
//   hexn_lut6_cell_ram_v1 table of 64 bits held in a small MEMORY (written by address), output registered
//   hexn_bsadd_cell_v1    bit-serial adder: inputs a, b, a word-start marker; one carry flip-flop (the fixed-function lower bound)
//   hexn_probe_line       N cells in a line, cell i listens to cells i-1, i+1, i-2, i+2 and two external bits (xa[i], xb[i]); KIND 0 flops, 1 memory, 2 bit-serial adder
module hexn_lut6_cell_v1 (input wire clk, input wire cfg_en, input wire cfg_in, output wire cfg_out, input wire [5:0] f, output reg out);
    reg [63:0] tbl = 64'd0; assign cfg_out = tbl[63];
    always @(posedge clk) begin if (cfg_en) tbl <= {tbl[62:0], cfg_in}; out <= tbl[f]; end
endmodule

module hexn_lut6_cell_ram_v1 (input wire clk, input wire we, input wire [5:0] wa, input wire wd, input wire [5:0] f, output reg out);
    reg [0:0] tbl [0:63]; integer i; initial for (i = 0; i < 64; i = i + 1) tbl[i] = 1'b0;
    always @(posedge clk) begin if (we) tbl[wa] <= wd; out <= tbl[f]; end
endmodule

module hexn_bsadd_cell_v1 (input wire clk, input wire a, input wire b, input wire start, output reg sum);
    reg c = 1'b0; wire ci = start ? 1'b0 : c;
    always @(posedge clk) begin sum <= a ^ b ^ ci; c <= (a & b) | (a & ci) | (b & ci); end
endmodule

module hexn_probe_line #(parameter N = 8, parameter KIND = 0) (input wire clk, input wire cfg_en, input wire cfg_in, input wire [5:0] wa, input wire wd, input wire [N-1:0] we_sel, input wire [N-1:0] xa, input wire [N-1:0] xb, input wire start, output wire [N-1:0] o, output wire cfg_out);
    wire [N:0] cc; assign cc[0] = cfg_in; assign cfg_out = cc[N];
    genvar i;
    generate for (i = 0; i < N; i = i + 1) begin : C
        wire n1 = o[(i + N - 1) % N], p1 = o[(i + 1) % N], n2 = o[(i + N - 2) % N], p2 = o[(i + 2) % N];
        if (KIND == 0) begin : K0 hexn_lut6_cell_v1 U (.clk(clk), .cfg_en(cfg_en), .cfg_in(cc[i]), .cfg_out(cc[i+1]), .f({n1, p1, n2, p2, xa[i], xb[i]}), .out(o[i])); end
        else if (KIND == 1) begin : K1 hexn_lut6_cell_ram_v1 U (.clk(clk), .we(we_sel[i]), .wa(wa), .wd(wd), .f({n1, p1, n2, p2, xa[i], xb[i]}), .out(o[i])); assign cc[i+1] = cc[i]; end
        else begin : K2 hexn_bsadd_cell_v1 U (.clk(clk), .a(xa[i]), .b(i == 0 ? xb[i] : o[i-1]), .start(start), .sum(o[i])); assign cc[i+1] = cc[i]; end
    end endgenerate
endmodule
