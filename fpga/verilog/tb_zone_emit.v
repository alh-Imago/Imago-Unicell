`timescale 1ns/1ps
// tb_zone_emit.v — command-emit routed THROUGH the array (v3.0). Cell 0 is a
// COMMAND_EMIT cell; when triggered it emits SET_LOGICAL targeted at cell 5. The
// array arbiter routes the emitted command back into the command distribution, so
// cell 5 (and only cell 5) reconfigures itself. No controller issued that command.
module tb_zone_emit;
    localparam NB=2;
    reg clk=0,rst=0; always #5 clk=~clk;
    reg [31:0] cbus=0,cdat=0; reg cv=0;
    wire [15:0] cpu_addr_w=(cbus[7:0]==8'd1)?cdat[31:16]:cdat[15:0];
    wire pre=(cbus[18:17]!=2'b00);
    wire cmv=cv&&(cbus[7:0]!=8'd1)&&((cbus[7:0]!=8'd0)||pre);
    wire [NB-1:0] tv=0; wire [NB*16-1:0] ta=0; wire [NB*32-1:0] td=0;
    wire [15:0] emit_count;
    unicell_zone #(.NUM_CELLS(28),.NUM_BRIDGES(NB),.ZONE_ID(0)) z(.clk(clk),.rst(rst),
      .cmd_bus(cbus),.cmd_data(cdat),.cmd_valid(cmv),.cpu_addr(cpu_addr_w),.cpu_data(cdat),.cpu_valid(cv),
      .out_addr(),.out_data(),.out_valid(),.armed_count(),.arrived_count(),.output_set_count(),
      .emit_count(emit_count),
      .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
      .bridge_n_in_valid(tv),.bridge_n_in_addr(ta),.bridge_n_in_data(td),.bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
      .bridge_s_in_valid(tv),.bridge_s_in_addr(ta),.bridge_s_in_data(td),.bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
      .bridge_e_in_valid(tv),.bridge_e_in_addr(ta),.bridge_e_in_data(td),.bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
      .bridge_w_in_valid(tv),.bridge_w_in_addr(ta),.bridge_w_in_data(td),.bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data());

    wire c5_phys = z.cells.cell_array[5].cell_inst.physical_mode;
    wire c6_phys = z.cells.cell_array[6].cell_inst.physical_mode;

    task xact; input [31:0] cb,cd; begin @(negedge clk);cbus<=cb;cdat<=cd;cv<=1;@(posedge clk);#1;cv<=0;repeat(5)@(posedge clk);#1; end endtask
    task inj;  input [31:0] d; begin @(negedge clk);cbus<=32'h1;cdat<=d;cv<=1;@(posedge clk);#1;cv<=0;repeat(5)@(posedge clk);#1; end endtask

    initial begin
        rst=1; repeat(5)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
        $display("=== command-emit through the array (zone) ===");
        $display("  BEFORE: cell5 phys=%b  cell6 phys=%b  emit_count=%0d", c5_phys, c6_phys, emit_count);

        // configure cell 0 as COMMAND_EMIT via the new opcode, target = cell 5
        xact(32'h00000047, 32'h00000000);   // CMD_TOPO_COMMAND_EMIT (armed)
        xact(32'h14A00003, 32'h00000005);   // SET_OUTPUT_ADDR = 5 (emit target)
        xact(32'h00000012, 32'h0000000E);   // CMD_SWAP_AB: a_data=SET_LOGICAL(0x0E), a_arrived=1 (ISSP-friendly load)
        inj (32'h00000055);                  // single trigger @ addr 0 -> cell0 EMITS
        repeat(8)@(posedge clk);#1;

        $display("  AFTER:  cell5 phys=%b  cell6 phys=%b  emit_count=%0d", c5_phys, c6_phys, emit_count);
        if (c5_phys==1'b0 && c6_phys==1'b1 && emit_count>0)
            $display("  >>> PASS: emit routed through array -> cell5 commanded (phys 1->0), cell6 untouched, emit_count=%0d", emit_count);
        else
            $display("  >>> FAIL");
        $finish;
    end
endmodule
