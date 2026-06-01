// top_xdma_unicell_zones.v — XDMA + AXI-Lite Bridge + 2×2 Zone Grid
//
// Top-level for YPCB-00338-1P1 (xc7k480tffg1156-2).
//
// 4 zones in a 2×2 grid, 50 cells/zone = 200 cells total
// 4 bridge lanes per side for inter-zone bandwidth
// Each zone: ~46 SLICE cols × 188 SLICE rows — ~20% LUT utilisation
//
// Grid layout:
//   [Z00]──4──[Z01]   row 0 (top,    Y189-Y377)
//     |          |
//     4          4
//     |          |
//   [Z02]──4──[Z03]   row 1 (bottom, Y0-Y188)
//
// Host: PCIe x8 Gen1, XDMA IP, BAR0 AXI-Lite → unicell bus
// Clock: 50 MHz SYS_CLK → XDMA MMCM → 125 MHz user_clk

`default_nettype none
`timescale 1ns / 1ps

module top_xdma_unicell_zones (
    input  wire        SYS_CLK,
    input  wire        SYS_RSTN,
    input  wire        pcie_perstn,
    input  wire        pcie_refclk_p,
    input  wire        pcie_refclk_n,
    input  wire  [7:0] pcie_rx_p,
    input  wire  [7:0] pcie_rx_n,
    output wire  [7:0] pcie_tx_p,
    output wire  [7:0] pcie_tx_n,
    output wire        led0,
    output wire        led1,
    output wire        led2
);

// ── Clocks and reset ──────────────────────────────────────────────────────
wire user_clk;
wire user_resetn;
wire user_lnk_up;

wire pcie_refclk_buf;
IBUFDS_GTE2 refclk_ibuf (
    .I(pcie_refclk_p), .IB(pcie_refclk_n), .CEB(1'b0),
    .O(pcie_refclk_buf), .ODIV2()
);

// ── AXI-Lite wires ────────────────────────────────────────────────────────
wire [31:0] m_axil_awaddr;  wire m_axil_awvalid; wire m_axil_awready;
wire [31:0] m_axil_wdata;   wire [3:0] m_axil_wstrb;
wire        m_axil_wvalid;  wire m_axil_wready;
wire  [1:0] m_axil_bresp;   wire m_axil_bvalid;  wire m_axil_bready;
wire [31:0] m_axil_araddr;  wire m_axil_arvalid; wire m_axil_arready;
wire [31:0] m_axil_rdata;   wire [1:0] m_axil_rresp;
wire        m_axil_rvalid;  wire m_axil_rready;

// ── UniCell bus (raw from bridge, pipelined) ──────────────────────────────
wire  [7:0] cpu_cmd_raw;  wire [15:0] cpu_addr_raw;
wire [31:0] cpu_data_raw; wire cpu_valid_raw; wire array_rst_raw;
wire [15:0] bus_addr_raw; wire [31:0] bus_data_raw; wire bus_valid_raw;

reg  [7:0]  cpu_cmd;   reg [15:0] cpu_addr;
reg [31:0]  cpu_data;  reg cpu_valid; reg array_rst; reg cmd_valid_w;

always @(posedge user_clk) begin
    cpu_cmd     <= cpu_cmd_raw;
    cpu_addr    <= cpu_addr_raw;
    cpu_data    <= cpu_data_raw;
    cpu_valid   <= cpu_valid_raw;
    array_rst   <= array_rst_raw;
    cmd_valid_w <= cpu_valid_raw && (cpu_cmd_raw != 8'd0) && (cpu_cmd_raw != 8'd1);
end

wire [15:0] out_addr;  wire [31:0] out_data;  wire out_valid;
wire [15:0] armed_count; wire [31:0] cycle_count;

// ── XDMA IP ───────────────────────────────────────────────────────────────
xdma_0 xdma_inst (
    .sys_clk(pcie_refclk_buf), .sys_rst_n(SYS_RSTN & pcie_perstn),
    .pci_exp_rxn(pcie_rx_n), .pci_exp_rxp(pcie_rx_p),
    .pci_exp_txn(pcie_tx_n), .pci_exp_txp(pcie_tx_p),
    .axi_aclk(user_clk), .axi_aresetn(user_resetn), .user_lnk_up(user_lnk_up),
    .m_axi_awready(1'b0), .m_axi_wready(1'b0), .m_axi_bid(4'h0),
    .m_axi_bresp(2'b0), .m_axi_bvalid(1'b0), .m_axi_arready(1'b0),
    .m_axi_rid(4'h0), .m_axi_rdata(64'h0), .m_axi_rresp(2'b0),
    .m_axi_rlast(1'b0), .m_axi_rvalid(1'b0),
    .m_axil_awaddr(m_axil_awaddr), .m_axil_awvalid(m_axil_awvalid), .m_axil_awready(m_axil_awready),
    .m_axil_wdata(m_axil_wdata),   .m_axil_wstrb(m_axil_wstrb),
    .m_axil_wvalid(m_axil_wvalid), .m_axil_wready(m_axil_wready),
    .m_axil_bresp(m_axil_bresp),   .m_axil_bvalid(m_axil_bvalid), .m_axil_bready(m_axil_bready),
    .m_axil_araddr(m_axil_araddr), .m_axil_arvalid(m_axil_arvalid), .m_axil_arready(m_axil_arready),
    .m_axil_rdata(m_axil_rdata),   .m_axil_rresp(m_axil_rresp),
    .m_axil_rvalid(m_axil_rvalid), .m_axil_rready(m_axil_rready)
);

// ── AXI-Lite → UniCell bridge ─────────────────────────────────────────────
axi_unicell_bridge #(.NUM_CELLS(200), .CELL_STRIDE(32)) bridge (
    .aclk(user_clk), .aresetn(user_resetn),
    .s_axil_awaddr(m_axil_awaddr), .s_axil_awvalid(m_axil_awvalid), .s_axil_awready(m_axil_awready),
    .s_axil_wdata(m_axil_wdata),   .s_axil_wstrb(m_axil_wstrb),
    .s_axil_wvalid(m_axil_wvalid), .s_axil_wready(m_axil_wready),
    .s_axil_bresp(m_axil_bresp),   .s_axil_bvalid(m_axil_bvalid), .s_axil_bready(m_axil_bready),
    .s_axil_araddr(m_axil_araddr), .s_axil_arvalid(m_axil_arvalid), .s_axil_arready(m_axil_arready),
    .s_axil_rdata(m_axil_rdata),   .s_axil_rresp(m_axil_rresp),
    .s_axil_rvalid(m_axil_rvalid), .s_axil_rready(m_axil_rready),
    .cpu_cmd(cpu_cmd_raw), .cpu_addr(cpu_addr_raw), .cpu_data(cpu_data_raw),
    .cpu_valid(cpu_valid_raw), .array_rst(array_rst_raw),
    .bus_addr(bus_addr_raw), .bus_data(bus_data_raw), .bus_valid(bus_valid_raw),
    .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
    .armed_count(armed_count), .cycle_count(cycle_count)
);

// ── 2×2 Zone grid (4 zones, 50 cells each, 4 bridge lanes per side) ───────
localparam NZ = 4;
localparam NB = 4;   // 4 bridge lanes per direction

// Per-zone outputs
wire [15:0] zo_addr  [0:3];
wire [31:0] zo_data  [0:3];
wire        zo_valid [0:3];
wire [15:0] zo_armed [0:3];
wire [31:0] zo_cycle [0:3];

// Tie-offs for unused bridge inputs
wire [NB-1:0]    tie_v = {NB{1'b0}};
wire [NB*16-1:0] tie_a = {(NB*16){1'b0}};
wire [NB*32-1:0] tie_d = {(NB*32){1'b0}};

// Horizontal bridge: Z00↔Z01 (row 0), Z02↔Z03 (row 1)
wire [NB-1:0]    h0_ev; wire [NB*16-1:0] h0_ea; wire [NB*32-1:0] h0_ed; // Z00 east → Z01 west
wire [NB-1:0]    h0_wv; wire [NB*16-1:0] h0_wa; wire [NB*32-1:0] h0_wd; // Z01 west → Z00 east
wire [NB-1:0]    h1_ev; wire [NB*16-1:0] h1_ea; wire [NB*32-1:0] h1_ed; // Z02 east → Z03 west
wire [NB-1:0]    h1_wv; wire [NB*16-1:0] h1_wa; wire [NB*32-1:0] h1_wd; // Z03 west → Z02 east

// Vertical bridge: Z00↔Z02 (col 0), Z01↔Z03 (col 1)
wire [NB-1:0]    v0_sv; wire [NB*16-1:0] v0_sa; wire [NB*32-1:0] v0_sd; // Z00 south → Z02 north
wire [NB-1:0]    v0_nv; wire [NB*16-1:0] v0_na; wire [NB*32-1:0] v0_nd; // Z02 north → Z00 south
wire [NB-1:0]    v1_sv; wire [NB*16-1:0] v1_sa; wire [NB*32-1:0] v1_sd; // Z01 south → Z03 north
wire [NB-1:0]    v1_nv; wire [NB*16-1:0] v1_na; wire [NB*32-1:0] v1_nd; // Z03 north → Z01 south

wire rst = ~user_resetn | array_rst;
wire [31:0] cmd_bus_w = {24'b0, cpu_cmd};

// ── Z00 (row0, col0) — top left ───────────────────────────────────────────
unicell_zone #(.NUM_CELLS(50), .NUM_BRIDGES(NB), .ZONE_ID(0)) z00 (
    .clk(user_clk), .rst(rst),
    .cmd_bus(cmd_bus_w), .cmd_data(cpu_data), .cmd_valid(cmd_valid_w),
    .cpu_addr(cpu_addr), .cpu_data(cpu_data), .cpu_valid(cpu_valid && (cpu_cmd == 8'd1)),
    .out_addr(zo_addr[0]), .out_data(zo_data[0]), .out_valid(zo_valid[0]),
    .armed_count(zo_armed[0]), .cycle_count(zo_cycle[0]),
    .bridge_n_in_valid(tie_v), .bridge_n_in_addr(tie_a), .bridge_n_in_data(tie_d),
    .bridge_n_out_valid(), .bridge_n_out_addr(), .bridge_n_out_data(),
    .bridge_s_in_valid(v0_nv), .bridge_s_in_addr(v0_na), .bridge_s_in_data(v0_nd),
    .bridge_s_out_valid(v0_sv), .bridge_s_out_addr(v0_sa), .bridge_s_out_data(v0_sd),
    .bridge_e_in_valid(h0_wv), .bridge_e_in_addr(h0_wa), .bridge_e_in_data(h0_wd),
    .bridge_e_out_valid(h0_ev), .bridge_e_out_addr(h0_ea), .bridge_e_out_data(h0_ed),
    .bridge_w_in_valid(tie_v), .bridge_w_in_addr(tie_a), .bridge_w_in_data(tie_d),
    .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data()
);

// ── Z01 (row0, col1) — top right ─────────────────────────────────────────
unicell_zone #(.NUM_CELLS(50), .NUM_BRIDGES(NB), .ZONE_ID(1)) z01 (
    .clk(user_clk), .rst(rst),
    .cmd_bus(cmd_bus_w), .cmd_data(cpu_data), .cmd_valid(cmd_valid_w),
    .cpu_addr(cpu_addr), .cpu_data(cpu_data), .cpu_valid(cpu_valid && (cpu_cmd == 8'd1)),
    .out_addr(zo_addr[1]), .out_data(zo_data[1]), .out_valid(zo_valid[1]),
    .armed_count(zo_armed[1]), .cycle_count(zo_cycle[1]),
    .bridge_n_in_valid(tie_v), .bridge_n_in_addr(tie_a), .bridge_n_in_data(tie_d),
    .bridge_n_out_valid(), .bridge_n_out_addr(), .bridge_n_out_data(),
    .bridge_s_in_valid(v1_nv), .bridge_s_in_addr(v1_na), .bridge_s_in_data(v1_nd),
    .bridge_s_out_valid(v1_sv), .bridge_s_out_addr(v1_sa), .bridge_s_out_data(v1_sd),
    .bridge_e_in_valid(tie_v), .bridge_e_in_addr(tie_a), .bridge_e_in_data(tie_d),
    .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
    .bridge_w_in_valid(h0_ev), .bridge_w_in_addr(h0_ea), .bridge_w_in_data(h0_ed),
    .bridge_w_out_valid(h0_wv), .bridge_w_out_addr(h0_wa), .bridge_w_out_data(h0_wd)
);

// ── Z02 (row1, col0) — bottom left ───────────────────────────────────────
unicell_zone #(.NUM_CELLS(50), .NUM_BRIDGES(NB), .ZONE_ID(2)) z02 (
    .clk(user_clk), .rst(rst),
    .cmd_bus(cmd_bus_w), .cmd_data(cpu_data), .cmd_valid(cmd_valid_w),
    .cpu_addr(cpu_addr), .cpu_data(cpu_data), .cpu_valid(cpu_valid && (cpu_cmd == 8'd1)),
    .out_addr(zo_addr[2]), .out_data(zo_data[2]), .out_valid(zo_valid[2]),
    .armed_count(zo_armed[2]), .cycle_count(zo_cycle[2]),
    .bridge_n_in_valid(v0_sv), .bridge_n_in_addr(v0_sa), .bridge_n_in_data(v0_sd),
    .bridge_n_out_valid(v0_nv), .bridge_n_out_addr(v0_na), .bridge_n_out_data(v0_nd),
    .bridge_s_in_valid(tie_v), .bridge_s_in_addr(tie_a), .bridge_s_in_data(tie_d),
    .bridge_s_out_valid(), .bridge_s_out_addr(), .bridge_s_out_data(),
    .bridge_e_in_valid(h1_wv), .bridge_e_in_addr(h1_wa), .bridge_e_in_data(h1_wd),
    .bridge_e_out_valid(h1_ev), .bridge_e_out_addr(h1_ea), .bridge_e_out_data(h1_ed),
    .bridge_w_in_valid(tie_v), .bridge_w_in_addr(tie_a), .bridge_w_in_data(tie_d),
    .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data()
);

// ── Z03 (row1, col1) — bottom right ──────────────────────────────────────
unicell_zone #(.NUM_CELLS(50), .NUM_BRIDGES(NB), .ZONE_ID(3)) z03 (
    .clk(user_clk), .rst(rst),
    .cmd_bus(cmd_bus_w), .cmd_data(cpu_data), .cmd_valid(cmd_valid_w),
    .cpu_addr(cpu_addr), .cpu_data(cpu_data), .cpu_valid(cpu_valid && (cpu_cmd == 8'd1)),
    .out_addr(zo_addr[3]), .out_data(zo_data[3]), .out_valid(zo_valid[3]),
    .armed_count(zo_armed[3]), .cycle_count(zo_cycle[3]),
    .bridge_n_in_valid(v1_sv), .bridge_n_in_addr(v1_sa), .bridge_n_in_data(v1_sd),
    .bridge_n_out_valid(v1_nv), .bridge_n_out_addr(v1_na), .bridge_n_out_data(v1_nd),
    .bridge_s_in_valid(tie_v), .bridge_s_in_addr(tie_a), .bridge_s_in_data(tie_d),
    .bridge_s_out_valid(), .bridge_s_out_addr(), .bridge_s_out_data(),
    .bridge_e_in_valid(tie_v), .bridge_e_in_addr(tie_a), .bridge_e_in_data(tie_d),
    .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
    .bridge_w_in_valid(h1_ev), .bridge_w_in_addr(h1_ea), .bridge_w_in_data(h1_ed),
    .bridge_w_out_valid(h1_wv), .bridge_w_out_addr(h1_wa), .bridge_w_out_data(h1_wd)
);

// ── Output collection — priority mux across 4 zones ──────────────────────
wire any_valid = zo_valid[0] | zo_valid[1] | zo_valid[2] | zo_valid[3];

reg [1:0] win_zone = 2'h0;
always @(*) begin
    win_zone = 2'h0;
    if (zo_valid[3]) win_zone = 2'd3;
    if (zo_valid[2]) win_zone = 2'd2;
    if (zo_valid[1]) win_zone = 2'd1;
    if (zo_valid[0]) win_zone = 2'd0;
end

assign out_valid   = any_valid;
assign out_addr    = zo_addr[win_zone];
assign out_data    = zo_data[win_zone];
assign armed_count = zo_armed[0] + zo_armed[1] + zo_armed[2] + zo_armed[3];
assign cycle_count = zo_cycle[0];

// ── LEDs ──────────────────────────────────────────────────────────────────
reg led0_r = 1'b0, led2_r = 1'b0;
always @(posedge user_clk) begin
    led0_r <= cycle_count[24];
    led2_r <= any_valid;
end
assign led0 = led0_r;
assign led1 = user_lnk_up;
assign led2 = led2_r;

// ── STARTUPE2 ─────────────────────────────────────────────────────────────
STARTUPE2 #(.PROG_USR("FALSE"), .SIM_CCLK_FREQ(0.0)) STARTUPE2_inst (
    .CFGCLK(), .CFGMCLK(), .EOS(), .PREQ(),
    .CLK(1'b0), .GSR(1'b0), .GTS(1'b0), .KEYCLEARB(1'b1),
    .PACK(1'b0), .USRCCLKO(1'b0), .USRCCLKTS(1'b1),
    .USRDONEO(1'b1), .USRDONETS(1'b0)
);

endmodule
