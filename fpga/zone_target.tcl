# zone_target.tcl — per-cell TARGETED config on silicon (heterogeneous config).
# target_en = cmd_bus[8], target_addr = cmd_bus[16:9]. Proves a targeted RECONFIGURE
# reaches ONLY the addressed cell:
#   1. targeted cell 0 -> XOR, trigger -> expect XOR(0xFFFFFFFF,0x0A)=0xFFFFFFF5
#   2. targeted cell 1 -> AND (different cell), trigger cell 0 again -> STILL XOR,
#      proving cell 1's reconfigure did NOT leak onto cell 0.
# auth_token 0xA5 rides cmd_bus[28:21] (the 0x14A0xxxx prefix), matching RC's auth_mask.
set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }
set ::INST $INST
proc uc_open {m} { set ns [get_hardware_names]; set ::HW [lindex $ns 0]
    foreach h $ns { if {[string match "*$m*" $h]} { set ::HW $h; break } }
    set ::DEV [lindex [get_device_names -hardware_name $::HW] 0]
    puts "Hardware : $::HW"; puts "Device   : $::DEV"
    start_insystem_source_probe -device_name $::DEV -hardware_name $::HW }
proc uc_close {} { end_insystem_source_probe }
proc sf {snap go cmd data} { set hi [expr {(($snap&1)<<1)|($go&1)}]
    write_source_data -instance_index $::INST -value [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]] -value_in_hex }
proc cmd {cb cd} { sf 0 0 $cb $cd; sf 0 1 $cb $cd; sf 0 0 $cb $cd }
proc rd {} { set v [expr {"0x[string trim [read_probe_data -instance_index $::INST -value_in_hex]]"}]
    return [list out_data [expr {($v>>48)&0xFFFFFFFF}] out_count [expr {($v>>97)&0xFFFF}]] }
proc trig {b exp tag} { cmd 0x14A40000 0x00000000; cmd 0x00000001 $b
    array set s [rd]; set ok [expr {($s(out_data)==$exp)?"PASS":"** FAIL **"}]
    puts [format "  %-22s out_data=0x%08x (want 0x%08x)  %s" $tag $s(out_data) $exp $ok] }

uc_open $HWM
puts "================= PER-CELL TARGETED CONFIG (heterogeneous) ================="
cmd 0x00200008 0x00000000                 ;# array reset
cmd 0x14A00103 0x00000200                 ;# SET_OUTPUT_ADDR=0x200, targeted cell 0 (target_en, addr0)
cmd 0x14A00104 [expr {0x52800800 | 0x0BC}] ;# targeted cell 0 -> XOR
trig 0x0000000A 0xFFFFFFF5 "cell0=XOR after target"

cmd 0x14A00304 [expr {0x52800800 | 0x007}] ;# targeted cell 1 -> AND (DIFFERENT cell)
trig 0x0000000A 0xFFFFFFF5 "cell0 after targeting c1"
puts "  (if both PASS: targeting hit cell 0, and configuring cell 1 left cell 0 intact)"
uc_close
puts "=== done ==="
