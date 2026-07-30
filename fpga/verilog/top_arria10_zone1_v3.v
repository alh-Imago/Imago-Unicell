// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// top_arria10.v — Imago UniCell Top Level for IEI Mustang-F100 (Arria 10 GX660)
// v1.0 — initial bring-up, 2×8 zone grid
//
// Target: 10AX066H2F34E2SG  Board: IEI Mustang-F100-A0E2-R10
//
// Grid: 2 rows × 8 cols = 16 zones × 28 cells = 448 cells total (~68% ALM load)
//
// Clock: 50MHz board ref → PLL stub → 200MHz target
//        Replace pll_stub with Quartus ALTPLL megafunction before full compile
//
// UART: fpga_bridge.py protocol unchanged from iCEBreaker
//
// Bridge wiring: all adjacent zones connected, unused directions tied low.
// Corner zones (Z00,Z07,Z08,Z15) stress the wired-OR bus across max distance.
//
// Pin assignments: set in .qsf — UART_RX, UART_TX, LED0_N, LED1_N
//
// TODO post bring-up:
//   - Replace PLL stub with generated megafunction
//   - Add PCIe Hard IP for DDR streaming
//   - Tune NUM_CELLS after first timing report

`default_nettype none
`timescale 1ns / 1ps

module top_arria10_zone1 (
    input  wire CLK_100M,  // 100 MHz board ref — diff pair CLK_2K_1, p-leg on E23 (pin in project .qsf)
    input  wire UART_RX,
    output wire UART_TX,
    output wire LED0_N,    // armed indicator (low = cells armed)
    output wire LED1_N,    // heartbeat blink

    // PCIe physical signals -- pin assignments TODO in .qsf at the real
    // Quartus machine (match pcie_hip_test.qsf's already-proven assignments
    // for this same board rather than guessing new ones).
    input  wire        pcie_refclk,
    input  wire        pcie_npor,
    input  wire        pcie_perst_n,
    input  wire [7:0]  pcie_rx_p,
    output wire [7:0]  pcie_tx_p
);

// ── Parameters ────────────────────────────────────────────────────────────────
localparam NUM_CELLS   = 25;
localparam NUM_BRIDGES = 2;

// ── Clock — 100 MHz → 25 MHz via synchronous /4 divider ──────────────────────
// Board ref measured at 100.00 MHz on the CLK_2K_1 differential pair (E23/E24).
// /4 keeps the fabric at the original 25 MHz target (clk_div Fmax ~40 MHz).
// Synchronous counter (not a ripple toggle) so there's no derived-clock skew.
// Refinement: feed CLK_100M into an IOPLL for a jitter-clean, tunable fabric clock.
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk_div = div_cnt[1];   // CLK_100M / 4 = 25 MHz
wire CLK = clk_div;

// ── Reset — simple power-on reset, no PLL lock dependency ────────────────────
reg [3:0] rst_sr = 4'hF;
always @(posedge CLK)
    rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

// ── Command bus — three masters muxed (UART + JTAG + PCIe) ──────────────────
wire [31:0] u_bus, u_data;   wire u_valid;   // UART master (uart_bridge)
wire [31:0] j_bus, j_data;   wire j_valid;   // JTAG master (unicell_issp_bridge)
wire [31:0] p_bus, p_data;   wire p_valid;   // PCIe master (pcie_unicell_bridge)
wire        array_rst_req;

// Priority: JTAG > PCIe > UART. JTAG keeps top priority since it's the
// known-good bring-up/debug path (icm64_readstate.tcl etc.) and must never
// be starved by a host driving PCIe; PCIe outranks UART since a host-side
// PCIe transaction is a deliberate, timed access that shouldn't silently
// lose arbitration to a UART bridge that's normally idle. Mirrors the
// existing two-master priority style exactly (highest-priority master's
// valid gates the mux), just extended to three.
wire [31:0] cpu_bus  = j_valid ? j_bus  : (p_valid ? p_bus  : u_bus);
wire [31:0] cpu_data = j_valid ? j_data : (p_valid ? p_data : u_data);
wire        cpu_valid = j_valid | p_valid | u_valid;

// ── Target latch — the address-lane transport for CMD_LOAD_AT (opcode 23) ───────
// The 2-word ISSP cannot carry target + config + opcode at once. SET_TARGET (opcode
// 24, top-only — the cells ignore it) latches the target address and HOLDS it on the
// address lane. The following CMD_LOAD_AT then carries config on cpu_data while the
// held target drives cpu_addr, so the addressed cell's addr_match delivers the load.
// Stream an ICM file as (SET_TARGET addr, CMD_LOAD_AT config) pairs. 16-bit now;
// widen to the full hierarchical address later with zero cell impact.
localparam [7:0] OP_SET_TARGET = 8'd24;
localparam [7:0] OP_LOAD_AT    = 8'd23;
reg [15:0] load_target = 16'h0;
always @(posedge CLK) begin
    if (cpu_valid && (cpu_bus[7:0] == OP_SET_TARGET))
        load_target <= cpu_data[15:0];
end

wire [15:0] cpu_addr_w   = (cpu_bus[7:0] == 8'd1)         ? cpu_data[31:16]
                         : (cpu_bus[7:0] == OP_LOAD_AT)   ? load_target
                         : (cpu_bus[7:0] == 8'd2)         ? load_target  // SET_INPUT_ADDR
                         : (cpu_bus[7:0] == 8'd3)         ? load_target  // SET_OUTPUT_ADDR
                         : (cpu_bus[7:0] == 8'd25)        ? load_target  // CMD_SET_METHOD wrapper -- vestigial in
                                                                          // v3.1 (no case match in the cell any
                                                                          // more), kept harmless; real cycle-2
                                                                          // words are the raw opcodes below.
                         : (cpu_bus[7:0] == 8'd30)        ? load_target  // METH_SET_MASK      (cycle 2, self-describing v3.1)
                         : (cpu_bus[7:0] == 8'd31)        ? load_target  // METH_SET_SHIFT_IN
                         : (cpu_bus[7:0] == 8'd32)        ? load_target  // METH_SET_SHIFT_OUT
                         : (cpu_bus[7:0] == 8'd33)        ? load_target  // METH_SET_LANE
                         : (cpu_bus[7:0] == 8'd34)        ? load_target  // METH_SET_ROUTING (routing_mask)
                         : (cpu_bus[7:0] == 8'd35)        ? load_target  // METH_SET_TRANSIT (transit_only)
                         : (cpu_bus[7:0] == 8'd27)        ? load_target  // CMD_LOAD_DONE (cycle-3 completion marker)
                         // FIX (2026-07-30, points.md #59 rearm-hazard investigation): every
                         // config_match-gated opcode MUST be listed here, or it silently falls
                         // through to cpu_data[15:0] -- the low 16 bits of that command's OWN
                         // payload, misread as an address, which then ALSO clobbers bus_addr
                         // for whatever config_match-gated command comes next (the array
                         // registers bus_addr on every host pulse, not just data writes). Three
                         // opcodes added since #42/#49 were missing from this list entirely --
                         // caught only because CMD_SWAP_AB's payload in one test (0x50) didn't
                         // coincidentally match the target CELL_ID (0), unlike an earlier test
                         // that got lucky with a payload of 0. Standing rule: any NEW
                         // config_match-gated opcode goes in this list in the SAME commit that
                         // adds it to the cell, same discipline as the cmd_latch field-map rule.
                         : (cpu_bus[7:0] == 8'd18)        ? load_target  // CMD_SWAP_AB
                         : (cpu_bus[7:0] == 8'd36)        ? load_target  // METH_SET_CARDINAL_EDGE (points.md #58)
                         : (cpu_bus[7:0] == 8'd37)        ? load_target  // CMD_SET_ROUTE_LATCH    (points.md #59)
                         : cpu_data[15:0];
wire        preload_act  = (cpu_bus[18:17] != 2'b00);
wire        cmd_valid_w  = cpu_valid
                         && (cpu_bus[7:0] != 8'd1)
                         && ((cpu_bus[7:0] != 8'd0) || preload_act);

// ── Authenticated array reset ──────────────────────────────────────────────────
reg auth_rst_pulse = 1'b0;
always @(posedge CLK) begin
    auth_rst_pulse <= 1'b0;
    if (cpu_valid && (cpu_bus[7:0] == 8'd8) && (cpu_bus[28:21] != 8'h0))
        auth_rst_pulse <= 1'b1;
end
wire rst_all = rst | array_rst_req | auth_rst_pulse;

// ── Zone output wires ─────────────────────────────────────────────────────────
wire [15:0] z_out_addr  [0:15];
wire [31:0] z_out_data  [0:15];
wire        z_out_valid [0:15];
wire [15:0] z_armed     [0:15];
wire [15:0] z_arrived   [0:15];
wire [15:0] z_outset    [0:15];
wire [15:0] z_emit      [0:15];
wire [31:0] z_dbg0_cl; wire [31:0] z_dbg0_ia; wire [31:0] z_dbg0_oa; wire [31:0] z_dbg0_ad;
wire [31:0] z_cycles    [0:15];

// ── Transit smoke-test observability (2026-07-07) ─────────────────────────────
// Z00's east bridge output, brought out so a transit fire's cross-border hop is
// visible over JTAG. A fire is a single-cycle pulse but JTAG readback is slow,
// so latch "east bridge asserted since reset" + the data/addr seen, into ISSP-
// readable registers. The plain zone out_* probes already show the local path,
// so the pair (bridge_e latched vs local seen) is the on-die transit verdict.
wire [NUM_BRIDGES-1:0]    z00_bre_v;
wire [NUM_BRIDGES*16-1:0] z00_bre_a;
wire [NUM_BRIDGES*32-1:0] z00_bre_d;
reg        bre_seen   = 1'b0;   // sticky: east bridge asserted at least once
reg [15:0] bre_addr_r = 16'h0;  // last east-bridge address
reg [31:0] bre_data_r = 32'h0;  // last east-bridge data

// Four-cardinal completion (2026-07-10, PLAN near-term Step 1): EAST was the
// only direction ever wired to observable capture. North needs a new named
// wire (bridge_n_out_* was previously left unconnected); South and West reuse
// the existing bv_v[0]/bh_v[0][0] wires the z00 instance already drives (they
// went nowhere useful in this single-zone build -- now they also feed capture).
wire [NUM_BRIDGES-1:0]    z00_brn_v;
wire [NUM_BRIDGES*16-1:0] z00_brn_a;
wire [NUM_BRIDGES*32-1:0] z00_brn_d;
reg        brn_seen   = 1'b0;
reg [15:0] brn_addr_r = 16'h0;
reg [31:0] brn_data_r = 32'h0;

reg        brs_seen   = 1'b0;
reg [15:0] brs_addr_r = 16'h0;
reg [31:0] brs_data_r = 32'h0;

reg        brw_seen   = 1'b0;
reg [15:0] brw_addr_r = 16'h0;
reg [31:0] brw_data_r = 32'h0;

// Local cluster bus sticky capture (2026-07-08). THIS is the signal the transit
// flag suppresses. out_valid (the outbound path) always fires so the value can
// reach the bridges, so out_seen can NOT prove suppression -- only this can.
//   transit=1 correct  => lbus_seen stays 0 (local untouched), bre_seen=1
//   transit=0 control  => lbus_seen=1 AND bre_seen=1
wire        z00_lbus_v;
wire [15:0] z00_lbus_a;
wire [31:0] z00_lbus_d;
reg        lbus_seen   = 1'b0;
reg [15:0] lbus_addr_r = 16'h0;
reg [31:0] lbus_data_r = 32'h0;
always @(posedge CLK) begin
    if (rst_all) begin
        lbus_seen <= 1'b0; lbus_addr_r <= 16'h0; lbus_data_r <= 32'h0;
    end else if (z00_lbus_v) begin
        lbus_seen   <= 1'b1;
        lbus_addr_r <= z00_lbus_a;
        lbus_data_r <= z00_lbus_d;
    end
end
always @(posedge CLK) begin
    if (rst_all) begin
        bre_seen <= 1'b0; bre_addr_r <= 16'h0; bre_data_r <= 32'h0;
    end else if (z00_bre_v[0]) begin
        bre_seen   <= 1'b1;
        bre_addr_r <= z00_bre_a[15:0];
        bre_data_r <= z00_bre_d[31:0];
    end
end
always @(posedge CLK) begin
    if (rst_all) begin
        brn_seen <= 1'b0; brn_addr_r <= 16'h0; brn_data_r <= 32'h0;
    end else if (z00_brn_v[0]) begin
        brn_seen   <= 1'b1;
        brn_addr_r <= z00_brn_a[15:0];
        brn_data_r <= z00_brn_d[31:0];
    end
end
always @(posedge CLK) begin
    if (rst_all) begin
        brs_seen <= 1'b0; brs_addr_r <= 16'h0; brs_data_r <= 32'h0;
    end else if (bv_v[0][0]) begin
        brs_seen   <= 1'b1;
        brs_addr_r <= bv_a[0][15:0];
        brs_data_r <= bv_d[0][31:0];
    end
end
always @(posedge CLK) begin
    if (rst_all) begin
        brw_seen <= 1'b0; brw_addr_r <= 16'h0; brw_data_r <= 32'h0;
    end else if (bh_v[0][0][0]) begin
        brw_seen   <= 1'b1;
        brw_addr_r <= bh_a[0][0][15:0];
        brw_data_r <= bh_d[0][0][31:0];
    end
end

// ── Bridge wires ──────────────────────────────────────────────────────────────
// Horizontal: between zone[r*8+c] east ↔ zone[r*8+c+1] west, r=0..1, c=0..6
// bh[r][c] carries east output of col c into west input of col c+1
wire [NUM_BRIDGES-1:0]    bh_v [0:1][0:6];
wire [NUM_BRIDGES*16-1:0] bh_a [0:1][0:6];
wire [NUM_BRIDGES*32-1:0] bh_d [0:1][0:6];

// Vertical: between zone[c] south ↔ zone[8+c] north, c=0..7
// bv[c] carries south output of row 0 into north input of row 1
wire [NUM_BRIDGES-1:0]    bv_v [0:7];
wire [NUM_BRIDGES*16-1:0] bv_a [0:7];
wire [NUM_BRIDGES*32-1:0] bv_d [0:7];

// Tie-off constants for unused bridge inputs
wire [NUM_BRIDGES-1:0]    tie_v  = {NUM_BRIDGES{1'b0}};
wire [NUM_BRIDGES*16-1:0] tie_a  = {(NUM_BRIDGES*16){1'b0}};
wire [NUM_BRIDGES*32-1:0] tie_d  = {(NUM_BRIDGES*32){1'b0}};

// ── Zone macro — reduces repetition ───────────────────────────────────────────
// 16 explicit instantiations: row 0 (Z00-Z07) then row 1 (Z08-Z15)
// Bridge connectivity:
//   Row 0: no north input  (tie), south output → bv[c]
//   Row 1: north input ← bv[c], no south output (tie outputs unused)
//   Col 0: no west input   (tie), east output → bh[r][0]
//   Col 7: east input ← bh[r][6], no east output (tie outputs unused)

// ── Row 0 ─────────────────────────────────────────────────────────────────────

// Z00  (r=0, c=0)  corners: no N, south→bv[0], no W, east→bh[0][0]
unicell_zone64_v3 #(.NUM_CELLS(NUM_CELLS),.NUM_BRIDGES(NUM_BRIDGES),.ZONE_ID(0),.DEBUG_SELECT(1)) z00 (
    .clk(CLK),.rst(rst_all),
    .cmd_bus(cpu_bus),.cmd_data(cpu_data),.cmd_valid(cmd_valid_w),
    .cpu_addr(cpu_addr_w),.cpu_data(cpu_data),.cpu_valid(cpu_valid),
    .out_addr(z_out_addr[0]),.out_data(z_out_data[0]),.out_valid(z_out_valid[0]),
    .armed_count(z_armed[0]),.arrived_count(z_arrived[0]),.output_set_count(z_outset[0]),.emit_count(z_emit[0]),.dbg0_cmd_latch(z_dbg0_cl),.dbg0_input_addr(z_dbg0_ia),.dbg0_output_addr(z_dbg0_oa),.dbg0_a_data(z_dbg0_ad),.cycle_count(z_cycles[0]),
    .bridge_n_in_valid(tie_v),.bridge_n_in_addr(tie_a),.bridge_n_in_data(tie_d),
    .bridge_n_out_valid(z00_brn_v),.bridge_n_out_addr(z00_brn_a),.bridge_n_out_data(z00_brn_d),
    .bridge_s_in_valid(tie_v),.bridge_s_in_addr(tie_a),.bridge_s_in_data(tie_d),
    .bridge_s_out_valid(bv_v[0]),.bridge_s_out_addr(bv_a[0]),.bridge_s_out_data(bv_d[0]),
    .bridge_e_in_valid(tie_v),.bridge_e_in_addr(tie_a),.bridge_e_in_data(tie_d),
    .bridge_e_out_valid(z00_bre_v),.bridge_e_out_addr(z00_bre_a),.bridge_e_out_data(z00_bre_d),
    .obs_bus_valid(z00_lbus_v),.obs_bus_addr(z00_lbus_a),.obs_bus_data(z00_lbus_d),
    .bridge_w_in_valid(tie_v),.bridge_w_in_addr(tie_a),.bridge_w_in_data(tie_d),
    .bridge_w_out_valid(bh_v[0][0]),.bridge_w_out_addr(bh_a[0][0]),.bridge_w_out_data(bh_d[0][0])
);

// ── (single-zone build: zones Z01..Z15 removed; only Z00 active) ──

// ── Output collection — priority encoder, Z0 highest ──────────────────────────
reg [15:0] out_addr_r;
reg [31:0] out_data_r;
reg        out_valid_r;
reg [15:0] total_armed;
reg [15:0] total_arrived;
reg [15:0] total_outset;
reg [15:0] total_emit;

integer i;
always @(*) begin
    out_addr_r  = 16'h0;
    out_data_r  = 32'h0;
    out_valid_r = 1'b0;
    total_armed = 16'h0; total_arrived = 16'h0; total_outset = 16'h0; total_emit = 16'h0;
    for (i = 0; i >= 0; i = i - 1) begin
        if (z_out_valid[i]) begin
            out_addr_r  = z_out_addr[i];
            out_data_r  = z_out_data[i];
            out_valid_r = 1'b1;
        end
        total_armed = total_armed + z_armed[i]; total_arrived = total_arrived + z_arrived[i]; total_outset = total_outset + z_outset[i]; total_emit = total_emit + z_emit[i];
    end
end

// ── UART bridge ───────────────────────────────────────────────────────────────
// uart_rx tied to constant idle-high (1'b1), NOT the UART_RX pin.
// UART_RX has never had a .qsf pin/pull-up assignment in this project's
// history, so on silicon it is a floating input: the RX state machine
// treats any low-going glitch as a start bit and will eventually decode
// noise into a spurious 9-byte UART_INJECT frame, asserting cpu_valid with
// garbage on cpu_bus/cpu_data. Since cpu_valid = j_valid | p_valid | u_valid,
// that trample reaches every master, not just UART -- prime suspect for the
// 2026-07-27 finding that the fabric silently ignores commands over BOTH
// JTAG and PCIe. No real UART hardware exists yet, so parking this input
// at a defined idle level removes the hazard by construction. Revert this
// tie-off (reconnect UART_RX, add a .qsf pin + WEAK_PULL_UP_RESISTOR ON)
// when real UART hardware is actually wired up.
uart_bridge #(
    .CLK_FREQ  (25_000_000),
    .BAUD_RATE (115_200)
) bridge (
    .clk         (CLK),
    .rst         (rst),
    .uart_rx     (1'b1),
    .uart_tx     (UART_TX),
    .cpu_bus     (u_bus),
    .cpu_data    (u_data),
    .cpu_valid   (u_valid),
    .array_rst   (array_rst_req),
    .array_freeze(),
    .out_addr    (out_addr_r),
    .out_data    (out_data_r),
    .out_valid   (out_valid_r),
    .armed_count (total_armed),
    .cycle_count (z_cycles[0])
);

// ── ISSP (JTAG) host bridge — In-System Sources & Probes test channel ─────────
// Second command-bus master, driven from quartus_stp over the USB-Blaster.
// Requires the `issp` IP (source width 66, probe width 113, source clock = CLK)
// and unicell_issp_bridge.v added to the project.
unicell_issp_bridge issp_host (
    .clk         (CLK),
    .rst         (rst_all),
    .cpu_bus_o   (j_bus),
    .cpu_data_o  (j_data),
    .cpu_valid_o (j_valid),
    .out_addr    (out_addr_r),
    .out_data    (out_data_r),
    .out_valid   (out_valid_r),
    .armed_count (total_armed),
    .arrived_count   (total_arrived),
    .output_set_count(total_outset),
    .emit_count      (total_emit),
    .dbg0_cmd_latch  (z_dbg0_cl),
    .dbg0_input_addr (z_dbg0_ia),
    .dbg0_output_addr(z_dbg0_oa),
    .dbg0_a_data     (z_dbg0_ad),
    .cycle_count (z_cycles[0]),
    .bre_seen    (bre_seen),
    .bre_addr    (bre_addr_r),
    .bre_data    (bre_data_r),
    .lbus_seen   (lbus_seen),
    .lbus_addr   (lbus_addr_r),
    .lbus_data   (lbus_data_r),
    .brn_seen    (brn_seen),
    .brn_addr    (brn_addr_r),
    .brn_data    (brn_data_r),
    .brs_seen    (brs_seen),
    .brs_addr    (brs_addr_r),
    .brs_data    (brs_data_r),
    .brw_seen    (brw_seen),
    .brw_addr    (brw_addr_r),
    .brw_data    (brw_data_r)
);

// ── PCIe bridge — third command-bus master, driven from the PCIe Hard IP ────
// (via pcie_hip_wrapper.v, which combines pcie_a10_hip_0 and pio_bridge_0 --
// see that file's own header for why two components, and pcie/pcie_unicell_
// bridge.v's header for why the interface is 16-bit address/32-bit data,
// narrower than this project's first assumption). Both pcie_hip_wrapper.v
// and the updated pcie_unicell_bridge.v are sim-verified against real,
// auto-parsed component port lists (points.md #44 follow-up) -- this is the
// first real, non-placeholder PCIe connection in this top-level.
wire [15:0]  hip_rxm_address;
wire [3:0]   hip_rxm_byteenable;
wire [31:0]  hip_rxm_writedata;
wire         hip_rxm_write;
wire         hip_rxm_read;
wire [31:0]  hip_rxm_readdata;
wire         hip_rxm_readdatavalid;
wire         hip_rxm_waitrequest;

pcie_hip_wrapper pcie_hip (
    .refclk       (pcie_refclk),
    .npor         (pcie_npor),
    .pin_perst    (pcie_perst_n),
    .pcie_rx_p    (pcie_rx_p),
    .pcie_tx_p    (pcie_tx_p),

    // Fabric clock/reset -- needed now that pcie_hip_wrapper instantiates
    // pcie_cdc_bridge internally (points.md #46's flagged CDC gap,
    // resolved). rxm_* below is already correctly synchronized to CLK by
    // the time it reaches pcie_unicell_bridge -- no change needed there.
    .slow_clk     (CLK),
    .slow_rst     (rst_all),

    .app_clk      (),   // TODO: consider driving fabric timing from this once PCIe is proven,
    .app_rst      (),   // rather than the current CLK_100M-derived clk_div -- not changed yet,
                         // deliberately out of scope for "get PCIe confirmed working" first pass

    .rxm_address      (hip_rxm_address),
    .rxm_byteenable   (hip_rxm_byteenable),
    .rxm_writedata    (hip_rxm_writedata),
    .rxm_write        (hip_rxm_write),
    .rxm_read         (hip_rxm_read),
    .rxm_readdata     (hip_rxm_readdata),
    .rxm_readdatavalid(hip_rxm_readdatavalid),
    .rxm_waitrequest  (hip_rxm_waitrequest)
);

pcie_unicell_bridge pcie_host (
    .clk         (CLK),
    .rst         (rst_all),

    .avs_address    (hip_rxm_address),
    .avs_byteenable (hip_rxm_byteenable),
    .avs_writedata  (hip_rxm_writedata),
    .avs_write      (hip_rxm_write),
    .avs_read       (hip_rxm_read),
    .avs_burstcount (6'h0),   // pio_bridge_0 never drives burstcount at all -- tied constant
    .avs_readdata   (hip_rxm_readdata),
    .avs_readdatavalid(hip_rxm_readdatavalid),
    .avs_waitrequest  (hip_rxm_waitrequest),

    .cpu_bus     (p_bus),
    .cpu_data    (p_data),
    .cpu_valid   (p_valid),

    .out_addr    (out_addr_r),
    .out_data    (out_data_r),
    .out_valid   (out_valid_r)
);

// ── Status LEDs ───────────────────────────────────────────────────────────────
reg led0_r    = 1'b1;
reg led1_r    = 1'b0;
reg [23:0] hb = 24'h0;

always @(posedge CLK) begin
    led0_r <= (total_armed == 0);
    hb     <= hb + 1'b1;
    led1_r <= hb[21];   // ~12Hz blink at 25MHz
end

assign LED0_N = led0_r;
assign LED1_N = ~led1_r;

endmodule
