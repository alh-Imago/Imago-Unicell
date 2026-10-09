# =============================================================================
# host_bridge_bram_icm.tcl — quartus_stp harness for
# host_bridge_bram_icm_v1.v (points.md #430's own queue item 2, first
# real slice). The first real host-driven (not self-test-FSM-driven)
# hardware bring-up in this project's own history -- proves real BRAM
# read/write and real ICM (SUPER_LATCH) loading over actual JTAG.
#
# RUN (once top_bram_icm_hostbridge_v1 is built, programmed, and the
# real `issp_bram_icm` IP has been generated per that file's own header
# instructions):
#     quartus_stp -t host_bridge_bram_icm.tcl [instance_index] [hw_name_match]
#   defaults: instance_index = 0, hw_name_match = "USB-Blaster"
#
# Same discovery/open/close/source-write conventions as this project's
# existing `sentinel_issp.tcl` (deliberately mirrored, not reinvented).
#
# BIT MAP — must match host_bridge_bram_icm_v1.v's own documented layout:
#   SOURCE (91b): [90]=snap_req [89]=cmd_go [88:86]=opcode
#                 [85:84]=target(reserved,0) [83:80]=addr [79:0]=data
#   PROBE (112b): [111:80]=free_cycle [79:48]=cmd_count
#                 [47:43]=status_core_select [42]=icm_load_done
#                 [41]=bram_write_done [40]=bram_read_valid [39:0]=bram_rdata
#
# OPCODES (source[88:86]):
#   0=nop  1=BRAM_READ  2=BRAM_WRITE  3=ICM_LOAD
# =============================================================================

set INSTANCE 0
if {$argc >= 1} { set INSTANCE [lindex $argv 0] }
set HWMATCH "USB-Blaster"
if {$argc >= 2} { set HWMATCH [lindex $argv 1] }

set ::INST $INSTANCE
set ::HW ""
set ::DEV ""

# ── open / close ─────────────────────────────────────────────────────────────
proc hb_open {match} {
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
proc hb_close {} { end_insystem_source_probe }

# ── low-level source write: builds the full 91-bit value via real
# bit-shift arithmetic, then formats as hex in one shot. Tcl 8.6's
# arbitrary-precision integer support means `expr`/`format %llx` handle
# values well past 64 bits correctly -- confirmed directly via a real
# round-trip test (pack all-ones through every field, unpack via shifts,
# confirm every field reads back exactly) before this was trusted. An
# earlier draft split the value into hand-placed hex nibbles and was
# CONFIRMED WRONG by that same test -- it misaligned snap_req/cmd_go by
# not accounting for the field boundaries not landing on nibble
# boundaries. Real bit-shift arithmetic avoids that whole class of bug. ──
proc hb_src_fields {snap go opcode addr data} {
    set v $data
    set v [expr {$v | (($addr & 0xF) << 80)}]
    set v [expr {$v | ((0 & 0x3) << 84)}]      ;# target, reserved, always 0
    set v [expr {$v | (($opcode & 0x7) << 86)}]
    set v [expr {$v | (($go & 0x1) << 89)}]
    set v [expr {$v | (($snap & 0x1) << 90)}]
    set hex [format "%023llx" $v]
    write_source_data -instance_index $::INST -value $hex -value_in_hex
}

# ── inject one command: 1-cycle cmd_go pulse with the given opcode/addr/data ──
proc hb_cmd {opcode addr data} {
    hb_src_fields 0 0 $opcode $addr $data
    hb_src_fields 0 1 $opcode $addr $data   ;# go 0->1: rising edge -> one pulse
    hb_src_fields 0 0 $opcode $addr $data
}

# ── take a readback snapshot ───────────────────────────────────────────────
proc hb_snap {} {
    hb_src_fields 0 0 0 0 0
    hb_src_fields 1 0 0 0 0   ;# snap_req 0->1: latch the probe word
    hb_src_fields 0 0 0 0 0
}

# ── read + unpack the probe (112 bits -- Tcl's arbitrary-precision
# integer support via [expr] handles this fine on 64-bit builds; kept
# as explicit mask/shift for clarity, not performance) ──
proc hb_read {} {
    set hex [string trim [read_probe_data -instance_index $::INST -value_in_hex]]
    set v [expr {"0x$hex"}]
    return [list \
        bram_rdata      [expr {$v & 0xFFFFFFFFFF}] \
        bram_read_valid [expr {($v >> 40) & 0x1}] \
        bram_write_done [expr {($v >> 41) & 0x1}] \
        icm_load_done   [expr {($v >> 42) & 0x1}] \
        core_select     [expr {($v >> 43) & 0x1F}] \
        cmd_count       [expr {($v >> 48) & 0xFFFFFFFF}] \
        free_cycle      [expr {($v >> 80) & 0xFFFFFFFF}]]
}

proc hb_status {} {
    hb_snap
    array set s [hb_read]
    puts [format "  bram_rdata=0x%010x read_valid=%u write_done=%u | icm_load_done=%u core_select=%u | cmd_count=%u free_cycle=%u" \
          $s(bram_rdata) $s(bram_read_valid) $s(bram_write_done) \
          $s(icm_load_done) $s(core_select) $s(cmd_count) $s(free_cycle)]
    return [array get s]
}

# ── real hardware exercise: channel-alive check, then BRAM write/read,
# then ICM load, matching the exact sequence already sim-proven in
# tests/fpga/tb_top_bram_icm_hostbridge_v1.v ──
proc hb_full_exercise {} {
    puts "\n--- channel-alive check: free_cycle should be advancing ---"
    array set s1 [hb_status]
    after 100
    array set s2 [hb_status]
    if {$s2(free_cycle) != $s1(free_cycle)} { puts "PASS: free_cycle genuinely advancing -- fabric clock alive" } \
    else { puts "FAIL: free_cycle did not advance -- check config is actually loaded (see TOOLCHAIN_SETUP.md reboot-after-JTAG rule)" }

    puts "\n--- BRAM_WRITE addr=5 data=0xABCD, then BRAM_READ addr=5 ---"
    hb_cmd 2 5 0xABCD
    hb_cmd 1 5 0
    array set s [hb_status]
    if {$s(bram_rdata) == 0xABCD && $s(bram_read_valid)} { puts "PASS: real BRAM read-back correct on real hardware" } \
    else { puts "FAIL: expected rdata=0xABCD valid=1, got rdata=0x[format %x $s(bram_rdata)] valid=$s(bram_read_valid)" }

    puts "\n--- BRAM_WRITE addr=6 data=0x1234, then BRAM_READ addr=6 (confirms address decode, not a fluke) ---"
    hb_cmd 2 6 0x1234
    hb_cmd 1 6 0
    array set s [hb_status]
    if {$s(bram_rdata) == 0x1234 && $s(bram_read_valid)} { puts "PASS: second address confirmed correct on real hardware" } \
    else { puts "FAIL: expected rdata=0x1234 valid=1, got rdata=0x[format %x $s(bram_rdata)] valid=$s(bram_read_valid)" }

    puts "\n--- ICM_LOAD: core_select=3 (SEL_ACC) ---"
    hb_cmd 3 0 3
    array set s [hb_status]
    if {$s(icm_load_done) && $s(core_select) == 3} { puts "PASS: real ICM load confirmed on real hardware -- core_select=3 (SEL_ACC)" } \
    else { puts "FAIL: expected icm_load_done=1 core_select=3, got icm_load_done=$s(icm_load_done) core_select=$s(core_select)" }

    puts "\n--- ICM_LOAD: core_select=5 (SEL_LATCH), confirms the channel isn't a one-shot fluke ---"
    hb_cmd 3 0 5
    array set s [hb_status]
    if {$s(icm_load_done) && $s(core_select) == 5} { puts "PASS: second real ICM load confirmed on real hardware -- core_select=5 (SEL_LATCH)" } \
    else { puts "FAIL: expected icm_load_done=1 core_select=5, got icm_load_done=$s(icm_load_done) core_select=$s(core_select)" }

    puts "\n--- real cmd_count sanity: 6 real commands issued above (2 writes + 2 reads + 2 loads) ---"
    if {$s(cmd_count) == 6} { puts "PASS: cmd_count correctly tracks real injected commands ($s(cmd_count))" } \
    else { puts "FAIL: expected cmd_count=6, got $s(cmd_count)" }

    puts "\n=== FULL EXERCISE complete -- see PASS/FAIL lines above for the real hardware result ==="
}

hb_open $HWMATCH
hb_full_exercise
hb_close
