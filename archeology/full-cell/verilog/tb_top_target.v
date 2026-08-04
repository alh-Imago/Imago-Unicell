`timescale 1ns/1ps
// tb_top_target.v — the TARGET LATCH transport (top-level logic) driving CMD_LOAD_AT.
// Mirrors top_arria10's load_target latch + cpu_addr_w derivation. Drives ISSP-style
// 2-word pulses: SET_TARGET(addr) holds the address lane, CMD_LOAD_AT(config) lands on
// it. Proves an ICM-style stream — (SET_TARGET, LOAD_AT) pairs — configures cells
// heterogeneously through the real transport, not a hand-driven cpu_addr.
module tb_top_target;
    reg clk=0,rst=0; always #5 clk=~clk;
    reg [31:0] cpu_bus=0, cpu_data=0; reg cpu_valid=0;

    // --- mirror of top_arria10 target-latch transport ---
    localparam [7:0] OP_SET_TARGET = 8'd24, OP_LOAD_AT = 8'd23;
    reg [15:0] load_target = 16'h0;
    always @(posedge clk) if (cpu_valid && cpu_bus[7:0]==OP_SET_TARGET) load_target <= cpu_data[15:0];
    wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1)       ? cpu_data[31:16]
                           : (cpu_bus[7:0]==OP_LOAD_AT) ? load_target
                           : cpu_data[15:0];
    wire preload_act = (cpu_bus[18:17]!=2'b00);
    wire cmd_valid_w = cpu_valid && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||preload_act);
    // ----------------------------------------------------

    wire [1:0] tv=0; wire [31:0] ta=0,td=0;
    unicell_zone #(.NUM_CELLS(28),.NUM_BRIDGES(2),.ZONE_ID(0)) z(.clk(clk),.rst(rst),
      .cmd_bus(cpu_bus),.cmd_data(cpu_data),.cmd_valid(cmd_valid_w),.cpu_addr(cpu_addr_w),.cpu_data(cpu_data),.cpu_valid(cpu_valid),
      .out_addr(),.out_data(),.out_valid(),.armed_count(),.arrived_count(),.output_set_count(),.emit_count(),
      .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
      .bridge_n_in_valid(tv),.bridge_n_in_addr(ta),.bridge_n_in_data(td),.bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
      .bridge_s_in_valid(tv),.bridge_s_in_addr(ta),.bridge_s_in_data(td),.bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
      .bridge_e_in_valid(tv),.bridge_e_in_addr(ta),.bridge_e_in_data(td),.bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
      .bridge_w_in_valid(tv),.bridge_w_in_addr(ta),.bridge_w_in_data(td),.bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data());
    wire [9:0] c0=z.cells.cell_array[0].cell_inst.cmd_latch[9:0];
    wire [9:0] c1=z.cells.cell_array[1].cell_inst.cmd_latch[9:0];
    wire [9:0] c5=z.cells.cell_array[5].cell_inst.cmd_latch[9:0];

    // one ISSP pulse: hold word for a cycle, strobe valid (3-write handshake equiv)
    task pulse; input [31:0] b,d; begin
        @(negedge clk); cpu_bus<=b; cpu_data<=d; cpu_valid<=1;
        @(posedge clk); #1; cpu_valid<=0; cpu_bus<=0; cpu_data<=0;
        repeat(3) @(posedge clk); #1;
    end endtask
    // ICM record = (SET_TARGET addr) then (LOAD_AT config)
    task icm; input [15:0] addr; input [31:0] cfg; begin
        pulse({24'h0,OP_SET_TARGET}, {16'h0,addr});
        pulse({24'h0,OP_LOAD_AT}, cfg);
    end endtask

    initial begin
        rst=1; repeat(5)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
        $display("=== TARGET LATCH transport: ICM (SET_TARGET,LOAD_AT) pairs ===");
        icm(16'd0, (32'h0BC | (32'h1<<11)));   // cell 0 -> XOR
        icm(16'd1, (32'h007 | (32'h1<<11)));   // cell 1 -> AND
        icm(16'd5, (32'h024 | (32'h1<<11)));   // cell 5 -> OR
        $display("  cell0=0x%03x(XOR 0x0BC)  cell1=0x%03x(AND 0x007)  cell5=0x%03x(OR 0x024)", c0,c1,c5);
        if (c0==10'h0BC && c1==10'h007 && c5==10'h024)
            $display("  >>> PASS: ICM stream configured 3 cells heterogeneously through the latch");
        else $display("  >>> FAIL");
        $finish;
    end
endmodule
