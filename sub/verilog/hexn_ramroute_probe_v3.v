`default_nettype none
// TAP = 0: no read tap, so a hold is at least 32 clocks (shorter waits are done by a routing detour or the work core's delay); TAP = 1: any delay 1..127.
// hexn_ramroute_probe_v3 -- MEASUREMENT PROTOTYPE (2 Nov 2026, Alan 07:46): RAM-routing cell with a ONE-WORD FIFO (32 bits, the same length as every other cell's word), TIMED release.
//   mode 0 PASS   : plain routing.
//   mode 1 HOLD   : a counter starts at the word-start flag (face wsel). The 32 bits of the word shift into the FIFO (clocks 0..31), then the FIFO freezes until clock dly,
//                   then shifts out (bit 0 first). dly < 32 = a plain delay (read tap), dly >= 32 = the stored word waits. The word always sits in the same bit positions; no pointers.
//   mode 2 REPEAT : the word is recorded (first 32 clocks after the start flag), then rotated forever onto face hout.
//   The held stream is face hsel; the held/replayed bit goes out on face hout; all other faces still route. Counts only, NOT function-tested (yosys 0.69, -nowidelut).
module hexn_ramroute_probe_v3 #(parameter DW = 7, parameter TAP = 1) (input wire clk, input wire [5:0] fi, output reg [5:0] fo, input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam CW = 18 + 2 + 3 + 3 + DW + 3;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [1:0] mode = cfg[19:18]; wire [2:0] hsel = cfg[22:20]; wire [2:0] hout = cfg[25:23];
    wire [DW-1:0] dly = cfg[25+DW:26]; wire [2:0] wsel = cfg[28+DW:26+DW];
    wire [7:0] fx = {2'b00, fi}; wire din = fx[hsel]; wire ws = fx[wsel];
    reg [31:0] sr = 0; reg [DW-1:0] cnt = {DW{1'b1}}; reg q = 1'b0;
    wire wr = (cnt < 32); wire rd = (cnt >= dly);
    wire [4:0] tap = (dly >= 32) ? 5'd31 : (dly[4:0] - 5'd1);
    always @(posedge clk) begin
        if (mode == 2'd0) cnt <= {DW{1'b1}};
        else begin
            if (ws) cnt <= 0; else if (cnt != {DW{1'b1}}) cnt <= cnt + 1'b1;
            if (mode == 2'd1) begin
                if (wr || rd) sr <= {sr[30:0], din & wr};         // shifts in during the write window, zero fill after
                q <= TAP ? sr[tap] : sr[31];
            end else begin
                if (wr) sr <= {sr[30:0], din}; else sr <= {sr[30:0], sr[31]};
                q <= sr[31];
            end
        end
    end
    integer j;
    always @(posedge clk) for (j = 0; j < 6; j = j + 1) fo[j] <= (mode != 2'd0 && hout == j) ? q : fx[cfg[3 * j +: 3]];
endmodule
