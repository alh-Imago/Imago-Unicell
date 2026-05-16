// tb_unicell_v3.v -- testbench, updated for 11-bit topo mk_cfg
`timescale 1ns / 1ps
module tb_unicell_v3;

reg clk=0,rst=0,freeze=0;
reg [31:0] cmd_bus=0; reg cmd_valid=0;
reg [31:0] bus_addr=0,bus_data=0; reg bus_valid=0;
wire [31:0] out_addr,out_data;
wire out_valid;
wire [31:0] dbg_cmd_latch,dbg_input_addr,dbg_output_addr;
wire dbg_frozen,dbg_trace,dbg_breakpoint,dbg_priority;

unicell_v3 #(.CELL_ID(42)) dut(
    .clk(clk),.rst(rst),.freeze(freeze),
    .cmd_bus(cmd_bus),.cmd_valid(cmd_valid),
    .bus_addr(bus_addr),.bus_data(bus_data),.bus_valid(bus_valid),
    .out_addr(out_addr),.out_data(out_data),.out_valid(out_valid),
    .dbg_cmd_latch(dbg_cmd_latch),
    .dbg_input_addr(dbg_input_addr),.dbg_output_addr(dbg_output_addr),
    .dbg_frozen(dbg_frozen),.dbg_trace(dbg_trace),
    .dbg_breakpoint(dbg_breakpoint),.dbg_priority(dbg_priority));

always #5 clk=~clk;
integer pass_count=0,fail_count=0;

task chk; input [255:0] n; input g,e;
    begin if(g===e) begin $display("  PASS %0s",n); pass_count=pass_count+1; end
    else begin $display("  FAIL %0s got=%b exp=%b",n,g,e); fail_count=fail_count+1; end end
endtask
task chk32; input [255:0] n; input [31:0] g,e;
    begin if(g===e) begin $display("  PASS %0s",n); pass_count=pass_count+1; end
    else begin $display("  FAIL %0s got=%08h exp=%08h",n,g,e); fail_count=fail_count+1; end end
endtask

task send; input [31:0] cmd,da,dd; input dv;
    begin @(negedge clk); cmd_bus<=cmd; cmd_valid<=1;
    bus_addr<=da; bus_data<=dd; bus_valid<=dv;
    @(posedge clk); #1; cmd_valid<=0; bus_valid<=0;
    @(posedge clk); #1; end
endtask

// mk_cfg: topo[10:0] (bit10=sync_wait), dtype, ctype, prio, tr, bp
// layout: {00, bp, tr, prio, ctype, dtype, 0(start), 0s(auth), topo[10:0]}
function [31:0] mk_cfg;
    input [10:0] topo; input [1:0] dtype,ctype; input prio,tr,bp;
    begin mk_cfg={2'b00,bp,tr,prio,ctype,dtype,1'b0,11'h0,topo}; end
endfunction

function [31:0] mk_cmd; input [3:0] code; input [10:0] tok;
    begin mk_cmd={17'h0,tok,code}; end
endfunction

localparam AUTH=11'h2A5, WRONG=11'h100;
localparam IN=32'h1000, OUT=32'h2000;
localparam NOT11=11'b00000000001; // topology=NOT, sync_wait=0
localparam SW11 =11'b10000000001; // topology=NOT, sync_wait=1

reg fired=0;
always @(posedge clk) if(out_valid) fired<=1;
task clr; begin @(negedge clk); fired<=0; end endtask

initial begin
$dumpfile("tb_unicell_v3.vcd"); $dumpvars(0,tb_unicell_v3);
$display("\n=== tb_unicell_v3 ===");

// [1] Reset
$display("\n[1] Reset");
rst=1; repeat(4)@(posedge clk);#1; rst=0; @(posedge clk);#1;
chk32("cmd_latch=0",dbg_cmd_latch,0);
chk  ("out=0",out_valid,0);

// [2] Set addresses
$display("\n[2] Set addresses");
send(mk_cmd(2,0),32'd42,IN, 1); chk32("in_addr", dbg_input_addr, IN);
send(mk_cmd(3,0),32'd42,OUT,1); chk32("out_addr",dbg_output_addr,OUT);

// [3] Bootstrap
$display("\n[3] Bootstrap");
send(mk_cmd(4,0),32'd42,{21'h0,AUTH},1);
@(negedge clk); bus_data<=mk_cfg(NOT11,2'b00,2'b00,0,0,0);
bus_valid<=1; @(posedge clk);#1; bus_valid<=0;
@(posedge clk);#1;
chk  ("armed",  dbg_cmd_latch[22],1);
chk32("topo=1", dbg_cmd_latch&32'h7FF,32'h1);
chk32("auth=0", dbg_cmd_latch&32'h003FF800,32'h0);

// [4] Valid reconfig
$display("\n[4] Valid reconfig");
send(mk_cmd(4,AUTH),32'd42,mk_cfg(NOT11,2'b00,2'b01,1,1,0),1);
@(posedge clk);#1; @(posedge clk);#1;
chk("prio",dbg_priority,1); chk("trace",dbg_trace,1);
chk32("ctype=LATCH",(dbg_cmd_latch>>25)&32'h3,32'h1);

// [5] Wrong auth rejected
$display("\n[5] Wrong auth rejected");
send(mk_cmd(4,WRONG),32'd42,mk_cfg(11'h7FF,2'b11,2'b11,0,0,1),1);
@(posedge clk);#1;
chk("prio unchanged",dbg_priority,1);
chk32("ctype unchanged",(dbg_cmd_latch>>25)&32'h3,32'h1);

// [6] CTYPE_STANDARD fires same cycle
$display("\n[6] CTYPE_STANDARD");
send(mk_cmd(4,AUTH),32'd42,mk_cfg(NOT11,2'b00,2'b00,0,0,0),1);
send(mk_cmd(2,AUTH),32'd42,IN, 1);
send(mk_cmd(3,AUTH),32'd42,OUT,1);
clr;
@(negedge clk); bus_addr<=IN; bus_data<=0; bus_valid<=1;
cmd_bus<=mk_cmd(1,0); cmd_valid<=1;
@(posedge clk);#1; bus_valid<=0; cmd_valid<=0;
repeat(3)@(posedge clk);#1;
chk  ("std fires",   fired,   1'b1);
chk32("std addr",    out_addr, OUT);
chk32("std NOT(0)=1",out_data, 32'h1);
clr;
@(negedge clk); bus_addr<=IN; bus_data<=1; bus_valid<=1;
cmd_bus<=mk_cmd(1,0); cmd_valid<=1;
@(posedge clk);#1; bus_valid<=0; cmd_valid<=0;
repeat(3)@(posedge clk);#1;
chk32("std NOT(1)=0",out_data,32'h0);
bus_valid<=0; cmd_valid<=0;

// [7] CTYPE_LATCH re-emits
$display("\n[7] CTYPE_LATCH");
send(mk_cmd(4,AUTH),32'd42,mk_cfg(NOT11,2'b00,2'b01,0,0,0),1);
send(mk_cmd(2,AUTH),32'd42,IN, 1);
send(mk_cmd(3,AUTH),32'd42,OUT,1);
clr;
@(negedge clk); bus_addr<=IN; bus_data<=0; bus_valid<=1;
cmd_bus<=mk_cmd(1,0); cmd_valid<=1;
@(posedge clk);#1;
chk  ("latch fires",   out_valid,1);
chk32("latch NOT(0)=1",out_data, 32'h1);
bus_valid<=0; cmd_valid<=0;
@(posedge clk);#1;
chk  ("latch re-emits",out_valid,1);
chk32("latch re-val=1",out_data, 32'h1);

// [8] CTYPE_POSEDGE
$display("\n[8] CTYPE_POSEDGE");
send(mk_cmd(4,AUTH),32'd42,mk_cfg(NOT11,2'b00,2'b10,0,0,0),1);
send(mk_cmd(2,AUTH),32'd42,IN, 1);
send(mk_cmd(3,AUTH),32'd42,OUT,1);
clr;
@(negedge clk); bus_addr<=IN; bus_data<=0; bus_valid<=1;
cmd_bus<=mk_cmd(1,0); cmd_valid<=1;
@(posedge clk);#1; bus_valid<=0; cmd_valid<=0;
repeat(3)@(posedge clk);#1;
chk  ("posedge fires",   fired,  1);
chk32("posedge NOT(0)=1",out_data,32'h1);

// [9] CTYPE_NEGEDGE
$display("\n[9] CTYPE_NEGEDGE");
send(mk_cmd(4,AUTH),32'd42,mk_cfg(NOT11,2'b00,2'b11,0,0,0),1);
send(mk_cmd(2,AUTH),32'd42,IN, 1);
send(mk_cmd(3,AUTH),32'd42,OUT,1);
clr;
@(negedge clk); bus_addr<=IN; bus_data<=0; bus_valid<=1;
cmd_bus<=mk_cmd(1,0); cmd_valid<=1;
@(posedge clk);#1; bus_valid<=0; cmd_valid<=0;
repeat(3)@(posedge clk);#1;
chk  ("negedge fires",   fired,  1);
chk32("negedge NOT(0)=1",out_data,32'h1);

// [10] SYNC_WAIT (bit 10 of topo)
$display("\n[10] SYNC_WAIT");
send(mk_cmd(4,AUTH),32'd42,mk_cfg(SW11,2'b00,2'b00,0,0,0),1);
send(mk_cmd(2,AUTH),32'd42,IN, 1);
send(mk_cmd(3,AUTH),32'd42,OUT,1);
clr;
@(negedge clk); bus_addr<=IN; bus_data<=0; bus_valid<=1;
cmd_bus<=mk_cmd(1,0); cmd_valid<=1;
@(posedge clk);#1; bus_valid<=0; cmd_valid<=0;
@(posedge clk);#1;
chk("sync no fire 1st",out_valid,0);
@(negedge clk); bus_addr<=IN; bus_data<=0; bus_valid<=1;
cmd_bus<=mk_cmd(1,0); cmd_valid<=1;
@(posedge clk);#1;
repeat(3)@(posedge clk);#1;
chk  ("sync fires 2nd",fired,   1'b1);
chk32("sync NOT(0)=1", out_data, 32'h1);
bus_valid<=0; cmd_valid<=0;
clr; @(negedge clk); bus_addr<=IN; bus_data<=1; bus_valid<=1;
cmd_bus<=mk_cmd(1,0); cmd_valid<=1;
@(posedge clk);#1; bus_valid<=0; cmd_valid<=0;
@(posedge clk);#1;
chk("sync no fire 3rd",out_valid,0);

// [11] FREEZE/RELEASE
$display("\n[11] FREEZE/RELEASE");
send(mk_cmd(4,AUTH),32'd42,mk_cfg(NOT11,2'b00,2'b00,0,0,0),1);
send(mk_cmd(2,AUTH),32'd42,IN, 1);
send(mk_cmd(3,AUTH),32'd42,OUT,1);
send(mk_cmd(5,AUTH),32'd42,0,0);
@(posedge clk);#1; chk("frozen",dbg_frozen,1);
@(negedge clk); bus_addr<=IN; bus_data<=0; bus_valid<=1;
cmd_bus<=mk_cmd(1,0); cmd_valid<=1;
@(posedge clk);#1; bus_valid<=0; cmd_valid<=0;
@(posedge clk);#1; chk("no out frozen",out_valid,0);
send(mk_cmd(6,AUTH),32'd42,0,0); @(posedge clk);#1;
chk("released",dbg_frozen,0);

// [12] Freeze wire
$display("\n[12] Freeze wire");
freeze=1; @(posedge clk);#1; chk("frozen wire",dbg_frozen,1);
@(negedge clk); bus_addr<=IN; bus_data<=0; bus_valid<=1;
cmd_bus<=mk_cmd(1,0); cmd_valid<=1;
@(posedge clk);#1; bus_valid<=0; cmd_valid<=0;
@(posedge clk);#1; chk("no out wire",out_valid,0);
freeze=0;

// [13] Flags
$display("\n[13] Flags");
send(mk_cmd(4,AUTH),32'd42,mk_cfg(NOT11,2'b00,2'b00,1,1,1),1);
@(posedge clk);#1;
chk("prio",dbg_priority,1); chk("trace",dbg_trace,1); chk("bp",dbg_breakpoint,1);

// [14] dtype
$display("\n[14] dtype");
send(mk_cmd(4,AUTH),32'd42,mk_cfg(NOT11,2'b01,2'b00,0,0,0),1);
@(posedge clk);#1;
chk32("dtype SIGNED",(dbg_cmd_latch>>23)&32'h3,32'h1);

// [15] auth zeroed
$display("\n[15] auth zeroed");
chk32("auth=0",dbg_cmd_latch&32'h003FF800,32'h0);

// [16] PING
$display("\n[16] PING");
clr; send(mk_cmd(9,0),32'd42,0,0);
@(posedge clk);#1;
chk  ("ping fired",  fired,   1);
chk32("ping CELL_ID",out_data,32'd42);

$display("\n=== %0d passed %0d failed ===",pass_count,fail_count);
if(fail_count==0) $display("ALL PASSED"); else $display("FAILURES");
$finish;
end
initial begin #200000; $display("TIMEOUT"); $finish; end
endmodule
