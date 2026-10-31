// tb_hexn_neural_v1: reads 64-bit command words from stim.hex: [63:62] cmd (0 eval, 1 learn, 2 write weight), [61] m2, [60:51] t (signed 10), [50:9] x (7 x 6 bits) ; for cmd 2: [8:5] addr, [50:35] data.
// Logs per command: cmd, y, then the 8 weights (7 weights + bias) after the command. Run: vvp with +N=<count>.
`timescale 1ns/1ps
module tb_hexn_neural_v1;
  parameter WB = 14;
  reg clk = 0, rst = 1; always #5 clk = ~clk;
  reg go_eval = 0, go_learn = 0, w_wr = 0, m2 = 0; reg [41:0] x = 0; reg signed [9:0] t = 0; reg [3:0] w_addr = 0; reg signed [15:0] w_data = 0;
  wire signed [9:0] y; wire done; wire [8*16-1:0] wf;
  hexn_neural_v1 #(.WB(WB)) dut (.clk(clk), .rst(rst), .go_eval(go_eval), .go_learn(go_learn), .x(x), .t(t), .m2(m2), .w_wr(w_wr), .w_addr(w_addr), .w_data(w_data), .y(y), .done(done), .w_flat(wf));
  reg [63:0] mem [0:4095]; integer n, i, f, j;
  initial begin
    $readmemh("stim.hex", mem); if (!$value$plusargs("N=%d", n)) n = 0; f = $fopen("neural_out.txt", "w");
    repeat (3) @(posedge clk); #1 rst = 0; @(posedge clk); #1;
    for (i = 0; i < n; i = i + 1) begin
      x = mem[i][50:9]; t = mem[i][60:51]; m2 = mem[i][61];
      if (mem[i][63:62] == 2) begin w_addr = mem[i][8:5]; w_data = mem[i][50:35]; w_wr = 1; @(posedge clk); #1 w_wr = 0; @(posedge clk); #1; end
      else begin
        if (mem[i][63:62] == 0) go_eval = 1; else go_learn = 1; @(posedge clk); #1 go_eval = 0; go_learn = 0;
        while (!done) begin @(posedge clk); #1; end @(posedge clk); #1;
      end
      $fwrite(f, "%0d %0d", mem[i][63:62], y); for (j = 0; j < 8; j = j + 1) $fwrite(f, " %0d", $signed(wf[j*16 +: 16])); $fwrite(f, "\n");
    end
    $fclose(f); $finish;
  end
endmodule
