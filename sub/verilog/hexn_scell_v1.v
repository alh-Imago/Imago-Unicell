`default_nettype none
// hexn_scell_v1 -- MEASUREMENT PROTOTYPE (2 Nov 2026, Alan 06:58 to 07:01): ONE bit-serial hex cell with several cores selected by a few config bits, plus ROUTING. Counts and one function test only; not the v2 design.
//   Six faces in (fi) and six faces out (fo, registered). Each output face j is either the cell's computed result (rmask[j] = 1) or a copy of one input face (rsrc[j], 3 bits). So ROUTE, CROSS (opposite faces straight through)
//   and CORNER (a bend) are not separate hardware: they are just route settings with rmask = 0, and the cell can carry up to six streams through while also computing one.
//   Computed result r (bit-serial, least significant bit first; ws = 1 on the first bit of a word):  mode 0 = a, 1 = add, 2 = subtract, 3 = logic (4-bit truth table tt on {a, b}), 4 = a delayed by shamt clocks (shift left, zeros enter)
//   a = face sela, b = face selb. Not included (they need a word-length counter or a word-wide register): compare, accumulate, shift right, mask.
module hexn_scell_v1 #(parameter ADD = 1, parameter LOGIC = 1, parameter DELAY = 1) (
    input wire clk, input wire ws, input wire [5:0] fi, output reg [5:0] fo,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam CW = 3 + 3 + 3 + 4 + 5 + 6 + 18;                 // mode, sela, selb, tt, shamt, rmask, rsrc x 6
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [2:0] mode = cfg[2:0], sela = cfg[5:3], selb = cfg[8:6]; wire [3:0] tt = cfg[12:9]; wire [4:0] sh = cfg[17:13]; wire [5:0] rmask = cfg[23:18];
    wire a = fi[sela > 5 ? 0 : sela], b = fi[selb > 5 ? 0 : selb];
    reg c = 1'b0; wire sub = (mode == 3'd2); wire bb = b ^ sub; wire ci = ws ? sub : c;
    wire sum = a ^ bb ^ ci; wire cn = (a & bb) | (a & ci) | (bb & ci);
    always @(posedge clk) if (ADD) c <= cn;
    wire lg = tt[{a, b}];
    reg [31:0] dl = 0; always @(posedge clk) if (DELAY) dl <= {dl[30:0], a};
    wire dly = (sh == 0) ? a : dl[sh - 1];
    reg r;
    always @* case (mode) 3'd0: r = a; 3'd1: r = ADD ? sum : 1'b0; 3'd2: r = ADD ? sum : 1'b0; 3'd3: r = LOGIC ? lg : 1'b0; 3'd4: r = DELAY ? dly : 1'b0; default: r = 1'b0; endcase
    integer j; reg [2:0] s;
    always @(posedge clk) for (j = 0; j < 6; j = j + 1) begin s = cfg[24 + 3 * j +: 3]; fo[j] <= rmask[j] ? r : fi[s > 5 ? 0 : s]; end
endmodule
