# run_vivado_v1.tcl - UNTESTED (no Vivado was available when this was written).
# Puts one of the multi-block builds through Vivado's own synthesis, placement and routing so the result can be compared with the open toolchain.
# Run from the s-core/k7 folder after "sh stage_mb_v6.sh" (that fills rtl/):
#   vivado -mode batch -source vivado/run_vivado_v1.tcl -tclargs hd12s2u1n1
# The argument is the project name used by the Makefile, e.g. hd8s4u1n1, hd12s2u1n1, hd16s2u1n1 (the top file sc_k7_<name>.v must exist).
# Reports (utilisation, timing, congestion) are written to vivado_out_<name>/.
set name [lindex $argv 0]
set out vivado_out_$name
file mkdir $out
create_project -in_memory -part xc7k480tffg1156-1
foreach f [glob rtl/*.sv] { read_verilog -sv $f }
read_verilog sc_k7_$name.v
read_xdc sc_k7_v1.xdc
# nextpnr takes the clock from --freq; Vivado needs it stated. 50 MHz = 20 ns, the same target as the open builds.
create_clock -period 20.000 -name SYS_CLK [get_ports SYS_CLK]
synth_design -top top -part xc7k480tffg1156-1
report_utilization -file $out/utilization_synth.txt
opt_design
place_design
report_utilization -file $out/utilization_placed.txt
route_design
report_utilization -file $out/utilization_routed.txt
report_timing_summary -file $out/timing_summary.txt
report_route_status -file $out/route_status.txt
report_design_analysis -congestion -file $out/congestion.txt
write_checkpoint -force $out/routed.dcp
