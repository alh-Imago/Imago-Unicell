# sc_k7_ddr3_v1: the S-Core pool on the Kintex-7 YPCB-00338-1P1 card with its far RAM in DDR3 channel 0 (UberDDR3, GPL-3.0: this whole build is GPL-3.0, see README.md).
# Build ONLY inside the nix shell:   nix develop github:openxc7/toolchain-nix
# Chip database: KINTEX7_CHIPDB is empty in that shell, so openXC7.mk uses ../chipdb/ (demo-projects/chipdb/xc7k480tffg1156.bin, built once).  Check it exists first:
#   ls -lh ../chipdb/xc7k480tffg1156.bin      (if it is missing the tool would regenerate it: stop)
# Copy this whole folder (ddr3_gpl3) into demo-projects/ as sc_k7_ddr3 (next to blinky-ypcb003381p1) so ../openXC7.mk is found, then inside it:
#   S_CORE=$HOME/Imago-Unicell-score/s-core sh stage.sh      (copies the pool RTL into rtl/ as .sv)
#   python3 make_mod.py ; python3 make_xdc.py                 (only needed if mod/ or the xdc are missing or upstream changed; both are committed)
#   make 2>&1 | tee build.log                                 (build; then check cclk >= 83.33 MHz, pool_clk >= 50, ref_clk >= 200 in the Max frequency lines)
#             make program JTAG_LINK="-c ft232"   (load into SRAM only)
# The DDR3 I/O needs sirmick's patched nextpnr (OLOGIC T1 patch 0003 at least; see README.md): an unpatched nextpnr may fail or build a bitstream that does not calibrate.
# Never write the card's flash.  Never load a bitstream whose timing check failed.
FAMILY  = kintex7
PART    = xc7k480tffg1156-1
BOARD   = ypcb003381p1
PROJECT = sc_k7_ddr3_v1
TOP_MODULE = top
XDC     = sc_k7_ddr3_v1.xdc
ADDITIONAL_SOURCES = rtl/uc_core_v2v.sv rtl/sc_sys_v12.sv rtl/jtag_link_v1.sv rtl/host_bridge_v10.sv rtl/far_copy.sv rtl/batch_seq_v2.sv rtl/sc_top_k7_v2.sv \
                     farram_ddr3_v1.v clk_ypcb_v1.v mod/ddr3_phy_ypcb_v1.v mod/ddr3_top_ypcb_v1.v upstream/rtl/ddr3_controller.v
CHIPDB  = ${KINTEX7_CHIPDB}
# nextpnr applies ONE target to every clock it has no constraint for and stops with an error when any clock misses it.  The slowest clock we need is the pool's
# 50 MHz, so the target is 50 and the faster clocks (cclk 83.33 MHz, ref_clk 200 MHz) are checked by hand against the 'Max frequency' lines of build.log.
# (First try, 2026-11-16, used 83.333: pool_clk reached 66.76 MHz, which is plenty for its 50 MHz, but nextpnr stopped and wrote no bitstream.)
PNR_ARGS ?= --freq 50
PYPY3  ?= python3

include ../openXC7.mk
