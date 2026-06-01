# kintex7_zones.xdc — Zone-based floorplan constraints
# YPCB-00338-1P1 (xc7k480tffg1156-2)
#
# Each zone is a Pblock region — independently routed, independently timed.
# Bridge signals are registered at zone boundaries.
# This eliminates routing congestion by keeping each zone self-contained.
#
# Kintex-7 XC7K480T die layout (approximate):
#   ~300 CLB columns × ~200 CLB rows = 60,000 CLBs
#   At 1285 LUTs/cell (v2.3), 50 cells ≈ 64,250 LUTs ≈ ~16,000 CLBs
#   Each zone needs roughly a 130×125 CLB region
#
# Zone placement (linear, horizontal):
#   Zone 0: left side of die
#   Zone 1: right of zone 0
#   Zone 2+: continue rightward or start second row

# ── Zone 0 ────────────────────────────────────────────────────────────────
create_pblock pblock_zone0
add_cells_to_pblock pblock_zone0 [get_cells -hierarchical -filter {NAME =~ *zone0*}]
resize_pblock pblock_zone0 -add {SLICE_X0Y0:SLICE_X129Y124}
resize_pblock pblock_zone0 -add {RAMB18_X0Y0:RAMB18_X3Y49}
resize_pblock pblock_zone0 -add {RAMB36_X0Y0:RAMB36_X3Y24}
set_property CONTAIN_ROUTING true [get_pblocks pblock_zone0]
set_property HD.PARTITION 1 [get_cells zone0]

# ── Zone 1 ────────────────────────────────────────────────────────────────
create_pblock pblock_zone1
add_cells_to_pblock pblock_zone1 [get_cells -hierarchical -filter {NAME =~ *zone1*}]
resize_pblock pblock_zone1 -add {SLICE_X130Y0:SLICE_X259Y124}
resize_pblock pblock_zone1 -add {RAMB18_X4Y0:RAMB18_X7Y49}
resize_pblock pblock_zone1 -add {RAMB36_X4Y0:RAMB36_X7Y24}
set_property CONTAIN_ROUTING true [get_pblocks pblock_zone1]
set_property HD.PARTITION 1 [get_cells zone1]

# ── Zone 2 (template — uncomment to add) ─────────────────────────────────
# create_pblock pblock_zone2
# add_cells_to_pblock pblock_zone2 [get_cells -hierarchical -filter {NAME =~ *zone2*}]
# resize_pblock pblock_zone2 -add {SLICE_X260Y0:SLICE_X389Y124}
# set_property CONTAIN_ROUTING true [get_pblocks pblock_zone2]

# ── Bridge signal timing constraints ──────────────────────────────────────
# Bridge signals cross Pblock boundaries — constrain to one clock cycle max
# This is the key timing guarantee: 1 tick latency per zone crossing.

set_max_delay -datapath_only -from [get_cells {zone0/bridge_east_out_reg*}] \
              -to   [get_cells {zone1/bridge_west_in_reg*}] 8.0

set_max_delay -datapath_only -from [get_cells {zone1/bridge_west_out_reg*}] \
              -to   [get_cells {zone0/bridge_east_in_reg*}] 8.0

# ── Clock ─────────────────────────────────────────────────────────────────
# 125MHz system clock — 8ns period
create_clock -period 8.000 -name sys_clk [get_ports pcie_clk]

# ── PCIe pins (YPCB-00338-1P1) ────────────────────────────────────────────
# GTX banks X0Y16-X0Y23, refclk J8
set_property PACKAGE_PIN Y26  [get_ports pcie_rst_n]
set_property IOSTANDARD LVCMOS18 [get_ports pcie_rst_n]

# ── LEDs ──────────────────────────────────────────────────────────────────
set_property PACKAGE_PIN P30 [get_ports {led[0]}]
set_property PACKAGE_PIN M30 [get_ports {led[1]}]
set_property PACKAGE_PIN N30 [get_ports {led[2]}]
set_property IOSTANDARD LVCMOS18 [get_ports {led[*]}]
