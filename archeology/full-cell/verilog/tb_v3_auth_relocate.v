// tb_v3_auth_relocate.v — STAGE 1: prove 11-bit auth works from its NEW home cmd_latch[63:53]
// (moved out of the freed lower [18:11]). Boot-writes auth, then checks the gate:
//   - right auth (token==mask) -> command applies
//   - wrong auth (token!=mask) -> command rejected
//   - auth_boot (mask==0) -> open before first auth set
// Isolated: NO two-slot decoder involved; this tests ONLY the relocation.
`timescale 1ns/1ps
module tb_v3_auth_relocate;
    reg clk=0, rst=0; reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] bus_addr=0; reg [31:0] bus_data=0; reg bus_valid=0;
    always #5 clk=~clk;
    // instantiate a single v3 cell with CELL_ID=0x0005
    wire [15:0] out_addr; wire [31:0] out_data; wire out_valid;
    wire [31:0] dbg_cmd_latch;
    unicell64_v3 #(.CELL_ID(16'h0005)) dut (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .bus_addr(bus_addr), .bus_data(bus_data), .bus_valid(bus_valid),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .dbg_cmd_latch(dbg_cmd_latch)
    );
    task cmd; input [31:0] cb, cd; begin
        @(negedge clk); cmd_bus=cb; cmd_data=cd; cmd_valid=1;
        @(posedge clk); #1; cmd_valid=0; repeat(3) @(posedge clk); #1;
    end endtask
    integer errors=0;
    task check; input [63:0] got, want; input [127:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%016x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%016x want=0x%016x", msg, got, want); errors=errors+1; end
    end endtask

    localparam CMD_LOAD_AT = 8'd23, CMD_BOOT_COMMIT = 8'd7;
    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== STAGE 1: 11-bit auth relocated to cmd_latch[63:53] ===");
        $display("reset: physical_mode=%0d auth_mask(new [63:53])=0x%03x", dut.physical_mode, dut.cmd_latch[63:53]);
        check(dut.cmd_latch[63:53], 11'h0, "reset: auth_mask zero (boot-open)");

        // 1. BOOT LOAD_AT: write 11-bit auth 0x5A5 into [63:53]. In physical_mode, auth_boot open.
        //    cmd_data[30:20] = 11-bit auth. 0x5A5 << 20 = 0x5A500000. topology 0x0BC in [9:0].
        cmd({8'h0, 3'b0, 11'h000, CMD_LOAD_AT}, (32'h5A5 << 20) | 32'h0000_00BC);
        // NOTE: config targets CELL_ID via address lane — drive bus_addr=CELL_ID during cmd.
        // Re-issue with address set (config_match needs bus_addr==CELL_ID):
        @(negedge clk); bus_addr=16'h0005; bus_valid=0;
        cmd({8'h0, 3'b0, 11'h000, CMD_LOAD_AT}, (32'h5A5 << 20) | 32'h0000_00BC);
        $display("after boot LOAD_AT: auth_mask[63:53]=0x%03x topology[9:0]=0x%03x physical=%0d",
                 dut.cmd_latch[63:53], dut.cmd_latch[9:0], dut.physical_mode);
        check(dut.cmd_latch[63:53], 11'h5A5, "boot: 11-bit auth_mask stored in [63:53]");

        // 2. Flip to RUN. Set mask consistently to 0x0A5 first, then commit with same auth.
        @(negedge clk); bus_addr=16'h0005;
        cmd({8'h0, 3'b0, 11'h000, CMD_LOAD_AT}, (32'h0A5 << 20) | 32'h0000_00BC); // mask=0x0A5
        cmd({8'h0, 3'b0, 11'h000, CMD_BOOT_COMMIT}, 32'h00A5_0100);  // commit; auth low8=0xA5 -> 0x0A5
        $display("BOOT_COMMIT: physical_mode=%0d auth_mask=0x%03x", dut.physical_mode, dut.cmd_latch[63:53]);
        check(dut.cmd_latch[63:53], 11'h0A5, "auth_mask consistent at 0x0A5 after commit");

        // 3. RUN-mode auth gate: RIGHT token 0x0A5, WRONG token 0x111.
        @(negedge clk); bus_addr=16'h0005;
        cmd({(32'h0A5<<19) | {8'h0,CMD_LOAD_AT}}, 32'h0000_0024); // OR topology, right auth
        check(dut.cmd_latch[9:0], 10'h024, "RUN LOAD_AT with RIGHT auth applied (topology=0x024)");

        @(negedge clk); bus_addr=16'h0005;
        cmd({(32'h111<<19) | {8'h0,CMD_LOAD_AT}}, 32'h0000_0007); // AND topology, WRONG auth
        check(dut.cmd_latch[9:0], 10'h024, "RUN LOAD_AT with WRONG auth REJECTED (topology unchanged 0x024)");

        if (errors==0) $display(">>> STAGE 1 PASS: 11-bit auth works from new home [63:53], gate correct");
        else $display(">>> STAGE 1 FAIL: %0d errors", errors);
        $finish;
    end
endmodule
