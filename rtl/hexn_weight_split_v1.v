// hexn_weight_split_v1: 16-bit weights carried 8 BITS AT A TIME, with a buffer to reassemble (new file, 1 Nov 2026; Alan 12:25: split each weight in two, 8 bits a time, a buffer to reassemble).
// Sits beside hexn_weight_port_v1 (untouched). Simulation only; nothing on a board. The wire format of a byte (which stream word carries it) is NOT fixed here: this block takes plain byte pulses.
// SAVE side: the port's streamed words (w_valid, w_addr, w_data, w_last) are collected in a buffer of NW words; once the last one is in, the buffer is sent out as 2 x NW bytes, low byte then high byte of each address,
//   with a ready/valid handshake (b_valid, b_ready), b_addr, b_half (0 low, 1 high), b_data, b_last. The byte order equals the little-endian i16 order of the loadable item payload.
// LOAD side: byte pulses (l_valid, l_addr, l_half, l_data) in EITHER half order. A weight is passed on to the port (p_valid, p_addr, p_data) only when BOTH its halves have arrived: never half a weight.
//   If a byte for a different address arrives while a pair is incomplete, the incomplete halves are DROPPED (nothing written) and err_pair goes high (sticky until rst); the new byte starts a new pair.
// A new SAVE word while the buffer is still being sent is ignored and err_over goes high (sticky until rst).
module hexn_weight_split_v1 #(parameter NW = 8, WW = 16) (
  input clk, input rst,
  input w_valid, input [3:0] w_addr, input signed [WW-1:0] w_data, input w_last,
  output reg b_valid, input b_ready, output reg [3:0] b_addr, output reg b_half, output reg [WW/2-1:0] b_data, output reg b_last,
  input l_valid, input [3:0] l_addr, input l_half, input [WW/2-1:0] l_data,
  output reg p_valid, output reg [3:0] p_addr, output reg signed [WW-1:0] p_data,
  output reg err_pair, output reg err_over);
  reg [WW-1:0] buf_w [0:NW-1]; reg sending; reg [4:0] idx;     // idx counts bytes 0 .. 2*NW-1
  reg have_lo, have_hi; reg [WW/2-1:0] lo, hi; reg [3:0] cur;
  reg same, t_lov, t_hiv; reg [WW/2-1:0] t_lo, t_hi;
  wire [3:0] sa = idx[4:1]; wire sh = idx[0];
  always @(posedge clk) begin
    p_valid <= 1'b0;
    if (rst) begin sending <= 1'b0; idx <= 5'd0; b_valid <= 1'b0; b_last <= 1'b0; have_lo <= 1'b0; have_hi <= 1'b0; err_pair <= 1'b0; err_over <= 1'b0; end
    else begin
      // ---- save side
      if (w_valid) begin
        if (sending) err_over <= 1'b1;
        else begin buf_w[w_addr] <= w_data; if (w_last) begin sending <= 1'b1; idx <= 5'd0; end end
      end
      if (sending && (!b_valid || b_ready)) begin
        b_valid <= 1'b1; b_addr <= sa; b_half <= sh; b_data <= sh ? buf_w[sa][WW-1:WW/2] : buf_w[sa][WW/2-1:0]; b_last <= (idx == 2*NW-1);
        if (idx == 2*NW-1) sending <= 1'b0; else idx <= idx + 5'd1;
      end else if (b_valid && b_ready) begin b_valid <= 1'b0; b_last <= 1'b0; end
      // ---- load side
      if (l_valid) begin
        same  = (have_lo || have_hi) && (l_addr == cur);
        if ((have_lo || have_hi) && !same) err_pair <= 1'b1;      // incomplete pair dropped, never written
        t_lov = same & have_lo; t_hiv = same & have_hi; t_lo = lo; t_hi = hi;
        if (l_half) begin t_hi = l_data; t_hiv = 1'b1; end else begin t_lo = l_data; t_lov = 1'b1; end
        if (t_lov && t_hiv) begin p_valid <= 1'b1; p_addr <= l_addr; p_data <= {t_hi, t_lo}; have_lo <= 1'b0; have_hi <= 1'b0; end
        else begin lo <= t_lo; hi <= t_hi; have_lo <= t_lov; have_hi <= t_hiv; end
        cur <= l_addr;
      end
    end
  end
endmodule
