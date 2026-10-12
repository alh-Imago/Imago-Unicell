// ledger #1094: closes the open-ring looped CORDIC (nano/examples/looped_cordic_v1_open.icm-hier.json -> project_assemble -s flex, top icm_open_flex): result is fed back into z_input; prints every result.
`timescale 1ns/1ps
module tb;
  reg clk=0, rst=1, cfg=0; always #5 clk=~clk;
  reg started=0, inj=0; reg [31:0] z0=32'd50000;
  wire [31:0] od; wire ov; wire iack;
  wire [31:0] idata = started ? od : z0;
  wire ivalid = started ? ov : inj;
  wire oack = started ? iack : 1'b0;
  icm_open_flex d(.clk(clk),.rst(rst),.cfg_valid(cfg),.in_z_input_data(idata),.in_z_input_valid(ivalid),.in_z_input_ack(iack),
                  .out_result_data(od),.out_result_valid(ov),.out_result_ack(oack));
  integer n=0, cyc=0, last=0;
  always @(posedge clk) begin
    cyc <= cyc+1;
    if (started && ov && oack) begin
      n <= n+1; $display("R %0d %0d %0d", n+1, $signed(od), cyc-last); last <= cyc;
      if (n+1 >= 40) begin $display("DONE"); $finish; end
    end
    if (!started && inj && iack) begin started <= 1; inj <= 0; last <= cyc; end
  end
  initial begin
    repeat(4) @(posedge clk); rst<=0; @(posedge clk); cfg<=1; @(posedge clk); cfg<=0;
    repeat(30) @(posedge clk); inj<=1;
    repeat(20000) @(posedge clk); $display("TIMEOUT n=%0d",n); $finish;
  end
endmodule
