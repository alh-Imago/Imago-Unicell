`default_nettype none
// hexn_tile_v3 = hexn_tile_v2 (untouched) on hexn_unary_core_v2 (3 Nov 2026, Alan 09:50 'the general wipe command'): adds a CLEAR input - while clear is 1 every state register goes to its idle value (words in flight, FIFO 'have' flags, counters, carries, routed registers). Hold it for at least 130 clocks if the pattern has RAM hold cells (their delay line is wiped one address per clock). The config chain is NOT touched. 
// hexn_tile_v3 = hexn_tile_v1 (untouched) + two changes found building a grid from a unit file (3 Nov 2026): (1) POWER-UP ZEROES on the routed-output registers (unknown values loop round routes that feed each other and never clear); (2) the core result goes to the output faces DIRECTLY from the core's own output register instead of through a second register, so a work cell costs the core's own latency only, as in the word-level planner model (hexn_wrgrid simulate9) and in the earlier grid RTL. A routed bit still costs 1 clock per hop. Ports as v1 except fo_d / fo_f are wires.
// hexn_tile_v1 text follows: the FIRST FULL HEX-N TILE (2 Nov 2026, Alan 18:27: "try the first tile and see how that works").
// One routing cell with a flag lane (hexn_rcore_flag_v1's structure) PLUS one work core (hexn_unary_core_v2, untouched), both set by ONE config shift chain.
// Faces are numbered 0 = N, 1 = E, 2 = S, 3 = W (4 now; FACES is a parameter, 6 reserved). Every face carries DATA (1 bit per clock, 32-bit words, least significant bit first) and a word-START FLAG.
// What the tile does: the work core reads its operand from face SELA (data and flag together); each output face j either carries the core's result (RMASK[j] = 1) or a copy of one input face (ROUTE[j]),
// so a work tile still routes other streams past the core. Outputs are registered: a routed bit costs 1 clock per hop; a computed bit costs the core's own latency + 1.
// CONFIG CHAIN (cfg_en high shifts one bit per clock; cfg_out is the last bit so tiles chain: the tile NEAREST cfg_out is shifted in FIRST, MSB of each tile's word first). Word layout, LSB = bit 0:
//   [3*j +: 3] ROUTE for output j (an index of FACES or more reads 0)   [3*FACES +: 3] SELA   [3*FACES+3 +: FACES] RMASK   then OP (3), K (5), MASK (8).  tools/hexn_tile_cfg_v1.py packs and unpacks it.
// Not in this tile: the other work cores (add/compare/join/seq/branch/merge/prio need their own wrappers), a WIPE input (loading all zeros through the chain is the wipe for now), the serial/parallel crossing.
module hexn_tile_v3 #(parameter FACES = 4) (
    input wire clk, input wire clear,
    input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output wire [FACES-1:0] fo_d, output wire [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam RW = 3 * FACES;
    localparam CW = RW + 3 + FACES + 3 + 5 + 8;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [2:0] sela = cfg[RW +: 3];
    wire [FACES-1:0] rmask = cfg[RW + 3 +: FACES];
    wire [2:0] op = cfg[RW + 3 + FACES +: 3];
    wire [4:0] k = cfg[RW + 6 + FACES +: 5];
    wire [7:0] mask = cfg[RW + 11 + FACES +: 8];
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f};
    wire r, rs;
    hexn_unary_core_v2 core (.clk(clk), .op(op), .k(k), .mask(mask), .clear(clear), .a(dx[sela]), .af(fx[sela]), .r(r), .rs(rs));
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
