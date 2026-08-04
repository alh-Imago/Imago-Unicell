`timescale 1ns/1ps
module tb_reset;
    reg clk=0, rst=0; reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] cpu_addr=0; reg [31:0] cpu_data=0; reg cpu_valid=0;
    always #5 clk=~clk;
    wire [15:0] za; wire [31:0] zd; wire zv;
    wire tie_v=0; wire [15:0] tie_a=0; wire [31:0] tie_d=0;
    unicell_zone64_v3 #(.NUM_CELLS(5),.NUM_BRIDGES(1),.ZONE_ID(0)) zone (
        .clk(clk),.rst(rst),.cmd_bus(cmd_bus),.cmd_data(cmd_data),.cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr),.cpu_data(cpu_data),.cpu_valid(cpu_valid),
        .out_addr(za),.out_data(zd),.out_valid(zv),
        .armed_count(),.arrived_count(),.output_set_count(),.emit_count(),
        .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
        .bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
        .bridge_n_in_valid(tie_v),.bridge_n_in_addr(tie_a),.bridge_n_in_data(tie_d),
        .bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
        .bridge_s_in_valid(tie_v),.bridge_s_in_addr(tie_a),.bridge_s_in_data(tie_d),
        .bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
        .bridge_e_in_valid(tie_v),.bridge_e_in_addr(tie_a),.bridge_e_in_data(tie_d),
        .bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data(),
        .bridge_w_in_valid(tie_v),.bridge_w_in_addr(tie_a),.bridge_w_in_data(tie_d));
    task tc; input [31:0] cb,cd; begin @(negedge clk);
        if (cb[7:0]==8'd1) begin cpu_addr=cd[31:16]; cpu_data=cd; cpu_valid=1; @(posedge clk);#1; cpu_valid=0; end
        else begin cmd_bus=cb; cmd_data=cd; cmd_valid=1; @(posedge clk);#1; cmd_valid=0; end
        repeat(2) @(posedge clk);#1; end endtask
    initial begin
        rst=1; repeat(4)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
        // First: boot cell to input_addr 0x100 and commit to RUN (simulate stale state)
        tc(32'h00000007, 32'h00A50100);  // boot -> input_addr 0x100, RUN
        $display("stale: physical_mode=%b input_addr=0x%04x",
            zone.cells.cell_array[0].cell_inst.physical_mode,
            zone.cells.cell_array[0].cell_inst.input_address);
        // Now ARRAY_RESET (auth 0xA5 token at [29:19] => 0x05280008)
        tc(32'h05280008, 32'h00000000);
        $display("after reset: physical_mode=%b input_addr=0x%04x (want physical_mode=1, addr=CELL_ID=0)",
            zone.cells.cell_array[0].cell_inst.physical_mode,
            zone.cells.cell_array[0].cell_inst.input_address);
        // Fresh boot to input_addr 0 should now TAKE (physical_mode=1)
        tc(32'h00000007, 32'h00A50000);
        $display("after fresh boot: physical_mode=%b input_addr=0x%04x (want addr=0)",
            zone.cells.cell_array[0].cell_inst.physical_mode,
            zone.cells.cell_array[0].cell_inst.input_address);
        // configure + fire
        tc(32'h00000018, 32'h00000000);
        tc(32'h05280004, 32'h5282082C);
        tc(32'h00000018, 32'h00000000);
        tc(32'h05280012, 32'h00000000);
        tc(32'h00000001, 32'h0000_00F0);
        begin: w integer k; reg seen; seen=0;
          for(k=0;k<20;k=k+1) begin if(zone.cells.bus_valid) seen=1; @(posedge clk);#1; end
          $display("fire after reset+reboot: local_bus=%b %s", seen, seen?">>> RESET WORKS":">>> no fire"); end
        $finish;
    end
endmodule
