# zone_target.tcl — TARGET LATCH + CMD_LOAD_AT on silicon (per-cell config).
# Requires the build with the top target-latch (SET_TARGET op24) + CMD_LOAD_AT (op23).
# Proves: a (SET_TARGET addr, CMD_LOAD_AT config) pair configures ONLY the addressed
# cell. Reads cell-0's cmd_latch directly via probe view selector 3.
#   1. target cell 0, load XOR -> cell0 latch topology = 0x0BC
#   2. target cell 1, load AND -> cell0 latch STILL 0x0BC (cell 1's load excluded cell 0)
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
# snapshot with view selector 3 (cell-0 latch), read cmd_latch from probe[79:48]
proc rd_latch {} { sf 1 0 0x00000003 0x0; sf 0 0 0x00000003 0x0
    set v [expr {"0x[string trim [read_probe_data -instance_index $::INST -value_in_hex]]"}]
    return [expr {($v>>48)&0xFFFFFFFF}] }
# ICM record: SET_TARGET(addr) holds the address lane, CMD_LOAD_AT(config) lands on it
proc icm {addr cfg} { cmd 0x00000018 $addr; cmd 0x00000017 $cfg }

uc_open $HWM
puts "================= TARGET LATCH — per-cell config via (SET_TARGET, LOAD_AT) ================="
cmd 0x00200008 0x00000000                 ;# array reset
icm 0x00000000 [expr {0x0BC | (1<<11)}]   ;# target cell 0, load XOR
set l0 [rd_latch]
puts [format "  after LOAD_AT cell0=XOR : cell0 latch topo = 0x%03x  (want 0x0BC)  %s" \
      [expr {$l0 & 0x3FF}] [expr {($l0 & 0x3FF)==0x0BC ? "PASS" : "** FAIL **"}]]
icm 0x00000001 [expr {0x007 | (1<<11)}]   ;# target cell 1, load AND (different cell)
set l0b [rd_latch]
puts [format "  after LOAD_AT cell1=AND : cell0 latch topo = 0x%03x  (must stay 0x0BC)  %s" \
      [expr {$l0b & 0x3FF}] [expr {($l0b & 0x3FF)==0x0BC ? "PASS" : "** FAIL **"}]]
puts "  (both PASS: LOAD_AT hit cell 0, and targeting cell 1 left cell 0 intact)"
uc_close
puts "=== done ==="
