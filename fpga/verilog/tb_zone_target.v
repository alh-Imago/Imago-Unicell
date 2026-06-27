`timescale 1ns/1ps
// tb_zone_target.v — Alan's address-lane targeting model via CMD_LOAD_AT.
// Target rides the ADDRESS lane (cpu_addr -> bus_addr -> addr_match); config rides
// cmd_data; auth in cmd_bus. Only the addressed cell applies. Proves heterogeneous
// per-cell config: cell0->XOR, cell1->AND, cell2 untouched — and that the address
// and command align across the registered bus.
module tb_zone_target;
    reg clk=0,rst=0; always #5 clk=~clk;
    reg [31:0] cb=0,cd=0; reg cv=0;
    reg [15:0] caddr=16'h0; reg cpv=0;          // address lane, driven INDEPENDENTLY
    wire [1:0] tv=0; wire [31:0] ta=0,td=0;
    unicell_zone #(.NUM_CELLS(28),.NUM_BRIDGES(2),.ZONE_ID(0)) z(.clk(clk),.rst(rst),
      .cmd_bus(cb),.cmd_data(cd),.cmd_valid(cv&&(cb[7:0]!=8'd1)),.cpu_addr(caddr),.cpu_data(cd),.cpu_valid(cpv),
      .out_addr(),.out_data(),.out_valid(),.armed_count(),.arrived_count(),.output_set_count(),.emit_count(),
      .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
      .bridge_n_in_valid(tv),.bridge_n_in_addr(ta),.bridge_n_in_data(td),.bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
      .bridge_s_in_valid(tv),.bridge_s_in_addr(ta),.bridge_s_in_data(td),.bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
      .bridge_e_in_valid(tv),.bridge_e_in_addr(ta),.bridge_e_in_data(td),.bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
      .bridge_w_in_valid(tv),.bridge_w_in_addr(ta),.bridge_w_in_data(td),.bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data());
    wire [9:0] c0=z.cells.cell_array[0].cell_inst.cmd_latch[9:0];
    wire [9:0] c1=z.cells.cell_array[1].cell_inst.cmd_latch[9:0];
    wire [9:0] c2=z.cells.cell_array[2].cell_inst.cmd_latch[9:0];
    localparam [7:0] LOAD_AT = 8'd23;

    // load_at(target, config): drive address lane to settle bus_addr_r=target,
    // then pulse CMD_LOAD_AT with config on cmd_data. Address held across the pulse.
    task load_at; input [15:0] tgt; input [31:0] cfg; begin
        @(negedge clk); caddr<=tgt; cpv<=1; cb<=0; cd<=0; cv<=0;   // settle address
        repeat(2) @(posedge clk); #1;
        @(negedge clk); caddr<=tgt; cpv<=1; cb<={24'h0,LOAD_AT}; cd<=cfg; cv<=1; // command
        @(posedge clk); #1; cv<=0; cpv<=0;
        repeat(3) @(posedge clk); #1;
    end endtask

    initial begin
        rst=1; repeat(5)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
        $display("=== CMD_LOAD_AT — per-cell targeting via the ADDRESS lane (addr_match) ===");
        load_at(16'd0, (32'h0BC | (32'h1<<11)));   // cell 0 -> XOR  (start_flag set)
        load_at(16'd1, (32'h007 | (32'h1<<11)));   // cell 1 -> AND
        $display("  cell0=0x%03x (want 0x0BC)  cell1=0x%03x (want 0x007)  cell2=0x%03x (untouched 0x000)", c0,c1,c2);
        if (c0==10'h0BC && c1==10'h007 && c2==10'h000)
            $display("  >>> PASS: address-lane targeting — two cells, two topologies, neighbour untouched");
        else $display("  >>> FAIL");
        $finish;
    end
endmodule
