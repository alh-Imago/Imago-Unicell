`default_nettype none
// hexn_rcore_flag_v1 -- routing cell with a FLAG LANE (2 Nov 2026, Alan 17:53: "with the flag lane, how will this affect the overall size ... needs to be confirmed, and built").
// Clone in spirit of hexn_rcore_v1 (untouched): FACES in and out (4 now, 6 reserved), each face carries DATA and a word-START FLAG. The flag follows the data: one select per output,
// shared by both lanes, so the config chain is no longer than before (3 bits per output). An index of FACES or more reads constant 0 on both lanes. Outputs are registered (one clock per hop).
module hexn_rcore_flag_v1 #(parameter FACES = 4) (
    input wire clk, input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output reg [FACES-1:0] fo_d, output reg [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam CW = 3 * FACES;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f}; integer j;
    always @(posedge clk) for (j = 0; j < FACES; j = j + 1) begin fo_d[j] <= dx[cfg[3 * j +: 3]]; fo_f[j] <= fx[cfg[3 * j +: 3]]; end
endmodule

// data-only twins with the same FACES parameter, for a like-for-like count (hexn_rcore_v1 is fixed at six faces)
module hexn_rcore_data_v1 #(parameter FACES = 4) (
    input wire clk, input wire [FACES-1:0] fi_d, output reg [FACES-1:0] fo_d,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam CW = 3 * FACES;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; integer j;
    always @(posedge clk) for (j = 0; j < FACES; j = j + 1) fo_d[j] <= dx[cfg[3 * j +: 3]];
endmodule
