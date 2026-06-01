# top_xdma_unicell_zones.xdc
# Constraints for top_xdma_unicell_zones on YPCB-00338-1P1 (xc7k480tffg1156-2)
# 16 zones × 24 cells = 384 cells total, ~70% LUT utilisation target
#
# Real die coordinates from first free-placement run:
#   SLICE X range: X0-X92  (93 columns)
#   SLICE Y range: Y0-Y377 (378 rows)
# Zone layout: 8 columns × 11 SLICE cols, 2 rows × 188 SLICE rows

# ── System clock (50 MHz, AA28) ───────────────────────────────────────────
set_property PACKAGE_PIN AA28 [get_ports SYS_CLK]
set_property IOSTANDARD LVCMOS18 [get_ports SYS_CLK]
create_clock -period 20.000 -name sys_clk [get_ports SYS_CLK]

# ── System reset (active low, R28) ───────────────────────────────────────
set_property PACKAGE_PIN R28 [get_ports SYS_RSTN]
set_property IOSTANDARD LVCMOS18 [get_ports SYS_RSTN]

# ── PCIe reset (active low, Y26) ─────────────────────────────────────────
set_property PACKAGE_PIN Y26 [get_ports pcie_perstn]
set_property IOSTANDARD LVCMOS18 [get_ports pcie_perstn]
set_property PULLUP true [get_ports pcie_perstn]

# ── PCIe reference clock (100 MHz, J8) ───────────────────────────────────
create_clock -period 10.000 -name pcie_refclk [get_ports pcie_refclk_p]

# ── LEDs (active high, LVCMOS18) ─────────────────────────────────────────
set_property PACKAGE_PIN P30 [get_ports led0]
set_property PACKAGE_PIN M30 [get_ports led1]
set_property PACKAGE_PIN N30 [get_ports led2]
set_property IOSTANDARD LVCMOS18 [get_ports led0]
set_property IOSTANDARD LVCMOS18 [get_ports led1]
set_property IOSTANDARD LVCMOS18 [get_ports led2]

# ── GTX lane LOC constraints (PCIe x8, X0Y16-X0Y23) ─────────────────────
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

# ── Zone Pblocks (2×8 grid, calibrated from actual K480T die layout) ──────
# Die: X0-X92, Y0-Y377. Zone: 11 cols × 188 rows each.
# Row 0 (top): Y189-Y377, Row 1 (bottom): Y0-Y188

create_pblock pb_z00
add_cells_to_pblock pb_z00 [get_cells -hierarchical -filter {NAME =~ *row0[0]*}]
resize_pblock pb_z00 -add {SLICE_X0Y189:SLICE_X10Y377}
set_property CONTAIN_ROUTING true [get_pblocks pb_z00]

create_pblock pb_z01
add_cells_to_pblock pb_z01 [get_cells -hierarchical -filter {NAME =~ *row0[1]*}]
resize_pblock pb_z01 -add {SLICE_X11Y189:SLICE_X21Y377}
set_property CONTAIN_ROUTING true [get_pblocks pb_z01]

create_pblock pb_z02
add_cells_to_pblock pb_z02 [get_cells -hierarchical -filter {NAME =~ *row0[2]*}]
resize_pblock pb_z02 -add {SLICE_X22Y189:SLICE_X32Y377}
set_property CONTAIN_ROUTING true [get_pblocks pb_z02]

create_pblock pb_z03
add_cells_to_pblock pb_z03 [get_cells -hierarchical -filter {NAME =~ *row0[3]*}]
resize_pblock pb_z03 -add {SLICE_X33Y189:SLICE_X43Y377}
set_property CONTAIN_ROUTING true [get_pblocks pb_z03]

create_pblock pb_z04
add_cells_to_pblock pb_z04 [get_cells -hierarchical -filter {NAME =~ *row0[4]*}]
resize_pblock pb_z04 -add {SLICE_X44Y189:SLICE_X54Y377}
set_property CONTAIN_ROUTING true [get_pblocks pb_z04]

create_pblock pb_z05
add_cells_to_pblock pb_z05 [get_cells -hierarchical -filter {NAME =~ *row0[5]*}]
resize_pblock pb_z05 -add {SLICE_X55Y189:SLICE_X65Y377}
set_property CONTAIN_ROUTING true [get_pblocks pb_z05]

create_pblock pb_z06
add_cells_to_pblock pb_z06 [get_cells -hierarchical -filter {NAME =~ *row0[6]*}]
resize_pblock pb_z06 -add {SLICE_X66Y189:SLICE_X76Y377}
set_property CONTAIN_ROUTING true [get_pblocks pb_z06]

create_pblock pb_z07
add_cells_to_pblock pb_z07 [get_cells -hierarchical -filter {NAME =~ *row0[7]*}]
resize_pblock pb_z07 -add {SLICE_X77Y189:SLICE_X92Y377}
set_property CONTAIN_ROUTING true [get_pblocks pb_z07]

create_pblock pb_z08
add_cells_to_pblock pb_z08 [get_cells -hierarchical -filter {NAME =~ *row1[0]*}]
resize_pblock pb_z08 -add {SLICE_X0Y0:SLICE_X10Y188}
set_property CONTAIN_ROUTING true [get_pblocks pb_z08]

create_pblock pb_z09
add_cells_to_pblock pb_z09 [get_cells -hierarchical -filter {NAME =~ *row1[1]*}]
resize_pblock pb_z09 -add {SLICE_X11Y0:SLICE_X21Y188}
set_property CONTAIN_ROUTING true [get_pblocks pb_z09]

create_pblock pb_z10
add_cells_to_pblock pb_z10 [get_cells -hierarchical -filter {NAME =~ *row1[2]*}]
resize_pblock pb_z10 -add {SLICE_X22Y0:SLICE_X32Y188}
set_property CONTAIN_ROUTING true [get_pblocks pb_z10]

create_pblock pb_z11
add_cells_to_pblock pb_z11 [get_cells -hierarchical -filter {NAME =~ *row1[3]*}]
resize_pblock pb_z11 -add {SLICE_X33Y0:SLICE_X43Y188}
set_property CONTAIN_ROUTING true [get_pblocks pb_z11]

create_pblock pb_z12
add_cells_to_pblock pb_z12 [get_cells -hierarchical -filter {NAME =~ *row1[4]*}]
resize_pblock pb_z12 -add {SLICE_X44Y0:SLICE_X54Y188}
set_property CONTAIN_ROUTING true [get_pblocks pb_z12]

create_pblock pb_z13
add_cells_to_pblock pb_z13 [get_cells -hierarchical -filter {NAME =~ *row1[5]*}]
resize_pblock pb_z13 -add {SLICE_X55Y0:SLICE_X65Y188}
set_property CONTAIN_ROUTING true [get_pblocks pb_z13]

create_pblock pb_z14
add_cells_to_pblock pb_z14 [get_cells -hierarchical -filter {NAME =~ *row1[6]*}]
resize_pblock pb_z14 -add {SLICE_X66Y0:SLICE_X76Y188}
set_property CONTAIN_ROUTING true [get_pblocks pb_z14]

create_pblock pb_z15
add_cells_to_pblock pb_z15 [get_cells -hierarchical -filter {NAME =~ *row1[7]*}]
resize_pblock pb_z15 -add {SLICE_X77Y0:SLICE_X92Y188}
set_property CONTAIN_ROUTING true [get_pblocks pb_z15]

# ── Bridge timing — cross-zone signals must meet 8 ns (125 MHz) ──────────
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

# ── BPI flash config (apply at write_bitstream time) ─────────────────────
# set_property BITSTREAM.CONFIG.SPI_BUSWIDTH NONE [current_design]
# set_property CONFIG_MODE BPI16 [current_design]
# set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
