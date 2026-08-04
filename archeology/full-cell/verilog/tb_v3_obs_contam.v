// Prove the obs tap is NOT set by the host inject (the silicon contamination).
// Inject alone, with NO cell configured to fire -> obs_bus_valid must stay 0.
`timescale 1ns/1ps
module tb_inject_contam;
    reg clk=0, rst=0; reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] cpu_addr=0; reg [31:0] cpu_data=0; reg cpu_valid=0;
    always #5 clk=~clk;
    wire obs_v; wire [15:0] obs_a; wire [31:0] obs_d;
    wire tie_v=0; wire [15:0] tie_a=0; wire [31:0] tie_d=0;
    unicell_zone64_v3 #(.NUM_CELLS(25),.NUM_BRIDGES(1),.ZONE_ID(0)) zone (
        .clk(clk),.rst(rst),.cmd_bus(cmd_bus),.cmd_data(cmd_data),.cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr),.cpu_data(cpu_data),.cpu_valid(cpu_valid),
        .out_addr(),.out_data(),.out_valid(),
        .armed_count(),.arrived_count(),.output_set_count(),.emit_count(),
        .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
        .obs_bus_valid(obs_v),.obs_bus_addr(obs_a),.obs_bus_data(obs_d),
        .bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
        .bridge_n_in_valid(tie_v),.bridge_n_in_addr(tie_a),.bridge_n_in_data(tie_d),
        .bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
        .bridge_s_in_valid(tie_v),.bridge_s_in_addr(tie_a),.bridge_s_in_data(tie_d),
        .bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
        .bridge_e_in_valid(tie_v),.bridge_e_in_addr(tie_a),.bridge_e_in_data(tie_d),
        .bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data(),
        .bridge_w_in_valid(tie_v),.bridge_w_in_addr(tie_a),.bridge_w_in_data(tie_d));
    integer errs=0;
    initial begin
        rst=1; repeat(4)@(posedge clk);#1; rst=0; repeat(4)@(posedge clk);#1;
        $display("=== INJECT CONTAMINATION TEST ===");
        // Inject with NO cell armed/configured. Nothing should fire.
        @(negedge clk); cpu_addr=16'h0000; cpu_data=32'h0000_00AA; cpu_valid=1'b1;
        @(posedge clk);#1; cpu_valid=1'b0;
        begin: w integer k; reg seen; seen=0;
          for(k=0;k<15;k=k+1) begin if(obs_v) seen=1; @(posedge clk);#1; end
          $display("  inject only, no fire: obs_bus_valid seen=%b (want 0)", seen);
          if (seen) begin $display("  FAIL: inject contaminates the local-bus observation"); errs=errs+1; end
          else $display("  PASS: inject does NOT set obs_bus_valid");
        end
        if (errs==0) $display(">>> CONTAM PASS: obs tap is fire-only, immune to inject");
        else $display(">>> CONTAM FAIL");
        $finish;
    end
endmodule
