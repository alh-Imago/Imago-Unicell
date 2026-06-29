// tb_zone64_ksstage.v — prove the Kogge-Stone JOIN on the new cell: a compute cell
// combining TWO operands where one is pre-shifted, via two-arrival firing.
// This is the last adder mechanism not yet isolated (linear chain + mid-chain shift
// already proven). Built on the PROVEN inject-twice pattern (tb_zone_adder): first
// inject -> stored A, second inject -> bus B (which the stored in-shift acts on), fire.
//
// Stage span=1: Gp = P & (G<<1). The cell's stored in-shift hits the BUS (2nd) operand,
// so inject A=P=0x55 first, B=G=0x22 second; AND(P, G<<1) = 0x55 & 0x44 = 0x44.
`timescale 1ns/1ps
module tb_zone64_ksstage;
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
    integer fires=0; reg [15:0] last_oaddr=0; reg [31:0] last_out=0;
    always @(posedge clk) if (ov) begin fires=fires+1; last_oaddr<=oa; last_out<=od; end

    localparam [31:0] RC = 32'h52800800;     // armed + start_flag + output_set base
    localparam [9:0]  T_AND = 10'h007;
    initial begin
        rst=1; repeat(5)@(posedge clk); #1; rst=0; repeat(2)@(posedge clk); #1;
        // cell 0 @ physical addr 0: AND, output 0x200, stored in-shift <<1 on the bus operand
        xact(32'h14A00003, 32'h00000200);          // SET_OUTPUT_ADDR=0x200
        xact(32'h14A00004, RC | T_AND);            // RECONFIGURE topology=AND, armed
        xact(32'h00000018, 32'h00000000);          // SET_TARGET cell0
        xact(32'h14A00019, 32'h00008200);          // SET_METHOD in_shift_en + shift_amt=1 -> cell0
        $display("cfg: armed=%0d  cell0 in=0x%04x out=0x%04x", ac, ia, oaa);
        // JOIN: inject P first (stored A), then G second (bus, gets <<1) -> AND(P, G<<1)
        xact(32'h00000001, 32'h00000055);          // inject A=P=0x55 @ addr 0 (1st arrival -> stored)
        xact(32'h00000001, 32'h00000022);          // inject B=G=0x22 @ addr 0 (2nd arrival -> shift+fire)
        repeat(20) @(posedge clk);
        $display("after joins: fires=%0d  out_addr=0x%04x  out=0x%08x  (want 0x44 = 0x55 & (0x22<<1))",
                 fires, last_oaddr, last_out);
        if (fires>=1 && last_out==32'h00000044)
            $display("  >>> PASS: KS-stage JOIN — AND(P, G<<1)=0x44 via two-arrival + stored shift");
        else
            $display("  >>> CHECK: out=0x%08x fires=%0d", last_out, fires);
        $finish;
    end
endmodule
