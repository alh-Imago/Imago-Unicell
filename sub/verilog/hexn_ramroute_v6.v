`default_nettype none
// hexn_ramroute_v6 -- RAM-routing cell with a TRIGGER-DRIVEN one-word FIFO (2 Nov 2026, Alan 09:02: a specific 'high' sets it off, it resets itself when empty, until the next pulse).
//   Two inputs matter: the data face (hsel) and the pulse face (psel); a pulse is a rising edge (a level that stays high counts once). No counter for timing, no delay register, no subtractor.
//   mode 0 PASS   : plain routing.
//   mode 1 HOLD   : empty -> first pulse (with bit 0 of the word on the data face) writes 32 bits. With a word present, the next pulse starts the read (address 0, 32 bits) onto face hout;
//                   a release pulse during the write is allowed (the read stays behind the write: bits leave while the word is still arriving). When the read ends the cell is empty again.
//   mode 2 REPEAT : as hold, but the word stays: every later pulse replays it.
//   Output has two registers (read register, then face register): bit 0 is on the face 2 clocks after the release pulse's clock edge. Pulse during a read in progress: ignored (NOT decided, see ledger).
//   Counts only until tested; test: tests/hexn_ramroute_tb_v2.v.
module hexn_ramroute_v6 (input wire clk, input wire [5:0] fi, output reg [5:0] fo, input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam CW = 18 + 2 + 3 + 3 + 3;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [1:0] mode = cfg[19:18]; wire [2:0] hsel = cfg[22:20]; wire [2:0] hout = cfg[25:23]; wire [2:0] psel = cfg[28:26];
    wire [7:0] fx = {2'b00, fi}; wire din = fx[hsel]; wire p = fx[psel];
    reg mem [0:31]; reg pq = 1'b0; reg have = 1'b0, wr_run = 1'b0, rd_run = 1'b0; reg [4:0] wa = 0, ra = 0; reg q = 1'b0;
    wire pe = p & ~pq;
    always @(posedge clk) begin
        pq <= p;
        if (mode == 2'd0) begin have <= 1'b0; wr_run <= 1'b0; rd_run <= 1'b0; q <= 1'b0; end
        else begin
            if (pe && !have) begin have <= 1'b1; wr_run <= 1'b1; wa <= 5'd1; mem[5'd0] <= din; end
            else if (wr_run) begin mem[wa] <= din; wa <= wa + 1'b1; if (wa == 5'd31) wr_run <= 1'b0; end
            if (pe && have && !rd_run) begin rd_run <= 1'b1; ra <= 5'd0; end
            if (rd_run) begin q <= mem[ra]; ra <= ra + 1'b1; if (ra == 5'd31) begin rd_run <= 1'b0; if (mode == 2'd1) have <= 1'b0; end end
            else q <= 1'b0;
        end
    end
    integer j;
    always @(posedge clk) for (j = 0; j < 6; j = j + 1) fo[j] <= (mode != 2'd0 && hout == j) ? q : fx[cfg[3 * j +: 3]];
endmodule
