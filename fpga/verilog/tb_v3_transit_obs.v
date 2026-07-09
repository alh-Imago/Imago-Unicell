`timescale 1ns/1ps
module tb_obs_run;
    reg clk=0, rst=0; reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] cpu_addr=0; reg [31:0] cpu_data=0; reg cpu_valid=0;
    always #5 clk=~clk;
    wire [15:0] za; wire [31:0] zd; wire zv;
    wire bre_v; wire [15:0] bre_a; wire [31:0] bre_d;
    wire obs_v; wire [15:0] obs_a; wire [31:0] obs_d;
    wire tie_v=0; wire [15:0] tie_a=0; wire [31:0] tie_d=0;
    unicell_zone64_v3 #(.NUM_CELLS(25),.NUM_BRIDGES(1),.ZONE_ID(0)) zone (
        .clk(clk),.rst(rst),.cmd_bus(cmd_bus),.cmd_data(cmd_data),.cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr),.cpu_data(cpu_data),.cpu_valid(cpu_valid),
        .out_addr(za),.out_data(zd),.out_valid(zv),
        .armed_count(),.arrived_count(),.output_set_count(),.emit_count(),
        .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
        .obs_bus_valid(obs_v),.obs_bus_addr(obs_a),.obs_bus_data(obs_d),
        .bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
        .bridge_n_in_valid(tie_v),.bridge_n_in_addr(tie_a),.bridge_n_in_data(tie_d),
        .bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
        .bridge_s_in_valid(tie_v),.bridge_s_in_addr(tie_a),.bridge_s_in_data(tie_d),
        .bridge_e_out_valid(bre_v),.bridge_e_out_addr(bre_a),.bridge_e_out_data(bre_d),
        .bridge_e_in_valid(tie_v),.bridge_e_in_addr(tie_a),.bridge_e_in_data(tie_d),
        .bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data(),
        .bridge_w_in_valid(tie_v),.bridge_w_in_addr(tie_a),.bridge_w_in_data(tie_d));
    task tc; input [31:0] cb,cd; begin @(negedge clk);
        if (cb[7:0]==8'd1) begin cpu_addr=cd[31:16]; cpu_data=cd; cpu_valid=1; @(posedge clk);#1; cpu_valid=0; end
        else begin cmd_bus=cb; cmd_data=cd; cmd_valid=1; @(posedge clk);#1; cmd_valid=0; end
        repeat(2) @(posedge clk);#1; end endtask
    integer errs=0;
    task run; input transit; begin : r
        reg lbus_seen, bre_seen; integer k;
        lbus_seen=0; bre_seen=0;
        tc(32'h05280008, 32'h00000000);        // ARRAY_RESET
        tc(32'h00000007, 32'h00A50000);        // BOOT input 0
        tc(32'h00000018, 32'h00000000);        // SET_TARGET 0 (CELL_ID)
        tc(32'h05280003, 32'h00000200);        // out_addr 0x200
        tc(32'h05280004, 32'h5282082C);        // PASS_B armed latch_in
        tc(32'h00000018, 32'h00000000);
        tc(32'h05280022, 32'h00000004);        // routing E
        tc(32'h00000018, 32'h00000000);
        tc(32'h05280023, transit?32'h1:32'h0); // transit flag
        tc(32'h00000018, 32'h00000000);
        tc(32'h05280012, 32'h00000000);        // SWAP_AB prime
        tc(32'h00000001, 32'h0000_00AA);       // INJECT -> fire
        for(k=0;k<25;k=k+1) begin
            if (obs_v)  lbus_seen=1;
            if (bre_v)  bre_seen=1;
            @(posedge clk);#1;
        end
        $display("  transit=%b : bre_seen=%b  lbus_seen=%b", transit, bre_seen, lbus_seen);
        if (transit) begin
            if (bre_seen && !lbus_seen) $display("    PASS: crossed east, LOCAL BUS QUIET (transit proven)");
            else begin $display("    FAIL: want bre=1 lbus=0"); errs=errs+1; end
        end else begin
            if (bre_seen && lbus_seen) $display("    PASS: crossed east AND local bus driven (control)");
            else begin $display("    FAIL: want bre=1 lbus=1"); errs=errs+1; end
        end
    end endtask
    initial begin
        rst=1; repeat(4)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
        $display("=== LOCAL-BUS OBSERVATION (the signal transit suppresses) ===");
        run(1'b1);
        run(1'b0);
        if (errs==0) $display(">>> OBS PASS: lbus_seen cleanly distinguishes transit from control");
        else $display(">>> OBS FAIL: %0d errors", errs);
        $finish;
    end
endmodule
