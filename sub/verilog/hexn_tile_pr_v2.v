`default_nettype none
// hexn_tile_pr_v2 = hexn_tile_pr_v1 (untouched) with SELECTABLE PORTS (3 Nov 2026, Alan 17:05, hex grid step H2): four 3-bit port selects (PSEL, the top 12 bits of the config word) say which face core port 0..3 reads, so on the six-face hex grid the priority tile can read any four of six faces. The rest is as v1 (MASK, RANKS, MODE, LEN, ORDER refer to the PORTS, not the faces).
// CONFIG CHAIN word, LSB = bit 0 (shifted in MSB first, farthest tile first), width 3*FACES + FACES + 4 + 8 + 2 + 3 + 8 (41 at four faces): ROUTE 3 bits per output | RMASK FACES | MASK 4 | RANKS 8 (2 bits per port) | MODE 2 | LEN 3 | ORDER 8 (2 bits per turn).
// The core's cfgload is held while the chain shifts (cfg_en) and while clear is high, so credits and the turn position start from zero after loading.
module hexn_tile_pr_v2 #(parameter FACES = 4) (
    input wire clk, input wire clear,
    input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output wire [FACES-1:0] fo_d, output wire [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam RW = 3 * FACES;
    localparam CW0 = RW + FACES + 4 + 8 + 2 + 3 + 8; localparam CW = CW0 + 12;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [FACES-1:0] rmask = cfg[RW +: FACES];
    wire [3:0] mask = cfg[RW + FACES +: 4];
    wire [7:0] ranks = cfg[RW + FACES + 4 +: 8];
    wire [1:0] mode = cfg[RW + FACES + 12 +: 2];
    wire [2:0] len = cfg[RW + FACES + 14 +: 3];
    wire [7:0] order = cfg[RW + FACES + 17 +: 8];
    wire [2:0] ps0 = cfg[CW0 +: 3], ps1 = cfg[CW0 + 3 +: 3], ps2 = cfg[CW0 + 6 +: 3], ps3 = cfg[CW0 + 9 +: 3];   // v2: the face each core port reads (default 3, 0, 2, 1 = the v1 ports; index >= FACES reads 0)
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f};
    wire r, rs;
    // faces: 0 N, 1 E, 2 S, 3 W -> core ports 0 W, 1 N, 2 S, 3 E
    hexn_prio_core_v2 core (.clk(clk), .clear(clear), .cfgload(cfg_en | clear), .mask(mask), .ranks(ranks), .mode(mode), .len(len), .order(order),
        .dn(dx[ps0]), .wsn(fx[ps0]), .ds(dx[ps1]), .wss(fx[ps1]), .de(dx[ps2]), .wse(fx[ps2]), .dw(dx[ps3]), .wsw(fx[ps3]), .r(r), .rs(rs));
    reg [FACES-1:0] ro_d = 0, ro_f = 0; integer j;
    always @(posedge clk) for (j = 0; j < FACES; j = j + 1) begin
        ro_d[j] <= clear ? 1'b0 : dx[cfg[3 * j +: 3]];
        ro_f[j] <= clear ? 1'b0 : fx[cfg[3 * j +: 3]];
    end
    genvar g;
    generate for (g = 0; g < FACES; g = g + 1) begin : o
        assign fo_d[g] = rmask[g] ? r  : ro_d[g];
        assign fo_f[g] = rmask[g] ? rs : ro_f[g];
    end endgenerate
endmodule
