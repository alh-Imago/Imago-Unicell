# build_blink_vivado_v1.tcl -- ledger #1192. Builds blink_k7.bit for the XC7K480T card with Vivado (the openXC7 route in build_k7_blink_v1.sh needs a chipdb that is not set up).
# NOT RUN by Claude (no Vivado here). Run from THIS folder:   vivado -mode batch -source build_blink_vivado_v1.tcl
# Output: build_vivado/blink_k7.bit. It stops BEFORE writing the bitstream if timing is not met. It never touches the card.
# Part: xc7k480tffg1156-2 (from the board notes; the package/speed grade has not been confirmed by Vivado on this card).
# Unverified: the pins (clock AA28, LEDs P30/M30/N30) come from an old board file and have not been measured; CFGBVS/CONFIG_VOLTAGE below are placeholders so the DRC passes, not confirmed board facts (they do not change an SRAM load through JTAG).
set here [file dirname [file normalize [info script]]]
set out  $here/build_vivado
file mkdir $out
create_project -in_memory -part xc7k480tffg1156-2
read_verilog $here/blink_k7_v1.v
read_xdc $here/blink_k7_v1.xdc
set_property CFGBVS GND [current_design]
set_property CONFIG_VOLTAGE 1.8 [current_design]
synth_design -top top
opt_design
place_design
route_design
report_timing_summary -file $out/timing.rpt
report_utilization    -file $out/util.rpt
set wns [get_property SLACK [get_timing_paths -max_paths 1 -setup]]
puts "WORST SETUP SLACK: $wns ns"
if {$wns < 0} { error "timing NOT met (slack $wns) - bitstream not written" }
write_bitstream -force $out/blink_k7.bit
puts "wrote $out/blink_k7.bit - load with:  sudo openFPGALoader -c ft232 build_vivado/blink_k7.bit   (SRAM only, never flash)"
