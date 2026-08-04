// tb_v3_bank.v — verify the debug bank switch: op26 bit16 selects which 32-bit half of the
// 64-bit cmd_latch the dbg_cmd_latch port shows. Confirms upper half (auth/methodology) readable.
`timescale 1ns/1ps
module tb_v3_bank;
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
    task ck; input [31:0] got,want; input [150:0] m; begin
        if (got===want) $display("  PASS: %0s (0x%08x)", m,got);
        else begin $display("  FAIL: %0s got=0x%08x want=0x%08x", m,got,want); errors=errors+1; end
    end endtask
    localparam CMD_LOAD_AT=8'd23, CMD_BOOT_COMMIT=8'd7, CMD_DBG_SEL=8'd26;
    localparam METH_SET_MASK=8'd30;
    initial begin
        rst=1; repeat(4)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
        // boot auth 0x0A5 into [63:53], set a mask so upper half is non-trivial
        cmd({8'h0,3'b0,11'h0,CMD_LOAD_AT},(32'h0A5<<20)|32'h0);
        cmd({8'h0,3'b0,11'h0,CMD_BOOT_COMMIT},32'h00A5_0100);
        cmd((32'h0A5<<19)|{24'h0,METH_SET_MASK},32'h0000_003C); // mask 0x3C -> upper[39:32]
        $display("=== bank switch test ===");
        $display("full cmd_latch = 0x%016x", dut.cmd_latch);
        // bank 0 (default): dbg shows lower [31:0]
        cmd({8'h0,CMD_DBG_SEL},32'h0000_0000); // op26, bit16=0 -> bank 0
        ck(dbg_cmd_latch, dut.cmd_latch[31:0], "bank 0 shows LOWER half");
        // bank 1: dbg shows upper [63:32] -> contains mask 0x3C at [39:32] and auth 0x0A5 at [63:53]
        cmd({8'h0,CMD_DBG_SEL},32'h0001_0000); // op26, bit16=1 -> bank 1
        ck(dbg_cmd_latch, dut.cmd_latch[63:32], "bank 1 shows UPPER half");
        // verify the upper half actually contains what we expect
        $display("  upper half = 0x%08x : mask[7:0]=0x%02x auth[31:21]=0x%03x",
                 dbg_cmd_latch, dbg_cmd_latch[7:0], dbg_cmd_latch[31:21]);
        ck({24'h0,dbg_cmd_latch[7:0]}, 32'h3C, "  -> mask 0x3C visible in upper half via bank 1");
        ck({21'h0,dbg_cmd_latch[31:21]}, 32'h0A5, "  -> auth 0x0A5 visible in upper half via bank 1");
        // flip back to bank 0
        cmd({8'h0,CMD_DBG_SEL},32'h0000_0000);
        ck(dbg_cmd_latch, dut.cmd_latch[31:0], "bank 0 again shows LOWER half");
        if (errors==0) $display(">>> BANK PASS: op26 bit16 banks the 64-bit latch through the 32-bit dbg window");
        else $display(">>> BANK FAIL: %0d errors",errors);
        $finish;
    end
endmodule
