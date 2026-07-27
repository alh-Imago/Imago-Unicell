// tb_pcie_bridge_sticky.v
//
// Covers the exact case that defeated the 2026-07-26 hardware bring-up and
// that no existing testbench exercised: out_valid from the fabric is
// combinational and only ONE CLK cycle wide, while a host polling over PCIe
// reads many cycles later. Before the sticky capture was added, the pulse was
// simply gone by the time the read arrived and STATUS_ADDR_VALID always read 0
// even though the fabric had fired correctly.
//
// Checks:
//   1. a 1-cycle out_valid pulse is still readable 100 cycles later
//   2. out_addr / out_data are captured with it, not just the flag
//   3. reads are non-destructive -- reading twice gives the same answer, and
//      the order of ADDR_VALID vs DATA reads does not matter
//   4. writing to REG_STATUS_ADDR_VALID clears the flag
//   5. a pulse coincident with a clear is KEPT (losing a real result is worse
//      than holding a stale flag)
//
// iverilog -o /tmp/t.vvp -g2012 tb_pcie_bridge_sticky.v pcie_unicell_bridge.v && vvp /tmp/t.vvp

`timescale 1ns/1ps

module tb_pcie_bridge_sticky;

reg         clk = 1'b0;
reg         rst = 1'b1;
always #5 clk = ~clk;

reg  [31:0] avs_address    = 32'h0;
reg  [3:0]  avs_byteenable = 4'hF;
reg  [31:0] avs_writedata  = 32'h0;
reg         avs_write      = 1'b0;
reg         avs_read       = 1'b0;
wire [31:0] avs_readdata;
wire        avs_readdatavalid;
wire        avs_waitrequest;

wire [31:0] cpu_bus, cpu_data;
wire        cpu_valid;

reg  [15:0] out_addr  = 16'h0;
reg  [31:0] out_data  = 32'h0;
reg         out_valid = 1'b0;

integer errors = 0;

task check;
    input [127:0] name;
    input [31:0]  got, want;
    begin
        if (got !== want) begin
            $display("  FAIL: %0s got=0x%08x want=0x%08x", name, got, want);
            errors = errors + 1;
        end else begin
            $display("  PASS: %0s", name);
        end
    end
endtask

// One read transaction; result lands in rdval one cycle later.
reg [31:0] rdval;
task do_read;
    input [31:0] addr;
    begin
        @(posedge clk);
        avs_address <= addr;
        avs_read    <= 1'b1;
        @(posedge clk);
        avs_read    <= 1'b0;
        @(posedge clk);
        rdval = avs_readdata;
    end
endtask

task do_write;
    input [31:0] addr;
    input [31:0] data;
    begin
        @(posedge clk);
        avs_address   <= addr;
        avs_writedata <= data;
        avs_write     <= 1'b1;
        @(posedge clk);
        avs_write     <= 1'b0;
    end
endtask

// Exactly one cycle wide, mirroring the combinational collector upstream.
task pulse_fabric;
    input [15:0] a;
    input [31:0] d;
    begin
        @(posedge clk);
        out_addr  <= a;
        out_data  <= d;
        out_valid <= 1'b1;
        @(posedge clk);
        out_valid <= 1'b0;
        out_addr  <= 16'h0;   // fabric stops driving these too
        out_data  <= 32'h0;
    end
endtask

pcie_unicell_bridge dut (
    .clk(clk), .rst(rst),
    .avs_address(avs_address), .avs_byteenable(avs_byteenable),
    .avs_writedata(avs_writedata), .avs_write(avs_write),
    .avs_read(avs_read), .avs_burstcount(6'h0),
    .avs_readdata(avs_readdata), .avs_readdatavalid(avs_readdatavalid),
    .avs_waitrequest(avs_waitrequest),
    .cpu_bus(cpu_bus), .cpu_data(cpu_data), .cpu_valid(cpu_valid),
    .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid)
);

integer k;

initial begin
    repeat (4) @(posedge clk);
    rst = 1'b0;
    repeat (2) @(posedge clk);

    // ---- 1/2: pulse, wait a long time, then read -------------------------
    pulse_fabric(16'h0200, 32'h000000AA);
    for (k = 0; k < 100; k = k + 1) @(posedge clk);

    do_read(32'h8);
    check("late read: valid bit still set",  (rdval >> 16) & 1, 32'h1);
    check("late read: out_addr held",         rdval & 32'hFFFF,  32'h0200);
    do_read(32'hC);
    check("late read: out_data held",         rdval,             32'h000000AA);

    // ---- 3: reads are non-destructive, order-independent ------------------
    do_read(32'hC);
    check("re-read DATA unchanged",           rdval,             32'h000000AA);
    do_read(32'h8);
    check("re-read ADDR_VALID unchanged",    (rdval >> 16) & 1,  32'h1);

    // ---- 4: explicit clear ------------------------------------------------
    do_write(32'h8, 32'h0);
    repeat (2) @(posedge clk);
    do_read(32'h8);
    check("after clear: valid bit low",      (rdval >> 16) & 1,  32'h0);

    // ---- 5: pulse coincident with clear is kept ---------------------------
    // Drive a clear write and a fabric pulse on the same edge.
    @(posedge clk);
    avs_address   <= 32'h8;
    avs_writedata <= 32'h0;
    avs_write     <= 1'b1;
    out_addr      <= 16'h0301;
    out_data      <= 32'h000000BB;
    out_valid     <= 1'b1;
    @(posedge clk);
    avs_write     <= 1'b0;
    out_valid     <= 1'b0;
    out_addr      <= 16'h0;
    out_data      <= 32'h0;

    repeat (4) @(posedge clk);
    do_read(32'h8);
    check("pulse during clear: kept",        (rdval >> 16) & 1,  32'h1);
    check("pulse during clear: addr kept",    rdval & 32'hFFFF,  32'h0301);
    do_read(32'hC);
    check("pulse during clear: data kept",    rdval,             32'h000000BB);

    $display("");
    if (errors == 0) $display("ALL CHECKS PASSED (0 errors)");
    else             $display("=== %0d FAILURE(S) ===", errors);
    $finish;
end

endmodule
