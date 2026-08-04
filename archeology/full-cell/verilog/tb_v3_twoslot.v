// tb_v3_twoslot.v — STAGE 2 (collapsed encoding): self-describing methodology opcodes.
// slot A = cmd_bus[7:0] IS the opcode; slot B [15:8] optional 2nd methodology gated by
// B_valid[16]; arm[18]. Guard: topology op in B refused. Auth [63:53] never touched.
`timescale 1ns/1ps
module tb_v3_twoslot;
    reg clk=0, rst=0; reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] bus_addr=0; reg [31:0] bus_data=0; reg bus_valid=0;
    always #5 clk=~clk;
    wire [15:0] out_addr; wire [31:0] out_data; wire out_valid; wire [31:0] dbg_cmd_latch;
    unicell64_v3 #(.CELL_ID(16'h0005)) dut (
        .clk(clk),.rst(rst),.cmd_bus(cmd_bus),.cmd_data(cmd_data),.cmd_valid(cmd_valid),
        .bus_addr(bus_addr),.bus_data(bus_data),.bus_valid(bus_valid),
        .out_addr(out_addr),.out_data(out_data),.out_valid(out_valid),.dbg_cmd_latch(dbg_cmd_latch));
    task cmd; input [31:0] cb,cd; begin
        @(negedge clk); bus_addr=16'h0005; cmd_bus=cb; cmd_data=cd; cmd_valid=1;
        @(posedge clk); #1; cmd_valid=0; repeat(3)@(posedge clk); #1; end endtask
    integer errors=0;
    task ck; input [63:0] got,want; input [200:0] m; begin
        if (got===want) $display("  PASS: %0s", m);
        else begin $display("  FAIL: %0s got=0x%0x want=0x%0x", m,got,want); errors=errors+1; end
    end endtask
    localparam CMD_LOAD_AT=8'd23, CMD_BOOT_COMMIT=8'd7;
    localparam METH_SET_MASK=8'd30, METH_SET_SHIFT_IN=8'd31, METH_SET_SHIFT_OUT=8'd32, METH_SET_LANE=8'd33;
    localparam CMD_TOPO_NOR=8'd53; // a topology op, for the guard test
    // word: opA[7:0] | opB[15:8] | Bvalid[16] | arm[18] | auth 0x0A5 [29:19]
    function [31:0] w; input [7:0] opA,opB; input bvalid,arm; begin
        w = (32'h0A5<<19)|(arm<<18)|(bvalid<<16)|({8'h0,opB}<<8)|{24'h0,opA}; end
    endfunction
    initial begin
        rst=1; repeat(4)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
        cmd({8'h0,3'b0,11'h0,CMD_LOAD_AT},(32'h0A5<<20)|32'h0);
        cmd({8'h0,3'b0,11'h0,CMD_BOOT_COMMIT},32'h00A5_0100);
        $display("=== STAGE 2 collapsed: self-describing opcodes, B_valid, arm ===");
        $display("auth=0x%03x physical=%0d",dut.cmd_latch[63:53],dut.physical_mode);

        // A only: SET_MASK 0x3C, no B
        cmd(w(METH_SET_MASK,8'h0, 1'b0,1'b0), 32'h0000_003C);
        ck(dut.cmd_latch[39:32],8'h3C,"A-only SET_MASK -> mask 0x3C");
        ck(dut.cmd_latch[40],1'b1,"mask_en set");
        ck(dut.cmd_latch[63:53],11'h0A5,"auth untouched");

        // A only: SET_SHIFT_IN 0x05 (this was the failing case before — now slot A IS the opcode)
        cmd(w(METH_SET_SHIFT_IN,8'h0, 1'b0,1'b0), 32'h0000_0005);
        ck(dut.cmd_latch[46:41],6'h05,"A-only SHIFT_IN -> amt 0x05 (collision fixed)");
        ck(dut.cmd_latch[47],1'b1,"in_shift_en set");

        // A + B compose: SHIFT_OUT(A)=0x07 + LANE(B)=0x2, B_valid, arm
        cmd(w(METH_SET_SHIFT_OUT,METH_SET_LANE, 1'b1,1'b1), (32'h2<<16)|32'h0000_0007);
        ck(dut.cmd_latch[46:41],6'h07,"compose: SHIFT_OUT(A) amt 0x07");
        ck(dut.cmd_latch[48],1'b1,"out_shift_en set");
        ck(dut.cmd_latch[51:49],3'h2,"compose: LANE(B) 0x2 in same pass");
        ck(dut.cmd_latch[22],1'b1,"ARMED via arm bit");
        ck(dut.cmd_latch[63:53],11'h0A5,"auth untouched through compose");

        // B_valid=0: slot B ignored even if it holds an opcode
        cmd(w(METH_SET_MASK,METH_SET_LANE, 1'b0,1'b0), (32'h5<<16)|32'h0000_0011);
        ck(dut.cmd_latch[39:32],8'h11,"B ignored when B_valid=0 (mask from A=0x11)");
        ck(dut.cmd_latch[51:49],3'h2,"lane UNCHANGED (B not applied, still 0x2)");

        // GUARD: topology op in B refused (B_valid=1 but B=CMD_TOPO_NOR)
        cmd(w(METH_SET_MASK,CMD_TOPO_NOR, 1'b1,1'b0), 32'h0000_0022);
        ck(dut.cmd_latch[39:32],8'h22,"guard: A mask applied (0x22)");
        ck(dut.cmd_latch[9:0],10'h0,"guard: topology in B REFUSED (topology still 0)");

        // wrong auth -> whole op rejected
        cmd((32'h111<<19)|{24'h0,METH_SET_MASK}, 32'h0000_00FF);
        ck(dut.cmd_latch[39:32],8'h22,"wrong-auth REJECTED (mask still 0x22)");

        if (errors==0) $display(">>> STAGE 2 PASS: collapsed encoding, collision fixed, compose+guard+auth");
        else $display(">>> STAGE 2 FAIL: %0d errors",errors);
        $finish;
    end
endmodule
