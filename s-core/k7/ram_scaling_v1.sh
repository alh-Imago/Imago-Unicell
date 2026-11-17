#!/bin/sh
# ram_scaling_v1.sh - which memories the S-Core pool contains at each size, and what Yosys turns them into (block RAM, LUT RAM, flip-flops).  Synthesis only, no place-and-route.
# Stops synth_xilinx BEFORE its LUT-mapping step (the step that crashed in the old Yosys 0.33 on this design), so the LUT counts it shows are not LUT counts: use only the RAM figures.
# Run from the s-core folder:   sh k7/ram_scaling_v1.sh 4 8 16          (default 4 8 16; needs k7/sc_k7_sN.v: python3 k7/make_sizes_v1.py N)
# Then:  python3 k7/ram_scaling_v1.py 4 8 16     (reads /tmp/ramsc_* files and prints the table)
XC=${XC:-/usr/share/yosys/xilinx}      # yosys' Xilinx simulation cells (the nix shell's yosys: $(dirname $(which yosys))/../share/yosys/xilinx)
SRC="uc_core_v2v.v sc_sys_v12.v fpga/jtag_link_v2.v fpga/host_bridge_v10.v fpga/farram_bram_v1.v fpga/far_copy.v fpga/batch_seq_v2.v fpga/sc_top_k7_v3.v"
for S in ${*:-4 8 16}; do
  ( yosys -q -l /tmp/ramsc_mem_$S.log -p "read_verilog -lib -specify $XC/cells_sim.v $XC/cells_xtra.v; read_verilog -sv $SRC k7/sc_k7_s$S.v; hierarchy -check -top top; proc; flatten; opt_clean; memory -nomap; tee -o /tmp/ramsc_dump_$S.txt dump t:\$mem_v2"
    yosys -q -l /tmp/ramsc_syn_$S.log -p "read_verilog -lib -specify $XC/cells_sim.v $XC/cells_xtra.v; read_verilog -sv $SRC k7/sc_k7_s$S.v; hierarchy -check -top top; synth_xilinx -top top -flatten -run begin:map_luts; tee -o /tmp/ramsc_stat_$S.txt stat" ) &
done
wait
ls -l /tmp/ramsc_dump_*.txt /tmp/ramsc_stat_*.txt
