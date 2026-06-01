# kintex7_zones.xdc — 2×8 zone grid floorplan
# YPCB-00338-1P1 (xc7k480tffg1156-2)
#
# 16 zones × 28 cells = 448 cells
# Each zone: ~35,952 LUTs in a ~130×70 CLB region
#
# Grid layout on die (approximate — tune after first placement run):
#   Row 0 (top):    Z00 Z01 Z02 Z03 Z04 Z05 Z06 Z07  (X=0..7, Y=1)
#   Row 1 (bottom): Z08 Z09 Z10 Z11 Z12 Z13 Z14 Z15  (X=0..7, Y=0)
#
# XC7K480T die: ~480 CLB columns × ~200 CLB rows
# Zone width: ~60 CLB columns each (480/8 = 60)
# Zone height: ~100 CLB rows each (200/2 = 100)

# ── Row 0 (top half of die) ───────────────────────────────────────────────

create_pblock pb_z00
add_cells_to_pblock pb_z00 [get_cells -hierarchical -filter {NAME =~ *row0[0]*}]
resize_pblock pb_z00 -add {SLICE_X0Y100:SLICE_X59Y199}
set_property CONTAIN_ROUTING true [get_pblocks pb_z00]

create_pblock pb_z01
add_cells_to_pblock pb_z01 [get_cells -hierarchical -filter {NAME =~ *row0[1]*}]
resize_pblock pb_z01 -add {SLICE_X60Y100:SLICE_X119Y199}
set_property CONTAIN_ROUTING true [get_pblocks pb_z01]

create_pblock pb_z02
add_cells_to_pblock pb_z02 [get_cells -hierarchical -filter {NAME =~ *row0[2]*}]
resize_pblock pb_z02 -add {SLICE_X120Y100:SLICE_X179Y199}
set_property CONTAIN_ROUTING true [get_pblocks pb_z02]

create_pblock pb_z03
add_cells_to_pblock pb_z03 [get_cells -hierarchical -filter {NAME =~ *row0[3]*}]
resize_pblock pb_z03 -add {SLICE_X180Y100:SLICE_X239Y199}
set_property CONTAIN_ROUTING true [get_pblocks pb_z03]

create_pblock pb_z04
add_cells_to_pblock pb_z04 [get_cells -hierarchical -filter {NAME =~ *row0[4]*}]
resize_pblock pb_z04 -add {SLICE_X240Y100:SLICE_X299Y199}
set_property CONTAIN_ROUTING true [get_pblocks pb_z04]

create_pblock pb_z05
add_cells_to_pblock pb_z05 [get_cells -hierarchical -filter {NAME =~ *row0[5]*}]
resize_pblock pb_z05 -add {SLICE_X300Y100:SLICE_X359Y199}
set_property CONTAIN_ROUTING true [get_pblocks pb_z05]

create_pblock pb_z06
add_cells_to_pblock pb_z06 [get_cells -hierarchical -filter {NAME =~ *row0[6]*}]
resize_pblock pb_z06 -add {SLICE_X360Y100:SLICE_X419Y199}
set_property CONTAIN_ROUTING true [get_pblocks pb_z06]

create_pblock pb_z07
add_cells_to_pblock pb_z07 [get_cells -hierarchical -filter {NAME =~ *row0[7]*}]
resize_pblock pb_z07 -add {SLICE_X420Y100:SLICE_X479Y199}
set_property CONTAIN_ROUTING true [get_pblocks pb_z07]

# ── Row 1 (bottom half of die) ────────────────────────────────────────────

create_pblock pb_z08
add_cells_to_pblock pb_z08 [get_cells -hierarchical -filter {NAME =~ *row1[0]*}]
resize_pblock pb_z08 -add {SLICE_X0Y0:SLICE_X59Y99}
set_property CONTAIN_ROUTING true [get_pblocks pb_z08]

create_pblock pb_z09
add_cells_to_pblock pb_z09 [get_cells -hierarchical -filter {NAME =~ *row1[1]*}]
resize_pblock pb_z09 -add {SLICE_X60Y0:SLICE_X119Y99}
set_property CONTAIN_ROUTING true [get_pblocks pb_z09]

create_pblock pb_z10
add_cells_to_pblock pb_z10 [get_cells -hierarchical -filter {NAME =~ *row1[2]*}]
resize_pblock pb_z10 -add {SLICE_X120Y0:SLICE_X179Y99}
set_property CONTAIN_ROUTING true [get_pblocks pb_z10]

create_pblock pb_z11
add_cells_to_pblock pb_z11 [get_cells -hierarchical -filter {NAME =~ *row1[3]*}]
resize_pblock pb_z11 -add {SLICE_X180Y0:SLICE_X239Y99}
set_property CONTAIN_ROUTING true [get_pblocks pb_z11]

create_pblock pb_z12
add_cells_to_pblock pb_z12 [get_cells -hierarchical -filter {NAME =~ *row1[4]*}]
resize_pblock pb_z12 -add {SLICE_X240Y0:SLICE_X299Y99}
set_property CONTAIN_ROUTING true [get_pblocks pb_z12]

create_pblock pb_z13
add_cells_to_pblock pb_z13 [get_cells -hierarchical -filter {NAME =~ *row1[5]*}]
resize_pblock pb_z13 -add {SLICE_X300Y0:SLICE_X359Y99}
set_property CONTAIN_ROUTING true [get_pblocks pb_z13]

create_pblock pb_z14
add_cells_to_pblock pb_z14 [get_cells -hierarchical -filter {NAME =~ *row1[6]*}]
resize_pblock pb_z14 -add {SLICE_X360Y0:SLICE_X419Y99}
set_property CONTAIN_ROUTING true [get_pblocks pb_z14]

create_pblock pb_z15
add_cells_to_pblock pb_z15 [get_cells -hierarchical -filter {NAME =~ *row1[7]*}]
resize_pblock pb_z15 -add {SLICE_X420Y0:SLICE_X479Y99}
set_property CONTAIN_ROUTING true [get_pblocks pb_z15]

# ── Bridge timing constraints ─────────────────────────────────────────────
# All bridge signals must cross Pblock boundaries in one clock cycle (8ns)

# Horizontal bridges (E/W within each row)
set_max_delay -datapath_only 8.0 \
    -from [get_cells -hierarchical -filter {NAME =~ *bridge_e_out*}] \
    -to   [get_cells -hierarchical -filter {NAME =~ *bridge_w_in*}]

set_max_delay -datapath_only 8.0 \
    -from [get_cells -hierarchical -filter {NAME =~ *bridge_w_out*}] \
    -to   [get_cells -hierarchical -filter {NAME =~ *bridge_e_in*}]

# Vertical bridges (N/S between rows)
set_max_delay -datapath_only 8.0 \
    -from [get_cells -hierarchical -filter {NAME =~ *bridge_s_out*}] \
    -to   [get_cells -hierarchical -filter {NAME =~ *bridge_n_in*}]

set_max_delay -datapath_only 8.0 \
    -from [get_cells -hierarchical -filter {NAME =~ *bridge_n_out*}] \
    -to   [get_cells -hierarchical -filter {NAME =~ *bridge_s_in*}]

# ── Clock ─────────────────────────────────────────────────────────────────
create_clock -period 8.000 -name sys_clk [get_ports clk]

# ── PCIe / board pins (YPCB-00338-1P1) ───────────────────────────────────
set_property PACKAGE_PIN AA28 [get_ports clk]
set_property IOSTANDARD LVCMOS18 [get_ports clk]

set_property PACKAGE_PIN P30 [get_ports {led[0]}]
set_property PACKAGE_PIN M30 [get_ports {led[1]}]
set_property PACKAGE_PIN N30 [get_ports {led[2]}]
set_property IOSTANDARD LVCMOS18 [get_ports {led[*]}]
