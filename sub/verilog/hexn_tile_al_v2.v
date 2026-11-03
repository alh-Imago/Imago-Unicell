`default_nettype none
// hexn_tile_al_v2 = hexn_tile_al_v1 (untouched) on hexn_aligned_core_v2 (3 Nov 2026, Alan 09:50 'the general wipe command'): adds a CLEAR input - while clear is 1 every state register goes to its idle value (words in flight, FIFO 'have' flags, counters, carries, routed registers). Hold it for at least 130 clocks if the pattern has RAM hold cells (their delay line is wiped one address per clock). The config chain is NOT touched. 
// hexn_tile_al_v2 -- a HEX-N TILE WITH THE ALIGNED TWO-INPUT CORE (3 Nov 2026): the same shape as hexn_tile_v2 (routing cell with flag lane, result straight from the core register, power-up zeros) but the work core is hexn_aligned_core_v2,
// reading operand A from face SELA and operand B from face SELB (data and flag; the flag used is A's). Faces 0 N, 1 E, 2 S, 3 W; FACES is a parameter (4 now).
// CONFIG CHAIN word, LSB = bit 0 (shifted in MSB first, farthest tile first): ROUTE 3 bits per output [3*j +: 3] (FACES or more reads 0), SELA 3, SELB 3, RMASK FACES, OP 3 = 3*FACES + 9 + FACES bits (25 at four faces).
module hexn_tile_al_v2 #(parameter FACES = 4) (
    input wire clk, input wire clear,
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
    hexn_aligned_core_v2 core (.clk(clk), .clear(clear), .op(op), .a(dx[sela]), .af(fx[sela]), .b(dx[selb]), .r(r), .rs(rs));
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
