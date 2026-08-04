// tb_zone64_add_entry.v — ADDER ENTRY stage, physics-driven, load-cold-then-release.
//   G = a & b   (AND)      P = a ^ b   (XOR)
// Two operands a,b presented at the entry; each fans to BOTH stage-0 cells; two-arrival fires
// each. Mirrors the real load: configure cells, FREEZE (inert during load), then ONE broadcast
// RELEASE = the single controller->physics handoff. Then present a,b — fabric does the rest.
//
// Current model convention: logical address = physical CELL_ID. Offsets consistent from a base.
// G=cell0 listens@0x100 emits@0x200 ; P=cell1 listens@0x100 emits@0x201. a,b injected to 0x100
// (shared listen = entry fan-out) -> a(1st=A), b(2nd=B) at each -> fire.
`timescale 1ns/1ps
module tb_zone64_add_entry;
    reg clk=0, rst=0; reg [31:0] cpu_bus=0, cpu_data=0; reg cpv=0;
    always #5 clk=~clk;
    reg [15:0] load_target=0;
    always @(posedge clk) if (cpv && cpu_bus[7:0]==8'd24) load_target<=cpu_data[15:0];
    wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1) ? cpu_data[31:16]
        : (cpu_bus[7:0]==8'd23||cpu_bus[7:0]==8'd2||cpu_bus[7:0]==8'd3||cpu_bus[7:0]==8'd25) ? load_target
        : cpu_data[15:0];
    wire pre = (cpu_bus[18:17]!=2'b00);
    wire cmd_valid_w = cpv && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||pre);
    localparam NB=2;
    wire [15:0] oa; wire [31:0] od; wire ov; wire [15:0] ac,rc_,oc,ec; wire [31:0] cl,ia,oaa,ad,cy;
    unicell_zone64 #(.NUM_CELLS(25),.NUM_BRIDGES(NB),.ZONE_ID(0),.DEBUG_SELECT(1)) z (
        .clk(clk),.rst(rst),.cmd_bus(cpu_bus),.cmd_data(cpu_data),.cmd_valid(cmd_valid_w),
        .cpu_addr(cpu_addr_w),.cpu_data(cpu_data),.cpu_valid(cpv),
        .out_addr(oa),.out_data(od),.out_valid(ov),
        .armed_count(ac),.arrived_count(rc_),.output_set_count(oc),.emit_count(ec),
        .dbg0_cmd_latch(cl),.dbg0_input_addr(ia),.dbg0_output_addr(oaa),.dbg0_a_data(ad),.cycle_count(cy),
        .bridge_n_in_valid({NB{1'b0}}),.bridge_n_in_addr({NB*16{1'b0}}),.bridge_n_in_data({NB*32{1'b0}}),.bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
        .bridge_s_in_valid({NB{1'b0}}),.bridge_s_in_addr({NB*16{1'b0}}),.bridge_s_in_data({NB*32{1'b0}}),.bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
        .bridge_e_in_valid({NB{1'b0}}),.bridge_e_in_addr({NB*16{1'b0}}),.bridge_e_in_data({NB*32{1'b0}}),.bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
        .bridge_w_in_valid({NB{1'b0}}),.bridge_w_in_addr({NB*16{1'b0}}),.bridge_w_in_data({NB*32{1'b0}}),.bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data());
    task xact; input [31:0] cb,cd; begin
        @(negedge clk); cpu_bus<=cb; cpu_data<=cd; cpv<=1;
        @(posedge clk); #1; cpv<=0; repeat(4) @(posedge clk); #1; end endtask
    integer fires=0; reg [31:0] gval=0,pval=0; reg gseen=0,pseen=0;
    always @(posedge clk) if (ov) begin
        fires=fires+1;
        if (oa==16'h0200) begin gseen<=1; gval<=od; end
        if (oa==16'h0201) begin pseen<=1; pval<=od; end
    end
    localparam [31:0] RC = 32'h52800800;   // armed (start_flag=1), output_set forced
    initial begin
        rst=1; repeat(5)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
        // ---- LOAD on PHYSICAL addressing (logical=physical; no mode switch) ----
        // G = cell0: emit 0x200, AND (listens on physical addr 0)
        xact(32'h00000018,32'h00000000);          // target cell0
        xact(32'h14A00003,32'h00000200);          // SET_OUTPUT_ADDR 0x200
        xact(32'h14A00017,RC|32'h007);            // LOAD_AT cell0 = AND (addr-gated, no broadcast)
        // P = cell1: emit 0x201, XOR (listens on physical addr 1)
        xact(32'h00000018,32'h00000001);          // target cell1
        xact(32'h14A00003,32'h00000201);          // SET_OUTPUT_ADDR 0x201
        xact(32'h14A00017,RC|32'h0BC);            // LOAD_AT cell1 = XOR (addr-gated, no broadcast)
        // ---- FREEZE all (inert) then RELEASE as ONE (the handoff) ----
        xact(32'h14A00005,32'h00000000);          // CMD_FREEZE broadcast
        $display("loaded+frozen: armed=%0d outset=%0d", ac, oc);
        xact(32'h14A00006,32'h00000000);          // CMD_RELEASE broadcast = GO LIVE
        // ---- entry fan-out: a to BOTH cells (A), then b to BOTH cells (B) ----
        xact(32'h00000001,32'h00001234);          // a -> cell0 [A]
        xact(32'h00000001,32'h0000ABCD);          // b -> cell0 [fire G]
        xact(32'h00000001,32'h00011234);          // a -> cell1 [A]
        xact(32'h00000001,32'h0001ABCD);          // b -> cell1 [fire P]
        repeat(25) @(posedge clk);
        $display("fires=%0d  G(0x200)=%0d:0x%08x  P(0x201)=%0d:0x%08x", fires, gseen, gval, pseen, pval);
        $display("want G=a&b=0x%08x  P=a^b=0x%08x", 32'h1234&32'hABCD, 32'h1234^32'hABCD);
        if (gseen && pseen && gval==(32'h1234&32'hABCD) && pval==(32'h1234^32'hABCD))
            $display("  >>> PASS: entry — load-cold/release, a&b presented, G=a&b and P=a^b both fired");
        else $display("  >>> CHECK: gseen=%0d pseen=%0d gval=0x%08x pval=0x%08x", gseen,pseen,gval,pval);
        $finish;
    end
endmodule
