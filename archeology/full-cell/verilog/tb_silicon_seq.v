// Replays the EXACT silicon command words from transit_diag.tcl through one zone,
// to verify the corrected sequence configures + fires IN SIM before flashing.
`timescale 1ns/1ps
module tb_silicon_seq;
    reg clk=0, rst=0;
    reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] cpu_addr=0; reg [31:0] cpu_data=0; reg cpu_valid=0;
    always #5 clk=~clk;

    wire [15:0] z_out_addr; wire [31:0] z_out_data; wire z_out_valid;
    wire bre_v; wire [15:0] bre_a; wire [31:0] bre_d;
    wire tie_v=1'b0; wire [15:0] tie_a=0; wire [31:0] tie_d=0;

    unicell_zone64_v3 #(.NUM_CELLS(5),.NUM_BRIDGES(1),.ZONE_ID(0)) zone (
        .clk(clk),.rst(rst),
        .cmd_bus(cmd_bus),.cmd_data(cmd_data),.cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr),.cpu_data(cpu_data),.cpu_valid(cpu_valid),
        .out_addr(z_out_addr),.out_data(z_out_data),.out_valid(z_out_valid),
        .armed_count(),.arrived_count(),.output_set_count(),.emit_count(),
        .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
        .bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
        .bridge_n_in_valid(tie_v),.bridge_n_in_addr(tie_a),.bridge_n_in_data(tie_d),
        .bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
        .bridge_s_in_valid(tie_v),.bridge_s_in_addr(tie_a),.bridge_s_in_data(tie_d),
        .bridge_e_out_valid(bre_v),.bridge_e_out_addr(bre_a),.bridge_e_out_data(bre_d),
        .bridge_e_in_valid(tie_v),.bridge_e_in_addr(tie_a),.bridge_e_in_data(tie_d),
        .bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data(),
        .bridge_w_in_valid(tie_v),.bridge_w_in_addr(tie_a),.bridge_w_in_data(tie_d)
    );

    // Replicate the top-level cpu_addr_w mux for opcode 1 (INJECT) and target latch
    reg [15:0] load_target=0;
    always @(posedge clk) if (cpu_valid_cmd && (cmd_bus[7:0]==8'd24)) load_target<=cmd_data[15:0];
    // Simplified: drive cmd path; for opcode1 the addr comes from cmd_data[31:16]
    reg cpu_valid_cmd;

    task tcmd; input [31:0] cb; input [31:0] cd; begin
        @(negedge clk);
        if (cb[7:0]==8'd1) begin
            // opcode 1 INJECT: pure cpu-path data write (NOT a command). The
            // silicon top-level's cmd_valid_w excludes opcode 1, routing it to
            // cpu_* instead. addr from cd[31:16], data = value.
            cpu_addr=cd[31:16]; cpu_data=cd; cpu_valid=1'b1;
            @(posedge clk); #1; cpu_valid=1'b0;
        end else begin
            cmd_bus=cb; cmd_data=cd; cmd_valid=1'b1;
            if (cb[7:0]==8'd24) load_target<=cd[15:0];
            @(posedge clk); #1; cmd_valid=1'b0;
        end
        repeat(2) @(posedge clk); #1;
    end endtask

    initial begin
        rst=1; repeat(4)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
        $display("=== SILICON SEQUENCE REPLAY (transit=1) ===");
        // exact words from transit_diag.tcl
        tcmd(32'h00000007, 32'h00A50000);  // BOOT input_addr=0
        tcmd(32'h00000018, 32'h00000000);  // SET_TARGET 0
        tcmd(32'h05280004, 32'h5282082C);  // RECONFIGURE PASS_B armed latch_in
        $display("  after reconfig: cmd_latch=0x%08x (topo=0x%03x start=%b latch_in=%b) in=0x%04x",
                 zone.cells.cell_array[0].cell_inst.cmd_latch[31:0],
                 zone.cells.cell_array[0].cell_inst.cmd_latch[9:0],
                 zone.cells.cell_array[0].cell_inst.cmd_latch[22],
                 zone.cells.cell_array[0].cell_inst.cmd_latch[26],
                 zone.cells.cell_array[0].cell_inst.input_address);
        tcmd(32'h00000018, 32'h00000000);  // SET_TARGET
        tcmd(32'h05280003, 32'h00000200);  // SET_OUTPUT 0x200
        tcmd(32'h00000018, 32'h00000000);
        tcmd(32'h05280022, 32'h00000004);  // ROUTING = E
        tcmd(32'h00000018, 32'h00000000);
        tcmd(32'h05280023, 32'h00000001);  // TRANSIT = 1
        $display("  after routing+transit: rmask=0x%x transit=%b out_addr=0x%04x",
                 zone.cells.cell_array[0].cell_inst.cmd_latch[14:11],
                 zone.cells.cell_array[0].cell_inst.cmd_latch[15],
                 zone.cells.cell_array[0].cell_inst.output_address);
        tcmd(32'h00000018, 32'h00000000);
        tcmd(32'h05280012, 32'h00000000);  // SWAP_AB prime
        $display("  after prime: a_arrived=%b", zone.cells.cell_array[0].cell_inst.a_arrived);
        tcmd(32'h00000001, 32'h0000_00F0);  // INJECT addr=0x100 value=0xAA

        // watch for fire
        begin: w integer k; reg seen_e, seen_l;
            seen_e=0; seen_l=0;
            for(k=0;k<20;k=k+1) begin
                if (bre_v) seen_e=1;
                if (zone.cells.bus_valid) seen_l=1;
                @(posedge clk); #1;
            end
            $display("  RESULT: east_bridge=%b  local_bus=%b", seen_e, seen_l);
            if (seen_e && !seen_l) $display("  >>> TRANSIT WORKS: crossed east, local suppressed");
            else if (!seen_e && !seen_l) $display("  >>> NOTHING FIRED - config/fire issue remains");
            else $display("  >>> east=%b local=%b (transit=1 wanted east=1,local=0)", seen_e, seen_l);
        end
        $finish;
    end
endmodule
