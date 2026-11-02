`default_nettype none
// hexn_ramroute_v5 -- v5 of the RAM-routing cell (2 Nov 2026, Alan 08:01 'model that'): v4 plus a FIX found by simulation: the word-start flag arrives WITH bit 0, so the counter value used this clock must be 0 at the flag (v4 used the old count and lost bit 0). Alan 07:58 idea: the RAM cell as a real one-word FIFO, 32 x 1 memory, that can START STREAMING OUT before the whole word is in.
//   One counter cnt starts at the word-start flag (face wsel). Write address = cnt (clocks 0..31). Read address = cnt - dly, read from clock dly on for 32 clocks.
//   dly = 1..31 : the first bits leave while the word is still arriving (the read trails the write by dly bits); dly >= 32 : the whole word waits, then leaves. Same cell, same memory, no mode difference.
//   mode 0 PASS, mode 1 HOLD (above), mode 2 REPEAT (record 32 bits, then read address cycles 0..31 forever). Counts only, NOT function-tested (yosys 0.69, -nowidelut).
module hexn_ramroute_v5 #(parameter DW = 7) (input wire clk, input wire [5:0] fi, output reg [5:0] fo, input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam CW = 18 + 2 + 3 + 3 + DW + 3;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [1:0] mode = cfg[19:18]; wire [2:0] hsel = cfg[22:20]; wire [2:0] hout = cfg[25:23];
    wire [DW-1:0] dly = cfg[25+DW:26]; wire [2:0] wsel = cfg[28+DW:26+DW];
    wire [7:0] fx = {2'b00, fi}; wire din = fx[hsel]; wire ws = fx[wsel];
    reg mem [0:31]; reg [DW-1:0] cnt = {DW{1'b1}}; reg q = 1'b0; reg [4:0] rr = 0;
    wire [DW-1:0] cc = ws ? {DW{1'b0}} : cnt;                      // the count of THIS clock: 0 on the clock the flag arrives with bit 0
    wire wr = (cc < 32); wire [DW-1:0] dd = cc - dly; wire rd = (cc >= dly) && (dd < 32);
    always @(posedge clk) begin
        if (mode == 2'd0) begin cnt <= {DW{1'b1}}; rr <= 0; end
        else begin
            if (cc != {DW{1'b1}}) cnt <= cc + 1'b1; else cnt <= cc;
            if (wr) mem[cc[4:0]] <= din;
            if (mode == 2'd1) q <= rd ? mem[dd[4:0]] : 1'b0;
            else begin rr <= (cc < 32) ? 5'd0 : rr + 1'b1; q <= (cc >= 32) ? mem[(cc < 32) ? 5'd0 : rr] : 1'b0; end
        end
    end
    integer j;
    always @(posedge clk) for (j = 0; j < 6; j = j + 1) fo[j] <= (mode != 2'd0 && hout == j) ? q : fx[cfg[3 * j +: 3]];
endmodule
