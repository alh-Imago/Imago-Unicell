// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// unicell_issp_bridge.v — JTAG host bridge via In-System Sources & Probes
//
// v1.1a — test channel over the Waveshare USB-Blaster, no PCIe, no card-USB,
//         no dependence on whether the UART pins (B3/AF10) are reachable.
//
// WHAT THIS DOES
//   Wraps one In-System Sources & Probes (altsource_probe) instance and turns
//   the host's source/probe words into UniCell command-bus transactions and
//   readback. The host (System Console / quartus_stp, or the ISSP Editor GUI)
//   writes the SOURCE word and reads the PROBE word over JTAG.
//
// CRITICAL — GENERATE THE IP CORRECTLY (IP Catalog → In-System Sources and
// Probes, name it `issp`):
//   * Source width = SRC_W (66)   Probe width = PRB_W (113)
//   * ENABLE "Source Clock"  -> connect source_clk to CLK (the 25 MHz fabric clock)
//   * ENABLE the source synchronisation registers (the "additional pair of
//     registers per source port" option)
//   Without a source clock + sync regs, the edge-detects below can glitch.
//   The generated module's ports are `source`, `probe`, `source_clk`
//   (and possibly `source_ena`). Reconcile the instance at the bottom of this
//   file against the template Quartus generates if the names differ by version.
//
// SOURCE word layout (host -> fabric):
//   source[31:0]   cpu_data        payload (address / cfg / shift amount)
//   source[63:32]  cpu_bus         command word (opcode in [7:0])
//   source[64]     cmd_go          rising edge = inject one command (1 CLK pulse)
//   source[65]     snap_req        rising edge = latch a readback snapshot
//   (host issues an array reset via the normal opcode-8 auth-reset command,
//    so no dedicated reset source bit is needed)
//
// PROBE word layout (fabric -> host), all from the last snapshot:
//   probe[31:0]    snap_cycle      cycle_count at snapshot
//   probe[47:32]   snap_armed      total armed cells at snapshot
//   probe[79:48]   snap_out_data   last output data captured since reset
//   probe[95:80]   snap_out_addr   last output addr captured since reset
//   probe[96]      snap_out_seen   1 = at least one output occurred since reset
//   probe[112:97]  snap_out_count  number of outputs since reset (saturation metric)
//
// READ PROTOCOL (host side):
//   1. write cpu_bus/cpu_data, pulse cmd_go (0->1->0)        // inject command
//   2. pulse snap_req (0->1->0)                              // freeze readback
//   3. read probe                                            // static, tear-free
//   Because the snapshot register only changes on snap_req, the multi-bit
//   free-running cycle_count is sampled once and held static during the read.

`default_nettype none

module unicell_issp_bridge #(
    parameter SRC_W = 66,
    parameter PRB_W = 113
)(
    input  wire        clk,          // fabric clock (CLK = 25 MHz) — also IP source_clk
    input  wire        rst,          // tie to rst_all: clears the per-run counters

    // to the command-bus mux in the top
    output wire [31:0] cpu_bus_o,
    output wire [31:0] cpu_data_o,
    output wire        cpu_valid_o,

    // readback taps from the top (same signals the UART bridge reads)
    input  wire [15:0] out_addr,
    input  wire [31:0] out_data,
    input  wire        out_valid,
    input  wire [15:0] armed_count,
    input  wire [15:0] arrived_count,
    input  wire [15:0] output_set_count,
    input  wire [31:0] cycle_count
);

    // ── ISSP source/probe nets ────────────────────────────────────────────────
    wire [SRC_W-1:0] source;   // driven by host, synchronous to clk (source_clk)
    reg  [PRB_W-1:0] probe;    // read by host

    wire [31:0] src_cpu_data = source[31:0];
    wire [31:0] src_cpu_bus  = source[63:32];
    wire        src_cmd_go   = source[64];
    wire        src_snap_req = source[65];

    // ── Command injection: edge-detect cmd_go -> 1-cycle cpu_valid ─────────────
    reg cmd_go_d;
    always @(posedge clk) cmd_go_d <= src_cmd_go;
    wire cmd_go_pulse = src_cmd_go & ~cmd_go_d;

    assign cpu_bus_o   = src_cpu_bus;
    assign cpu_data_o  = src_cpu_data;
    assign cpu_valid_o = cmd_go_pulse;

    // ── Sticky output capture + event count ──────────────────────────────────
    // out_valid is a 1-cycle pulse; the host link is far too slow to catch it
    // live, so latch the last output and count how many occurred.
    (* preserve *) reg [15:0] out_addr_l;
    (* preserve *) reg [31:0] out_data_l;
    (* preserve *) reg [15:0] out_count;
    (* preserve *) reg        out_seen;
    always @(posedge clk) begin
        if (rst) begin
            out_count <= 16'h0;
            out_seen  <= 1'b0;
        end else if (out_valid) begin
            out_addr_l <= out_addr;
            out_data_l <= out_data;
            out_count  <= out_count + 16'h1;
            out_seen   <= 1'b1;
        end
    end

    // ── Snapshot: freeze readback into a static word on snap_req rising edge ───
    reg snap_d;
    always @(posedge clk) snap_d <= src_snap_req;
    wire snap_pulse = src_snap_req & ~snap_d;

    (* preserve *) reg [31:0] snap_cycle;
    (* preserve *) reg [15:0] snap_armed;
    (* preserve *) reg [31:0] snap_out_data;
    (* preserve *) reg [15:0] snap_out_addr;
    (* preserve *) reg        snap_out_seen;
    (* preserve *) reg [15:0] snap_out_count;

    always @(posedge clk) if (snap_pulse) begin
        snap_cycle     <= cycle_count;
        snap_armed     <= (src_cpu_bus[1:0]==2'd1) ? arrived_count :
                          (src_cpu_bus[1:0]==2'd2) ? output_set_count : armed_count;
        snap_out_data  <= out_data_l;
        snap_out_addr  <= out_addr_l;
        snap_out_seen  <= out_seen;
        snap_out_count <= out_count;
    end

    always @(*) probe = { snap_out_count,   // [112:97]
                          snap_out_seen,    // [96]
                          snap_out_addr,    // [95:80]
                          snap_out_data,    // [79:48]
                          snap_armed,       // [47:32]
                          snap_cycle };     // [31:0]

    // ── In-System Sources & Probes IP instance ───────────────────────────────
    // Generate via IP Catalog as described in the header. Match these ports to
    // the generated template. source_clk = clk makes sources synchronous here.
    issp issp_inst (
        .source     (source),
        .probe      (probe),
        .source_clk (clk)
        // .source_ena (1'b1)   // include if the generated IP exposes it
    );

endmodule
