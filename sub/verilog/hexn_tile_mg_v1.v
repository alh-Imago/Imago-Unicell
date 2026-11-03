`default_nettype none
// hexn_tile_mg_v1 -- a HEX-N TILE WITH THE MERGE CORE hexn_merge_core_v1 (3 Nov 2026): routing cell with flag lane + the serial merge (A from face SELA, B from face SELB, ONE output to the faces in RMASK).
// MODE: 0 A only, 1 B only, 2 arbitrate (round robin, one word at a time; the order of words depends on arrival), 3 join-OR (A | B when both are there). Each input has a one-word FIFO cell inside the core.
// CONFIG CHAIN word, LSB = bit 0 (shifted in MSB first, farthest tile first), width 3*FACES + 6 + FACES + 2 (24 at four faces): ROUTE 3 bits per output | SELA 3 | SELB 3 | RMASK FACES | MODE 2.
module hexn_tile_mg_v1 #(parameter FACES = 4) (
    input wire clk,
    input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output wire [FACES-1:0] fo_d, output wire [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam RW = 3 * FACES;
    localparam CW = RW + 6 + FACES + 2;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [2:0] sela = cfg[RW +: 3];
    wire [2:0] selb = cfg[RW + 3 +: 3];
    wire [FACES-1:0] rmask = cfg[RW + 6 +: FACES];
    wire [1:0] mode = cfg[RW + 6 + FACES +: 2];
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f};
    wire r, rs;
    hexn_merge_core_v1 core (.clk(clk), .mode(mode), .a(dx[sela]), .wsa(fx[sela]), .b(dx[selb]), .wsb(fx[selb]), .r(r), .rs(rs));
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
