// top_kintex7_zones.v — Kintex-7 top with zone-based timing partitioning
// Protocol v2.3
//
// Zone layout (linear chain, expandable to 2D grid):
//
//   [Zone 0] ──4 bridges──► [Zone 1] ──4 bridges──► [Zone 2] ── ...
//      50 cells                50 cells                50 cells
//
// Each zone is a Pblock region in XDC — independently routed,
// independently timed. Bridge signals are registered at zone boundaries
// giving exactly 1 tick of latency per zone crossing.
//
// To add more zones: instantiate another unicell_zone and wire bridges.
// The pattern is identical for every zone — just change ZONE_ID.
//
// Current config: 2 zones = 100 cells (matches existing tested build)
// Expand to: 10 zones = 500 cells, 20 zones = 1000 cells
//
// XDC Pblock constraints (add to constraints/kintex7.xdc):
//   create_pblock pblock_zone0
//   add_cells_to_pblock pblock_zone0 [get_cells zone0]
//   resize_pblock pblock_zone0 -add SLICE_X0Y0:SLICE_X49Y49
//
//   create_pblock pblock_zone1
//   add_cells_to_pblock pblock_zone1 [get_cells zone1]
//   resize_pblock pblock_zone1 -add SLICE_X50Y0:SLICE_X99Y49

`default_nettype none
`timescale 1ns / 1ps

module top #(
    parameter NUM_ZONES   = 2,     // start with 2, expand freely
    parameter CELLS_PER_ZONE = 50, // 50 cells per zone = clean timing
    parameter NUM_BRIDGES = 4      // 4 bridges per direction
) (
    // PCIe / XDMA interface (from Xilinx IP)
    input  wire        pcie_clk,
    input  wire        pcie_rst_n,

    // AXI-Lite from XDMA (simplified — expand for full XDMA)
    input  wire        axi_clk,
    input  wire        axi_rst_n,
    input  wire [31:0] axi_araddr,
    input  wire        axi_arvalid,
    output wire        axi_arready,
    output wire [31:0] axi_rdata,
    output wire        axi_rvalid,
    input  wire        axi_rready,
    input  wire [31:0] axi_awaddr,
    input  wire        axi_awvalid,
    output wire        axi_awready,
    input  wire [31:0] axi_wdata,
    input  wire        axi_wvalid,
    output wire        axi_wready,

    // LEDs
    output wire [2:0]  led
);

wire clk = axi_clk;
wire rst = ~axi_rst_n;

// ── Command bus (broadcast to all zones) ──────────────────────────────────
wire [31:0] cmd_bus;
wire [31:0] cmd_data;
wire        cmd_valid;
wire [15:0] cpu_addr;
wire [31:0] cpu_data_w;
wire        cpu_valid;

// ── Fired cell outputs (from all zones, collected) ─────────────────────────
wire [15:0] z0_out_addr, z1_out_addr;
wire [31:0] z0_out_data, z1_out_data;
wire        z0_out_valid, z1_out_valid;

// ── Bridge wiring between zones ───────────────────────────────────────────
// Zone 0 east ──► Zone 1 west   (zone 0 fires to zone 1)
// Zone 1 west ──► Zone 0 east   (zone 1 fires back to zone 0)
// North/South unused in linear chain — tie off

wire [NUM_BRIDGES-1:0]    z0_east_out_valid,  z1_west_in_valid;
wire [NUM_BRIDGES*16-1:0] z0_east_out_addr,   z1_west_in_addr;
wire [NUM_BRIDGES*32-1:0] z0_east_out_data,   z1_west_in_data;

wire [NUM_BRIDGES-1:0]    z1_west_out_valid,  z0_east_in_valid;
wire [NUM_BRIDGES*16-1:0] z1_west_out_addr,   z0_east_in_addr;
wire [NUM_BRIDGES*32-1:0] z1_west_out_data,   z0_east_in_data;

assign z1_west_in_valid = z0_east_out_valid;
assign z1_west_in_addr  = z0_east_out_addr;
assign z1_west_in_data  = z0_east_out_data;

assign z0_east_in_valid = z1_west_out_valid;
assign z0_east_in_addr  = z1_west_out_addr;
assign z0_east_in_data  = z1_west_out_data;

// Unused bridge directions tied off
wire [NUM_BRIDGES-1:0]    tie_valid = {NUM_BRIDGES{1'b0}};
wire [NUM_BRIDGES*16-1:0] tie_addr  = {NUM_BRIDGES*16{1'b0}};
wire [NUM_BRIDGES*32-1:0] tie_data  = {NUM_BRIDGES*32{1'b0}};

// ── Zone 0 ────────────────────────────────────────────────────────────────
unicell_zone #(
    .NUM_CELLS   (CELLS_PER_ZONE),
    .NUM_BRIDGES (NUM_BRIDGES),
    .ZONE_ID     (0)
) zone0 (
    .clk          (clk),
    .rst          (rst),
    .cmd_bus      (cmd_bus),
    .cmd_data     (cmd_data),
    .cmd_valid    (cmd_valid),
    .cpu_addr     (cpu_addr),
    .cpu_data     (cpu_data_w),
    .cpu_valid    (cpu_valid),
    .out_addr     (z0_out_addr),
    .out_data     (z0_out_data),
    .out_valid    (z0_out_valid),
    .armed_count  (),
    .cycle_count  (),
    // North/South unused
    .bridge_north_in_valid (tie_valid), .bridge_north_in_addr (tie_addr), .bridge_north_in_data (tie_data),
    .bridge_north_out_valid(), .bridge_north_out_addr(), .bridge_north_out_data(),
    .bridge_south_in_valid (tie_valid), .bridge_south_in_addr (tie_addr), .bridge_south_in_data (tie_data),
    .bridge_south_out_valid(), .bridge_south_out_addr(), .bridge_south_out_data(),
    // East → Zone 1
    .bridge_east_in_valid  (z0_east_in_valid),
    .bridge_east_in_addr   (z0_east_in_addr),
    .bridge_east_in_data   (z0_east_in_data),
    .bridge_east_out_valid (z0_east_out_valid),
    .bridge_east_out_addr  (z0_east_out_addr),
    .bridge_east_out_data  (z0_east_out_data),
    // West unused (zone 0 is leftmost)
    .bridge_west_in_valid  (tie_valid), .bridge_west_in_addr (tie_addr), .bridge_west_in_data (tie_data),
    .bridge_west_out_valid(), .bridge_west_out_addr(), .bridge_west_out_data()
);

// ── Zone 1 ────────────────────────────────────────────────────────────────
unicell_zone #(
    .NUM_CELLS   (CELLS_PER_ZONE),
    .NUM_BRIDGES (NUM_BRIDGES),
    .ZONE_ID     (1)
) zone1 (
    .clk          (clk),
    .rst          (rst),
    .cmd_bus      (cmd_bus),
    .cmd_data     (cmd_data),
    .cmd_valid    (cmd_valid),
    .cpu_addr     (cpu_addr),
    .cpu_data     (cpu_data_w),
    .cpu_valid    (cpu_valid),
    .out_addr     (z1_out_addr),
    .out_data     (z1_out_data),
    .out_valid    (z1_out_valid),
    .armed_count  (),
    .cycle_count  (),
    // North/South unused
    .bridge_north_in_valid (tie_valid), .bridge_north_in_addr (tie_addr), .bridge_north_in_data (tie_data),
    .bridge_north_out_valid(), .bridge_north_out_addr(), .bridge_north_out_data(),
    .bridge_south_in_valid (tie_valid), .bridge_south_in_addr (tie_addr), .bridge_south_in_data (tie_data),
    .bridge_south_out_valid(), .bridge_south_out_addr(), .bridge_south_out_data(),
    // West ← Zone 0
    .bridge_west_in_valid  (z1_west_in_valid),
    .bridge_west_in_addr   (z1_west_in_addr),
    .bridge_west_in_data   (z1_west_in_data),
    .bridge_west_out_valid (z1_west_out_valid),
    .bridge_west_out_addr  (z1_west_out_addr),
    .bridge_west_out_data  (z1_west_out_data),
    // East unused (zone 1 is rightmost in 2-zone config)
    .bridge_east_in_valid  (tie_valid), .bridge_east_in_addr (tie_addr), .bridge_east_in_data (tie_data),
    .bridge_east_out_valid(), .bridge_east_out_addr(), .bridge_east_out_data()
);

// ── AXI-Lite bridge → cmd_bus + data bus ──────────────────────────────────
// Placeholder — expand with full XDMA AXI bridge
// For now: simple register map at BAR0
axi_unicell_bridge #(
    .CELL_STRIDE (32)
) axib (
    .clk        (clk),
    .rst        (rst),
    .axi_araddr (axi_araddr), .axi_arvalid (axi_arvalid), .axi_arready (axi_arready),
    .axi_rdata  (axi_rdata),  .axi_rvalid  (axi_rvalid),  .axi_rready  (axi_rready),
    .axi_awaddr (axi_awaddr), .axi_awvalid (axi_awvalid), .axi_awready (axi_awready),
    .axi_wdata  (axi_wdata),  .axi_wvalid  (axi_wvalid),  .axi_wready  (axi_wready),
    .cmd_bus    (cmd_bus),
    .cmd_data   (cmd_data),
    .cmd_valid  (cmd_valid),
    .cpu_addr   (cpu_addr),
    .cpu_data   (cpu_data_w),
    .cpu_valid  (cpu_valid),
    // Fired output from both zones (zone 0 priority, zone 1 secondary)
    .out_addr   (z0_out_valid ? z0_out_addr : z1_out_addr),
    .out_data   (z0_out_valid ? z0_out_data : z1_out_data),
    .out_valid  (z0_out_valid | z1_out_valid)
);

// LEDs — zone 0 armed indicator
assign led[0] = z0_out_valid;
assign led[1] = z1_out_valid;
assign led[2] = ~rst;

endmodule
