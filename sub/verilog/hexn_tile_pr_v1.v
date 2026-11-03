`default_nettype none
// hexn_tile_pr_v1 -- a HEX-N TILE WITH THE PRIORITY CORE hexn_prio_core_v2 (3 Nov 2026, Alan 10:07 "run through the other tiles"): routing cell with flag lane + the serial priority core. Core ports 0..3 read faces W, N, S, E (the planner's input order W N S, E spare); ONE output to the faces in RMASK.
// CONFIG CHAIN word, LSB = bit 0 (shifted in MSB first, farthest tile first), width 3*FACES + FACES + 4 + 8 + 2 + 3 + 8 (41 at four faces): ROUTE 3 bits per output | RMASK FACES | MASK 4 | RANKS 8 (2 bits per port) | MODE 2 | LEN 3 | ORDER 8 (2 bits per turn).
// The core's cfgload is held while the chain shifts (cfg_en) and while clear is high, so credits and the turn position start from zero after loading.
module hexn_tile_pr_v1 #(parameter FACES = 4) (
    input wire clk, input wire clear,
    input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output wire [FACES-1:0] fo_d, output wire [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam RW = 3 * FACES;
    localparam CW = RW + FACES + 4 + 8 + 2 + 3 + 8;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [FACES-1:0] rmask = cfg[RW +: FACES];
    wire [3:0] mask = cfg[RW + FACES +: 4];
    wire [7:0] ranks = cfg[RW + FACES + 4 +: 8];
    wire [1:0] mode = cfg[RW + FACES + 12 +: 2];
    wire [2:0] len = cfg[RW + FACES + 14 +: 3];
    wire [7:0] order = cfg[RW + FACES + 17 +: 8];
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f};
    wire r, rs;
    // faces: 0 N, 1 E, 2 S, 3 W -> core ports 0 W, 1 N, 2 S, 3 E
    hexn_prio_core_v2 core (.clk(clk), .clear(clear), .cfgload(cfg_en | clear), .mask(mask), .ranks(ranks), .mode(mode), .len(len), .order(order),
        .dn(dx[3]), .wsn(fx[3]), .ds(dx[0]), .wss(fx[0]), .de(dx[2]), .wse(fx[2]), .dw(dx[1]), .wsw(fx[1]), .r(r), .rs(rs));
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
