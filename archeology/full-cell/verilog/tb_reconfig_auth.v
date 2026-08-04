// tb_reconfig_auth.v — proves invariant clause 3 for CMD_RECONFIGURE:
//   auth_mask is WRITE-ONCE, BOOT-ONLY. A run-mode RECONFIGURE may change a
//   cell's FUNCTION (topology/flags) but must NOT rewrite its auth_mask — the
//   data-path route to auth closes when physical_mode clears. (CMD_LOAD_AT
//   already enforced this; this test covers the legacy broadcast RECONFIGURE.)
// auth_mask is zeroed in dbg_cmd_latch, so we read it hierarchically: dut.cmd_latch.
// Run: iverilog -o /tmp/o tb_reconfig_auth.v unicell.v && vvp /tmp/o
`timescale 1ns/1ps
module tb_reconfig_auth;
    reg clk=0, rst=0, cmd_valid=0, bus_valid=0;
    reg [31:0] cmd_bus=0, cmd_data=0, bus_addr=0, bus_data=0;
    wire [31:0] out_addr,out_data,dbg_cmd_latch,dbg_input_addr,dbg_output_addr,dbg_a_data;
    wire out_valid,dbg_start_flag,dbg_armed,dbg_frozen,dbg_priority,dbg_trace,dbg_breakpoint,dbg_output_set,dbg_a_arrived;
    wire [1:0] dbg_dtype;
    integer fails=0;
    always #5 clk=~clk;

    unicell #(.CELL_ID(42), .ENABLE_LATCH_IN(1)) dut (
        .clk(clk),.rst(rst),.cmd_bus(cmd_bus),.cmd_data(cmd_data),.cmd_valid(cmd_valid),
        .bus_addr(bus_addr),.bus_data(bus_data),.bus_valid(bus_valid),
        .out_addr(out_addr),.out_data(out_data),.out_valid(out_valid),
        .dbg_cmd_latch(dbg_cmd_latch),.dbg_input_addr(dbg_input_addr),.dbg_input_addr_short(),
        .dbg_output_addr(dbg_output_addr),.dbg_start_flag(dbg_start_flag),.dbg_armed(dbg_armed),
        .dbg_frozen(dbg_frozen),.dbg_priority(dbg_priority),.dbg_trace(dbg_trace),
        .dbg_breakpoint(dbg_breakpoint),.dbg_dtype(dbg_dtype),
        .dbg_output_set(dbg_output_set),.dbg_a_arrived(dbg_a_arrived),.dbg_a_data(dbg_a_data)
    );

    task cmd; input [31:0] cb,cd; begin
        @(negedge clk); cmd_bus<=cb; cmd_data<=cd; cmd_valid<=1;
        @(posedge clk); #1; cmd_valid<=0; cmd_bus<=0; cmd_data<=0;
        @(posedge clk); #1;
    end endtask

    task expect8; input [7:0] got, want; input [255:0] label; begin
        $display("  %-44s 0x%02x (want 0x%02x)  %s", label, got, want, (got===want)?"PASS":"** FAIL **");
        if (got!==want) fails=fails+1;
    end endtask

    task expect10; input [9:0] got, want; input [255:0] label; begin
        $display("  %-44s 0x%03x (want 0x%03x)  %s", label, got, want, (got===want)?"PASS":"** FAIL **");
        if (got!==want) fails=fails+1;
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; @(posedge clk); #1;
        $display("=== CMD_RECONFIGURE auth-write gate (invariant clause 3) ===");
        $display("reset:        physical_mode=%0d auth_mask=0x%02x", dut.physical_mode, dut.cmd_latch[18:11]);

        // 1. BOOT-mode RECONFIGURE: auth_boot (token 0) -> auth_mask write ALLOWED.
        //    cmd_data: topology=0x0BC [9:0], auth_mask=0xA5 [30:23] -> 0x528000BC
        cmd(32'h00000004, 32'h528000BC);
        $display("boot RECONFIGURE (auth=0xA5, topo=0x0BC):");
        expect8(dut.cmd_latch[18:11], 8'hA5, "  boot: auth_mask accepted");
        expect10(dut.cmd_latch[9:0], 10'h0BC, "  boot: topology loaded");

        // 2. Flip to RUN via BOOT_COMMIT (addr=0x100, auth=0xA5).
        cmd(32'h00000007, 32'h00A50100);
        $display("BOOT_COMMIT -> physical_mode=%0d", dut.physical_mode);

        // 3. RUN-mode RECONFIGURE with VALID auth (token 0xA5) trying to rewrite
        //    auth_mask -> 0x3C and topology -> 0x024.
        //    cmd_bus: opcode 4 + auth_token 0xA5 in [28:21] -> 0x14A00004
        //    cmd_data: topology=0x024, auth_mask=0x3C [30:23] -> 0x1E000024
        cmd(32'h14A00004, 32'h1E000024);
        $display("run RECONFIGURE (auth-ok token, tries auth->0x3C, topo->0x024):");
        // clause 3: auth_mask must be UNCHANGED (still 0xA5), but the FUNCTION change lands
        expect8(dut.cmd_latch[18:11], 8'hA5, "  run: auth_mask UNCHANGED (boot-only)   ");
        expect10(dut.cmd_latch[9:0], 10'h024, "  run: topology DID change (reconfig works)");

        if (fails==0) $display("  >>> PASS: run-mode RECONFIGURE changes function, not auth (clause 3 holds)");
        else          $display("  >>> FAIL: %0d check(s) — auth gate not enforced", fails);
        $finish;
    end
endmodule
