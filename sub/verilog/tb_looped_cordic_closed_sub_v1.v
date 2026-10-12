// ledger #1111: the CLOSED-ring looped CORDIC in generated SUB RTL (fixed 1-clock cells, no ack). The host injects z0 with a one-clock valid; each lap ends at the measure point, which HOLDS
// the word; the control refires it until N laps are done, then ring_stopped rises and the Nth word stays held. With RELEASE defined the tb pulses ring_release HOLD clocks after the stop.
// Defines: TOP, Z0, NSTEPS (results to count), MAXCYC. Prints "R n value clocks_since_previous", "S cyc n=.." at the stop rise, "END".
`ifndef HOLD
`define HOLD 20
`endif
`timescale 1ns/1ps
module tb;
  reg clk=0, rst=1, cfg=0; always #5 clk=~clk;
  reg inj=0; reg [31:0] z0=`Z0; reg rel=0;
  wire [31:0] od; wire ov; wire held, stopped;
  `TOP d(.clk(clk),.rst(rst),.cfg_valid(cfg),.in_z_input_data(z0),.in_z_input_valid(inj),
         .out_result_data(od),.out_result_valid(ov),.ring_release(rel),.ring_held(held),.ring_stopped(stopped));
  integer n=0, cyc=0, last=0, hold=0, injected=0; reg sprev=0;
  always @(posedge clk) begin
    cyc <= cyc+1;
    if (stopped && !sprev) $display("S %0d n=%0d", cyc, n);
    sprev <= stopped;
    if (stopped) hold <= hold+1; else hold <= 0;
`ifdef RELEASE
    rel <= (stopped && hold == `HOLD);
`endif
    if (inj) begin inj <= 0; last <= cyc; end
    if (ov) begin n <= n+1; $display("R %0d %0d %0d", n+1, $signed(od), cyc-last); last <= cyc; if (n+1 >= `NSTEPS) begin #1; $display("END stopped=%0d held=%0d word=%0d", stopped, held, $signed(od)); $finish; end end
  end
  initial begin
    repeat(4) @(posedge clk); rst<=0; @(posedge clk); cfg<=1; @(posedge clk); cfg<=0;
    repeat(60) @(posedge clk); inj<=1;
    repeat(`MAXCYC) @(posedge clk); $display("TIMEOUT n=%0d stopped=%0d held=%0d word=%0d", n, stopped, held, $signed(od)); $finish;
  end
endmodule
