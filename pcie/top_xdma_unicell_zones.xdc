# top_xdma_unicell_zones.xdc
# YPCB-00338-1P1 (xc7k480tffg1156-2)
# 2×2 zone grid, 50 cells/zone, 200 cells total, ~20% LUT utilisation
#
# Die coords from first free-placement run: X0-X92, Y0-Y377
# 4 zones: 2 cols × 46 SLICE cols, 2 rows × 188 SLICE rows

# ── Clocks ────────────────────────────────────────────────────────────────
set_property PACKAGE_PIN AA28 [get_ports SYS_CLK]
set_property IOSTANDARD LVCMOS18 [get_ports SYS_CLK]
create_clock -period 20.000 -name sys_clk [get_ports SYS_CLK]
create_clock -period 10.000 -name pcie_refclk [get_ports pcie_refclk_p]

# ── Reset / PCIe ──────────────────────────────────────────────────────────
set_property PACKAGE_PIN R28 [get_ports SYS_RSTN]
set_property IOSTANDARD LVCMOS18 [get_ports SYS_RSTN]
set_property PACKAGE_PIN Y26 [get_ports pcie_perstn]
set_property IOSTANDARD LVCMOS18 [get_ports pcie_perstn]
set_property PULLUP true [get_ports pcie_perstn]

# ── LEDs ──────────────────────────────────────────────────────────────────
set_property PACKAGE_PIN P30 [get_ports led0]
set_property PACKAGE_PIN M30 [get_ports led1]
set_property PACKAGE_PIN N30 [get_ports led2]
set_property IOSTANDARD LVCMOS18 [get_ports led0]
set_property IOSTANDARD LVCMOS18 [get_ports led1]
set_property IOSTANDARD LVCMOS18 [get_ports led2]

# ── GTX LOC constraints ───────────────────────────────────────────────────
set_property LOC GTXE2_CHANNEL_X0Y23 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[0].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y22 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[1].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y21 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[2].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y20 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[3].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y19 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[4].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y18 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[5].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y17 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[6].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y16 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[7].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]

# ── PCIe TX pins ──────────────────────────────────────────────────────────
set_property PACKAGE_PIN F2 [get_ports {pcie_tx_p[0]}]
set_property PACKAGE_PIN H2 [get_ports {pcie_tx_p[1]}]
set_property PACKAGE_PIN K2 [get_ports {pcie_tx_p[2]}]
set_property PACKAGE_PIN M2 [get_ports {pcie_tx_p[3]}]
set_property PACKAGE_PIN N4 [get_ports {pcie_tx_p[4]}]
set_property PACKAGE_PIN P2 [get_ports {pcie_tx_p[5]}]
set_property PACKAGE_PIN T2 [get_ports {pcie_tx_p[6]}]
set_property PACKAGE_PIN U4 [get_ports {pcie_tx_p[7]}]

# ── Timing exceptions ─────────────────────────────────────────────────────
set_false_path -from [get_ports SYS_RSTN]
set_false_path -from [get_ports pcie_perstn]

# ── Zone Pblocks (2×2, calibrated from real K480T die) ───────────────────
# Z00: top-left    X0-X45,  Y189-Y377
# Z01: top-right   X46-X92, Y189-Y377
# Z02: bot-left    X0-X45,  Y0-Y188
# Z03: bot-right   X46-X92, Y0-Y188

create_pblock pb_z00
add_cells_to_pblock pb_z00 [get_cells z00]
resize_pblock pb_z00 -add {SLICE_X0Y189:SLICE_X45Y377}
set_property CONTAIN_ROUTING true [get_pblocks pb_z00]

create_pblock pb_z01
add_cells_to_pblock pb_z01 [get_cells z01]
resize_pblock pb_z01 -add {SLICE_X46Y189:SLICE_X92Y377}
set_property CONTAIN_ROUTING true [get_pblocks pb_z01]

create_pblock pb_z02
add_cells_to_pblock pb_z02 [get_cells z02]
resize_pblock pb_z02 -add {SLICE_X0Y0:SLICE_X45Y188}
set_property CONTAIN_ROUTING true [get_pblocks pb_z02]

create_pblock pb_z03
add_cells_to_pblock pb_z03 [get_cells z03]
resize_pblock pb_z03 -add {SLICE_X46Y0:SLICE_X92Y188}
set_property CONTAIN_ROUTING true [get_pblocks pb_z03]

# ── Bridge timing constraints (8 ns = 125 MHz) ────────────────────────────
set_max_delay -datapath_only 8.0 \
    -from [get_cells -hierarchical -filter {NAME =~ *bridge_e_out*}] \
    -to   [get_cells -hierarchical -filter {NAME =~ *bridge_w_in*}]
set_max_delay -datapath_only 8.0 \
    -from [get_cells -hierarchical -filter {NAME =~ *bridge_w_out*}] \
    -to   [get_cells -hierarchical -filter {NAME =~ *bridge_e_in*}]
set_max_delay -datapath_only 8.0 \
    -from [get_cells -hierarchical -filter {NAME =~ *bridge_s_out*}] \
    -to   [get_cells -hierarchical -filter {NAME =~ *bridge_n_in*}]
set_max_delay -datapath_only 8.0 \
    -from [get_cells -hierarchical -filter {NAME =~ *bridge_n_out*}] \
    -to   [get_cells -hierarchical -filter {NAME =~ *bridge_s_in*}]
