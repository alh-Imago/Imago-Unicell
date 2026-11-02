`default_nettype none
// hexn_grid_v1 -- a small GRID of UCC v2 look-up cells (2 Nov 2026, Alan 06:04: 'try the 16 grid with shell, and faces'). A MEASUREMENT PROTOTYPE, not the v2 design.
//   Hex cells on an R x C grid, odd rows shifted half a cell to the right ('odd-r' layout). Cell index = row * C + col. Six faces: E, W, NE, NW, SE, SW (the six hex neighbours).
//   Each cell has ONE registered output bit, visible to all its neighbours. A face with no neighbour reads an external input bit (ext_in[cell*6 + face]).
//   The cell's function is a 128 x 1 table (6 faces + the cell's own previous output as state), held in small memory, written through a SHELL: cfg_we + cfg_cell + cfg_addr + cfg_data.
//   Table address bits: 0 E, 1 W, 2 NE, 3 NW, 4 SE, 5 SW, 6 self.
//   Streams are bit-serial and synchronous: one hop = one clock. No start marker: each word carries a zero pad bit, which returns an adder's carry to 0 by itself.
module hexn_grid_v1 #(parameter R = 4, parameter C = 4) (
    input  wire clk, input wire cfg_we, input wire [15:0] cfg_cell, input wire [6:0] cfg_addr, input wire cfg_data,
    input  wire [R*C*6-1:0] ext_in, output wire [R*C-1:0] o);
    genvar r, c;
    generate for (r = 0; r < R; r = r + 1) begin : RW
        for (c = 0; c < C; c = c + 1) begin : CL
            localparam ME = r * C + c, ODD = r % 2;
            localparam vE  = (c + 1 < C),                                  iE  = vE  ? r * C + c + 1 : ME;
            localparam vW  = (c > 0),                                      iW  = vW  ? r * C + c - 1 : ME;
            localparam cNE = ODD ? c + 1 : c, vNE = (r > 0) && (cNE < C),   iNE = vNE ? (r - 1) * C + cNE : ME;
            localparam cNW = ODD ? c : c - 1, vNW = (r > 0) && (cNW >= 0),  iNW = vNW ? (r - 1) * C + cNW : ME;
            localparam cSE = ODD ? c + 1 : c, vSE = (r + 1 < R) && (cSE < C), iSE = vSE ? (r + 1) * C + cSE : ME;
            localparam cSW = ODD ? c : c - 1, vSW = (r + 1 < R) && (cSW >= 0), iSW = vSW ? (r + 1) * C + cSW : ME;
            wire [6:0] a = { o[ME],
                             vSW ? o[iSW] : ext_in[ME * 6 + 5], vSE ? o[iSE] : ext_in[ME * 6 + 4], vNW ? o[iNW] : ext_in[ME * 6 + 3],
                             vNE ? o[iNE] : ext_in[ME * 6 + 2], vW  ? o[iW]  : ext_in[ME * 6 + 1], vE  ? o[iE]  : ext_in[ME * 6 + 0] };
            reg tbl [0:127]; integer i; initial for (i = 0; i < 128; i = i + 1) tbl[i] = 1'b0;
            reg q = 1'b0; assign o[ME] = q;
            always @(posedge clk) begin if (cfg_we && cfg_cell == ME) tbl[cfg_addr] <= cfg_data; q <= tbl[a]; end
        end
    end endgenerate
endmodule
