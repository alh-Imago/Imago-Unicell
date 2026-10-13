// tb_flex_std_adapter_v1.v -- ledger #1160: std ram -> std_to_flex_v1 -> flex ram -> flex_to_std_v1 -> std ram. Defines: N words, STALL (1 = the flex middle cell is held off and the sink acks at random),
// STDRAM (module name of the std ram: ram_cell_v4c or ram_cell_v4). Prints "I n data cyc" per word into the flex cell, "O n data cyc" per word the std sink delivers; END.
`timescale 1ns/1ps
`ifndef STALL
`define STALL 0
`endif
module tb;
  localparam [79:0] CFG_FLOWING = {14'h0, 20'h0, 32'h0, 1'b0, 1'b0, 6'b001000, 6'b000100};
  reg clk=0, rst=1, cfg=0; always #5 clk=~clk;
  reg [31:0] wdata=0; reg wpulse=0;
  reg hold=0;
  wire [31:0] sd; wire sfire, sack, sready;
  `STDRAM #(.CELL_ID(16'd1)) src(.clk(clk),.rst(rst),.active(1'b1),.cfg_valid(cfg),.cfg_data(CFG_FLOWING),
    .data_in_n(32'h0),.data_in_s(32'h0),.data_in_e(32'h0),.data_in_w(wdata),.arrived_n(1'b0),.arrived_s(1'b0),.arrived_e(1'b0),.arrived_w(wpulse),
    .data_out_n(),.data_out_s(),.data_out_e(sd),.data_out_w(),.fire_n(),.fire_s(),.fire_e(sfire),.fire_w(),.ready_out(sready),
    .ready_in_n(1'b1),.ready_in_s(1'b1),.ready_in_e(1'b1),.ready_in_w(1'b1),.ack_out_n(),.ack_out_s(),.ack_out_e(),.ack_out_w(),
    .ack_in_n(1'b0),.ack_in_s(1'b0),.ack_in_e(sack),.ack_in_w(1'b0),.program_in(1'b0),.program_done(),
    .prog_data_in_n(32'h0),.prog_data_in_s(32'h0),.prog_data_in_e(32'h0),.prog_data_in_w(32'h0),.prog_arrived_in_n(1'b0),.prog_arrived_in_s(1'b0),.prog_arrived_in_e(1'b0),.prog_arrived_in_w(1'b0),
    .prog_ack_out_n(),.prog_ack_out_s(),.prog_ack_out_e(),.prog_ack_out_w(),.freeze_in(1'b0),.status_data_valid());
  wire [31:0] fd_in; wire fv_in, fack_out;
  std_to_flex_v1 a1(.std_data(sd),.std_fire(sfire),.std_ack(sack),.flex_ack(fack_out & ~hold),.flex_data(fd_in),.flex_valid(fv_in));
  wire [31:0] fd_out; wire fv_out, fack_in;
  ram_cell_v4sa #(.CELL_ID(16'd2)) mid(.clk(clk),.rst(rst),.freeze_in(1'b0),.cfg_valid(cfg),.cfg_data(32'h0),.cfg_fixed_mode(1'b0),.data_in(fd_in),.valid_in(fv_in & ~hold),.ack_out(fack_out),.data_out(fd_out),.valid_out(fv_out),.ack_in(fack_in));
  wire [31:0] kd; wire kready, kfire; reg kack=0; wire [31:0] od, ad; wire apulse;
  flex_to_std_v1 a2(.flex_data(fd_out),.flex_valid(fv_out),.flex_ack(fack_in),.std_ready(kready & ~hold),.std_data(ad),.std_arrived(apulse));
  `STDRAM #(.CELL_ID(16'd3)) snk(.clk(clk),.rst(rst),.active(1'b1),.cfg_valid(cfg),.cfg_data(CFG_FLOWING),
    .data_in_n(32'h0),.data_in_s(32'h0),.data_in_e(32'h0),.data_in_w(ad),.arrived_n(1'b0),.arrived_s(1'b0),.arrived_e(1'b0),.arrived_w(apulse),
    .data_out_n(),.data_out_s(),.data_out_e(od),.data_out_w(),.fire_n(),.fire_s(),.fire_e(kfire),.fire_w(),.ready_out(kready),
    .ready_in_n(1'b1),.ready_in_s(1'b1),.ready_in_e(1'b1),.ready_in_w(1'b1),.ack_out_n(),.ack_out_s(),.ack_out_e(),.ack_out_w(),
    .ack_in_n(1'b0),.ack_in_s(1'b0),.ack_in_e(kack),.ack_in_w(1'b0),.program_in(1'b0),.program_done(),
    .prog_data_in_n(32'h0),.prog_data_in_s(32'h0),.prog_data_in_e(32'h0),.prog_data_in_w(32'h0),.prog_arrived_in_n(1'b0),.prog_arrived_in_s(1'b0),.prog_arrived_in_e(1'b0),.prog_arrived_in_w(1'b0),
    .prog_ack_out_n(),.prog_ack_out_s(),.prog_ack_out_e(),.prog_ack_out_w(),.freeze_in(1'b0),.status_data_valid());
  integer cyc=0, ni=0, no=0, sent=0; reg [31:0] lfsr=32'hACE1; reg took=0;
  always @(posedge clk) begin
    cyc <= cyc+1; lfsr <= {lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
    hold <= `STALL ? (lfsr[2] & lfsr[6]) : 1'b0;
    wpulse <= 0;
    if (!rst && sent < `N && sready && !wpulse && !sfire) begin wdata <= 32'd100 + sent*7; wpulse <= 1; sent <= sent+1; end
    if (fv_in && fack_out && !hold) begin $display("I %0d %0d %0d", ni+1, fd_in, cyc); ni <= ni+1; end
    kack <= 0; took <= 0;
    if (kfire && !took && (`STALL ? (lfsr[3] & lfsr[5]) : 1'b1)) begin $display("O %0d %0d %0d", no+1, od, cyc); no <= no+1; kack <= 1; took <= 1; if (no+1 >= `N) begin $display("END"); $finish; end end
    if (cyc > 40000) begin $display("TIMEOUT in=%0d out=%0d", ni, no); $finish; end
  end
  initial begin repeat(3) @(posedge clk); rst<=0; @(posedge clk); cfg<=1; @(posedge clk); cfg<=0; end
endmodule
