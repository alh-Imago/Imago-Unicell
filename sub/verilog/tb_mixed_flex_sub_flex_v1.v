// ledger #1114: the generated MIXED design (flex block -> SUB block -> flex block, bridges inserted by tools/flexsub_mixed_v1.py). Host pushes N words (valid/ack), takes results (valid/ack, random stall if STALL).
// Prints "I n data cyc" per word accepted, "O n data cyc" per result taken, END.  Defines: TOP, N, STALL, ADD (offset to expect is checked by the test).
`timescale 1ns/1ps
`ifndef STALL
`define STALL 0
`endif
module tb;
  reg clk=0, rst=1, cfg=0; always #5 clk=~clk;
  reg [31:0] xd=0; reg xv=0; wire xack; wire [31:0] yd; wire yv; reg yack=0;
  `TOP d(.clk(clk),.rst(rst),.cfg_valid(cfg),.in_x_in_data(xd),.in_x_in_valid(xv),.in_x_in_ack(xack),.out_y_out_data(yd),.out_y_out_valid(yv),.out_y_out_ack(yack));
  integer cyc=0, sent=0, got=0; reg [31:0] lfsr=32'hACE1;
  always @(posedge clk) begin
    cyc <= cyc+1; lfsr <= {lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
    yack <= `STALL ? (lfsr[3] & lfsr[5]) : 1'b1;
    if (!rst) begin
      if (xv && xack) begin $display("I %0d %0d %0d", sent, xd, cyc); xv <= 0; end
      else if (!xv && sent < `N && cyc > 100) begin xd <= 32'd100 + sent*7; xv <= 1; sent <= sent+1; end
      if (yv && yack) begin $display("O %0d %0d %0d", got+1, yd, cyc); got <= got+1; if (got+1 >= `N) begin $display("END"); $finish; end end
    end
    if (cyc > 30000) begin $display("TIMEOUT sent=%0d got=%0d", sent, got); $finish; end
  end
  initial begin repeat(3) @(posedge clk); rst<=0; @(posedge clk); cfg<=1; @(posedge clk); cfg<=0; end
endmodule
