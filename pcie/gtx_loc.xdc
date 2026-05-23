# GTX lane location constraints for YPCB-00338-1P1
# PCIe x8 Gen2 — GTXE2_CHANNEL_X0Y16 through X0Y23
# These constrain the S7PCIEPHY pipe_lane instances to the correct
# physical GTX channels connected to the PCIe edge connector.
#
# Source: TiferKing/ypcb_00338_1p1_hack pcie_port.xdc

set_property LOC GTXE2_CHANNEL_X0Y23 [get_cells -hierarchical -filter {NAME =~ *pipe_lane[0]*gtxe2_channel*}]
set_property LOC GTXE2_CHANNEL_X0Y22 [get_cells -hierarchical -filter {NAME =~ *pipe_lane[1]*gtxe2_channel*}]
set_property LOC GTXE2_CHANNEL_X0Y21 [get_cells -hierarchical -filter {NAME =~ *pipe_lane[2]*gtxe2_channel*}]
set_property LOC GTXE2_CHANNEL_X0Y20 [get_cells -hierarchical -filter {NAME =~ *pipe_lane[3]*gtxe2_channel*}]
set_property LOC GTXE2_CHANNEL_X0Y19 [get_cells -hierarchical -filter {NAME =~ *pipe_lane[4]*gtxe2_channel*}]
set_property LOC GTXE2_CHANNEL_X0Y18 [get_cells -hierarchical -filter {NAME =~ *pipe_lane[5]*gtxe2_channel*}]
set_property LOC GTXE2_CHANNEL_X0Y17 [get_cells -hierarchical -filter {NAME =~ *pipe_lane[6]*gtxe2_channel*}]
set_property LOC GTXE2_CHANNEL_X0Y16 [get_cells -hierarchical -filter {NAME =~ *pipe_lane[7]*gtxe2_channel*}]

# PCIe reference clock (100 MHz)
create_clock -name pcie_refclk -period 10.0 [get_ports pcie_x8_clk_p]
