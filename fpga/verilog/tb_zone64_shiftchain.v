// tb_zone64_shiftchain.v — prove STORED SHIFT works INSIDE a chained multi-cell graph
// on the new cell. This is the mechanism the packed adder needs but no test has yet
// exercised on the variant: a cell that pre-shifts its operand, gates, and feeds the
// NEXT cell. Single-cell shift was proven on silicon; CHAINED shift-then-gate-then-
// handoff is the new variable. Smallest graph that isolates it.
//
// Graph (default addressing, input=CELL_ID, output=CELL_ID+1):
//   cell0: OR, a_data=0  -> passes injected B to cell1            (out = B)
//   cell1: OR, a_data=0, STORED in-shift <<4 on the bus operand   (out = B<<4)
//   cell2: OR, a_data=0  -> passes it on                          (out = B<<4)
// Inject B=0x00002340 -> expect the value to ripple and arrive as 0x00023400 (B<<4),
// proving the shift happened MID-CHAIN and the handoff carried the shifted value.
`timescale 1ns/1ps
module tb_zone64_shiftchain;
    reg clk=0, rst=0; reg [31:0] cpu_bus=0, cpu_data=0; reg cpv=0;
    always #5 clk=~clk;
    // top_arria10_64-style cmd derivation (op24 SET_TARGET latch; op 23/2/3/25 ride it)
    reg [15:0] load_target=0;
    always @(posedge clk) if (cpv && cpu_bus[7:0]==8'd24) load_target<=cpu_data[15:0];
    wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1) ? cpu_data[31:16]
                           : (cpu_bus[7:0]==8'd23||cpu_bus[7:0]==8'd2||cpu_bus[7:0]==8'd3||cpu_bus[7:0]==8'd25) ? load_target
                           : cpu_data[15:0];
    wire pre = (cpu_bus[18:17]!=2'b00);
    wire cmd_valid_w = cpv && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||pre);
    localparam NB=2;
    wire [15:0] oa; wire [31:0] od; wire ov;
    wire [15:0] ac,rc,oc,ec; wire [31:0] cl,ia,oaa,ad,cy;
    unicell_zone64 #(.NUM_CELLS(25),.NUM_BRIDGES(NB),.ZONE_ID(0)) z (
        .clk(clk),.rst(rst),
        .cmd_bus(cpu_bus),.cmd_data(cpu_data),.cmd_valid(cmd_valid_w),
        .cpu_addr(cpu_addr_w),.cpu_data(cpu_data),.cpu_valid(cpv),
        .out_addr(oa),.out_data(od),.out_valid(ov),
        .armed_count(ac),.arrived_count(rc),.output_set_count(oc),.emit_count(ec),
        .dbg0_cmd_latch(cl),.dbg0_input_addr(ia),.dbg0_output_addr(oaa),.dbg0_a_data(ad),.cycle_count(cy),
        .bridge_n_in_valid({NB{1'b0}}),.bridge_n_in_addr({NB*16{1'b0}}),.bridge_n_in_data({NB*32{1'b0}}),.bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
        .bridge_s_in_valid({NB{1'b0}}),.bridge_s_in_addr({NB*16{1'b0}}),.bridge_s_in_data({NB*32{1'b0}}),.bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
        .bridge_e_in_valid({NB{1'b0}}),.bridge_e_in_addr({NB*16{1'b0}}),.bridge_e_in_data({NB*32{1'b0}}),.bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
        .bridge_w_in_valid({NB{1'b0}}),.bridge_w_in_addr({NB*16{1'b0}}),.bridge_w_in_data({NB*32{1'b0}}),.bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data());
    task xact; input [31:0] cb,cd; begin
        @(negedge clk); cpu_bus<=cb; cpu_data<=cd; cpv<=1;
        @(posedge clk); #1; cpv<=0; repeat(4) @(posedge clk); #1; end endtask
    integer fires=0; reg [15:0] last_addr=0; reg [31:0] last_data=0;
    always @(posedge clk) if (ov) begin fires=fires+1; last_addr<=oa; last_data<=od; end
    initial begin
        rst=1; repeat(5) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        // all cells: OR, physical mode, auth_boot, a_data=0 (so OR(0,B)=B passes the wave)
        xact(32'h14A00004, 32'h52800824);  // RECONFIGURE OR (0x024) broadcast, auth_boot
        xact(32'h14A20000, 32'h00000000);  // preload sel=01 -> a_data=0, a_arrived=1 (broadcast)
        // give cell1 a STORED in-shift <<4: SET_TARGET cell1's run addr, SET_METHOD in_shift_en+amt4
        // after RECONFIGURE (physical mode), cell1's addr_match key is its CELL_ID=1 (physical)
        xact(32'h00000018, 32'h00000001);  // SET_TARGET 1 (cell1)
        xact(32'h14A00019, 32'h00008800);  // SET_METHOD in_shift_en + shift_amt=4 -> cell1 only
        $display("after cfg: armed=%0d outset=%0d  cell0(dbg) in=0x%04x out=0x%04x", ac, oc, ia, oaa);
        // inject B at cell0 (addr 0); wave: cell0 out=B -> cell1 shifts <<4 -> cell2 passes
        xact(32'h00000001, 32'h00002340);  // INJECT B=0x2340 at addr 0
        repeat(60) @(posedge clk);
        $display("after inject: fires=%0d  last_out_addr=0x%04x last_out_data=0x%08x",
                 fires, last_addr, last_data);
        if (fires>=2 && last_data==32'h00023400)
            $display("  >>> PASS: stored shift applied MID-CHAIN — B<<4 rippled through (0x2340 -> 0x23400)");
        else if (fires>=2 && last_data==32'h00002340)
            $display("  >>> FAIL: chain propagated but shift did NOT apply mid-chain (value unshifted)");
        else
            $display("  >>> CHECK: fires=%0d data=0x%08x (chain/handoff issue, not the shift)", fires, last_data);
        $finish;
    end
endmodule
