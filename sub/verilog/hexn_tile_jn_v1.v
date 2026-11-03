`default_nettype none
// hexn_tile_jn_v1 -- a HEX-N TILE WITH THE JOIN CORE hexn_join_core_v2 (3 Nov 2026): same shape as hexn_tile_al_v1 (routing cell with flag lane, result straight from the core register, power-up zeros), but each operand brings ITS OWN start flag
// (A from face SELA, B from face SELB) and the two one-word FIFO cells inside the core hold the first word until the other arrives, so the operands may meet in any order. Ops: add 0, sub 1, and 2, or 3, xor 4, lt 5, min 6, max 7.
// Config word and layout exactly as hexn_tile_al_v1 (25 bits at four faces; OP has the three bits, so lt min max fit).
module hexn_tile_jn_v1 #(parameter FACES = 4) (
    input wire clk,
    input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output wire [FACES-1:0] fo_d, output wire [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam RW = 3 * FACES;
    localparam CW = RW + 6 + FACES + 3;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [2:0] sela = cfg[RW +: 3];
    wire [2:0] selb = cfg[RW + 3 +: 3];
    wire [FACES-1:0] rmask = cfg[RW + 6 +: FACES];
    wire [2:0] op = cfg[RW + 6 + FACES +: 3];
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f};
    wire r, rs;
    hexn_join_core_v2 core (.clk(clk), .op(op), .a(dx[sela]), .wsa(fx[sela]), .b(dx[selb]), .wsb(fx[selb]), .r(r), .rs(rs));
    reg [FACES-1:0] ro_d = 0, ro_f = 0; integer j;
    always @(posedge clk) for (j = 0; j < FACES; j = j + 1) begin
        ro_d[j] <= dx[cfg[3 * j +: 3]];
        ro_f[j] <= fx[cfg[3 * j +: 3]];
    end
    genvar g;
    generate for (g = 0; g < FACES; g = g + 1) begin : o
        assign fo_d[g] = rmask[g] ? r  : ro_d[g];
        assign fo_f[g] = rmask[g] ? rs : ro_f[g];
    end endgenerate
endmodule
