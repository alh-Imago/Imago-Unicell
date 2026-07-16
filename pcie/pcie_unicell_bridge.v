// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// pcie_unicell_bridge.v — Avalon-MM SLAVE that receives the PCIe Hard IP's
// rxm_bar0 AVALON-MM MASTER interface (BAR0 memory-mapped window) and
// translates single-beat 128-bit register accesses into the fabric's
// unified 32-bit command bus (cmd_bus/cmd_data/cmd_valid), matching the
// same master-side interface convention as uart_bridge.v and
// unicell_issp_bridge.v.
//
// STATUS: first-cut design, NOT YET SILICON-TESTED. Ground-truth interface
// widths/port names confirmed directly from pcie_test_1.sopcinfo (2026-07-16):
//   rxm_bar0_address_o      [63:0]  out (from HIP)  -> avs_address
//   rxm_bar0_byteenable_o   [15:0]  out             -> avs_byteenable
//   rxm_bar0_writedata_o    [127:0] out             -> avs_writedata
//   rxm_bar0_write_o        [0:0]   out             -> avs_write
//   rxm_bar0_read_o         [0:0]   out             -> avs_read
//   rxm_bar0_burstcount_o   [5:0]   out             -> avs_burstcount (unused: burst disabled in qsys)
//   rxm_bar0_readdata_i     [127:0] in  (to HIP)     <- avs_readdata
//   rxm_bar0_readdatavalid_i [0:0]  in              <- avs_readdatavalid
//   rxm_bar0_waitrequest_i  [0:0]   in              <- avs_waitrequest
//
// REGISTER MAP (proposed, pending review — matching convention will need
// documenting in docs/V3_COMMAND_CONTRACT.md or a new PCIE doc once
// confirmed on real hardware). Beat-addressed (128-bit / 16-byte beats,
// burst disabled so every access is a single beat): avs_address[7:4]
// selects the register, matching addressUnits as configured in the qsys
// (WORDS vs SYMBOLS not yet re-verified against real hardware — first
// thing to check if real host-side reads/writes land on the wrong offset).
//
//   beat 0 (address[7:4]==0) — CMD (write-only; MVP smallest test):
//     writedata[31:0]  = cmd_data
//     writedata[63:32] = cmd_bus
//     A write here pulses cmd_valid for exactly one clk cycle, atomically
//     presenting cmd_bus+cmd_data together — same atomicity as the ISSP
//     bridge's combined source-register write.
//     Read of this beat echoes the last-written {cmd_bus,cmd_data} for
//     host-side debug/verification, no side effect.
//
//   beat 1 (address[7:4]==1) — STATUS (read-only; MVP smallest test):
//     readdata[15:0]   = out_addr
//     readdata[16]     = out_valid
//     readdata[63:32]  = out_data
//     (upper 64 bits reserved/zero for now)
//
// Deferred to a follow-up (NOT in this first cut, per smallest-test-first):
//   cycle_count / armed_count readback, array_rst / array_freeze control,
//   a dedicated ARM/GO semantics beyond the raw one-shot cmd_valid pulse.
//
// Avalon-MM timing: simple always-ready slave (avs_waitrequest tied 0).
// Write: captured and cmd_valid pulsed same cycle as avs_write. Read:
// registered, 1-cycle latency (avs_readdatavalid asserts the cycle after
// avs_read) — standard fixed-latency-1 Avalon-MM slave. NOT yet confirmed
// against the qsys's configured readLatency parameter for rxm_bar0 — check
// this first if real hardware read cycles don't land correctly.

`timescale 1ns / 1ps
`default_nettype none

module pcie_unicell_bridge (
    input  wire         clk,
    input  wire         rst,

    // Avalon-MM slave, driven by the PCIe Hard IP's rxm_bar0 master
    input  wire [63:0]  avs_address,
    input  wire [15:0]  avs_byteenable,
    input  wire [127:0] avs_writedata,
    input  wire         avs_write,
    input  wire         avs_read,
    input  wire [5:0]   avs_burstcount,   // unused: burst disabled in qsys config
    output wire [127:0] avs_readdata,
    output wire         avs_readdatavalid,
    output wire         avs_waitrequest,

    // Fabric command-bus master output (same convention as uart_bridge.v /
    // unicell_issp_bridge.v's top-level connection: cpu_bus/cpu_data/cpu_valid)
    output reg  [31:0]  cpu_bus,
    output reg  [31:0]  cpu_data,
    output reg          cpu_valid,

    // Fabric status readback (STATUS beat, MVP subset)
    input  wire [15:0]  out_addr,
    input  wire [31:0]  out_data,
    input  wire         out_valid
);

// Always-ready slave: no back-pressure needed for this simple design.
assign avs_waitrequest = 1'b0;

localparam BEAT_CMD    = 4'h0;
localparam BEAT_STATUS = 4'h1;

wire [3:0] beat_sel = avs_address[7:4];

// --- Write path: CMD beat only, one-cycle cmd_valid pulse ---
reg [31:0] cmd_bus_echo, cmd_data_echo;  // last-written values, for CMD-beat readback

always @(posedge clk) begin
    if (rst) begin
        cpu_bus       <= 32'h0;
        cpu_data      <= 32'h0;
        cpu_valid     <= 1'b0;
        cmd_bus_echo  <= 32'h0;
        cmd_data_echo <= 32'h0;
    end else begin
        cpu_valid <= 1'b0;   // default: one-cycle pulse, clear unless re-asserted below
        if (avs_write && beat_sel == BEAT_CMD) begin
            cpu_data      <= avs_writedata[31:0];
            cpu_bus       <= avs_writedata[63:32];
            cpu_valid     <= 1'b1;
            cmd_data_echo <= avs_writedata[31:0];
            cmd_bus_echo  <= avs_writedata[63:32];
        end
    end
end

// --- Read path: 1-cycle registered latency, both beats ---
reg [127:0] readdata_r;
reg         readdatavalid_r;

always @(posedge clk) begin
    if (rst) begin
        readdata_r      <= 128'h0;
        readdatavalid_r <= 1'b0;
    end else begin
        readdatavalid_r <= avs_read;   // valid exactly one cycle after the read request
        case (beat_sel)
            BEAT_CMD:    readdata_r <= {cmd_bus_echo, cmd_data_echo};
            BEAT_STATUS: readdata_r <= {64'h0, out_data, 15'h0, out_valid, out_addr};
            default:     readdata_r <= 128'h0;
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
