# k7_freeze_v1: self-check of the Tang std_tree4 design on the Kintex card, through the openXC7 flow.
# Copy this whole folder into demo-projects/ (next to blinky-ypcb003381p1) so ../openXC7.mk is found, then:
#   make            (build)      make program JTAG_LINK="-c ft232"   (load into SRAM only)
# Never write the card's flash. openXC7.mk gives yosys the files as plain arguments: a .v file is read as plain Verilog,
# a .sv file as SystemVerilog, so the design files under rtl/ are .sv (they use always_comb) and the small top is .v.
FAMILY  = kintex7
PART    = xc7k480tffg1156-1
BOARD   = ypcb003381p1
PROJECT = k7_freeze_v1
TOP_MODULE = top
XDC     = k7_freeze_v1.xdc
ADDITIONAL_SOURCES = rtl/std_tree4_frz.sv rtl/adder_cell_v4e.sv rtl/adder_shell_v1e.sv rtl/adder_v1.sv rtl/invert_addon_v1.sv rtl/nibble_mask_addon_v1.sv rtl/ram_cell_v4.sv rtl/ram_shell_v1.sv rtl/shift_lane_addon_v1.sv
CHIPDB  = ${KINTEX7_CHIPDB}
PYPY3  ?= python3

include ../openXC7.mk

sim:
	iverilog -g2012 -o sim.vvp tb_k7_freeze_v1.v k7_freeze_v1.v rtl/std_tree4_frz.sv rtl/adder_cell_v4e.sv rtl/adder_shell_v1e.sv rtl/adder_v1.sv rtl/invert_addon_v1.sv rtl/nibble_mask_addon_v1.sv rtl/ram_cell_v4.sv rtl/ram_shell_v1.sv rtl/shift_lane_addon_v1.sv && vvp sim.vvp