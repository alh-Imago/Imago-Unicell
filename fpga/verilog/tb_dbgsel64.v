`timescale 1ns/1ps
module tb_dbgsel;
  reg clk=0,rst=0; reg [31:0] cpu_bus=0,cpu_data=0; reg cpu_valid=0;
  always #5 clk=~clk;
  reg [15:0] load_target=0;
  always @(posedge clk) if (cpu_valid && cpu_bus[7:0]==8'd24) load_target<=cpu_data[15:0];
  wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1)?cpu_data[31:16]
                         : (cpu_bus[7:0]==8'd23||cpu_bus[7:0]==8'd2||cpu_bus[7:0]==8'd3||cpu_bus[7:0]==8'd25)?load_target
                         : cpu_data[15:0];
  wire pact=(cpu_bus[18:17]!=0);
  wire cv = cpu_valid && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||pact);
  localparam NB=2;
  wire [31:0] d0_cl,d0_ia,d0_oa,d0_ad,cyc; wire [15:0] oa,ac,arc,osc,ec; wire [31:0] od; wire ov;
  unicell_zone64 #(.NUM_CELLS(25),.NUM_BRIDGES(NB),.ZONE_ID(0)) z(.clk(clk),.rst(rst),
    .cmd_bus(cpu_bus),.cmd_data(cpu_data),.cmd_valid(cv),.cpu_addr(cpu_addr_w),.cpu_data(cpu_data),.cpu_valid(cpu_valid),
    .out_addr(oa),.out_data(od),.out_valid(ov),.armed_count(ac),.arrived_count(arc),.output_set_count(osc),.emit_count(ec),
    .dbg0_cmd_latch(d0_cl),.dbg0_input_addr(d0_ia),.dbg0_output_addr(d0_oa),.dbg0_a_data(d0_ad),.cycle_count(cyc),
    .bridge_n_in_valid({NB{1'b0}}),.bridge_n_in_addr({NB*16{1'b0}}),.bridge_n_in_data({NB*32{1'b0}}),.bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
    .bridge_s_in_valid({NB{1'b0}}),.bridge_s_in_addr({NB*16{1'b0}}),.bridge_s_in_data({NB*32{1'b0}}),.bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
    .bridge_e_in_valid({NB{1'b0}}),.bridge_e_in_addr({NB*16{1'b0}}),.bridge_e_in_data({NB*32{1'b0}}),.bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
    .bridge_w_in_valid({NB{1'b0}}),.bridge_w_in_addr({NB*16{1'b0}}),.bridge_w_in_data({NB*32{1'b0}}),.bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data());
  task x; input [31:0] b,d; begin @(negedge clk); cpu_bus<=b;cpu_data<=d;cpu_valid<=1; @(posedge clk);#1; cpu_valid<=0; repeat(3)@(posedge clk);#1; end endtask
  integer fails=0;
  initial begin
    rst=1; repeat(5)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
    // cell 0: LOAD_AT topology 0x0BC armed ; cell 2: topology 0x024 armed
    x(32'h00000018,32'd0); x(32'h00000017,32'h008000BC);      // SET_TARGET 0, LOAD_AT topo=0x0BC arm
    x(32'h00000018,32'd2); x(32'h00000017,32'h00800024);      // SET_TARGET 2, LOAD_AT topo=0x024 arm
    x(32'h0000001A,32'd0); #1;                                 // DBG_SELECT 0
    $display("dbg_sel=0: cmd_latch[9:0]=0x%03x (want 0x0BC)", d0_cl[9:0]); if(d0_cl[9:0]!==10'h0BC) fails=fails+1;
    x(32'h0000001A,32'd2); #1;                                 // DBG_SELECT 2
    $display("dbg_sel=2: cmd_latch[9:0]=0x%03x (want 0x024)", d0_cl[9:0]); if(d0_cl[9:0]!==10'h024) fails=fails+1;
    $display("%s", fails==0?">>> PASS: debug-select reads the chosen cell":">>> FAIL");
    $finish;
  end
endmodule
