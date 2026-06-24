# zone_emit.tcl — command-emit on silicon (v3.0). Configures cell 0 as a
# COMMAND_EMIT cell, loads a command word into a_data (ISSP-friendly via SWAP_AB),
# triggers it, and reads the emit_count probe (selector 3) to confirm the cell drove
# the command bus. The emitted command is routed by the array arbiter to its target;
# the target reconfigure is sim-proven (tb_zone_emit) — on silicon emit_count is the
# observable (the probe only surfaces cell 0).
#   quartus_stp -t zone_emit.tcl [instance] [hw_match]
# Requires the v3.0 bitstream (emit routing + emit_count probe selector 3).

set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }
set ::INST $INST

proc uc_open {m} {
    set ns [get_hardware_names]; set ::HW [lindex $ns 0]
    foreach h $ns { if {[string match "*$m*" $h]} { set ::HW $h; break } }
    set ::DEV [lindex [get_device_names -hardware_name $::HW] 0]
    puts "Hardware : $::HW"; puts "Device   : $::DEV"
    start_insystem_source_probe -device_name $::DEV -hardware_name $::HW
}
proc uc_close {} { end_insystem_source_probe }
proc sf {snap go cmd data} {
    set hi [expr {(($snap&1)<<1)|($go&1)}]
    write_source_data -instance_index $::INST -value [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]] -value_in_hex
}
proc cmd {cb cd} { sf 0 0 $cb $cd; sf 0 1 $cb $cd; sf 0 0 $cb $cd }
proc rd {} {
    set v [expr {"0x[string trim [read_probe_data -instance_index $::INST -value_in_hex]]"}]
    return [list field [expr {($v>>32)&0xFFFF}] out_data [expr {($v>>48)&0xFFFFFFFF}] \
                 out_addr [expr {($v>>80)&0xFFFF}] out_count [expr {($v>>97)&0xFFFF}]]
}
# readview drives src_cpu_bus[1:0]=sel into the snapshot: 0=armed 1=arrived 2=outset 3=emit
proc readview {sel} { sf 0 0 $sel 0; sf 1 0 $sel 0; sf 0 0 0 0; return [rd] }
proc field {sel} { array set s [readview $sel]; return $s(field) }

uc_open $HWM
puts "================= COMMAND-EMIT TEST (cell 0 emits, selector-3 = emit_count) ================="

cmd 0x00200008 0x00000000          ;# array reset
puts [format "  emit_count BEFORE = %d   (armed=%d)" [field 3] [field 0]]

cmd 0x00000047 0x00000000          ;# CMD_TOPO_COMMAND_EMIT (armed) on cell 0
cmd 0x14A00003 0x00000005          ;# SET_OUTPUT_ADDR=5  (emit target cell)
cmd 0x00000012 0x0000000E          ;# CMD_SWAP_AB: a_data=SET_LOGICAL(0x0E), a_arrived=1
cmd 0x00000001 0x00000055          ;# single trigger @ addr 0 -> cell 0 EMITS

set ec [field 3]
puts [format "  emit_count AFTER  = %d" $ec]
if {$ec > 0} {
    puts "  >>> PASS: cell 0 drove the command bus (emit_count incremented) — fabric commanded itself on silicon"
} else {
    puts "  >>> FAIL: no emit registered (check v3.0 bitstream is flashed)"
}
uc_close
puts "=== done ==="
