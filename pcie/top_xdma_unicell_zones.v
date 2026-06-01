// top_xdma_unicell_zones.v — XDMA + AXI-Lite Bridge + 16-Zone UniCell Grid
//
// Top-level for YPCB-00338-1P1 (xc7k480tffg1156-2).
//
// Instantiates:
//   1. XDMA IP (PCIe x8 Gen1, BAR0 AXI-Lite)
//   2. axi_unicell_bridge — AXI-Lite → UniCell bus
//   3. 16 unicell_zone instances in a 2×8 grid (448 cells total)
//      Each zone: 28 cells, CONTAIN_ROUTING, 125 MHz
//      Zones connected E/W within rows, N/S between rows via 2 bridges each
//
// Host interface:
//   Linux: xdma.ko / /dev/xdma0_user (BAR0 MMIO)
//   Python: unicell_tool.py (mmap BAR0)
//
// PCIe:  x8 Gen1, GTX X0Y16-X0Y23, refclk J8, perst Y26
// Clock: 50 MHz SYS_CLK (AA28) → XDMA MMCM → 125 MHz user_clk
// LEDs:  P30=heartbeat, M30=PCIe link up, N30=any cell fired

`default_nettype none
`timescale 1ns / 1ps

module top_xdma_unicell_zones (
    // System
    input  wire        SYS_CLK,        // 50 MHz (AA28)
    input  wire        SYS_RSTN,       // Active low (R28)

    // PCIe
    input  wire        pcie_perstn,    // PCIe reset (Y26, active low)
    input  wire        pcie_refclk_p,  // 100 MHz refclk (J8)
    input  wire        pcie_refclk_n,
    input  wire  [7:0] pcie_rx_p,
    input  wire  [7:0] pcie_rx_n,
    output wire  [7:0] pcie_tx_p,
    output wire  [7:0] pcie_tx_n,

    // LEDs (active high, LVCMOS18)
    output wire        led0,           // heartbeat (cycle_count blink)
    output wire        led1,           // PCIe link up
    output wire        led2            // any cell fired
);

// ── Clocks and reset ──────────────────────────────────────────────────────
wire user_clk;      // 125 MHz from XDMA MMCM
wire user_resetn;   // active low, synchronised to user_clk
wire user_lnk_up;  // PCIe link status

// PCIe refclk buffer — XDMA requires IBUFDS_GTE2 output
wire pcie_refclk_buf;
IBUFDS_GTE2 refclk_ibuf (
    .I    (pcie_refclk_p),
    .IB   (pcie_refclk_n),
    .CEB  (1'b0),
    .O    (pcie_refclk_buf),
    .ODIV2()
);

// ── AXI-Lite interface (XDMA → bridge) ───────────────────────────────────
wire [31:0] m_axil_awaddr;
wire        m_axil_awvalid;
wire        m_axil_awready;
wire [31:0] m_axil_wdata;
wire  [3:0] m_axil_wstrb;
wire        m_axil_wvalid;
wire        m_axil_wready;
wire  [1:0] m_axil_bresp;
wire        m_axil_bvalid;
wire        m_axil_bready;
wire [31:0] m_axil_araddr;
wire        m_axil_arvalid;
wire        m_axil_arready;
wire [31:0] m_axil_rdata;
wire  [1:0] m_axil_rresp;
wire        m_axil_rvalid;
wire        m_axil_rready;

// ── UniCell bus signals (raw from bridge) ─────────────────────────────────
wire  [7:0] cpu_cmd_raw;
wire [15:0] cpu_addr_raw;
wire [31:0] cpu_data_raw;
wire        cpu_valid_raw;
wire        array_rst_raw;
wire [15:0] bus_addr_raw;
wire [31:0] bus_data_raw;
wire        bus_valid_raw;

// Pipeline register — breaks high-fanout on cpu_cmd, closes timing at 125 MHz
reg  [7:0]  cpu_cmd;
reg  [15:0] cpu_addr;
reg  [31:0] cpu_data;
reg         cpu_valid;
reg         array_rst;
reg         cmd_valid_w;

always @(posedge user_clk) begin
    cpu_cmd     <= cpu_cmd_raw;
    cpu_addr    <= cpu_addr_raw;
    cpu_data    <= cpu_data_raw;
    cpu_valid   <= cpu_valid_raw;
    array_rst   <= array_rst_raw;
    cmd_valid_w <= cpu_valid_raw && (cpu_cmd_raw != 8'd0) && (cpu_cmd_raw != 8'd1);
end

// ── Array output signals ──────────────────────────────────────────────────
wire [15:0] out_addr;
wire [31:0] out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

// ── XDMA IP ───────────────────────────────────────────────────────────────
xdma_0 xdma_inst (
    .sys_clk                (pcie_refclk_buf),
    .sys_rst_n              (SYS_RSTN & pcie_perstn),

    .pci_exp_rxn            (pcie_rx_n),
    .pci_exp_rxp            (pcie_rx_p),
    .pci_exp_txn            (pcie_tx_n),
    .pci_exp_txp            (pcie_tx_p),

    .axi_aclk               (user_clk),
    .axi_aresetn            (user_resetn),
    .user_lnk_up            (user_lnk_up),

    // AXI4 memory (unused — tie off)
    .m_axi_awready          (1'b0),
    .m_axi_wready           (1'b0),
    .m_axi_bid              (4'h0),
    .m_axi_bresp            (2'b0),
    .m_axi_bvalid           (1'b0),
    .m_axi_arready          (1'b0),
    .m_axi_rid              (4'h0),
    .m_axi_rdata            (64'h0),
    .m_axi_rresp            (2'b0),
    .m_axi_rlast            (1'b0),
    .m_axi_rvalid           (1'b0),

    // AXI-Lite master (BAR0)
    .m_axil_awaddr          (m_axil_awaddr),
    .m_axil_awvalid         (m_axil_awvalid),
    .m_axil_awready         (m_axil_awready),
    .m_axil_wdata           (m_axil_wdata),
    .m_axil_wstrb           (m_axil_wstrb),
    .m_axil_wvalid          (m_axil_wvalid),
    .m_axil_wready          (m_axil_wready),
    .m_axil_bresp           (m_axil_bresp),
    .m_axil_bvalid          (m_axil_bvalid),
    .m_axil_bready          (m_axil_bready),
    .m_axil_araddr          (m_axil_araddr),
    .m_axil_arvalid         (m_axil_arvalid),
    .m_axil_arready         (m_axil_arready),
    .m_axil_rdata           (m_axil_rdata),
    .m_axil_rresp           (m_axil_rresp),
    .m_axil_rvalid          (m_axil_rvalid),
    .m_axil_rready          (m_axil_rready)
);

// ── AXI-Lite → UniCell bridge ─────────────────────────────────────────────
// NUM_CELLS=448: 16 zones × 28 cells each
axi_unicell_bridge #(
    .NUM_CELLS  (448),
    .CELL_STRIDE(32)
) bridge (
    .aclk           (user_clk),
    .aresetn        (user_resetn),

    .s_axil_awaddr  (m_axil_awaddr),
    .s_axil_awvalid (m_axil_awvalid),
    .s_axil_awready (m_axil_awready),
    .s_axil_wdata   (m_axil_wdata),
    .s_axil_wstrb   (m_axil_wstrb),
    .s_axil_wvalid  (m_axil_wvalid),
    .s_axil_wready  (m_axil_wready),
    .s_axil_bresp   (m_axil_bresp),
    .s_axil_bvalid  (m_axil_bvalid),
    .s_axil_bready  (m_axil_bready),
    .s_axil_araddr  (m_axil_araddr),
    .s_axil_arvalid (m_axil_arvalid),
    .s_axil_arready (m_axil_arready),
    .s_axil_rdata   (m_axil_rdata),
    .s_axil_rresp   (m_axil_rresp),
    .s_axil_rvalid  (m_axil_rvalid),
    .s_axil_rready  (m_axil_rready),

    .cpu_cmd        (cpu_cmd_raw),
    .cpu_addr       (cpu_addr_raw),
    .cpu_data       (cpu_data_raw),
    .cpu_valid      (cpu_valid_raw),
    .array_rst      (array_rst_raw),
    .bus_addr       (bus_addr_raw),
    .bus_data       (bus_data_raw),
    .bus_valid      (bus_valid_raw),

    .out_addr       (out_addr),
    .out_data       (out_data),
    .out_valid      (out_valid),
    .armed_count    (armed_count),
    .cycle_count    (cycle_count)
);

// ── 16-Zone grid (2×8, 28 cells/zone, 448 total) ─────────────────────────

localparam NZ = 16;
localparam NB = 2;   // bridge lanes per direction

// Per-zone outputs
wire [15:0] zo_addr  [0:NZ-1];
wire [31:0] zo_data  [0:NZ-1];
wire        zo_valid [0:NZ-1];
wire [15:0] zo_armed [0:NZ-1];
wire [31:0] zo_cycle [0:NZ-1];

// Tie-off wires for unused bridge inputs
wire [NB-1:0]        tie_v = {NB{1'b0}};
wire [NB*16-1:0]     tie_a = {(NB*16){1'b0}};
wire [NB*32-1:0]     tie_d = {(NB*32){1'b0}};

// Horizontal bridge wires — row 0
wire [NB-1:0]    bh_ev  [0:6];   // east-valid  (col → col+1)
wire [NB*16-1:0] bh_ea  [0:6];
wire [NB*32-1:0] bh_ed  [0:6];
wire [NB-1:0]    bh_wv  [0:6];   // west-valid  (col+1 → col)
wire [NB*16-1:0] bh_wa  [0:6];
wire [NB*32-1:0] bh_wd  [0:6];

// Horizontal bridge wires — row 1
wire [NB-1:0]    bh_ev1 [0:6];
wire [NB*16-1:0] bh_ea1 [0:6];
wire [NB*32-1:0] bh_ed1 [0:6];
wire [NB-1:0]    bh_wv1 [0:6];
wire [NB*16-1:0] bh_wa1 [0:6];
wire [NB*32-1:0] bh_wd1 [0:6];

// Vertical bridge wires (row 0 south ↔ row 1 north)
wire [NB-1:0]    bv_sv  [0:7];
wire [NB*16-1:0] bv_sa  [0:7];
wire [NB*32-1:0] bv_sd  [0:7];
wire [NB-1:0]    bv_nv  [0:7];
wire [NB*16-1:0] bv_na  [0:7];
wire [NB*32-1:0] bv_nd  [0:7];

// Reset = PCIe reset OR array soft-reset from host
wire rst = ~user_resetn | array_rst;

genvar c;
generate

// ── Row 0: Z00-Z07 ────────────────────────────────────────────────────────
for (c = 0; c < 8; c = c + 1) begin : row0
    unicell_zone #(.NUM_CELLS(28), .NUM_BRIDGES(NB), .ZONE_ID(c)) z (
        .clk (user_clk), .rst (rst),
        .cmd_bus   ({24'b0, cpu_cmd}),   // zero-extend 8→32
        .cmd_data  (cpu_data),
        .cmd_valid (cmd_valid_w),
        .cpu_addr  (cpu_addr),
        .cpu_data  (cpu_data),
        .cpu_valid (cpu_valid && (cpu_cmd == 8'd1)),
        .out_addr  (zo_addr[c]),  .out_data  (zo_data[c]),  .out_valid (zo_valid[c]),
        .armed_count (zo_armed[c]), .cycle_count (zo_cycle[c]),
        // North — unused (row 0, no zone above)
        .bridge_n_in_valid (tie_v), .bridge_n_in_addr (tie_a), .bridge_n_in_data (tie_d),
        .bridge_n_out_valid (), .bridge_n_out_addr (), .bridge_n_out_data (),
        // South → row 1 north
        .bridge_s_in_valid  (bv_nv[c]), .bridge_s_in_addr  (bv_na[c]), .bridge_s_in_data  (bv_nd[c]),
        .bridge_s_out_valid (bv_sv[c]), .bridge_s_out_addr (bv_sa[c]), .bridge_s_out_data (bv_sd[c]),
        // East (col 0-6 only; col 7 has no east neighbour)
        .bridge_e_in_valid  (c < 7 ? bh_wv[c]  : tie_v),
        .bridge_e_in_addr   (c < 7 ? bh_wa[c]  : tie_a),
        .bridge_e_in_data   (c < 7 ? bh_wd[c]  : tie_d),
        .bridge_e_out_valid (bh_ev[c < 7 ? c : 0]),
        .bridge_e_out_addr  (bh_ea[c < 7 ? c : 0]),
        .bridge_e_out_data  (bh_ed[c < 7 ? c : 0]),
        // West (col 1-7 only; col 0 has no west neighbour)
        .bridge_w_in_valid  (c > 0 ? bh_ev[c-1] : tie_v),
        .bridge_w_in_addr   (c > 0 ? bh_ea[c-1] : tie_a),
        .bridge_w_in_data   (c > 0 ? bh_ed[c-1] : tie_d),
        .bridge_w_out_valid (bh_wv[c > 0 ? c-1 : 0]),
        .bridge_w_out_addr  (bh_wa[c > 0 ? c-1 : 0]),
        .bridge_w_out_data  (bh_wd[c > 0 ? c-1 : 0])
    );
end

// ── Row 1: Z08-Z15 ────────────────────────────────────────────────────────
for (c = 0; c < 8; c = c + 1) begin : row1
    unicell_zone #(.NUM_CELLS(28), .NUM_BRIDGES(NB), .ZONE_ID(c+8)) z (
        .clk (user_clk), .rst (rst),
        .cmd_bus   ({24'b0, cpu_cmd}),
        .cmd_data  (cpu_data),
        .cmd_valid (cmd_valid_w),
        .cpu_addr  (cpu_addr),
        .cpu_data  (cpu_data),
        .cpu_valid (cpu_valid && (cpu_cmd == 8'd1)),
        .out_addr  (zo_addr[c+8]), .out_data  (zo_data[c+8]), .out_valid (zo_valid[c+8]),
        .armed_count (zo_armed[c+8]), .cycle_count (zo_cycle[c+8]),
        // North ← row 0 south
        .bridge_n_in_valid  (bv_sv[c]), .bridge_n_in_addr  (bv_sa[c]), .bridge_n_in_data  (bv_sd[c]),
        .bridge_n_out_valid (bv_nv[c]), .bridge_n_out_addr (bv_na[c]), .bridge_n_out_data (bv_nd[c]),
        // South — unused (row 1, no zone below)
        .bridge_s_in_valid (tie_v), .bridge_s_in_addr (tie_a), .bridge_s_in_data (tie_d),
        .bridge_s_out_valid (), .bridge_s_out_addr (), .bridge_s_out_data (),
        // East
        .bridge_e_in_valid  (c < 7 ? bh_wv1[c]  : tie_v),
        .bridge_e_in_addr   (c < 7 ? bh_wa1[c]  : tie_a),
        .bridge_e_in_data   (c < 7 ? bh_wd1[c]  : tie_d),
        .bridge_e_out_valid (bh_ev1[c < 7 ? c : 0]),
        .bridge_e_out_addr  (bh_ea1[c < 7 ? c : 0]),
        .bridge_e_out_data  (bh_ed1[c < 7 ? c : 0]),
        // West
        .bridge_w_in_valid  (c > 0 ? bh_ev1[c-1] : tie_v),
        .bridge_w_in_addr   (c > 0 ? bh_ea1[c-1] : tie_a),
        .bridge_w_in_data   (c > 0 ? bh_ed1[c-1] : tie_d),
        .bridge_w_out_valid (bh_wv1[c > 0 ? c-1 : 0]),
        .bridge_w_out_addr  (bh_wa1[c > 0 ? c-1 : 0]),
        .bridge_w_out_data  (bh_wd1[c > 0 ? c-1 : 0])
    );
end

endgenerate

// ── Output collection — priority mux across all 16 zones ─────────────────
wire any_valid = |{zo_valid[15], zo_valid[14], zo_valid[13], zo_valid[12],
                   zo_valid[11], zo_valid[10], zo_valid[9],  zo_valid[8],
                   zo_valid[7],  zo_valid[6],  zo_valid[5],  zo_valid[4],
                   zo_valid[3],  zo_valid[2],  zo_valid[1],  zo_valid[0]};

reg [3:0] win_zone = 4'h0;
integer   zi;
always @(*) begin
    win_zone = 4'h0;
    for (zi = 15; zi >= 0; zi = zi - 1)
        if (zo_valid[zi]) win_zone = zi[3:0];
end

// Route collection to bridge readback inputs
assign out_valid = any_valid;
assign out_addr  = zo_addr[win_zone];
assign out_data  = zo_data[win_zone];

assign armed_count = zo_armed[0]  + zo_armed[1]  + zo_armed[2]  + zo_armed[3]  +
                     zo_armed[4]  + zo_armed[5]  + zo_armed[6]  + zo_armed[7]  +
                     zo_armed[8]  + zo_armed[9]  + zo_armed[10] + zo_armed[11] +
                     zo_armed[12] + zo_armed[13] + zo_armed[14] + zo_armed[15];
assign cycle_count = zo_cycle[0];  // all zones share clock

// ── Status LEDs ───────────────────────────────────────────────────────────
// P30 led0: heartbeat — cycle_count bit blink so yosys can't prune array
// M30 led1: PCIe link up
// N30 led2: any cell fired this cycle
reg led0_r = 1'b0;
reg led2_r = 1'b0;
always @(posedge user_clk) begin
    led0_r <= cycle_count[24];   // ~0.8 Hz blink at 125 MHz
    led2_r <= any_valid;
end

assign led0 = led0_r;
assign led1 = user_lnk_up;
assign led2 = led2_r;

// ── STARTUPE2 — required for BPI flash access via JTAG indirect programming
STARTUPE2 #(
    .PROG_USR      ("FALSE"),
    .SIM_CCLK_FREQ (0.0)
) STARTUPE2_inst (
    .CFGCLK    (),
    .CFGMCLK   (),
    .EOS       (),
    .PREQ      (),
    .CLK       (1'b0),
    .GSR       (1'b0),
    .GTS       (1'b0),
    .KEYCLEARB (1'b1),
    .PACK      (1'b0),
    .USRCCLKO  (1'b0),
    .USRCCLKTS (1'b1),
    .USRDONEO  (1'b1),
    .USRDONETS (1'b0)
);

endmodule
