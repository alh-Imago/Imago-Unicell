// tb_zone_chain.v — OR chain via DEFAULT addressing (input=CELL_ID, output=CELL_ID+1).
// No BOOT_COMMIT -> cells stay in physical mode and route by CELL_ID, forming a
// natural chain 0->1->2->... Preload A=0 so OR(0,B)=B passes B down the chain
// unchanged. Inject B at addr 0; B should ripple to the last cell. Tests the
// cell-to-cell handoff (za_out feedback + the ibus_addr fix).
`timescale 1ns/1ps
module tb_zone_chain;
    reg clk=0, rst=0; reg [31:0] cpu_bus=0, cpu_data=0; reg cpv=0;
    always #5 clk=~clk;
    wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1) ? cpu_data[31:16] : cpu_data[15:0];
    wire pre = (cpu_bus[18:17]!=2'b00);
    wire cmd_valid_w = cpv && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||pre);
    localparam NB=7;
    wire [15:0] oa; wire [31:0] od; wire ov;
    wire [15:0] ac,rc,oc; wire [31:0] cl,ia,oaa,ad,cy;
    unicell_zone #(.ZONE_ID(0)) z (
        .clk(clk),.rst(rst),
        .cmd_bus(cpu_bus),.cmd_data(cpu_data),.cmd_valid(cmd_valid_w),
        .cpu_addr(cpu_addr_w),.cpu_data(cpu_data),.cpu_valid(cpv),
        .out_addr(oa),.out_data(od),.out_valid(ov),
        .armed_count(ac),.arrived_count(rc),.output_set_count(oc),
        .dbg0_cmd_latch(cl),.dbg0_input_addr(ia),.dbg0_output_addr(oaa),.dbg0_a_data(ad),.cycle_count(cy),
        .bridge_n_in_valid({NB{1'b0}}),.bridge_n_in_addr({NB*16{1'b0}}),.bridge_n_in_data({NB*32{1'b0}}),
        .bridge_s_in_valid({NB{1'b0}}),.bridge_s_in_addr({NB*16{1'b0}}),.bridge_s_in_data({NB*32{1'b0}}),
        .bridge_e_in_valid({NB{1'b0}}),.bridge_e_in_addr({NB*16{1'b0}}),.bridge_e_in_data({NB*32{1'b0}}),
        .bridge_w_in_valid({NB{1'b0}}),.bridge_w_in_addr({NB*16{1'b0}}),.bridge_w_in_data({NB*32{1'b0}}));
    task xact; input [31:0] cb,cd; begin
        @(negedge clk); cpu_bus<=cb; cpu_data<=cd; cpv<=1;
        @(posedge clk); #1; cpv<=0; repeat(4) @(posedge clk); #1; end endtask
    integer fires=0; reg [15:0] last_addr=0; reg [31:0] last_data=0;
    always @(posedge clk) if (ov) begin fires=fires+1; last_addr<=oa; last_data<=od; end
    initial begin
        rst=1; repeat(5) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        xact(32'h14A00004, 32'h52800824);  // RECONFIGURE OR (topology 0x024), physical mode, auth_boot
        xact(32'h14A20000, 32'h00000000);  // preload sel=01 -> a_data=0, a_arrived=1
        $display("after cfg+preload: armed=%0d outset=%0d arrived=%0d  cell0 in=0x%04x out=0x%04x", ac,oc,rc,ia,oaa);
        xact(32'h00000001, 32'h00002340);  // INJECT B=0x2340 at addr 0 (cpu_data[31:16]=0)
        repeat(60) @(posedge clk);          // let the wave ripple
        $display("after inject: fires=%0d  last_out_addr=0x%04x last_out_data=0x%08x  arrived_now=%0d", fires, last_addr, last_data, rc);
        $display("%s", (fires>=2 && last_data==32'h00002340) ?
            ">>> CHAIN PROPAGATED: B rippled cell-to-cell, fires>=2, value intact" :
            (fires==1) ? ">>> only 1 fire — no handoff (cells parallel or feedback addr wrong)" :
                         ">>> no/partial fire — inspect");
        $finish;
    end
endmodule
