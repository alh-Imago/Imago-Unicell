// tb_std_sub_bridge_v1.v -- ledger #1113: the SAME bridge (flex_sub_bridge_v1.v, untouched) against the STANDARD (v4c, arrived/fire/ack) family: std ram -> flex_to_sub_v1 -> three sub cells (+1000, relay, +234)
// -> sub_to_flex_v1 -> std ram. Adapter wiring only: std fire_e is the valid level, ack_in_e the ack; the std sink takes an `arrived_w` pulse when it is ready_out. Defines N, STALL.
`timescale 1ns/1ps
`ifndef STALL
`define STALL 0
`endif
module tb;
  localparam K1 = 32'd1000, K2 = 32'd234;
  localparam [79:0] CFG_FLOWING = {14'h0, 20'h0, 32'h0, 1'b0, 1'b0, 6'b001000, 6'b000100};
  reg clk=0, rst=1, cfg=0; always #5 clk=~clk;
  reg [31:0] wdata=0; reg wpulse=0;
  wire [31:0] sd; wire sfire; wire sack; wire sready;
  ram_cell_v4c #(.CELL_ID(16'd1)) src(.clk(clk),.rst(rst),.active(1'b1),.cfg_valid(cfg),.cfg_data(CFG_FLOWING),
    .data_in_n(32'h0),.data_in_s(32'h0),.data_in_e(32'h0),.data_in_w(wdata),.arrived_n(1'b0),.arrived_s(1'b0),.arrived_e(1'b0),.arrived_w(wpulse),
    .data_out_n(),.data_out_s(),.data_out_e(sd),.data_out_w(),.fire_n(),.fire_s(),.fire_e(sfire),.fire_w(),.ready_out(sready),
    .ready_in_n(1'b1),.ready_in_s(1'b1),.ready_in_e(1'b1),.ready_in_w(1'b1),.ack_out_n(),.ack_out_s(),.ack_out_e(),.ack_out_w(),
    .ack_in_n(1'b0),.ack_in_s(1'b0),.ack_in_e(sack),.ack_in_w(1'b0),.program_in(1'b0),.program_done(),
    .prog_data_in_n(32'h0),.prog_data_in_s(32'h0),.prog_data_in_e(32'h0),.prog_data_in_w(32'h0),.prog_arrived_in_n(1'b0),.prog_arrived_in_s(1'b0),.prog_arrived_in_e(1'b0),.prog_arrived_in_w(1'b0),
    .prog_ack_out_n(),.prog_ack_out_s(),.prog_ack_out_e(),.prog_ack_out_w(),.freeze_in(1'b0),.status_data_valid());
  wire [31:0] subd; wire subv; wire done;
  flex_to_sub_v1 f2s(.clk(clk),.rst(rst),.in_data(sd),.in_valid(sfire),.in_ack(sack),.sub_data(subd),.sub_valid(subv),.done(done));
  wire [31:0] k1d,k2d; wire k1v,k2v;
  ram_cell_v4s #(.CELL_ID(16'd2)) k1(.clk(clk),.rst(rst),.cfg_valid(cfg),.cfg_data(K1),.cfg_fixed_mode(1'b1),.data_in(32'h0),.valid_in(1'b0),.data_out(k1d),.valid_out(k1v));
  ram_cell_v4s #(.CELL_ID(16'd3)) k2(.clk(clk),.rst(rst),.cfg_valid(cfg),.cfg_data(K2),.cfg_fixed_mode(1'b1),.data_in(32'h0),.valid_in(1'b0),.data_out(k2d),.valid_out(k2v));
  wire [31:0] a1d,r1d,a2d; wire a1v,r1v,a2v;
  adder_cell_v4s #(.CELL_ID(16'd4)) a1(.clk(clk),.rst(rst),.cfg_valid(cfg),.cfg_data(32'h0),.in_a(subd),.in_b(k1d),.valid_in(subv),.data_out(a1d),.valid_out(a1v));
  ram_cell_v4s #(.CELL_ID(16'd5)) r1(.clk(clk),.rst(rst),.cfg_valid(cfg),.cfg_data(32'h0),.cfg_fixed_mode(1'b0),.data_in(a1d),.valid_in(a1v),.data_out(r1d),.valid_out(r1v));
  adder_cell_v4s #(.CELL_ID(16'd6)) a2(.clk(clk),.rst(rst),.cfg_valid(cfg),.cfg_data(32'h0),.in_a(r1d),.in_b(k2d),.valid_in(r1v),.data_out(a2d),.valid_out(a2v));
  wire [31:0] hd; wire hv; wire hack;
  sub_to_flex_v1 s2f(.clk(clk),.rst(rst),.sub_data(a2d),.sub_valid(a2v),.out_data(hd),.out_valid(hv),.out_ack(hack),.done(done));
  reg kack=0; wire [31:0] od; wire ofire; wire kready;
  assign hack = kready;                                   // the std sink takes the held word when it is ready; arrived is a pulse at that transfer
  ram_cell_v4c #(.CELL_ID(16'd7)) snk(.clk(clk),.rst(rst),.active(1'b1),.cfg_valid(cfg),.cfg_data(CFG_FLOWING),
    .data_in_n(32'h0),.data_in_s(32'h0),.data_in_e(32'h0),.data_in_w(hd),.arrived_n(1'b0),.arrived_s(1'b0),.arrived_e(1'b0),.arrived_w(hv & hack),
    .data_out_n(),.data_out_s(),.data_out_e(od),.data_out_w(),.fire_n(),.fire_s(),.fire_e(ofire),.fire_w(),.ready_out(kready),
    .ready_in_n(1'b1),.ready_in_s(1'b1),.ready_in_e(1'b1),.ready_in_w(1'b1),.ack_out_n(),.ack_out_s(),.ack_out_e(),.ack_out_w(),
    .ack_in_n(1'b0),.ack_in_s(1'b0),.ack_in_e(kack),.ack_in_w(1'b0),.program_in(1'b0),.program_done(),
    .prog_data_in_n(32'h0),.prog_data_in_s(32'h0),.prog_data_in_e(32'h0),.prog_data_in_w(32'h0),.prog_arrived_in_n(1'b0),.prog_arrived_in_s(1'b0),.prog_arrived_in_e(1'b0),.prog_arrived_in_w(1'b0),
    .prog_ack_out_n(),.prog_ack_out_s(),.prog_ack_out_e(),.prog_ack_out_w(),.freeze_in(1'b0),.status_data_valid());
  integer cyc=0, ni=0, no=0, sent=0; reg [31:0] lfsr=32'hACE1; reg took=0;
  always @(posedge clk) begin
    cyc <= cyc+1; lfsr <= {lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
    wpulse <= 0;
    if (!rst && sent < `N && sready && !wpulse && !sfire) begin wdata <= 32'd100 + sent*7; wpulse <= 1; sent <= sent+1; end
    if (sack) begin $display("I %0d %0d %0d", ni+1, sd, cyc); ni <= ni+1; end
    kack <= 0; took <= 0;
    if (ofire && !took && (`STALL ? (lfsr[3] & lfsr[5]) : 1'b1)) begin $display("O %0d %0d %0d", no+1, od, cyc); no <= no+1; kack <= 1; took <= 1; if (no+1 >= `N) begin $display("END"); $finish; end end
    if (cyc > 20000) begin $display("TIMEOUT in=%0d out=%0d", ni, no); $finish; end
  end
  initial begin repeat(3) @(posedge clk); rst<=0; @(posedge clk); cfg<=1; @(posedge clk); cfg<=0; end
endmodule
