# ypcb003381p1_unicell.xdc
# Constraints for top_xdma_unicell on YPCB-00338-1P1 (xc7k480tffg1156-2)
# Instance name: xdma_inst (matches top_xdma_unicell.v)

# ── System clock ──────────────────────────────────────────────────────────────
set_property PACKAGE_PIN AA28 [get_ports SYS_CLK]
set_property IOSTANDARD LVCMOS18 [get_ports SYS_CLK]
create_clock -period 20.000 -name sys_clk [get_ports SYS_CLK]

# ── System reset (active low) ─────────────────────────────────────────────────
set_property PACKAGE_PIN R28 [get_ports SYS_RSTN]
set_property IOSTANDARD LVCMOS18 [get_ports SYS_RSTN]

# ── PCIe reset (active low) ───────────────────────────────────────────────────
set_property PACKAGE_PIN Y26 [get_ports pcie_perstn]
set_property IOSTANDARD LVCMOS18 [get_ports pcie_perstn]
set_property PULLUP true [get_ports pcie_perstn]

# ── PCIe reference clock (100 MHz, J8) ───────────────────────────────────────
set_property PACKAGE_PIN AB8 [get_ports pcie_refclk_p]
# pcie_refclk_n is implicit (differential pair)
create_clock -period 10.000 -name pcie_refclk [get_ports pcie_refclk_p]

# ── LEDs (active high, LVCMOS18) ─────────────────────────────────────────────
set_property PACKAGE_PIN P30 [get_ports led0]
set_property PACKAGE_PIN M30 [get_ports led1]
set_property PACKAGE_PIN N30 [get_ports led2]
set_property IOSTANDARD LVCMOS18 [get_ports led0]
set_property IOSTANDARD LVCMOS18 [get_ports led1]
set_property IOSTANDARD LVCMOS18 [get_ports led2]

# ── GTX lane LOC constraints ──────────────────────────────────────────────────
# Instance path: xdma_inst (top_xdma_unicell.v line: xdma_0 xdma_inst (...))
set_property LOC GTXE2_CHANNEL_X0Y23 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[0].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y22 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[1].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y21 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[2].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y20 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[3].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y19 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[4].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y18 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[5].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y17 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[6].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]
set_property LOC GTXE2_CHANNEL_X0Y16 [get_cells {xdma_inst/inst/top_xdma_0_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/gt_top_i/pipe_wrapper_i/pipe_lane[7].gt_wrapper_i/gtx_channel.gtxe2_channel_i}]

# ── PCIe TX pins ──────────────────────────────────────────────────────────────
set_property PACKAGE_PIN F2 [get_ports {pcie_tx_p[0]}]
set_property PACKAGE_PIN H2 [get_ports {pcie_tx_p[1]}]
set_property PACKAGE_PIN K2 [get_ports {pcie_tx_p[2]}]
set_property PACKAGE_PIN M2 [get_ports {pcie_tx_p[3]}]
set_property PACKAGE_PIN N4 [get_ports {pcie_tx_p[4]}]
set_property PACKAGE_PIN P2 [get_ports {pcie_tx_p[5]}]
set_property PACKAGE_PIN T2 [get_ports {pcie_tx_p[6]}]
set_property PACKAGE_PIN U4 [get_ports {pcie_tx_p[7]}]

# ── Timing exceptions ─────────────────────────────────────────────────────────
# PCIe user clock (125MHz from XDMA MMCM) - auto-derived, no manual constraint needed
# False path on async reset
set_false_path -from [get_ports SYS_RSTN]
set_false_path -from [get_ports pcie_perstn]
