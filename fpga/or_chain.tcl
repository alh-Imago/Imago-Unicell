# or_chain.tcl — minimal OR-cell CHAIN on silicon (self-contained, sources nothing).
#   quartus_stp -t or_chain.tcl [instance] [hw_match]
#
# Uses DEFAULT addressing (input=CELL_ID, output=CELL_ID+1) -> a natural chain.
# NO BOOT_COMMIT: cells stay in physical mode and route by CELL_ID, so cell N's
# output (N+1) feeds cell N+1's input. Preload A=0 -> OR(0,B)=B passes B down the
# chain unchanged. Inject B at addr 0; B should ripple to the chain end.
# Proven in sim (tb_zone_chain.v): fires>=2, value intact, out_addr advances.
#
# ORACLE: out_data = 0x00002340 (B, unchanged by OR-with-0 at each hop);
#         out_count > 1 (multiple cells fired = chain, not parallel);
#         out_addr advances past 0x0001 (output reached deeper cells).
# Within a zone the wave ripples (sim-proven); crossing zone boundaries exercises
# the inter-zone bridge path (less tested) — watch how far out_addr climbs.

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
    return [list armed [expr {($v>>32)&0xFFFF}] out_data [expr {($v>>48)&0xFFFFFFFF}] \
                 out_addr [expr {($v>>80)&0xFFFF}] out_count [expr {($v>>97)&0xFFFF}]]
}
proc readview {v} { sf 0 0 $v 0; sf 1 0 $v 0; sf 0 0 0 0; return [rd] }
proc count {sel} { array set s [readview $sel]; return $s(armed) }
proc show {tag} {
    # take a FRESH view-0 snapshot NOW, then read out_*. (Previously rd ran before
    # the snapshot, so out_* always showed the PREVIOUS step's state — e.g. the
    # "after inject" line displayed the pre-fire after-preload values.)
    array set s [readview 0]
    puts [format "  %-14s armed=%-3d arrived=%-3d  out_count=%-3d out_addr=0x%04x out_data=0x%08x" \
          $tag [count 0] [count 1] $s(out_count) $s(out_addr) $s(out_data)]
}

uc_open $HWM
puts "=== STEP 1: array reset ==="
cmd 0x00200008 0x00000000
show "fresh"
puts "=== STEP 2: RECONFIGURE OR (broadcast, physical mode -> CELL_ID chain) ==="
cmd 0x14A00004 0x52800824   ;# topology OR=0x024, start_flag, auth_mask=0xA5
show "after OR cfg"
puts "    expect armed=448"
puts "=== STEP 3: preload A=0 (sel=01) -> OR(0,B)=B passthrough ==="
cmd 0x14A20000 0x00000000
show "after preload"
puts "    expect arrived=448"
puts "=== STEP 4: inject B=0x2340 at addr 0 ==="
cmd 0x00000001 0x00002340
show "after inject"
puts "    ORACLE: out_data=0x00002340 (B intact), out_count>1 (chain), out_addr advanced"
puts "    PASS: out_count=28, out_addr=0x001c => full within-zone chain (28 cells)"
puts "    out_addr stops at 0x001c (cell 27 -> addr 28, no cell 28 in zone):"
puts "    crossing into the next zone needs the inter-zone BRIDGE path = next."
uc_close
puts "=== done ==="
