`default_nettype none
// hexn_tile_br_v2 = hexn_tile_br_v1 (untouched) on hexn_branch_core_v2 (3 Nov 2026, Alan 09:50 'the general wipe command'): adds a CLEAR input - while clear is 1 every state register goes to its idle value (words in flight, FIFO 'have' flags, counters, carries, routed registers). Hold it for at least 130 clocks if the pattern has RAM hold cells (their delay line is wiped one address per clock). The config chain is NOT touched. 
// hexn_tile_br_v2 -- a HEX-N TILE WITH THE BRANCH CORE hexn_branch_core_v2 (3 Nov 2026): routing cell with flag lane + the serial branch (3-way signed compare of the words on faces SELA and SELB, per-outcome route mask, emit a / b / a-b / fixed).
// The core has TWO outputs: out1 goes to every face set in R1MASK, out2 to every face set in R2MASK (a face in neither carries the routed stream; a face in both takes out1). The planner puts out1 on E and out2 on S.
// CONFIG CHAIN word, LSB = bit 0 (shifted in MSB first, farthest tile first), width 3*FACES + 6 + 2*FACES + 8 + 32 (66 at four faces):
//   ROUTE 3 bits per output [3*j +: 3] | SELA 3 | SELB 3 | R1MASK FACES | R2MASK FACES | ROUTE_LT 2 | ROUTE_EQ 2 | ROUTE_GT 2 | EMIT 2 | FIXED 32.   Route code: bit 0 = out1, bit 1 = out2, 00 = drop both.
module hexn_tile_br_v2 #(parameter FACES = 4) (
    input wire clk, input wire clear,
    input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output wire [FACES-1:0] fo_d, output wire [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam RW = 3 * FACES;
    localparam CW = RW + 6 + 2 * FACES + 8 + 32;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [2:0] sela = cfg[RW +: 3];
    wire [2:0] selb = cfg[RW + 3 +: 3];
    wire [FACES-1:0] m1 = cfg[RW + 6 +: FACES];
    wire [FACES-1:0] m2 = cfg[RW + 6 + FACES +: FACES];
    localparam P = RW + 6 + 2 * FACES;
    wire [1:0] rlt = cfg[P +: 2];
    wire [1:0] req = cfg[P + 2 +: 2];
    wire [1:0] rgt = cfg[P + 4 +: 2];
    wire [1:0] emit = cfg[P + 6 +: 2];
    wire [31:0] fixed = cfg[P + 8 +: 32];
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f};
    wire o1, o1s, o2, o2s;
    hexn_branch_core_v2 core (.clk(clk), .clear(clear), .route_lt(rlt), .route_eq(req), .route_gt(rgt), .emit(emit), .fixed(fixed),
                              .a(dx[sela]), .wsa(fx[sela]), .b(dx[selb]), .wsb(fx[selb]), .o1(o1), .o1s(o1s), .o2(o2), .o2s(o2s));
    reg [FACES-1:0] ro_d = 0, ro_f = 0; integer j;
    always @(posedge clk) for (j = 0; j < FACES; j = j + 1) begin
        ro_d[j] <= clear ? 1'b0 : dx[cfg[3 * j +: 3]];
        ro_f[j] <= clear ? 1'b0 : fx[cfg[3 * j +: 3]];
    end
    genvar g;
    generate for (g = 0; g < FACES; g = g + 1) begin : o
        assign fo_d[g] = m1[g] ? o1  : m2[g] ? o2  : ro_d[g];
        assign fo_f[g] = m1[g] ? o1s : m2[g] ? o2s : ro_f[g];
    end endgenerate
endmodule
