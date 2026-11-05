`default_nettype none
// hexn_tile_wk_v1 -- the MERGED WORK CELL (5 Nov 2026, Alan 21:25: "build the merged cell type"). One tile that holds the six work cores used by the two Kintex arrays: UN (hexn_unary_core_v2), AL (hexn_aligned_core_v2), JN (hexn_join_core_v3),
// BR (hexn_branch_core_v2), MG (hexn_merge_core_v2), PR (hexn_prio_core_v2). The cores are the proven ones, untouched. A FUNC field in the config chain says which core drives the output faces (a table: FUNC -> core), so a cell changes its type by a program load, not a new bitstream.
// The routing part (route table, flag lane, power-up zeros, result straight from the core register) is exactly that of hexn_tile_v3 / _al_v2 / _jn_v2 / _br_v2 / _mg_v2 / _pr_v2; the old tiles stay as they are. Not included: SQ (sequencer) and LT (latch), unused by the arrays; the RAM hold cell (hexn_ramhold_v1) and the plain routing/path cell stay separate, as Alan ruled.
// An unselected core is held in clear, so no stray words wait in its FIFOs when its function is chosen later. A selected core sees exactly what the old tile gave it, so the outputs equal the old tile's, clock for clock (tests/vm/test_hexn_tile_wk_v1.py).
// CONFIG CHAIN word, LSB = bit 0, shifted in MSB first, farthest tile first, cfg_out = last bit (as every tile). Width 3*FACES + 9 + 2*FACES + 3 + 40 (82 at six faces; the old tiles are 25 to 76 bits).
//   [3*j +: 3] ROUTE for output face j | FUNC 3 (0 UN, 1 AL, 2 JN, 3 BR, 4 MG, 5 PR, 6 and 7 route only) | SELA 3 | SELB 3 | M1 FACES (faces that take the core result; for BR the out1 faces) | M2 FACES (BR out2 faces) | OP 3 (AL, JN, UN) | PW 40 (the parameter word, shared by the cores, only the chosen core reads it):
//   UN: K = PW[4:0], MASK = PW[12:5].  MG: MODE = PW[1:0].  BR: ROUTE_LT = PW[1:0], EQ = PW[3:2], GT = PW[5:4], EMIT = PW[7:6], FIXED = PW[39:8].
//   PR: MASK = PW[3:0], RANKS = PW[11:4], MODE = PW[13:12], LEN = PW[16:14], ORDER = PW[24:17], PS0..PS3 = PW[27:25], [30:28], [33:31], [36:34] (the face each core port reads).
module hexn_tile_wk_v1 #(parameter FACES = 4) (
    input wire clk, input wire clear,
    input wire [FACES-1:0] fi_d, input wire [FACES-1:0] fi_f,
    output wire [FACES-1:0] fo_d, output wire [FACES-1:0] fo_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam RW = 3 * FACES;
    localparam CW = RW + 9 + 2 * FACES + 3 + 40;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [2:0] func = cfg[RW +: 3];
    wire [2:0] sela = cfg[RW + 3 +: 3];
    wire [2:0] selb = cfg[RW + 6 +: 3];
    wire [FACES-1:0] m1 = cfg[RW + 9 +: FACES];
    wire [FACES-1:0] m2 = cfg[RW + 9 + FACES +: FACES];
    wire [2:0] op = cfg[RW + 9 + 2 * FACES +: 3];
    wire [39:0] pw = cfg[RW + 12 + 2 * FACES +: 40];
    wire [7:0] dx = {{(8-FACES){1'b0}}, fi_d}; wire [7:0] fx = {{(8-FACES){1'b0}}, fi_f};
    // every core is held in clear unless it is the chosen one
    wire clr_un = clear | (func != 3'd0), clr_al = clear | (func != 3'd1), clr_jn = clear | (func != 3'd2);
    wire clr_br = clear | (func != 3'd3), clr_mg = clear | (func != 3'd4), clr_pr = clear | (func != 3'd5);
    wire r_un, rs_un, r_al, rs_al, r_jn, rs_jn, r_mg, rs_mg, r_pr, rs_pr, o1, o1s, o2, o2s;
    hexn_unary_core_v2 c_un (.clk(clk), .op(op), .k(pw[4:0]), .mask(pw[12:5]), .clear(clr_un), .a(dx[sela]), .af(fx[sela]), .r(r_un), .rs(rs_un));
    hexn_aligned_core_v2 c_al (.clk(clk), .clear(clr_al), .op(op), .a(dx[sela]), .af(fx[sela]), .b(dx[selb]), .r(r_al), .rs(rs_al));
    hexn_join_core_v3 c_jn (.clk(clk), .clear(clr_jn), .op(op), .a(dx[sela]), .wsa(fx[sela]), .b(dx[selb]), .wsb(fx[selb]), .r(r_jn), .rs(rs_jn));
    hexn_branch_core_v2 c_br (.clk(clk), .clear(clr_br), .route_lt(pw[1:0]), .route_eq(pw[3:2]), .route_gt(pw[5:4]), .emit(pw[7:6]), .fixed(pw[39:8]),
                              .a(dx[sela]), .wsa(fx[sela]), .b(dx[selb]), .wsb(fx[selb]), .o1(o1), .o1s(o1s), .o2(o2), .o2s(o2s));
    hexn_merge_core_v2 c_mg (.clk(clk), .clear(clr_mg), .mode(pw[1:0]), .a(dx[sela]), .wsa(fx[sela]), .b(dx[selb]), .wsb(fx[selb]), .r(r_mg), .rs(rs_mg));
    wire [2:0] ps0 = pw[27:25], ps1 = pw[30:28], ps2 = pw[33:31], ps3 = pw[36:34];
    hexn_prio_core_v2 c_pr (.clk(clk), .clear(clr_pr), .cfgload(cfg_en | clr_pr), .mask(pw[3:0]), .ranks(pw[11:4]), .mode(pw[13:12]), .len(pw[16:14]), .order(pw[24:17]),
        .dn(dx[ps0]), .wsn(fx[ps0]), .ds(dx[ps1]), .wss(fx[ps1]), .de(dx[ps2]), .wse(fx[ps2]), .dw(dx[ps3]), .wsw(fx[ps3]), .r(r_pr), .rs(rs_pr));
    // the table FUNC -> result lane (BR has a second output, used only by BR)
    reg r, rs;
    always @* case (func)
        3'd0: begin r = r_un; rs = rs_un; end
        3'd1: begin r = r_al; rs = rs_al; end
        3'd2: begin r = r_jn; rs = rs_jn; end
        3'd3: begin r = o1;   rs = o1s;   end
        3'd4: begin r = r_mg; rs = rs_mg; end
        3'd5: begin r = r_pr; rs = rs_pr; end
        default: begin r = 1'b0; rs = 1'b0; end
    endcase
    wire isbr = (func == 3'd3), live = (func <= 3'd5);
    reg [FACES-1:0] ro_d = 0, ro_f = 0; integer j;
    always @(posedge clk) for (j = 0; j < FACES; j = j + 1) begin
        ro_d[j] <= clear ? 1'b0 : dx[cfg[3 * j +: 3]];
        ro_f[j] <= clear ? 1'b0 : fx[cfg[3 * j +: 3]];
    end
    genvar g;
    generate for (g = 0; g < FACES; g = g + 1) begin : o
        assign fo_d[g] = (m1[g] && live) ? r  : (m2[g] && isbr) ? o2  : ro_d[g];
        assign fo_f[g] = (m1[g] && live) ? rs : (m2[g] && isbr) ? o2s : ro_f[g];
    end endgenerate
endmodule
