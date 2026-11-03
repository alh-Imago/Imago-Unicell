`default_nettype none
// hexn_tilegrid_v1 -- a ROWS x COLS grid of hexn_tile_v1 tiles on ONE config chain (2 Nov 2026, Alan 08:15: "start with a row of tiles from a unit file").
// Tile (r, c) is chain position r*COLS + c (row-major, chain input -> tile 0 -> ... -> chain output). Faces 0 N, 1 E, 2 S, 3 W; a tile's E output feeds the next column's W input, N/S likewise.
// External lanes: the WEST face of column 0 is the data+flag INPUT of each row (w_d, w_f), the EAST face of the last column is the OUTPUT of each row (e_d, e_f). North of row 0 and south of the last row read 0.
// The shape is generic: what the grid does is decided only by the chain (tools/hexn_tilegrid_load_v1.py builds it from a unit file). The tiles hold the unary work core only (cp shl shr mask inv acc).
module hexn_tilegrid_v1 #(parameter ROWS = 7, parameter COLS = 7) (
    input wire clk, input wire clear,
    input wire [ROWS-1:0] w_d, input wire [ROWS-1:0] w_f,
    output wire [ROWS-1:0] e_d, output wire [ROWS-1:0] e_f,
    input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam N = ROWS * COLS;
    wire [4*N-1:0] od, of;
    wire [N:0] cc; assign cc[0] = cfg_in; assign cfg_out = cc[N];
    genvar r, c;
    generate for (r = 0; r < ROWS; r = r + 1) begin : row
        for (c = 0; c < COLS; c = c + 1) begin : col
            localparam I = r * COLS + c;
            wire nd = (r == 0)        ? 1'b0 : od[4 * (I - COLS) + 2];
            wire nf = (r == 0)        ? 1'b0 : of[4 * (I - COLS) + 2];
            wire ed = (c == COLS - 1) ? 1'b0 : od[4 * (I + 1) + 3];
            wire ef = (c == COLS - 1) ? 1'b0 : of[4 * (I + 1) + 3];
            wire sd = (r == ROWS - 1) ? 1'b0 : od[4 * (I + COLS) + 0];
            wire sf = (r == ROWS - 1) ? 1'b0 : of[4 * (I + COLS) + 0];
            wire wd = (c == 0)        ? w_d[r] : od[4 * (I - 1) + 1];
            wire wf = (c == 0)        ? w_f[r] : of[4 * (I - 1) + 1];
            hexn_tile_v2 #(.FACES(4)) t (.clk(clk), .clear(clear), .fi_d({wd, sd, ed, nd}), .fi_f({wf, sf, ef, nf}),
                .fo_d(od[4 * I +: 4]), .fo_f(of[4 * I +: 4]), .cfg_en(cfg_en), .cfg_in(cc[I]), .cfg_out(cc[I + 1]));
        end
        assign e_d[r] = od[4 * (r * COLS + COLS - 1) + 1];
        assign e_f[r] = of[4 * (r * COLS + COLS - 1) + 1];
    end endgenerate
endmodule
