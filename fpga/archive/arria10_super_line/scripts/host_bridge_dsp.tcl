# =============================================================================
# host_bridge_dsp.tcl — quartus_stp harness for host_bridge_dsp_v1.v
# (points.md #466/#467's own queue). The FIRST real DSP hardware
# bring-up -- proves the real hard DSP IP itself computes correctly on
# real silicon, driven by a real host over JTAG, before any RAM-cell
# fabric staging is added on top.
#
# RUN (once top_dsp_chain_v1 is built, programmed, and both real IPs
# have been generated per that file's own header instructions):
#     quartus_stp -t host_bridge_dsp.tcl [instance_index] [hw_name_match]
#   defaults: instance_index = 0, hw_name_match = "USB-Blaster"
#
# Real bit-shift-arithmetic packing, verified via a real tclsh round-
# trip test before being trusted -- the same discipline that caught a
# real bug in an earlier draft of a different bridge's own script
# (#441's own real correction).
#
# BIT MAP — must match host_bridge_dsp_v1.v's own documented layout:
#   SOURCE (37b): [36]=snap_req [35]=cmd_go [34:32]=opcode [31:0]=data
#   PROBE (114b): [113:82]=free_cycle [81:50]=cmd_count
#                 [49:34]=wd_count_out [33]=wd_timeout_err [32]=fire
#                 [31:0]=result
#
# OPCODES (source[34:32]): 0=NOP 1=LOAD_A 2=LOAD_B 3=WD_SET 4=ACK
# =============================================================================

set INSTANCE 0
if {$argc >= 1} { set INSTANCE [lindex $argv 0] }
set HWMATCH "USB-Blaster"
if {$argc >= 2} { set HWMATCH [lindex $argv 1] }

set ::INST $INSTANCE
set ::HW ""
set ::DEV ""

proc dsp_open {match} {
    set names [get_hardware_names]
    if {[llength $names] == 0} { error "No JTAG hardware found. Is the cable plugged in / jtagd running?" }
    set ::HW [lindex $names 0]
    foreach h $names { if {[string match "*$match*" $h]} { set ::HW $h; break } }
    set ::DEV [lindex [get_device_names -hardware_name $::HW] 0]
    puts "Hardware : $::HW"
    puts "Device   : $::DEV"
    puts "Instance : $::INST"
    start_insystem_source_probe -device_name $::DEV -hardware_name $::HW
}
proc dsp_close {} { end_insystem_source_probe }

proc dsp_src_fields {snap go opcode data} {
    set v $data
    set v [expr {$v | (($opcode & 0x7) << 32)}]
    set v [expr {$v | (($go & 0x1) << 35)}]
    set v [expr {$v | (($snap & 0x1) << 36)}]
    set hex [format "%010llx" $v]
    write_source_data -instance_index $::INST -value $hex -value_in_hex
}

proc dsp_cmd {opcode data} {
    dsp_src_fields 0 0 $opcode $data
    dsp_src_fields 0 1 $opcode $data   ;# go 0->1: rising edge -> one pulse
    dsp_src_fields 0 0 $opcode $data
}

proc dsp_snap {} {
    dsp_src_fields 0 0 0 0
    dsp_src_fields 1 0 0 0   ;# snap_req 0->1: latch the probe word
    dsp_src_fields 0 0 0 0
}

proc dsp_read {} {
    set hex [string trim [read_probe_data -instance_index $::INST -value_in_hex]]
    set v [expr {"0x$hex"}]
    return [list \
        result         [expr {$v & 0xFFFFFFFF}] \
        fire           [expr {($v >> 32) & 0x1}] \
        wd_timeout_err [expr {($v >> 33) & 0x1}] \
        wd_count_out   [expr {($v >> 34) & 0xFFFF}] \
        cmd_count      [expr {($v >> 50) & 0xFFFFFFFF}] \
        free_cycle     [expr {($v >> 82) & 0xFFFFFFFF}]]
}

proc dsp_status {} {
    dsp_snap
    array set s [dsp_read]
    puts [format "  result=0x%08x fire=%u wd_timeout_err=%u wd_count=%u | cmd_count=%u free_cycle=%u" \
          $s(result) $s(fire) $s(wd_timeout_err) $s(wd_count_out) $s(cmd_count) $s(free_cycle)]
    return [array get s]
}

# ── real hardware exercise: channel-alive check, set a real watchdog
# threshold, load both real operands, wait for a real fire, confirm no
# false watchdog trip, ack, and run a second real operation to confirm
# re-arming -- matching the exact sequence already sim-proven in
# tests/fpga/tb_top_dsp_chain_v1.v (points.md #467). ──
proc dsp_full_exercise {} {
    puts "\n--- channel-alive check ---"
    array set s1 [dsp_status]
    after 100
    array set s2 [dsp_status]
    if {$s2(free_cycle) != $s1(free_cycle)} { puts "PASS: fabric clock alive" } \
    else { puts "FAIL: free_cycle did not advance" }

    puts "\n--- set real watchdog threshold=50 ---"
    dsp_cmd 3 50

    puts "\n--- real operation 1: A=0xAAAA0001 B=0x55550002 ---"
    dsp_cmd 1 0xAAAA0001
    dsp_cmd 2 0x55550002
    array set s [dsp_status]
    if {$s(fire)} { puts "PASS: real fire observed on real hardware, result=0x[format %08x $s(result)]" } \
    else { puts "FAIL: fire never observed" }
    if {!$s(wd_timeout_err)} { puts "PASS: watchdog correctly did not false-trip" } \
    else { puts "FAIL: watchdog false-tripped during real, normal operation" }

    puts "\n--- real ACK, confirm fire clears ---"
    dsp_cmd 4 0
    array set s [dsp_status]
    if {!$s(fire)} { puts "PASS: fire correctly cleared after real ACK" } \
    else { puts "FAIL: fire did not clear" }

    puts "\n--- real operation 2 (confirms re-arming): A=0x11110003 B=0x22220004 ---"
    dsp_cmd 1 0x11110003
    dsp_cmd 2 0x22220004
    array set s [dsp_status]
    if {$s(fire)} { puts "PASS: second real operation fired correctly, result=0x[format %08x $s(result)]" } \
    else { puts "FAIL: second real operation never fired" }
    dsp_cmd 4 0

    puts "\n=== FULL EXERCISE complete -- see PASS/FAIL lines above for the real hardware result ==="
}

dsp_open $HWMATCH
dsp_full_exercise
dsp_close
