// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// pcie_unicell_bridge.v — Avalon-MM SLAVE receiving the "hprxm" master
// interface from Intel's PIO Avalon-ST-to-Avalon-MM bridge (pio_bridge_0,
// itself sitting on the PCIe Hard IP's raw Avalon-ST application interface)
// and translating narrow register accesses into the fabric's unified 32-bit
// command bus (cmd_bus/cmd_data/cmd_valid), matching the same master-side
// interface convention as uart_bridge.v and unicell_issp_bridge.v.
//
// STATUS: first-cut design, NOT YET SILICON-TESTED.
//
// REVISION (2026-07-21): rewritten for the interface pio_bridge_0 actually
// provides -- 16-bit address, 32-bit data, 4-bit byteenable -- confirmed
// directly from pio_bridge_0.cmp, genuinely narrower than the 64-bit/
// 128-bit/16-bit interface this file originally assumed (which matched the
// ORIGINAL pcie_test_1.sopcinfo's rxm_bar0, a different, wider interface
// this specific IP generation path doesn't produce). A wider "DMA"-style
// Avalon-MM variant may exist separately (seen referenced in IP Catalog's
// own documentation panel) and could replace this narrower path later if
// throughput ever needs it -- deliberately deferred, not pursued now, per
// "get PCIe confirmed working first."
//
// Ground-truth interface widths/port names confirmed directly from
// pio_bridge_0.cmp (2026-07-21):
//   AvRxmAddress_0_o     [15:0]  out (from bridge) -> avs_address
//   AvRxmByteEnable_0_o  [3:0]   out                -> avs_byteenable
//   AvRxmWriteData_0_o   [31:0]  out                -> avs_writedata
//   AvRxmWrite_0_o       [0:0]   out                -> avs_write
//   AvRxmRead_0_o        [0:0]   out                -> avs_read
//   (no burstcount signal at all -- pio_bridge_0 is a single-beat PIO
//   master; avs_burstcount is tied to a constant by whatever instantiates
//   this bridge, not driven by anything real)
//   AvRxmReadData_0_i        [31:0] in  (to bridge) <- avs_readdata
//   AvRxmReadDataValid_0_i   [0:0]  in              <- avs_readdatavalid
//   AvRxmWaitRequest_0_i     [0:0]  in              <- avs_waitrequest
//
// REGISTER MAP (proposed, pending review — matching convention will need
// documenting in docs/V3_COMMAND_CONTRACT.md or a new PCIE doc once
// confirmed on real hardware). Word-addressed, 4 bytes/register, burst
// disabled so every access is a single beat: avs_address[3:2] selects the
// register (addressUnits=SYMBOLS/byte-addressed, confirmed against the real
// qsys -- byte offsets 0x0/0x4/0x8/0xC map to word indices 0/1/2/3).
//
//   0x0 CMD_DATA (write-only staging register; MVP smallest test):
//     A write here stages cmd_data for the NEXT CMD_BUS write -- does not
//     itself present anything to the fabric yet. Read echoes the last
//     staged value, no side effect.
//
//   0x4 CMD_BUS (write fires the fabric command; MVP smallest test):
//     A write here pulses cmd_valid for exactly one clk cycle, presenting
//     the value written here as cpu_bus together with whatever cmd_data was
//     most recently staged at 0x0 -- same atomic PRESENTATION to the fabric
//     as the original packed design had, just assembled across two host
//     writes instead of one (host convention: always write CMD_DATA, then
//     CMD_BUS, in that order). Read echoes the last-written cmd_bus value,
//     no side effect.
//
//   0x8 STATUS_ADDR_VALID (read-only; MVP smallest test):
//     readdata[15:0]  = out_addr
//     readdata[16]    = out_valid
//     (upper bits reserved/zero for now)
//
//   0xC STATUS_DATA (read-only; MVP smallest test):
//     readdata[31:0]  = out_data
//
// Deferred to a follow-up (NOT in this first cut, per smallest-test-first):
//   cycle_count / armed_count readback, array_rst / array_freeze control,
//   a dedicated ARM/GO semantics beyond the raw one-shot cmd_valid pulse.
//
// Avalon-MM timing: simple always-ready slave (avs_waitrequest tied 0).
// Write: captured same cycle as avs_write. Read: registered, 1-cycle
// latency (avs_readdatavalid asserts the cycle after avs_read) — standard
// fixed-latency-1 Avalon-MM slave. Confirmed compatible with the qsys's
// configured readLatency=0 for the (original, wider) rxm_bar0 interface via
// Avalon-MM's own variable-latency rules (a slave driving readdatavalid
// puts the interface in variable-latency mode, overriding a fixed
// readLatency expectation) — same reasoning applies here; worth confirming
// directly once real hardware access is possible, not just re-assumed.

`timescale 1ns / 1ps
`default_nettype none

module pcie_unicell_bridge (
    input  wire         clk,
    input  wire         rst,

    // Avalon-MM slave, driven by pio_bridge_0's hprxm master
    input  wire [15:0]  avs_address,
    input  wire [3:0]   avs_byteenable,
    input  wire [31:0]  avs_writedata,
    input  wire         avs_write,
    input  wire         avs_read,
    input  wire [5:0]   avs_burstcount,   // unused: pio_bridge_0 doesn't drive this at all, tied constant upstream
    output wire [31:0]  avs_readdata,
    output wire         avs_readdatavalid,
    output wire         avs_waitrequest,

    // Fabric command-bus master output (same convention as uart_bridge.v /
    // unicell_issp_bridge.v's top-level connection: cpu_bus/cpu_data/cpu_valid)
    output reg  [31:0]  cpu_bus,
    output reg  [31:0]  cpu_data,
    output reg          cpu_valid,

    // Fabric status readback (STATUS registers, MVP subset)
    input  wire [15:0]  out_addr,
    input  wire [31:0]  out_data,
    input  wire         out_valid
);

// Always-ready slave: no back-pressure needed for this simple design.
assign avs_waitrequest = 1'b0;

localparam REG_CMD_DATA          = 2'h0;
localparam REG_CMD_BUS           = 2'h1;
localparam REG_STATUS_ADDR_VALID = 2'h2;
localparam REG_STATUS_DATA       = 2'h3;

wire [1:0] reg_sel = avs_address[3:2];

// --- Write path: CMD_DATA stages, CMD_BUS write fires cmd_valid ---
reg [31:0] cmd_data_staged;   // staged by a CMD_DATA write, consumed by the next CMD_BUS write
reg [31:0] cmd_bus_echo;      // last-written CMD_BUS value, for readback only

always @(posedge clk) begin
    if (rst) begin
        cpu_bus         <= 32'h0;
        cpu_data        <= 32'h0;
        cpu_valid       <= 1'b0;
        cmd_data_staged <= 32'h0;
        cmd_bus_echo    <= 32'h0;
    end else begin
        cpu_valid <= 1'b0;   // default: one-cycle pulse, clear unless re-asserted below
        if (avs_write) begin
            case (reg_sel)
                REG_CMD_DATA: cmd_data_staged <= avs_writedata;
                REG_CMD_BUS: begin
                    cpu_data     <= cmd_data_staged;
                    cpu_bus      <= avs_writedata;
                    cpu_valid    <= 1'b1;
                    cmd_bus_echo <= avs_writedata;
                end
                default: ; // STATUS registers are read-only, writes ignored
            endcase
        end
    end
end

// --- Sticky capture of the fabric output pulse -------------------------------
// out_valid from the fabric is COMBINATIONAL (see the always @(*) output
// collector in top_arria10_zone1_v3.v) and therefore only one CLK cycle wide
// -- 40ns at 25MHz. A host polling over PCIe arrives microseconds later and
// can never catch it. Found 2026-07-26: the full command path was verified
// working (writes land, registers read back correctly) while STATUS_ADDR_VALID
// still read 0, because there was nothing holding the result.
//
// These registers latch the pulse and hold it until explicitly cleared, so a
// polled read can observe it. Cleared by WRITING to REG_STATUS_ADDR_VALID
// (previously ignored, since the STATUS registers are read-only) -- an
// explicit clear rather than clear-on-read, so that reading ADDR_VALID and
// DATA in either order is safe and non-destructive.
//
// Same clock domain throughout (pcie_unicell_bridge is instantiated on CLK,
// the fabric clock), so no CDC is required here.
reg [15:0] out_addr_sticky;
reg [31:0] out_data_sticky;
reg        out_valid_sticky;

always @(posedge clk) begin
    if (rst) begin
        out_addr_sticky  <= 16'h0;
        out_data_sticky  <= 32'h0;
        out_valid_sticky <= 1'b0;
    end else begin
        // Clear takes precedence over capture on the same cycle only when no
        // new pulse arrives; a pulse coincident with a clear is kept, since
        // losing a real result is worse than a stale flag.
        if (out_valid) begin
            out_addr_sticky  <= out_addr;
            out_data_sticky  <= out_data;
            out_valid_sticky <= 1'b1;
        end else if (avs_write && (reg_sel == REG_STATUS_ADDR_VALID)) begin
            out_valid_sticky <= 1'b0;
        end
    end
end

// --- Read path: 1-cycle registered latency, all four registers ---
reg [31:0] readdata_r;
reg        readdatavalid_r;

always @(posedge clk) begin
    if (rst) begin
        readdata_r      <= 32'h0;
        readdatavalid_r <= 1'b0;
    end else begin
        readdatavalid_r <= avs_read;   // valid exactly one cycle after the read request
        case (reg_sel)
            REG_CMD_DATA:          readdata_r <= cmd_data_staged;
            REG_CMD_BUS:           readdata_r <= cmd_bus_echo;
            REG_STATUS_ADDR_VALID: readdata_r <= {15'h0, out_valid_sticky, out_addr_sticky};
            REG_STATUS_DATA:       readdata_r <= out_data_sticky;
            default:               readdata_r <= 32'h0;
        endcase
    end
end

assign avs_readdata      = readdata_r;
assign avs_readdatavalid = readdatavalid_r;

endmodule

// Restore the default net type: `default_nettype none` above is a
// compilation-unit-wide directive that otherwise persists into whatever
// file Quartus compiles next in the same run. Left unreset, it breaks
// Intel's own generated PCIe Hard IP files (e.g.
// altpciexpav128_p2a_addrtrans.v), which rely on the classic implicit-wire
// default and were not written with `default_nettype none` in mind.
// Confirmed via: Error (10162) on altpciexpav128_p2a_addrtrans.v line 61,
// "can't declare implicit net... because 'default_nettype is none" --
// this reset is the fix. (Same latent issue exists in uart_bridge.v and
// unicell_issp_bridge.v, harmless there only because neither has yet been
// compiled in the same run as the PCIe Hard IP's generated files -- worth
// the same fix if/when they are.)
`default_nettype wire
