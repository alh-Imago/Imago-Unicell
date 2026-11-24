# run_vivado_v4.tcl - clone of run_vivado_v2.tcl (left as it is) plus write_bitstream at the end. The far-RAM DRC REQP-1962 stays ON (this script never lowers it): if it fails, no bitstream is made. UNTESTED: the bitstream step has not run yet; Vivado may ask for config-voltage settings for this card.
# v2 uses the plain non-project flow: sources and constraints are read first, then synth_design opens the design.
# Run from the s-core/k7 folder after "sh stage_mb_v6.sh":
#   vivado -mode batch -source vivado/run_vivado_v4.tcl -tclargs hd8s4u1n1 2>&1 | tee vivado_hd8s4u1n1.log
# The argument is the project name used by the Makefile (hd8s4u1n1, hd12s2u1n1, hd16s2u1n1; the top file sc_k7_<name>.v must exist).
# Reports (utilisation, timing, route status, congestion) go to vivado_out_<name>/.
set name [lindex $argv 0]
set out vivado_out_$name
file mkdir $out
set part xc7k480tffg1156-1
foreach f [glob rtl/*.sv] { read_verilog -sv $f }
read_verilog sc_k7_$name.v
read_xdc sc_k7_v1.xdc
read_xdc vivado/clock50_v1.xdc
synth_design -top top -part $part
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
write_bitstream -force $out/$name.bit
