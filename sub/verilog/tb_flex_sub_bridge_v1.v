// tb_flex_sub_bridge_v1.v -- ledger #1112: flex ram (source) -> flex_to_sub_v1 -> SUB math (adder +K1, relay, adder +K2: 3 sub cells) -> sub_to_flex_v1 -> flex ram (sink).
// Defines: N words, STALL (1 = the sink acks only at random), SEED. Prints "I n data cyc" for each word taken from the source, "O n data cyc" for each word the sink delivers; END.
`timescale 1ns/1ps
`ifndef STALL
`define STALL 0
`endif
module tb;
  localparam K1 = 32'd1000, K2 = 32'd234;
  reg clk=0, rst=1, cfg=0; always #5 clk=~clk;
  reg [31:0] wdata=0; reg wvalid=0; wire wack;
  wire [31:0] sd; wire sv; wire sack_in;
  ram_cell_v4sa #(.CELL_ID(16'd1)) src(.clk(clk),.rst(rst),.freeze_in(1'b0),.cfg_valid(cfg),.cfg_data(32'h0),.cfg_fixed_mode(1'b0),.data_in(wdata),.valid_in(wvalid),.ack_out(wack),.data_out(sd),.valid_out(sv),.ack_in(sack_in));
  wire [31:0] subd; wire subv; wire done;
  flex_to_sub_v1 f2s(.clk(clk),.rst(rst),.in_data(sd),.in_valid(sv),.in_ack(sack_in),.sub_data(subd),.sub_valid(subv),.done(done));
  wire [31:0] k1d,k2d; wire k1v,k2v;
  ram_cell_v4s #(.CELL_ID(16'd2)) k1(.clk(clk),.rst(rst),.cfg_valid(cfg),.cfg_data(K1),.cfg_fixed_mode(1'b1),.data_in(32'h0),.valid_in(1'b0),.data_out(k1d),.valid_out(k1v));
  ram_cell_v4s #(.CELL_ID(16'd3)) k2(.clk(clk),.rst(rst),.cfg_valid(cfg),.cfg_data(K2),.cfg_fixed_mode(1'b1),.data_in(32'h0),.valid_in(1'b0),.data_out(k2d),.valid_out(k2v));
  wire [31:0] a1d,r1d,a2d; wire a1v,r1v,a2v;
  adder_cell_v4s #(.CELL_ID(16'd4)) a1(.clk(clk),.rst(rst),.cfg_valid(cfg),.cfg_data(32'h0),.in_a(subd),.in_b(k1d),.valid_in(subv),.data_out(a1d),.valid_out(a1v));
  ram_cell_v4s #(.CELL_ID(16'd5)) r1(.clk(clk),.rst(rst),.cfg_valid(cfg),.cfg_data(32'h0),.cfg_fixed_mode(1'b0),.data_in(a1d),.valid_in(a1v),.data_out(r1d),.valid_out(r1v));
  adder_cell_v4s #(.CELL_ID(16'd6)) a2(.clk(clk),.rst(rst),.cfg_valid(cfg),.cfg_data(32'h0),.in_a(r1d),.in_b(k2d),.valid_in(r1v),.data_out(a2d),.valid_out(a2v));
  wire [31:0] hd; wire hv, hack; wire [31:0] kd; wire kv;
  sub_to_flex_v1 s2f(.clk(clk),.rst(rst),.sub_data(a2d),.sub_valid(a2v),.out_data(hd),.out_valid(hv),.out_ack(hack),.done(done));
  reg kack=0; wire [31:0] od; wire ov;
  ram_cell_v4sa #(.CELL_ID(16'd7)) snk(.clk(clk),.rst(rst),.freeze_in(1'b0),.cfg_valid(cfg),.cfg_data(32'h0),.cfg_fixed_mode(1'b0),.data_in(hd),.valid_in(hv),.ack_out(hack),.data_out(od),.valid_out(ov),.ack_in(kack));
  integer cyc=0, ni=0, no=0, sent=0; reg [31:0] lfsr=32'hACE1;
  always @(posedge clk) begin
    cyc <= cyc+1; lfsr <= {lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
    kack <= `STALL ? lfsr[3] & lfsr[5] : 1'b1;
    if (!rst && sent < `N && !wvalid && wack) begin wdata <= 32'd100 + sent*7; wvalid <= 1; sent <= sent+1; end
    else if (wvalid) wvalid <= 0;
    if (sack_in) begin $display("I %0d %0d %0d", ni+1, sd, cyc); ni <= ni+1; end
    if (ov && kack) begin $display("O %0d %0d %0d", no+1, od, cyc); no <= no+1; if (no+1 >= `N) begin $display("END"); $finish; end end
    if (cyc > 20000) begin $display("TIMEOUT in=%0d out=%0d", ni, no); $finish; end
  end
  initial begin repeat(3) @(posedge clk); rst<=0; @(posedge clk); cfg<=1; @(posedge clk); cfg<=0; end
endmodule
