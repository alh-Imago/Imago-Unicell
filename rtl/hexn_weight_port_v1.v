// hexn_weight_port_v1: SAVE AND LOAD PORT FOR hexn_neural_v1 (new file, 1 Nov 2026; hexn_neural_v1 is untouched). Simulation only; nothing on a board.
// SAVE: a one-clock pulse `rd_start` copies all NW weights (the neural judge's w_flat bus) into a snapshot in ONE clock, then streams them out one per clock:
//   out_valid, out_addr (0..NW-1; the last address is the bias), out_data, out_last. The copy is consistent because it is taken at one instant.
// LOAD: one pulse of in_valid per word (in_addr, in_data) becomes one w_wr pulse, one clock later, to the neural judge.
// GUARD: both are taken only while `idle` is high (the caller says no eval/learn is in flight; a learn step updates the weights one by one, so a copy or a write
//   in the middle would mix old and new values) and while no save stream is running. Otherwise the request is IGNORED and err_busy goes high (sticky until rst): it is never silently half-done.
module hexn_weight_port_v1 #(parameter NW = 8, WW = 16) (
  input clk, input rst, input idle,
  input rd_start, input [NW*WW-1:0] w_flat,
  output reg out_valid, output reg [3:0] out_addr, output reg signed [WW-1:0] out_data, output reg out_last,
  input in_valid, input [3:0] in_addr, input signed [WW-1:0] in_data,
  output reg w_wr, output reg [3:0] w_addr, output reg signed [WW-1:0] w_data,
  output reg err_busy);
  reg [NW*WW-1:0] snap; reg running; reg [3:0] cnt;
  always @(posedge clk) begin
    out_valid <= 1'b0; out_last <= 1'b0; w_wr <= 1'b0;
    if (rst) begin running <= 1'b0; cnt <= 4'd0; err_busy <= 1'b0; end
    else begin
      if (rd_start) begin
        if (idle && !running) begin snap <= w_flat; running <= 1'b1; cnt <= 4'd0; end
        else err_busy <= 1'b1;
      end
      if (in_valid) begin
        if (idle && !running && !rd_start) begin w_wr <= 1'b1; w_addr <= in_addr; w_data <= in_data; end
        else err_busy <= 1'b1;
      end
      if (running) begin
        out_valid <= 1'b1; out_addr <= cnt; out_data <= snap[cnt*WW +: WW]; out_last <= (cnt == NW-1);
        cnt <= cnt + 4'd1; if (cnt == NW-1) running <= 1'b0;
      end
    end
  end
endmodule
