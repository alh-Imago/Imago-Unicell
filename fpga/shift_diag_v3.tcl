# =============================================================================
# shift_diag_v3.tcl — SELF-CONTAINED inject-path diagnostic (sources nothing).
#
#   quartus_stp -t shift_diag_v3.tcl [instance_index] [hw_name_match]
#   defaults: instance_index = 0, hw_name_match = "USB-Blaster"
#
# Inlines its own primitives on purpose: issp_unicell.tcl runs a test body and
# closes the session when sourced, so harnesses must not depend on it.
#
# Needs the rebuild with arrived_count / output_set_count instrumentation.
# Counters via uc_count: 0=armed 1=arrived 2=output_set (selector = cpu_bus[1:0]
# at snapshot; bridge reports the chosen counter in the armed probe slot).
#
# PROBE (113b): [112:97]out_count [96]out_seen [95:80]out_addr
#               [79:48]out_data   [47:32]armed   [31:0]cycle
# SOURCE (66b): [65]snap_req [64]cmd_go [63:32]cpu_bus [31:0]cpu_data
# =============================================================================

set INSTANCE 0
if {$argc >= 1} { set INSTANCE [lindex $argv 0] }
set HWMATCH "USB-Blaster"
if {$argc >= 2} { set HWMATCH [lindex $argv 1] }
set ::INST $INSTANCE

proc uc_open {match} {
    set names [get_hardware_names]
    if {[llength $names] == 0} { error "No JTAG hardware found." }
    set ::HW [lindex $names 0]
    foreach h $names { if {[string match "*$match*" $h]} { set ::HW $h; break } }
    set ::DEV [lindex [get_device_names -hardware_name $::HW] 0]
    puts "Hardware : $::HW"
    puts "Device   : $::DEV"
    start_insystem_source_probe -device_name $::DEV -hardware_name $::HW
}
proc uc_close {} { end_insystem_source_probe }

proc uc_src_fields {snap go cmd data} {
    set hi [expr {(($snap & 1) << 1) | ($go & 1)}]
    set hex [format "%x%08x%08x" $hi [expr {$cmd & 0xFFFFFFFF}] [expr {$data & 0xFFFFFFFF}]]
    write_source_data -instance_index $::INST -value $hex -value_in_hex
}
proc uc_cmd {cmd_word data_word} {
    uc_src_fields 0 0 $cmd_word $data_word
    uc_src_fields 0 1 $cmd_word $data_word
    uc_src_fields 0 0 $cmd_word $data_word
}
proc uc_read {} {
    set hex [string trim [read_probe_data -instance_index $::INST -value_in_hex]]
    set v [expr {"0x$hex"}]
    return [list \
        cycle     [expr {$v & 0xFFFFFFFF}] \
        armed     [expr {($v >> 32) & 0xFFFF}] \
        out_data  [expr {($v >> 48) & 0xFFFFFFFF}] \
        out_addr  [expr {($v >> 80) & 0xFFFF}] \
        out_seen  [expr {($v >> 96) & 0x1}] \
        out_count [expr {($v >> 97) & 0xFFFF}]]
}
# selected aggregate counter: cpu_bus[1:0]=sel at snapshot -> armed slot = count
proc uc_count {sel} {
    uc_src_fields 0 0 $sel 0
    uc_src_fields 1 0 $sel 0
    uc_src_fields 0 0 0 0
    array set s [uc_read]
    return $s(armed)
}
proc counts {tag} {
    set a [uc_count 0]; set o [uc_count 2]; set r [uc_count 1]
    array set s [uc_read]
    puts [format "  %-16s armed=%-3d output_set=%-3d arrived=%-3d out_count=%d out_data=0x%08x" \
          $tag $a $o $r $s(out_count) $s(out_data)]
}
# read cell-0's actual internal latches (broadcast config -> cell 0 represents all)
proc uc_dump {tag} {
    uc_src_fields 0 0 3 0 ; uc_src_fields 1 0 3 0 ; uc_src_fields 0 0 0 0
    array set v [uc_read]
    uc_src_fields 0 0 4 0 ; uc_src_fields 1 0 4 0 ; uc_src_fields 0 0 0 0
    array set w [uc_read]
    puts [format "      cell0: cmd_latch=0x%08x input_addr=0x%04x output_addr=0x%04x a_data=0x%08x" \
          $v(out_data) $v(out_addr) $v(armed) $w(out_data)]
}

# ═════════════════════════════════════════════════════════════════════════════
uc_open $HWMATCH

puts "=== STEP 1: fresh ==="
uc_cmd 0x00200008 0x00000000
counts "fresh"

puts "=== STEP 2: configure PASS_B, in=0x100 out=0x200, auth=0xA5 ==="
uc_cmd 0x00000007 0x00A50100   ;# BOOT_COMMIT
uc_cmd 0x14A00003 0x00000200   ;# SET_OUTPUT_ADDR  (must precede arming)
uc_cmd 0x14A00004 0x5280082C   ;# RECONFIGURE PASS_B armed  (arms + locks auth -> last)
counts "after config"
  uc_dump "after config"
puts "    expect armed=448 output_set=448 arrived=0"

puts "=== STEP 3: preload (sets a_arrived) ==="
uc_cmd 0x14A40000 0x00000000
counts "after preload"
  uc_dump "after preload"
puts "    expect arrived=448  (if 0 -> command/preload not reaching cells)"

puts "=== STEP 4: plain inject W=0x01002340 ==="
uc_cmd 0x00000001 0x01002340
counts "after inject"
  uc_dump "after inject"
puts "    KEY: arrived 448->~0 => inject REACHED cells (zone fix live)"
puts "         arrived stays 448 => inject DROPPED (fix not in bitstream)"
puts "         arrived dropped but out_count=0 => output path, not inject"

uc_close
puts "=== done ==="
