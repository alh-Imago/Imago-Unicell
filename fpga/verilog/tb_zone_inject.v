// tb_zone_inject.v — drive the host-inject path through a full zone exactly as
// top_arria10 does, and watch whether a cell ever fires. Reproduces the silicon
// no-fire in sim with full visibility.
`timescale 1ns/1ps
module tb_zone_inject;
    reg clk=0, rst=0;
    reg [31:0] cpu_bus=0, cpu_data=0; reg cpu_valid_r2=0;
    always #5 clk=~clk;

    // replicate top_arria10 command/data derivation
    wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1) ? cpu_data[31:16] : cpu_data[15:0];
    wire preload_act = (cpu_bus[18:17]!=2'b00);
    wire cmd_valid_w = cpu_valid_r2 && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||preload_act);

    localparam NB = 7;
    wire [15:0] out_addr; wire [31:0] out_data; wire out_valid;
    wire [15:0] armed_c, arrived_c, outset_c;
    wire [31:0] d0_cl, d0_ia, d0_oa, d0_ad; wire [31:0] cyc;

    unicell_zone #(.ZONE_ID(0)) z (
        .clk(clk), .rst(rst),
        .cmd_bus(cpu_bus), .cmd_data(cpu_data), .cmd_valid(cmd_valid_w),
        .cpu_addr(cpu_addr_w), .cpu_data(cpu_data), .cpu_valid(cpu_valid_r2),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .armed_count(armed_c), .arrived_count(arrived_c), .output_set_count(outset_c),
        .dbg0_cmd_latch(d0_cl), .dbg0_input_addr(d0_ia), .dbg0_output_addr(d0_oa), .dbg0_a_data(d0_ad),
        .cycle_count(cyc),
        .bridge_n_in_valid({NB{1'b0}}), .bridge_n_in_addr({NB*16{1'b0}}), .bridge_n_in_data({NB*32{1'b0}}),
        .bridge_s_in_valid({NB{1'b0}}), .bridge_s_in_addr({NB*16{1'b0}}), .bridge_s_in_data({NB*32{1'b0}}),
        .bridge_e_in_valid({NB{1'b0}}), .bridge_e_in_addr({NB*16{1'b0}}), .bridge_e_in_data({NB*32{1'b0}}),
        .bridge_w_in_valid({NB{1'b0}}), .bridge_w_in_addr({NB*16{1'b0}}), .bridge_w_in_data({NB*32{1'b0}})
    );

    // one host transaction: present bus, pulse cpu_valid for 1 cycle
    task xact; input [31:0] cb, cd; begin
        @(negedge clk); cpu_bus<=cb; cpu_data<=cd; cpu_valid_r2<=1;
        @(posedge clk); #1; cpu_valid_r2<=0;
        repeat(4) @(posedge clk); #1;   // settle (commands need a few cycles through the pipe)
    end endtask

    integer fires=0;
    always @(posedge clk) if (out_valid) fires=fires+1;

    initial begin
        rst=1; repeat(5) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        xact(32'h00000007, 32'h00A50100);  // BOOT_COMMIT
        xact(32'h14A00003, 32'h00000200);  // SET_OUTPUT_ADDR
        xact(32'h14A00004, 32'h5280082C);  // RECONFIGURE
        $display("after config:  armed=%0d outset=%0d arrived=%0d  cell0 cl=0x%08x oa=0x%04x", armed_c, outset_c, arrived_c, d0_cl, d0_oa);
        xact(32'h14A40000, 32'h00000000);  // preload -> a_arrived
        $display("after preload: arrived=%0d  cell0 a_data=0x%08x", arrived_c, d0_ad);
        xact(32'h00000001, 32'h01002340);  // INJECT (opcode 1, addr=0x0100 in [31:16])
        repeat(6) @(posedge clk);
        $display("after inject:  arrived=%0d  out_valid_fires=%0d  out_addr=0x%04x out_data=0x%08x", arrived_c, fires, out_addr, out_data);
        $display("%s", (arrived_c < 28) ? ">>> FIRED in sim: delivery path OK -> silicon issue is timing/CDC/build" :
                                          ">>> NO FIRE in sim: reproduced! the bug is in the zone/array delivery logic");
        $finish;
    end
endmodule
