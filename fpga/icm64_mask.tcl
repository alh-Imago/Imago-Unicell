# icm64_mask.tcl — DATAPATH CONFIRM (nibble mask) for the 64-bit cell on the GX660 (top_arria10_64).
# Loads a PASS_B cell with a NIBBLE MASK via CMD_SET_METHOD (op 25), injects a value,
# and reads the FIRED output at probe selector 0. If out_data comes back with the masked
# nibbles zeroed, the 64-bit methodology datapath (nibble mask) works on silicon.
#
#   inject 0x01002340 ; mask_en + nibble_mask=0xF0 (block hi 4 nibbles) ; expect 0x00002340
#   (the A/B: WITHOUT the mask the same inject reads 0x01002340)
#
# Requires the top_arria10_64 bitstream (unicell_zone64, 25 cells/zone, op25 -> load_target).
# Mirrors tb_zone64_method.v exactly. Run: quartus_stp -t icm64_shift.tcl [INST] [HWM]

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
# snapshot at selector 0 (default view): fired out_data, out_seen
proc rd_raw {} { sf 1 0 0x00000000 0x0; sf 0 0 0x00000000 0x0
    return [expr {"0x[string trim [read_probe_data -instance_index $::INST -value_in_hex]]"}] }

uc_open $HWM
puts "================= 64-bit datapath confirm: nibble mask ================="
cmd 0x00000007 0x00A50100   ;# BOOT_COMMIT: logical=0x100, auth=0xA5, -> RUN
cmd 0x00000018 0x00000100   ;# SET_TARGET 0x100 (held target = run address)
cmd 0x14A00003 0x00000200   ;# SET_OUTPUT_ADDR=0x200 (addr_match-gated, on held target)
cmd 0x14A00004 0x5280082C   ;# RECONFIGURE PASS_B armed (broadcast + auth)
cmd 0x00000018 0x00000100   ;# SET_TARGET 0x100 (hold for SET_METHOD)
cmd 0x14A00019 0x000001F0   ;# CMD_SET_METHOD (op25, auth=0xA5): mask_en + nibble_mask=0xF0
cmd 0x14A40000 0x00000000   ;# preload -> a_arrived
cmd 0x00000001 0x01002340   ;# INJECT: addr=0x0100, value=0x01002340

set v [rd_raw]
set seen [expr {($v>>96)&0x1}]
set od   [expr {($v>>48)&0xFFFFFFFF}]
set oa   [expr {($v>>80)&0xFFFF}]
puts [format "  fired=%d  out_addr=0x%04x  out_data=0x%08x  (want 0x00002340 = 0x01002340 masked)" $seen $oa $od]
if {$seen && $od==0x00002340} {
    puts "  >>> PASS: nibble mask applied on silicon — 64-bit methodology datapath confirmed"
} elseif {$seen && $od==0x01002340} {
    puts "  >>> FAIL: fired but NOT masked — SET_METHOD/nibble mask not taking on die"
} else {
    puts [format "  >>> FAIL: no fire or unexpected (fired=%d out=0x%08x)" $seen $od]
}
uc_close
puts "=== done ==="
