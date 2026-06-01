# top_xdma_unicell_zones.xdc
# Constraints for top_xdma_unicell_zones on YPCB-00338-1P1 (xc7k480tffg1156-2)
# Merges: ypcb003381p1_unicell.xdc (PCIe/IO) + kintex7_zones.xdc (Pblocks)

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
# IBUFDS_GTE2 handles the differential pair — no PACKAGE_PIN/IOSTANDARD needed
create_clock -period 10.000 -name pcie_refclk [get_ports pcie_refclk_p]

# ── LEDs (active high, LVCMOS18) ─────────────────────────────────────────
set_property PACKAGE_PIN P30 [get_ports led0]
set_property PACKAGE_PIN M30 [get_ports led1]
set_property PACKAGE_PIN N30 [get_ports led2]
set_property IOSTANDARD LVCMOS18 [get_ports led0]
set_property IOSTANDARD LVCMOS18 [get_ports led1]
set_property IOSTANDARD LVCMOS18 [get_ports led2]

# ── GTX lane LOC constraints (PCIe x8, X0Y16-X0Y23) ─────────────────────
# Instance path: xdma_inst (matches module top_xdma_unicell_zones)
set_property LOC GTXE2_CHANNEL_X0Y23 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[0].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y22 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[1].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y21 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[2].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y20 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[3].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y19 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[4].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y18 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[5].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y17 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[6].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y16 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[7].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]

# ── PCIe TX/RX pins ───────────────────────────────────────────────────────
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

# ── Zone Pblock floorplan (2×8 grid, 28 cells/zone) ──────────────────────
# XC7K480T: ~480 CLB columns × ~200 CLB rows
# Zone width: 60 CLB columns (480/8), height: 100 CLB rows (200/2)
# Row 0: top half (Y100-Y199), Row 1: bottom half (Y0-Y99)
# Pblock cell-filter matches generate block hierarchy: row0[c].z / row1[c].z

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z00
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z00 [get_cells -hierarchical -filter {NAME =~ *row0[0]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z00 -add {SLICE_X0Y100:SLICE_X59Y199}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z00]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z01
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z01 [get_cells -hierarchical -filter {NAME =~ *row0[1]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z01 -add {SLICE_X60Y100:SLICE_X119Y199}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z01]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z02
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z02 [get_cells -hierarchical -filter {NAME =~ *row0[2]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z02 -add {SLICE_X120Y100:SLICE_X179Y199}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z02]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z03
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z03 [get_cells -hierarchical -filter {NAME =~ *row0[3]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z03 -add {SLICE_X180Y100:SLICE_X239Y199}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z03]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z04
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z04 [get_cells -hierarchical -filter {NAME =~ *row0[4]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z04 -add {SLICE_X240Y100:SLICE_X299Y199}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z04]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z05
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z05 [get_cells -hierarchical -filter {NAME =~ *row0[5]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z05 -add {SLICE_X300Y100:SLICE_X359Y199}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z05]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z06
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z06 [get_cells -hierarchical -filter {NAME =~ *row0[6]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z06 -add {SLICE_X360Y100:SLICE_X419Y199}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z06]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z07
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z07 [get_cells -hierarchical -filter {NAME =~ *row0[7]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z07 -add {SLICE_X420Y100:SLICE_X479Y199}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z07]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z08
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z08 [get_cells -hierarchical -filter {NAME =~ *row1[0]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z08 -add {SLICE_X0Y0:SLICE_X59Y99}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z08]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z09
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z09 [get_cells -hierarchical -filter {NAME =~ *row1[1]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z09 -add {SLICE_X60Y0:SLICE_X119Y99}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z09]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z10
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z10 [get_cells -hierarchical -filter {NAME =~ *row1[2]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z10 -add {SLICE_X120Y0:SLICE_X179Y99}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z10]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z11
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z11 [get_cells -hierarchical -filter {NAME =~ *row1[3]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z11 -add {SLICE_X180Y0:SLICE_X239Y99}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z11]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z12
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z12 [get_cells -hierarchical -filter {NAME =~ *row1[4]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z12 -add {SLICE_X240Y0:SLICE_X299Y99}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z12]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z13
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z13 [get_cells -hierarchical -filter {NAME =~ *row1[5]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z13 -add {SLICE_X300Y0:SLICE_X359Y99}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z13]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z14
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z14 [get_cells -hierarchical -filter {NAME =~ *row1[6]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z14 -add {SLICE_X360Y0:SLICE_X419Y99}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z14]

# DISABLED (coordinates need calibration after first free placement): create_pblock pb_z15
# DISABLED (coordinates need calibration after first free placement): add_cells_to_pblock pb_z15 [get_cells -hierarchical -filter {NAME =~ *row1[7]*}]
# DISABLED (coordinates need calibration after first free placement): resize_pblock pb_z15 -add {SLICE_X420Y0:SLICE_X479Y99}
# DISABLED (coordinates need calibration after first free placement): set_property CONTAIN_ROUTING true [get_pblocks pb_z15]

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

# ── BPI flash config ──────────────────────────────────────────────────────
# Applied at write_bitstream time in Vivado Tcl:
#   set_property BITSTREAM.CONFIG.SPI_BUSWIDTH NONE [current_design]
#   set_property CONFIG_MODE BPI16 [current_design]
#   set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
