`timescale 1ns/1ps
module tb_chain_probe;
    reg clk=0, rst=0; reg [31:0] cpu_bus=0, cpu_data=0; reg cpv=0;
    always #5 clk=~clk;
    wire [15:0] cpu_addr_w = (cpu_bus[7:0]==8'd1) ? cpu_data[31:16] : cpu_data[15:0];
    wire pre = (cpu_bus[18:17]!=2'b00);
    wire cmd_valid_w = cpv && (cpu_bus[7:0]!=8'd1) && ((cpu_bus[7:0]!=8'd0)||pre);
    localparam NB=7;
    wire [15:0] oa; wire [31:0] od; wire ov;
    wire [15:0] ac,rc,oc; wire [31:0] cl,ia,oaa,ad,cy;
    unicell_zone #(.ZONE_ID(0)) z (
        .clk(clk),.rst(rst),
        .cmd_bus(cpu_bus),.cmd_data(cpu_data),.cmd_valid(cmd_valid_w),
        .cpu_addr(cpu_addr_w),.cpu_data(cpu_data),.cpu_valid(cpv),
        .out_addr(oa),.out_data(od),.out_valid(ov),
        .armed_count(ac),.arrived_count(rc),.output_set_count(oc),
        .dbg0_cmd_latch(cl),.dbg0_input_addr(ia),.dbg0_output_addr(oaa),.dbg0_a_data(ad),.cycle_count(cy),
        .bridge_n_in_valid({NB{1'b0}}),.bridge_n_in_addr({NB*16{1'b0}}),.bridge_n_in_data({NB*32{1'b0}}),
        .bridge_s_in_valid({NB{1'b0}}),.bridge_s_in_addr({NB*16{1'b0}}),.bridge_s_in_data({NB*32{1'b0}}),
        .bridge_e_in_valid({NB{1'b0}}),.bridge_e_in_addr({NB*16{1'b0}}),.bridge_e_in_data({NB*32{1'b0}}),
        .bridge_w_in_valid({NB{1'b0}}),.bridge_w_in_addr({NB*16{1'b0}}),.bridge_w_in_data({NB*32{1'b0}}));

    // hoist per-cell a_arrived into a flat vector
    wire [27:0] arr;
    genvar gi;
    generate for (gi=0; gi<28; gi=gi+1) begin: probe
        assign arr[gi] = z.cells.cell_array[gi].cell_inst.a_arrived;
    end endgenerate

    task xact; input [31:0] cb,cd; begin
        @(negedge clk); cpu_bus<=cb; cpu_data<=cd; cpv<=1;
        @(posedge clk); #1; cpv<=0; repeat(4) @(posedge clk); #1; end endtask

    integer fires=0; integer k; integer n;
    always @(posedge clk) if (z.cells.out_valid) begin
        fires=fires+1;
        $display("  t=%0t FIRE out_addr=0x%04x out_data=0x%08x", $time, z.cells.out_addr, z.cells.out_data);
    end
    task dump; begin
        n=0; for (k=0;k<28;k=k+1) if (arr[k]) n=n+1;
        $write("  arrived=%0d  [", n);
        for (k=0;k<28;k=k+1) $write("%0d", arr[k]);
        $write("]\n");
    end endtask

    initial begin
        rst=1; repeat(5) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        xact(32'h14A00004, 32'h52800824);
        xact(32'h14A20000, 32'h00000000);
        $display("AFTER CFG+PRELOAD:"); dump();
        $display("INJECT B=0x2340 @ addr 0:");
        xact(32'h00000001, 32'h00002340);
        repeat(60) @(posedge clk);
        $display("AFTER INJECT (fires=%0d):", fires); dump();
        $finish;
    end
endmodule
