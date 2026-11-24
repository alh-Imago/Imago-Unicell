# run_vivado_v5.tcl - clone of run_vivado_v4.tcl (left as it is). v4 (and v2/v3) read EVERY file in rtl/ (glob rtl/*.sv); rtl/ holds all the unit variants (uc_unitw/h/p/d/e/r 4/8/16),
# which define the same module names (sc_lane, sc_rdsel..., sc_wacc...) with different contents, so Vivado printed "CRITICAL WARNING [Synth 8-9873] overwriting previous definition of module"
# and the definition it kept was the last one read, not the one the build names.  v5 reads only the files that the build's own Makefile lists in ADDITIONAL_SOURCES (the same list the open tools use).
# The far-RAM DRC REQP-1962 stays ON.  UNTESTED.   Run from s-core/k7:  vivado -mode batch -source vivado/run_vivado_v5.tcl -tclargs hd8s4u1n1 2>&1 | tee vivado_hd8s4u1n1_v5.log
set name [lindex $argv 0]
set out vivado_out_$name
file mkdir $out
set part xc7k480tffg1156-1
# find the Makefile whose PROJECT is sc_k7_<name> and take its source list
set srcs ""
foreach f [glob -nocomplain Makefile.*] {
    set fh [open $f]; set txt [read $fh]; close $fh
    if {[regexp "PROJECT\\s*=\\s*sc_k7_$name\\s" $txt] && [regexp {ADDITIONAL_SOURCES\s*=\s*([^\n]*)} $txt -> srcs]} { puts "v5: using the source list of $f"; break }
}
if {$srcs eq ""} { puts "v5: no Makefile with PROJECT = sc_k7_$name found"; exit 1 }
foreach f $srcs { puts "v5: reading $f"; read_verilog -sv $f }
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
