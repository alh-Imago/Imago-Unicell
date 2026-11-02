`default_nettype none
// hexn_split_probe_v1 -- MEASUREMENT PROTOTYPES (2 Nov 2026, Alan 07:07): the cell split into a WORK core and a ROUTING core. Counts only.
//   hexn_rcore_v1 : pure switch. Six faces in, six faces out (registered, so it is also the buffer between work cores). Each output picks one input face (3 bits per output, no compute, no state beyond the output flip-flops).
//   hexn_wcore_v1 : work core with ONE input end (two bits, a and b) and ONE output end (one bit): the same cores as hexn_scell_v1 (copy, add, subtract, a 4-bit logic table, delay 0 to 31), no routing at all.
module hexn_rcore_v1 (input wire clk, input wire [5:0] fi, output reg [5:0] fo, input wire cfg_en, input wire cfg_in, output wire cfg_out);
    reg [17:0] cfg = 0; assign cfg_out = cfg[17];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[16:0], cfg_in};
    wire [7:0] fx = {2'b00, fi}; integer j;                       // an index of 6 or 7 reads a constant 0 (no comparison needed)
    always @(posedge clk) for (j = 0; j < 6; j = j + 1) fo[j] <= fx[cfg[3 * j +: 3]];
endmodule

module hexn_wcore_v1 #(parameter ADD = 1, parameter LOGIC = 1, parameter DELAY = 1) (input wire clk, input wire ws, input wire a, input wire b, output reg r_o, input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam CW = 3 + 4 + 5;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [2:0] mode = cfg[2:0]; wire [3:0] tt = cfg[6:3]; wire [4:0] sh = cfg[11:7];
    reg c = 1'b0; wire sub = (mode == 3'd2); wire bb = b ^ sub; wire ci = ws ? sub : c;
    wire sum = a ^ bb ^ ci; wire cn = (a & bb) | (a & ci) | (bb & ci);
    always @(posedge clk) if (ADD) c <= cn;
    wire lg = tt[{a, b}];
    reg [31:0] dl = 0; always @(posedge clk) if (DELAY) dl <= {dl[30:0], a};
    wire [32:0] dv = {dl, a}; wire dly = dv[sh];                  // delay of sh clocks, sh = 0 is a
    reg r;
    always @* case (mode) 3'd0: r = a; 3'd1: r = ADD ? sum : 1'b0; 3'd2: r = ADD ? sum : 1'b0; 3'd3: r = LOGIC ? lg : 1'b0; 3'd4: r = DELAY ? dly : 1'b0; default: r = 1'b0; endcase
    always @(posedge clk) r_o <= r;
endmodule
