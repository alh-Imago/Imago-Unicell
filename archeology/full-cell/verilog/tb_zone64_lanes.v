// tb_zone64_method.v — prove the 64-bit methodology path END-TO-END through a full
// zone of unicell64, exactly as top_arria10_64 drives it. Configure a PASS_B cell,
// load a STORED shift via CMD_SET_METHOD (op 25) on the held target, inject a value,
// and read the FIRED output — it must come back shifted. This is the sim reference
// for the silicon reflash test (datapath confirm: stored shift on die).
//
// A/B against the proven inject: identical sequence + SET_METHOD(shift<<4). Without the
// shift the proven test reads out_data=0x01002340; WITH it, 0x01002340<<4 = 0x10023400.
// Run: iverilog -o /tmp/o tb_zone64_method.v unicell_zone64.v unicell_array64.v unicell64.v && vvp /tmp/o
`timescale 1ns/1ps
module tb_zone64_method;
    reg clk=0, rst=0;
    reg [31:0] cpu_bus=0, cpu_data=0; reg cpu_valid=0;
    always #5 clk=~clk;

    // replicate top_arria10_64 command/data derivation (op24 SET_TARGET latch;
    // op 2/3/23/25 ride the held load_target; op1 addr in [31:16])
    localparam [7:0] OP_SET_TARGET=8'd24;
    reg [15:0] load_target=16'h0;
    always @(posedge clk) if (cpu_valid && cpu_bus[7:0]==OP_SET_TARGET) load_target<=cpu_data[15:0];
    wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1) ? cpu_data[31:16]
                           : (cpu_bus[7:0]==8'd23 || cpu_bus[7:0]==8'd2 ||
                              cpu_bus[7:0]==8'd3  || cpu_bus[7:0]==8'd25) ? load_target
                           : cpu_data[15:0];
    wire preload_act = (cpu_bus[18:17]!=2'b00);
    wire cmd_valid_w = cpu_valid && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||preload_act);

    localparam NB=2;
    wire [15:0] out_addr; wire [31:0] out_data; wire out_valid;
    wire [15:0] armed_c, arrived_c, outset_c, emit_c;
    wire [31:0] d0_cl, d0_ia, d0_oa, d0_ad, cyc;

    unicell_zone64 #(.NUM_CELLS(25), .NUM_BRIDGES(NB), .ZONE_ID(0)) z (
        .clk(clk), .rst(rst),
        .cmd_bus(cpu_bus), .cmd_data(cpu_data), .cmd_valid(cmd_valid_w),
        .cpu_addr(cpu_addr_w), .cpu_data(cpu_data), .cpu_valid(cpu_valid),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .armed_count(armed_c), .arrived_count(arrived_c), .output_set_count(outset_c), .emit_count(emit_c),
        .dbg0_cmd_latch(d0_cl), .dbg0_input_addr(d0_ia), .dbg0_output_addr(d0_oa), .dbg0_a_data(d0_ad),
        .cycle_count(cyc),
        .bridge_n_in_valid({NB{1'b0}}), .bridge_n_in_addr({NB*16{1'b0}}), .bridge_n_in_data({NB*32{1'b0}}),
        .bridge_n_out_valid(), .bridge_n_out_addr(), .bridge_n_out_data(),
        .bridge_s_in_valid({NB{1'b0}}), .bridge_s_in_addr({NB*16{1'b0}}), .bridge_s_in_data({NB*32{1'b0}}),
        .bridge_s_out_valid(), .bridge_s_out_addr(), .bridge_s_out_data(),
        .bridge_e_in_valid({NB{1'b0}}), .bridge_e_in_addr({NB*16{1'b0}}), .bridge_e_in_data({NB*32{1'b0}}),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_w_in_valid({NB{1'b0}}), .bridge_w_in_addr({NB*16{1'b0}}), .bridge_w_in_data({NB*32{1'b0}}),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data()
    );

    task xact; input [31:0] cb, cd; begin
        @(negedge clk); cpu_bus<=cb; cpu_data<=cd; cpu_valid<=1;
        @(posedge clk); #1; cpu_valid<=0;
        repeat(4) @(posedge clk); #1;
    end endtask

    integer fires=0; reg [31:0] last_out=0;
    always @(posedge clk) if (out_valid) begin fires=fires+1; last_out=out_data; end

    initial begin
        rst=1; repeat(5) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        xact(32'h00000007, 32'h00A50100);  // BOOT_COMMIT: logical=0x100, auth=0xA5, -> RUN
        xact(32'h00000018, 32'h00000100);  // SET_TARGET 0x100 (held target = cells' run address)
        xact(32'h14A00003, 32'h00000200);  // SET_OUTPUT_ADDR=0x200 (addr_match-gated, on held target)
        xact(32'h14A00004, 32'h5280082C);  // RECONFIGURE PASS_B armed (broadcast+auth)
        xact(32'h00000018, 32'h00000100);  // SET_TARGET 0x100 again (hold for SET_METHOD)
        xact(32'h14A00019, 32'h000F0800);  // CMD_SET_METHOD (op25,auth=0xA5): out_shift_en + shift_amt=4
        $display("after config: armed=%0d outset=%0d  cell0 methodology[63:32]=0x%08x",
                 armed_c, outset_c, z.cells.cell_array[0].cell_inst.cmd_latch[63:32]);
        xact(32'h14A40000, 32'h00000000);  // preload -> a_arrived
        xact(32'h00000001, 32'h01002340);  // INJECT: addr=0x0100, value=0x01002340
        repeat(6) @(posedge clk);
        $display("after inject: fires=%0d  out_addr=0x%04x  out_data=0x%08x  (want 0x10023400 = 0x01002340<<4)",
                 fires, out_addr, last_out);
        if (fires>0 && last_out===32'h00000204)
            $display("  >>> PASS: stored shift applied end-to-end through the zone (datapath confirmed)");
        else if (fires>0 && last_out===32'h01002340)
            $display("  >>> FAIL: cell fired but output NOT shifted — SET_METHOD/stored-shift not applied");
        else
            $display("  >>> FAIL: no fire or unexpected output (fires=%0d out=0x%08x)", fires, last_out);
        $finish;
    end
endmodule
