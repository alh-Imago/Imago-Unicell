// ledger #1109: the CLOSED-ring looped CORDIC in generated flex RTL (no wrapper register): the host injects z0 once through in_z_input and acks every result; the ring feeds itself.
// Top name and Z0 are passed with -D (TOP=..., Z0=...). Prints "R n value cycles_since_previous" per result; stops after NSTEPS results.
`ifndef ACK
`define ACK 1'b1
`endif
`timescale 1ns/1ps
module tb;
  reg clk=0, rst=1, cfg=0; always #5 clk=~clk;
  reg inj=0; reg [31:0] z0=`Z0; reg done_inj=0;
  wire [31:0] od; wire ov; wire iack;
  `TOP d(.clk(clk),.rst(rst),.cfg_valid(cfg),.in_z_input_data(z0),.in_z_input_valid(inj),.in_z_input_ack(iack),
         .out_result_data(od),.out_result_valid(ov),.out_result_ack(`ACK));
  integer n=0, cyc=0, last=0;
  always @(posedge clk) begin
    cyc <= cyc+1;
    if (inj && iack) begin inj <= 0; done_inj <= 1; last <= cyc; end
    if (ov && `ACK) begin n <= n+1; $display("R %0d %0d %0d", n+1, $signed(od), cyc-last); last <= cyc; if (n+1 >= `NSTEPS) $finish; end
  end
  initial begin
    repeat(4) @(posedge clk); rst<=0; @(posedge clk); cfg<=1; @(posedge clk); cfg<=0;
    repeat(30) @(posedge clk); inj<=1;
    repeat(`MAXCYC) @(posedge clk); $display("TIMEOUT n=%0d", n); $finish;
  end
endmodule
