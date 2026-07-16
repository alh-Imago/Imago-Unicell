// tb_pcie_unicell_bridge.v — standalone sim test for pcie_unicell_bridge.v,
// BEFORE any silicon/Hard IP involvement (sim-first, smallest-test-first).
// Drives fake Avalon-MM write/read cycles as if from the PCIe Hard IP's
// rxm_bar0 master, and checks:
//   1. A write to the CMD beat pulses cpu_valid for exactly one cycle with
//      the correct cpu_bus/cpu_data split out of the 128-bit writedata.
//   2. cpu_valid returns to 0 the following cycle (true one-shot pulse).
//   3. A read of the CMD beat echoes back the last-written {cmd_bus,cmd_data}
//      with correct 1-cycle registered latency and readdatavalid timing.
//   4. A read of the STATUS beat correctly packs out_addr/out_data/out_valid.
//   5. avs_waitrequest stays low throughout (always-ready slave, as designed).
`timescale 1ns/1ps
module tb_pcie_unicell_bridge;
    reg clk=0, rst=1;
    always #5 clk=~clk;

    reg  [63:0]  avs_address=0;
    reg  [15:0]  avs_byteenable=16'hFFFF;
    reg  [127:0] avs_writedata=0;
    reg          avs_write=0, avs_read=0;
    reg  [5:0]   avs_burstcount=6'd1;
    wire [127:0] avs_readdata;
    wire         avs_readdatavalid;
    wire         avs_waitrequest;

    wire [31:0]  cpu_bus, cpu_data;
    wire         cpu_valid;

    reg  [15:0]  out_addr=0;
    reg  [31:0]  out_data=0;
    reg          out_valid=0;

    pcie_unicell_bridge dut (
        .clk(clk), .rst(rst),
        .avs_address(avs_address), .avs_byteenable(avs_byteenable),
        .avs_writedata(avs_writedata), .avs_write(avs_write), .avs_read(avs_read),
        .avs_burstcount(avs_burstcount),
        .avs_readdata(avs_readdata), .avs_readdatavalid(avs_readdatavalid),
        .avs_waitrequest(avs_waitrequest),
        .cpu_bus(cpu_bus), .cpu_data(cpu_data), .cpu_valid(cpu_valid),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid)
    );

    integer errors=0;
    task check; input got; input want; input [511:0] msg; begin
        if (got===want) $display("  PASS: %0s", msg);
        else begin $display("  FAIL: %0s got=%0d want=%0d", msg, got, want); errors=errors+1; end
    end endtask
    task check32; input [31:0] got, want; input [511:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08x want=0x%08x", msg, got, want); errors=errors+1; end
    end endtask
    task check128; input [127:0] got, want; input [511:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%032x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%032x want=0x%032x", msg, got, want); errors=errors+1; end
    end endtask

    localparam [3:0] BEAT_CMD = 4'h0, BEAT_STATUS = 4'h1;

    // Drive one write beat: address selects which register, writedata is the
    // full 128-bit payload. Deasserted the following cycle (single-beat,
    // burst disabled).
    task avalon_write; input [3:0] beat; input [127:0] wdata; begin
        @(negedge clk);
        avs_address    = {56'h0, beat, 4'h0};   // beat_sel = address[7:4]
        avs_writedata  = wdata;
        avs_write      = 1'b1;
        @(posedge clk); #1;
        @(negedge clk);
        avs_write      = 1'b0;
    end endtask

    // Drive one read beat, wait the fixed 1-cycle latency, capture result.
    task avalon_read; input [3:0] beat; output [127:0] rdata; begin
        @(negedge clk);
        avs_address = {56'h0, beat, 4'h0};
        avs_read    = 1'b1;
        @(negedge clk);
        avs_read    = 1'b0;
        // readdatavalid asserts the cycle after the read request (1-cycle latency)
        check(avs_readdatavalid, 1'b1, "read: readdatavalid asserted at expected 1-cycle latency");
        rdata = avs_readdata;
    end endtask

    reg [127:0] rd;

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== pcie_unicell_bridge: standalone Avalon-MM sim test ===");

        // waitrequest must be low throughout -- always-ready slave design.
        check(avs_waitrequest, 1'b0, "avs_waitrequest low at reset/idle");

        // --- 1. CMD beat write: cmd_data=0x000000AA, cmd_bus=0x05280004 ---
        // writedata[31:0]=cmd_data, writedata[63:32]=cmd_bus (per header spec)
        avalon_write(BEAT_CMD, {64'h0, 32'h05280004, 32'h000000AA});
        check(cpu_valid, 1'b1, "CMD write: cpu_valid pulsed high same cycle as avs_write");
        check32(cpu_bus,  32'h05280004, "CMD write: cpu_bus == writedata[63:32]");
        check32(cpu_data, 32'h000000AA, "CMD write: cpu_data == writedata[31:0]");

        @(posedge clk); #1;
        check(cpu_valid, 1'b0, "CMD write: cpu_valid returns to 0 the following cycle (one-shot)");
        check(avs_waitrequest, 1'b0, "avs_waitrequest still low after write");

        // --- 2. CMD beat read: should echo back the last-written pair ---
        avalon_read(BEAT_CMD, rd);
        check128(rd, {64'h0, 32'h05280004, 32'h000000AA}, "CMD read: echoes last-written {cmd_bus,cmd_data}");

        // --- 3. STATUS beat read: fabric status packing ---
        out_addr  = 16'h0200;
        out_data  = 32'h000000AA;
        out_valid = 1'b1;
        #1; // let combinational-adjacent regs settle before the read samples them
        avalon_read(BEAT_STATUS, rd);
        check128(rd, {64'h0, 32'h000000AA, 15'h0, 1'b1, 16'h0200}, "STATUS read: out_addr/out_valid/out_data packed correctly");

        // --- 4. A second, different CMD write to confirm no stale-state leakage ---
        avalon_write(BEAT_CMD, {64'h0, 32'h00000018, 32'h00000000});
        check(cpu_valid, 1'b1, "second CMD write: cpu_valid pulsed again");
        check32(cpu_bus,  32'h00000018, "second CMD write: cpu_bus updated (SET_TARGET)");
        check32(cpu_data, 32'h00000000, "second CMD write: cpu_data updated");

        $display("");
        if (errors==0) $display("=== ALL PASS ===");
        else           $display("=== %0d FAILURE(S) ===", errors);
        $finish;
    end
endmodule
