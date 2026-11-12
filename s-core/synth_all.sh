#!/bin/bash
# usage: synth_all.sh file module W  -> prints ice40 LUT4 / gowin LUT / xilinx LUT / FF
f=$1; m=$2; W=$3
run() { yosys -q -p "read_verilog -sv $f; chparam -set W $W $m; hierarchy -top $m; $1 -top $m; tee -o /tmp/s_$$.txt stat" >/dev/null 2>&1; }
run synth_ice40;  ice=$(awk '$1=="SB_LUT4"{print $2}' /tmp/s_$$.txt)
run synth_gowin;  gw=$(awk '$1 ~ /^LUT[1-4]$/{s+=$2} END{print s}' /tmp/s_$$.txt); gwff=$(awk '$1 ~ /^DFF/{s+=$2} END{print s}' /tmp/s_$$.txt)
run synth_xilinx; xl=$(awk '$1 ~ /^LUT[1-6]$/{s+=$2} END{print s}' /tmp/s_$$.txt); xlff=$(awk '$1 ~ /^FD/{s+=$2} END{print s}' /tmp/s_$$.txt)
printf "%-10s W=%-2s  iCE40 LUT4=%-5s  Gowin LUT=%-5s FF=%-4s  Xilinx LUT=%-5s FF=%-4s\n" $m $W "$ice" "$gw" "$gwff" "$xl" "$xlff"
