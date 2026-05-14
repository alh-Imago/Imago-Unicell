// tb_unicell_v3.v — Testbench for unicell_v3
// Tests:
//  1.  Reset state
//  2.  CMD_SET_INPUT_ADDR / CMD_SET_OUTPUT_ADDR (no auth)
//  3.  CMD_RECONFIGURE bootstrap (auth_mask=0)
//  4.  Auth token: valid token accepted
//  5.  Auth token: wrong token silently rejected
//  6.  CTYPE_STANDARD: fires on data arrival
//  7.  CTYPE_LATCH: re-emits each tick
//  8.  CTYPE_POSEDGE: releases on posedge
//  9.  CTYPE_NEGEDGE: releases on negedge (odd_phase)
// 10.  SYNC_WAIT: two arrivals, fires on second, re-arms
// 11.  CMD_FREEZE / CMD_RELEASE (auth required)
// 12.  Freeze wire: cell silent while frozen
// 13.  Priority / trace / breakpoint flags stored in cmd_latch
// 14.  Data type field stored in cmd_latch
// 15.  auth_mask zeroed on dbg_cmd_latch output
// 16.  CMD_PING: returns CELL_ID

`timescale 1ns / 1ps

module tb_unicell_v3;

// ── DUT ────────────────────────────────────────────────────────────────────────
reg         clk=0, rst=0, freeze=0;
reg  [31:0] cmd_bus=0;
reg         cmd_valid=0;
reg  [31:0] bus_addr=0, bus_data=0;
reg         bus_valid=0;
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [31:0] dbg_cmd_latch, dbg_input_addr, dbg_output_addr;
wire        dbg_frozen, dbg_trace, dbg_breakpoint, dbg_priority;

unicell_v3 #(.CELL_ID(42)) dut (
    .clk(clk), .rst(rst), .freeze(freeze),
    .cmd_bus(cmd_bus), .cmd_valid(cmd_valid),
    .bus_addr(bus_addr), .bus_data(bus_data), .bus_valid(bus_valid),
    .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
    .dbg_cmd_latch(dbg_cmd_latch),
    .dbg_input_addr(dbg_input_addr), .dbg_output_addr(dbg_output_addr),
    .dbg_frozen(dbg_frozen), .dbg_trace(dbg_trace),
    .dbg_breakpoint(dbg_breakpoint), .dbg_priority(dbg_priority)
);

always #5 clk = ~clk;

// ── Counters ───────────────────────────────────────────────────────────────────
integer pass_count=0, fail_count=0;

task chk;
    input [255:0] name;
    input         got, expected;
    begin
        if (got === expected) begin
            $display("  PASS %0s", name);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL %0s  got=%b expected=%b", name, got, expected);
            fail_count = fail_count + 1;
        end
    end
endtask

task chk32;
    input [255:0] name;
    input [31:0]  got, expected;
    begin
        if (got === expected) begin
            $display("  PASS %0s", name);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL %0s  got=%08h expected=%08h", name, got, expected);
            fail_count = fail_count + 1;
        end
    end
endtask

// ── Constants ──────────────────────────────────────────────────────────────────
localparam AUTH       = 11'h2A5;
localparam WRONG_AUTH = 11'h100;
localparam IN_ADDR    = 32'h0000_1000;
localparam OUT_ADDR   = 32'h0000_2000;

// ── Helpers ────────────────────────────────────────────────────────────────────
// Build cmd_bus word: zero upper bits, token in 14:4, code in 3:0
function [31:0] mk_cmd;
    input [3:0]  code;
    input [10:0] token;
    begin mk_cmd = {17'h0, token, code}; end
endfunction

// Build 32-bit config word (for CMD_RECONFIGURE)
// Bit layout: 31-30=reserved, 29=bp, 28=trace, 27=prio,
//             26-25=ctype, 24-23=dtype, 22=start(hw), 21-11=auth(hw),
//             10=sync_wait, 9-0=topo
function [31:0] mk_cfg;
    input [9:0]  topo;
    input        sw;      // sync_wait
    input [1:0]  dtype;
    input [1:0]  ctype;
    input        prio, tr, bp;
    begin
        mk_cfg = {2'b00, bp, tr, prio, ctype, dtype,
                  1'b0,       // start_flag (set by hw)
                  11'h0,      // auth_mask (preserved by hw)
                  sw, topo};
    end
endfunction

task idle_bus;
    begin
        cmd_bus <= 0; cmd_valid <= 0;
        bus_addr <= 0; bus_data <= 0; bus_valid <= 0;
        freeze <= 0;
    end
endtask

// Issue a command + optional data in same cycle
task send;
    input [31:0] cmd;
    input [31:0] daddr, ddata;
    input        dv;
    begin
        @(negedge clk);
        cmd_bus <= cmd; cmd_valid <= 1;
        bus_addr <= daddr; bus_data <= ddata; bus_valid <= dv;
        @(posedge clk); #1;
        cmd_valid <= 0; bus_valid <= 0;
    end
endtask

// Subsequent CMD_RECONFIGURE: cmd + config word in same cycle
task reconfig;
    input [31:0] cfg;
    begin
        send(mk_cmd(4'd4, AUTH), 32'h0, cfg, 1'b1);
        @(posedge clk); #1;
    end
endtask

// ── out_valid capture — latches any pulse, cleared by clear_fired ──────────────
reg fired = 0;
always @(posedge clk) if (out_valid) fired <= 1;
task clear_fired; begin @(negedge clk); fired <= 0; end endtask

// Write data and wait long enough to capture any output pulse
task write_and_wait;
    input [31:0] val;
    input integer ncycles;
    begin
        clear_fired;
        @(negedge clk);
        bus_addr <= IN_ADDR; bus_data <= val; bus_valid <= 1;
        @(posedge clk); #1;
        bus_valid <= 0;
        repeat(ncycles) @(posedge clk); #1;
    end
endtask

// ── TESTS ──────────────────────────────────────────────────────────────────────
initial begin
    $dumpfile("tb_unicell_v3.vcd");
    $dumpvars(0, tb_unicell_v3);
    $display("\n=== tb_unicell_v3 ===");

    // [1] Reset
    $display("\n[1] Reset");
    idle_bus; rst=1;
    repeat(4) @(posedge clk); #1;
    rst=0; @(posedge clk); #1;

    chk32("cmd_latch=0",   dbg_cmd_latch,   32'h0);
    chk32("in_addr=0",     dbg_input_addr,  32'h0);
    chk32("out_addr=0",    dbg_output_addr, 32'h0);
    chk  ("out_valid=0",   out_valid,       1'b0);
    chk  ("not frozen",    dbg_frozen,      1'b0);

    // [2] Set port addresses
    $display("\n[2] CMD_SET_INPUT_ADDR / CMD_SET_OUTPUT_ADDR");
    send(mk_cmd(4'd2,11'h0), 32'h0, IN_ADDR,  1'b1); @(posedge clk); #1;
    chk32("in_addr set",  dbg_input_addr,  IN_ADDR);
    send(mk_cmd(4'd3,11'h0), 32'h0, OUT_ADDR, 1'b1); @(posedge clk); #1;
    chk32("out_addr set", dbg_output_addr, OUT_ADDR);

    // [3] Bootstrap CMD_RECONFIGURE (auth_mask==0)
    $display("\n[3] CMD_RECONFIGURE bootstrap");
    // Word 0: auth_mask
    send(mk_cmd(4'd4,11'h0), 32'h0, {21'h0, AUTH}, 1'b1);
    @(posedge clk); #1;
    // Word 1: config word (on next bus_valid)
    @(negedge clk);
    bus_data  <= mk_cfg(10'b0000000001, 1'b0, 2'b00, 2'b00, 1'b0, 1'b0, 1'b0);
    bus_valid <= 1;
    @(posedge clk); #1;
    bus_valid <= 0;
    @(posedge clk); #1;

    chk  ("start_flag set",   dbg_cmd_latch[22], 1'b1);
    chk32("topology=1",       dbg_cmd_latch & 32'h7FF, 32'h1);
    chk32("auth_mask zeroed", dbg_cmd_latch & 32'h003FF800, 32'h0);

    // [4] Valid auth accepted
    $display("\n[4] Auth token — valid");
    // ctype=LATCH(01), prio=1, trace=1
    reconfig(mk_cfg(10'b0000000001, 1'b0, 2'b00, 2'b01, 1'b1, 1'b1, 1'b0));
    chk  ("priority set",  dbg_priority, 1'b1);
    chk  ("trace set",     dbg_trace,    1'b1);
    chk32("ctype=LATCH",   (dbg_cmd_latch>>25)&32'h3, 32'h1);

    // [5] Wrong auth silently rejected
    $display("\n[5] Auth token — wrong token rejected");
    send(mk_cmd(4'd4, WRONG_AUTH), 32'h0,
         mk_cfg(10'b1111111111, 1'b0, 2'b11, 2'b11, 1'b0, 1'b0, 1'b1), 1'b1);
    @(posedge clk); #1;
    // Config must be unchanged
    chk  ("priority unchanged", dbg_priority, 1'b1);
    chk  ("trace unchanged",    dbg_trace,    1'b1);
    chk32("ctype unchanged",    (dbg_cmd_latch>>25)&32'h3, 32'h1);

    // [6] CTYPE_STANDARD
    $display("\n[6] CTYPE_STANDARD");
    reconfig(mk_cfg(10'b0000000001, 1'b0, 2'b00, 2'b00, 1'b0, 1'b0, 1'b0));
    write_and_wait(32'h0, 4);
    chk  ("std: fires",    fired,    1'b1);
    chk32("std: addr",     out_addr, OUT_ADDR);
    chk32("std: NOT(0)=1", out_data, 32'h1);
    write_and_wait(32'h1, 4);
    chk32("std: NOT(1)=0", out_data, 32'h0);

    // [7] CTYPE_LATCH
    $display("\n[7] CTYPE_LATCH");
    reconfig(mk_cfg(10'b0000000001, 1'b0, 2'b00, 2'b01, 1'b0, 1'b0, 1'b0));
    write_and_wait(32'h0, 4);
    chk  ("latch: fires",    fired,   1'b1);
    chk32("latch: NOT(0)=1", out_data,32'h1);
    clear_fired;
    repeat(2) @(posedge clk); #1;
    chk  ("latch: re-emits", fired,   1'b1);
    chk32("latch: re-val=1", out_data,32'h1);

    // [8] CTYPE_POSEDGE
    $display("\n[8] CTYPE_POSEDGE");
    reconfig(mk_cfg(10'b0000000001, 1'b0, 2'b00, 2'b10, 1'b0, 1'b0, 1'b0));
    write_and_wait(32'h0, 4);
    chk  ("posedge: fires",    fired,   1'b1);
    chk32("posedge: NOT(0)=1", out_data,32'h1);

    // [9] CTYPE_NEGEDGE
    $display("\n[9] CTYPE_NEGEDGE");
    reconfig(mk_cfg(10'b0000000001, 1'b0, 2'b00, 2'b11, 1'b0, 1'b0, 1'b0));
    write_and_wait(32'h0, 4);
    chk  ("negedge: fires",    fired,   1'b1);
    chk32("negedge: NOT(0)=1", out_data,32'h1);

    // [10] SYNC_WAIT
    $display("\n[10] SYNC_WAIT");
    reconfig(mk_cfg(10'b0000000001, 1'b1, 2'b00, 2'b00, 1'b0, 1'b0, 1'b0));
    write_and_wait(32'h0, 4);
    chk("sync: no fire on 1st", fired, 1'b0);
    write_and_wait(32'h0, 4);
    chk  ("sync: fires on 2nd", fired,   1'b1);
    chk32("sync: NOT(0)=1",     out_data,32'h1);
    write_and_wait(32'h1, 4);
    chk("sync: no fire on 3rd (re-armed)", fired, 1'b0);

    // [11] CMD_FREEZE / CMD_RELEASE
    $display("\n[11] CMD_FREEZE / CMD_RELEASE");
    reconfig(mk_cfg(10'b0000000001, 1'b0, 2'b00, 2'b00, 1'b0, 1'b0, 1'b0));
    send(mk_cmd(4'd5, AUTH), 32'h0, 32'h0, 1'b0);
    @(posedge clk); #1;
    chk("frozen after CMD_FREEZE", dbg_frozen, 1'b1);
    write_and_wait(32'h0, 4);
    chk("no output while frozen",  fired,      1'b0);
    send(mk_cmd(4'd6, AUTH), 32'h0, 32'h0, 1'b0);
    @(posedge clk); #1;
    chk("released after CMD_RELEASE", dbg_frozen, 1'b0);

    // [12] Freeze wire
    $display("\n[12] Freeze wire");
    freeze=1; @(posedge clk); #1;
    chk("frozen by wire", dbg_frozen, 1'b1);
    write_and_wait(32'h0, 4);
    chk("no output while freeze wire", fired, 1'b0);
    freeze=0;

    // [13] Persistent flags
    $display("\n[13] Priority / trace / breakpoint");
    reconfig(mk_cfg(10'b0000000001, 1'b0, 2'b00, 2'b00, 1'b1, 1'b1, 1'b1));
    chk("priority stored",   dbg_priority,   1'b1);
    chk("trace stored",      dbg_trace,      1'b1);
    chk("breakpoint stored", dbg_breakpoint, 1'b1);

    // [14] Data type
    $display("\n[14] Data type field");
    reconfig(mk_cfg(10'b0000000001, 1'b0, 2'b01, 2'b00, 1'b0, 1'b0, 1'b0));
    chk32("dtype=SIGNED", (dbg_cmd_latch>>23)&32'h3, 32'h1);

    // [15] auth_mask zeroed on debug output
    $display("\n[15] auth_mask zeroed on dbg_cmd_latch");
    chk32("auth bits=0", dbg_cmd_latch & 32'h003FF800, 32'h0);

    // [16] CMD_PING
    $display("\n[16] CMD_PING");
    clear_fired;
    send(mk_cmd(4'd9, 11'h0), 32'h0, 32'h0, 1'b0);
    @(posedge clk); #1;
    chk  ("ping: fired",     fired,   1'b1);
    chk32("ping: CELL_ID=42",out_data,32'd42);

    // Summary
    $display("\n=== %0d passed, %0d failed ===", pass_count, fail_count);
    if (fail_count == 0) $display("ALL TESTS PASSED");
    else                 $display("FAILURES — review above");
    $finish;
end

initial begin #200000; $display("TIMEOUT"); $finish; end

endmodule
