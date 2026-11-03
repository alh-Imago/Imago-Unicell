`default_nettype none
// hexn_tile_lt_v1 -- a HEX-N TILE WITH THE LATCH CORE hexn_latch_core_v2 (3 Nov 2026, Alan 10:07). INTERPRETATION TO REVISIT: the latch makes a held LEVEL, not a word. Here SET, CLEAR and TOGGLE are the FLAG lanes of three chosen faces (a word's start flag = one pulse; select 7 = never),
// and the held level q is put on the DATA lane of the output faces in RMASK, with the flag lane 0 there. Clear wins over set. CONFIG CHAIN word, LSB = bit 0, width 3*FACES + 9 + FACES (25 at four faces): ROUTE 3 bits per output | SELS 3 | SELC 3 | SELT 3 | RMASK FACES.
module hexn_tile_lt_v1 #(parameter FACES = 4) (
    input wire clk, input wire clear,
    input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output wire [FACES-1:0] fo_d, output wire [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam RW = 3 * FACES;
    localparam CW = RW + 9 + FACES;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [2:0] sels = cfg[RW +: 3], selc = cfg[RW + 3 +: 3], selt = cfg[RW + 6 +: 3];
    wire [FACES-1:0] rmask = cfg[RW + 9 +: FACES];
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f};
    wire q;
    hexn_latch_core_v2 core (.clk(clk), .clear(clear | cfg_en), .set_in(fx[sels]), .clear_in(fx[selc]), .toggle_in(fx[selt]), .q(q));
    reg [FACES-1:0] ro_d = 0, ro_f = 0; integer j;
    always @(posedge clk) for (j = 0; j < FACES; j = j + 1) begin
        ro_d[j] <= clear ? 1'b0 : dx[cfg[3 * j +: 3]];
        ro_f[j] <= clear ? 1'b0 : fx[cfg[3 * j +: 3]];
    end
    genvar g;
    generate for (g = 0; g < FACES; g = g + 1) begin : o
        assign fo_d[g] = rmask[g] ? q : ro_d[g];
        assign fo_f[g] = rmask[g] ? 1'b0 : ro_f[g];
    end endgenerate
endmodule
