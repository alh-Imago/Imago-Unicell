# =============================================================================
# sentinel_issp.tcl — quartus_stp harness for the sentinel_issp_bridge_v1
# JTAG channel (points.md #279/#281/#287)
#
# RUN (once a build with sentinel_issp_bridge_v1.v is compiled and
# programmed, and the real `issp` IP has been generated per that file's
# own header instructions):
#     quartus_stp -t sentinel_issp.tcl [instance_index] [hw_name_match]
#   defaults: instance_index = 0, hw_name_match = "USB-Blaster"
#
# Same discovery/open/close/source-write conventions as this project's
# existing `issp_unicell.tcl` (deliberately mirrored, not reinvented) --
# see that file for the general pattern this one follows.
#
# BIT MAP — must match sentinel_issp_bridge_v1.v's own documented layout:
#   SOURCE (66b): [65]=snap_req [64]=cmd_go [63:32]=cpu_bus(opcode in [7:0])
#                 [31:0]=cpu_data
#   PROBE (113b): [112:105]=reserved [104:89]=cmd_count [88:73]=chain_length
#                 [72:41]=diff (signed) [40:32]=flags [31:0]=cycle
#   flags bit order (bit0=LSB): need_data, results_ready, safe_to_intervene,
#     freeze_out, freeze_in, err_flag, err_negative, err_overflow, out_frozen
#
# OPCODES (cpu_bus[7:0], injected via cmd_go rising edge):
#   0=nop  1=feed_pulse  2=collect_pulse  3=out_wrap_pulse
#   4=host_unfreeze_pulse  5=set chain_length := cpu_data
# =============================================================================

set INSTANCE 0
if {$argc >= 1} { set INSTANCE [lindex $argv 0] }
set HWMATCH "USB-Blaster"
if {$argc >= 2} { set HWMATCH [lindex $argv 1] }

set ::INST $INSTANCE
set ::HW ""
set ::DEV ""

# ── open / close ─────────────────────────────────────────────────────────────
proc sn_open {match} {
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
proc sn_close {} { end_insystem_source_probe }

# ── low-level source write, same field-packing convention as issp_unicell.tcl
proc sn_src_fields {snap go cmd data} {
    set hi [expr {(($snap & 1) << 1) | ($go & 1)}]
    set hex [format "%x%08x%08x" $hi [expr {$cmd & 0xFFFFFFFF}] [expr {$data & 0xFFFFFFFF}]]
    write_source_data -instance_index $::INST -value $hex -value_in_hex
}

# ── inject one command: 1-cycle cmd_go pulse with the given opcode/data ───────
proc sn_cmd {opcode data} {
    sn_src_fields 0 0 $opcode $data
    sn_src_fields 0 1 $opcode $data ;# go 0->1: rising edge -> one pulse
    sn_src_fields 0 0 $opcode $data
}

# ── take a readback snapshot ───────────────────────────────────────────────
proc sn_snap {} {
    sn_src_fields 0 0 0 0
    sn_src_fields 1 0 0 0 ;# snap_req 0->1: latch the probe word
    sn_src_fields 0 0 0 0
}

# ── read + unpack the probe ─────────────────────────────────────────────────
proc sn_read {} {
    set hex [string trim [read_probe_data -instance_index $::INST -value_in_hex]]
    set v [expr {"0x$hex"}]
    set flags [expr {($v >> 32) & 0x1FF}]
    return [list \
        cycle          [expr {$v & 0xFFFFFFFF}] \
        need_data      [expr {$flags & 0x1}] \
        results_ready  [expr {($flags >> 1) & 0x1}] \
        safe           [expr {($flags >> 2) & 0x1}] \
        freeze_out     [expr {($flags >> 3) & 0x1}] \
        freeze_in      [expr {($flags >> 4) & 0x1}] \
        err_flag       [expr {($flags >> 5) & 0x1}] \
        err_negative   [expr {($flags >> 6) & 0x1}] \
        err_overflow   [expr {($flags >> 7) & 0x1}] \
        out_frozen     [expr {($flags >> 8) & 0x1}] \
        diff           [expr {($v >> 41) & 0xFFFFFFFF}] \
        chain_length   [expr {($v >> 73) & 0xFFFF}] \
        cmd_count      [expr {($v >> 89) & 0xFFFF}]]
}

# ── snapshot + read + pretty-print ──────────────────────────────────────────
proc sn_status {} {
    sn_snap
    array set s [sn_read]
    puts [format "  cycle=%u diff=%d chain_length=%u cmd_count=%u | need_data=%u results_ready=%u safe=%u | freeze_out=%u freeze_in=%u out_frozen=%u | err=%u (neg=%u overflow=%u)" \
          $s(cycle) $s(diff) $s(chain_length) $s(cmd_count) \
          $s(need_data) $s(results_ready) $s(safe) \
          $s(freeze_out) $s(freeze_in) $s(out_frozen) \
          $s(err_flag) $s(err_negative) $s(err_overflow)]
    return [array get s]
}

# =============================================================================
sn_open $HWMATCH

puts "\n--- channel-alive: cycle must advance between snapshots ---"
array set a [sn_status]
after 250
array set b [sn_status]
if {$b(cycle) != $a(cycle)} {
    puts "PASS: cycle moved [expr {$b(cycle) - $a(cycle)}] ticks — JTAG read path + fabric clock are live."
} else {
    puts "FAIL: cycle did not change. Check: correct .sof programmed, instance_index,"
    puts "      and that the IP was built with Use Source Clock = the real fabric clock."
}

puts "\n--- power-on state (points.md #287): should show need_data/results_ready/safe already set ---"
sn_status

puts "\n--- configuring chain_length=4 (opcode 5) ---"
sn_cmd 5 4
sn_status

puts "\ndone. Use sn_cmd {opcode data} + sn_status for further real hardware exercises --"
puts "e.g. 'sn_cmd 1 0' injects one feed_pulse, 'sn_cmd 4 0' unfreezes."

sn_close
