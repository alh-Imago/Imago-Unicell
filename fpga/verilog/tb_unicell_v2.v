// tb_unicell_v2.v — Testbench for unicell.v (command latch architecture)
// Tests all features of the v2 command bus cell in order.
// Run with: iverilog -o tb_unicell_v2 tb_unicell_v2.v unicell.v && vvp tb_unicell_v2
//
// Test plan:
//  [1]  Reset state
//  [2]  CMD_SET_INPUT_ADDR / CMD_SET_OUTPUT_ADDR
//  [3]  CMD_RECONFIGURE — boot (auth_mask=0, accept unconditionally)
//  [4]  CMD_RECONFIGURE — valid auth token
//  [5]  CMD_RECONFIGURE — wrong auth rejected
//  [6]  PASS gate — data flows through
//  [7]  NOT gate  — output inverted
//  [8]  invert_out — extra inversion after gate tree
//  [9]  latch_in  — re-emits last value when no new data
//  [10] loop_back — computed output fed back to data_reg
//  [11] one_shot  — fires once then disarms
//  [12] sync_wait — requires two arrivals before firing
//  [13] CMD_FREEZE / CMD_RELEASE
//  [14] priority / trace / breakpoint stored in latch
//  [15] dtype stored in latch
//  [16] auth_mask zeroed in debug output

`timescale 1ns / 1ps

module tb_unicell_v2;

// ── DUT ports ─────────────────────────────────────────────────────────────────
reg         clk      = 0;
reg         rst      = 0;
reg  [31:0] cmd_bus  = 0;
reg  [31:0] cmd_data = 0;
reg         cmd_valid = 0;
reg  [31:0] bus_addr = 0;
reg  [31:0] bus_data = 0;
reg         bus_valid = 0;

wire [31:0] out_addr;
wire [31:0] out_data;
wire        out_valid;
wire [31:0] dbg_cmd_latch;
wire [31:0] dbg_input_addr;
wire [31:0] dbg_output_addr;
wire        dbg_start_flag;
wire        dbg_armed;
wire        dbg_frozen;
wire        dbg_priority;
wire        dbg_trace;
wire        dbg_breakpoint;
wire [1:0]  dbg_dtype;

unicell #(.CELL_ID(42)) dut (
    .clk            (clk),
    .rst            (rst),
    .cmd_bus        (cmd_bus),
    .cmd_data       (cmd_data),
    .cmd_valid      (cmd_valid),
    .bus_addr       (bus_addr),
    .bus_data       (bus_data),
    .bus_valid      (bus_valid),
    .out_addr       (out_addr),
    .out_data       (out_data),
    .out_valid      (out_valid),
    .dbg_cmd_latch  (dbg_cmd_latch),
    .dbg_input_addr (dbg_input_addr),
    .dbg_output_addr(dbg_output_addr),
    .dbg_start_flag (dbg_start_flag),
    .dbg_armed      (dbg_armed),
    .dbg_frozen     (dbg_frozen),
    .dbg_priority   (dbg_priority),
    .dbg_trace      (dbg_trace),
    .dbg_breakpoint (dbg_breakpoint),
    .dbg_dtype      (dbg_dtype)
);

always #5 clk = ~clk;  // 100 MHz sim clock

// ── Counters ──────────────────────────────────────────────────────────────────
integer pass_count = 0;
integer fail_count = 0;

// ── Check tasks ───────────────────────────────────────────────────────────────
task chk;
    input [255:0] name;
    input got, exp;
    begin
        if (got === exp) begin
            $display("  PASS %0s", name);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL %0s  got=%b exp=%b", name, got, exp);
            fail_count = fail_count + 1;
        end
    end
endtask

task chk32;
    input [255:0] name;
    input [31:0] got, exp;
    begin
        if (got === exp) begin
            $display("  PASS %0s", name);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL %0s  got=%08h exp=%08h", name, got, exp);
            fail_count = fail_count + 1;
        end
    end
endtask

// ── Command helpers ───────────────────────────────────────────────────────────
// Send a command with optional simultaneous data bus transaction
task send_cmd;
    input [3:0]  code;
    input [10:0] token;
    input [31:0] payload;
    begin
        @(negedge clk);
        cmd_bus   <= {17'h0, token, code};
        cmd_data  <= payload;
        cmd_valid <= 1'b1;
        @(posedge clk); #1;
        cmd_valid <= 1'b0;
        @(posedge clk); #1;
    end
endtask

// Put data on the data bus for one cycle, then wait for output to settle
// odd_phase drain takes 1-2 cycles, registered latch_reemit takes 1 more
task send_data;
    input [31:0] addr;
    input [31:0] data;
    begin
        @(negedge clk);
        bus_addr  <= addr;
        bus_data  <= data;
        bus_valid <= 1'b1;
        @(posedge clk); #1;
        bus_valid <= 1'b0;
        repeat(4) @(posedge clk); #1;  // wait for odd_phase drain + latch_reemit
    end
endtask

// ── Command latch builder ─────────────────────────────────────────────────────
// mk_cfg: builds a 32-bit command latch word
// topo[9:0]   = NOR gate selection
// sync_wait   = topo[10]
// auth[10:0]  = bits 21:11 (stored, zeroed in debug)
// start       = bit 22 (set to 1 = armed)
// dtype[1:0]  = bits 24:23
// invert_out  = bit 25
// latch_in    = bit 26
// priority    = bit 27
// trace       = bit 28
// breakpoint  = bit 29
// one_shot    = bit 30
// loop_back   = bit 31
function [31:0] mk_cfg;
    input [9:0]  topo;
    input        sync_wait;
    input [10:0] auth;
    input [1:0]  dtype;
    input        invert_out, latch_in;
    input        priority, trace, breakpoint;
    input        one_shot, loop_back;
    begin
        mk_cfg = {loop_back, one_shot, breakpoint, trace, priority,
                  latch_in, invert_out, dtype,
                  1'b1,         // start_flag always set
                  auth,
                  sync_wait, topo};
    end
endfunction

// Topology constants
localparam TOPO_PASS = 10'b0000000000;
localparam TOPO_NOT  = 10'b0000000001;
localparam TOPO_NOR  = 10'b0000000100;

// Auth tokens
localparam AUTH      = 11'h2A5;
localparam WRONG     = 11'h100;

// Addresses
localparam IN        = 32'h1000;
localparam OUT       = 32'h2000;

// ── Fired flag — latches out_valid and captures out_data/out_addr ─────────────
reg fired = 0;
reg [31:0] last_out_data = 0;
reg [31:0] last_out_addr = 0;
always @(posedge clk) begin
    if (out_valid) begin
        fired         <= 1;
        last_out_data <= out_data;
        last_out_addr <= out_addr;
    end
end
task clr_fired;
    begin
        @(negedge clk);
        fired         <= 0;
        last_out_data <= 0;
        last_out_addr <= 0;
    end
endtask

// ── Test sequence ─────────────────────────────────────────────────────────────
initial begin
    $dumpfile("tb_unicell_v2.vcd");
    $dumpvars(0, tb_unicell_v2);
    $display("\n=== tb_unicell_v2 — unicell command latch architecture ===");

    // ── [1] Reset ─────────────────────────────────────────────────────────────
    $display("\n[1] Reset");
    rst = 1; repeat(4) @(posedge clk); #1;
    rst = 0; @(posedge clk); #1;
    chk32("cmd_latch=0",  dbg_cmd_latch,  32'h0);
    chk32("in_addr=0",    dbg_input_addr, 32'h0);
    chk  ("not armed",    dbg_armed,      1'b0);
    chk  ("not frozen",   dbg_frozen,     1'b0);
    chk  ("no output",    out_valid,      1'b0);

    // ── [2] Set addresses ─────────────────────────────────────────────────────
    $display("\n[2] CMD_SET_INPUT_ADDR / CMD_SET_OUTPUT_ADDR");
    send_cmd(4'd2, 11'h0, IN);
    chk32("in_addr=IN",   dbg_input_addr,  IN);
    send_cmd(4'd3, 11'h0, OUT);
    chk32("out_addr=OUT", dbg_output_addr, OUT);

    // ── [3] Boot reconfigure — auth_mask=0, accept unconditionally ────────────
    $display("\n[3] Boot CMD_RECONFIGURE (auth_mask=0)");
    send_cmd(4'd4, 11'h0, mk_cfg(TOPO_NOT, 0, AUTH, 2'b00, 0,0, 0,0,0, 0,0));
    chk  ("armed after boot", dbg_armed,         1'b1);
    chk32("topology=NOT",     dbg_cmd_latch & 32'h3FF, 32'h1);
    chk32("auth zeroed",      dbg_cmd_latch & 32'h003FF800, 32'h0);

    // ── [4] Valid auth reconfig ───────────────────────────────────────────────
    $display("\n[4] CMD_RECONFIGURE — valid auth");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_PASS, 0, AUTH, 2'b00, 0,0, 1,1,0, 0,0));
    chk("priority set",  dbg_priority, 1'b1);
    chk("trace set",     dbg_trace,    1'b1);
    chk("still armed",   dbg_armed,    1'b1);

    // ── [5] Wrong auth rejected ───────────────────────────────────────────────
    $display("\n[5] CMD_RECONFIGURE — wrong auth rejected");
    send_cmd(4'd4, WRONG, mk_cfg(TOPO_NOR, 0, AUTH, 2'b11, 1,1, 0,0,1, 1,1));
    chk("priority unchanged",  dbg_priority,                    1'b1);
    chk("trace unchanged",     dbg_trace,                       1'b1);
    chk32("topo unchanged",    dbg_cmd_latch & 32'h3FF,         32'h0); // PASS
    chk32("dtype unchanged",   (dbg_cmd_latch >> 23) & 32'h3,  32'h0);

    // ── [6] PASS gate ─────────────────────────────────────────────────────────
    $display("\n[6] PASS gate");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_PASS, 0, AUTH, 2'b00, 0,0, 0,0,0, 0,0));
    send_cmd(4'd2, 11'h0, IN);
    send_cmd(4'd3, 11'h0, OUT);
    clr_fired;
    send_data(IN, 32'h1);
    chk  ("PASS fires",   fired,    1'b1);
    chk32("PASS(1)=1",    last_out_data, 32'h1);
    chk32("addr=OUT",     last_out_addr, OUT);
    clr_fired;
    send_data(IN, 32'h0);
    chk32("PASS(0)=0",    last_out_data, 32'h0);

    // ── [7] NOT gate ──────────────────────────────────────────────────────────
    $display("\n[7] NOT gate");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_NOT, 0, AUTH, 2'b00, 0,0, 0,0,0, 0,0));
    clr_fired;
    send_data(IN, 32'h0);
    chk  ("NOT fires",    fired,    1'b1);
    chk32("NOT(0)=1",     out_data, 32'h1);
    clr_fired;
    send_data(IN, 32'h1);
    chk32("NOT(1)=0",     out_data, 32'h0);

    // ── [8] invert_out ────────────────────────────────────────────────────────
    $display("\n[8] invert_out — NOT gate + invert = PASS");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_NOT, 0, AUTH, 2'b00, 1,0, 0,0,0, 0,0));
    clr_fired;
    send_data(IN, 32'h0);
    chk32("NOT+inv(0)=0", last_out_data, 32'h0);  // NOT(0)=1, invert=0
    clr_fired;
    send_data(IN, 32'h1);
    chk32("NOT+inv(1)=1", last_out_data, 32'h1);  // NOT(1)=0, invert=1

    // ── [9] latch_in — re-emits last value ───────────────────────────────────
    $display("\n[9] latch_in");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_NOT, 0, AUTH, 2'b00, 0,1, 0,0,0, 0,0));
    clr_fired;
    @(negedge clk);
    bus_addr  <= IN; bus_data <= 32'h0; bus_valid <= 1'b1;
    @(posedge clk); #1; bus_valid <= 1'b0;
    @(posedge clk); #1;  // odd_phase drain
    chk  ("latch fires",      out_valid, 1'b1);
    chk32("latch NOT(0)=1",   out_data,  32'h1);
    clr_fired;
    // latch_reemit is registered — takes 2 cycles: compute then drain
    repeat(4) @(posedge clk); #1;
    chk  ("latch re-emits",   fired,          1'b1);
    chk32("latch re-val=1",   last_out_data,  32'h1);

    // ── [10] loop_back ────────────────────────────────────────────────────────
    // loop_back stores computed_output into data_reg instead of bus_data.
    // input_val still reads bus_data when bus is valid — so the loop only
    // affects subsequent idle cycles (latch_in re-emission uses data_reg).
    // With active bus: each fire computes NOT(bus_data), stores result in data_reg.
    $display("\n[10] loop_back — output feeds back to data_reg");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_NOT, 0, AUTH, 2'b00, 0,0, 0,0,0, 0,1));
    clr_fired;
    send_data(IN, 32'h0);      // NOT(bus[0]=0)=1, data_reg <= 1
    chk32("loop first=1",  last_out_data, 32'h1);
    clr_fired;
    send_data(IN, 32'h0);      // NOT(bus[0]=0)=1 (bus_data takes precedence)
    chk32("loop second=1", last_out_data, 32'h1);
    // Verify data_reg holds computed output — enable latch_in to see it
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_NOT, 0, AUTH, 2'b00, 0,1, 0,0,0, 0,1));
    clr_fired;
    send_data(IN, 32'h0);      // fire once, data_reg <= NOT(0)=1
    repeat(5) @(posedge clk); #1;  // let latch_reemit register and drain
    chk  ("loop latch re-emits", fired,         1'b1);
    chk32("loop latch val=1",    last_out_data,  32'h1);

    // ── [11] one_shot ─────────────────────────────────────────────────────────
    $display("\n[11] one_shot — fires once then disarms");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_NOT, 0, AUTH, 2'b00, 0,0, 0,0,0, 1,0));
    clr_fired;
    send_data(IN, 32'h0);
    chk  ("one_shot fires",   fired,    1'b1);
    chk32("one_shot NOT(0)=1",out_data, 32'h1);
    chk  ("disarmed",         dbg_armed,1'b0);
    clr_fired;
    send_data(IN, 32'h0);
    chk  ("no second fire",   fired,    1'b0);
    // Re-arm and verify
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_NOT, 0, AUTH, 2'b00, 0,0, 0,0,0, 1,0));
    clr_fired;
    send_data(IN, 32'h0);
    chk  ("re-armed fires",   fired,    1'b1);

    // ── [12] sync_wait ────────────────────────────────────────────────────────
    $display("\n[12] sync_wait — two arrivals before firing");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_NOT, 1, AUTH, 2'b00, 0,0, 0,0,0, 0,0));
    clr_fired;
    send_data(IN, 32'h0);
    chk  ("sync no fire 1st", fired,    1'b0);
    send_data(IN, 32'h0);
    chk  ("sync fires 2nd",   fired,    1'b1);
    chk32("sync NOT(0)=1",    last_out_data, 32'h1);
    // Verify reset — third arrival alone should not fire
    clr_fired;
    send_data(IN, 32'h0);
    chk  ("sync no fire 3rd", fired,    1'b0);
    // Fourth fires again
    send_data(IN, 32'h1);
    chk  ("sync fires 4th",   fired,    1'b1);
    chk32("sync NOT(1)=0",    last_out_data, 32'h0);

    // ── [13] CMD_FREEZE / CMD_RELEASE ─────────────────────────────────────────
    $display("\n[13] CMD_FREEZE / CMD_RELEASE");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_NOT, 0, AUTH, 2'b00, 0,0, 0,0,0, 0,0));
    send_cmd(4'd5, AUTH, 32'h0);   // CMD_FREEZE
    chk  ("frozen",             dbg_frozen, 1'b1);
    clr_fired;
    send_data(IN, 32'h0);
    chk  ("no out when frozen", fired,      1'b0);
    send_cmd(4'd6, AUTH, 32'h0);   // CMD_RELEASE
    chk  ("released",           dbg_frozen, 1'b0);
    clr_fired;
    send_data(IN, 32'h0);
    chk  ("fires after release",fired,      1'b1);
    // Wrong auth cannot freeze
    send_cmd(4'd5, WRONG, 32'h0);
    chk  ("wrong auth no freeze", dbg_frozen, 1'b0);

    // ── [14] priority / trace / breakpoint ────────────────────────────────────
    $display("\n[14] priority / trace / breakpoint");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_PASS, 0, AUTH, 2'b00, 0,0, 1,1,1, 0,0));
    chk("priority",   dbg_priority,   1'b1);
    chk("trace",      dbg_trace,      1'b1);
    chk("breakpoint", dbg_breakpoint, 1'b1);
    // Clear them
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_PASS, 0, AUTH, 2'b00, 0,0, 0,0,0, 0,0));
    chk("priority clr",   dbg_priority,   1'b0);
    chk("trace clr",      dbg_trace,      1'b0);
    chk("breakpoint clr", dbg_breakpoint, 1'b0);

    // ── [15] dtype ────────────────────────────────────────────────────────────
    $display("\n[15] dtype");
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_PASS, 0, AUTH, 2'b00, 0,0, 0,0,0, 0,0));
    chk32("dtype NUMERIC",  dbg_dtype, 2'b00);
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_PASS, 0, AUTH, 2'b01, 0,0, 0,0,0, 0,0));
    chk32("dtype SIGNED",   dbg_dtype, 2'b01);
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_PASS, 0, AUTH, 2'b10, 0,0, 0,0,0, 0,0));
    chk32("dtype ALPHA",    dbg_dtype, 2'b10);
    send_cmd(4'd4, AUTH, mk_cfg(TOPO_PASS, 0, AUTH, 2'b11, 0,0, 0,0,0, 0,0));
    chk32("dtype DATETIME", dbg_dtype, 2'b11);

    // ── [16] auth_mask zeroed in debug output ─────────────────────────────────
    $display("\n[16] auth_mask zeroed in debug");
    chk32("auth=0 in dbg", dbg_cmd_latch & 32'h003FF800, 32'h0);

    // ── Summary ───────────────────────────────────────────────────────────────
    $display("\n=== %0d passed  %0d failed ===", pass_count, fail_count);
    if (fail_count == 0)
        $display("ALL PASSED");
    else
        $display("FAILURES DETECTED");
    $finish;
end

// Timeout guard
initial begin
    #500000;
    $display("TIMEOUT — testbench hung");
    $finish;
end

endmodule
