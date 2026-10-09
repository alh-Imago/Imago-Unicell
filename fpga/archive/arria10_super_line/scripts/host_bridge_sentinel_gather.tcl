# =============================================================================
# host_bridge_sentinel_gather.tcl — quartus_stp harness for
# host_bridge_sentinel_gather_v1.v (points.md #430's own queue item 2,
# extension to the full mechanism). Drives the ENTIRE v2 sentinel+
# gather mechanism (top_sentinel_gather_shared_bram_v3.v) over real
# JTAG -- extends #441/#442's own real-hardware-confirmed single-cell
# bridge to all 4 configurable cells (H1/H2/H3/QUEUE), real per-chain
# unfreeze, and the real per-round ADVANCE the mechanism needs (it does
# NOT free-run once armed -- confirmed directly against the RTL).
#
# RUN (once top_sentinel_gather_shared_bram_v3 is built, programmed,
# and the real `issp_sentinel_gather` IP has been generated per that
# file's own header instructions):
#     quartus_stp -t host_bridge_sentinel_gather.tcl [instance_index] [hw_name_match]
#   defaults: instance_index = 0, hw_name_match = "USB-Blaster"
#
# Same bit-shift-arithmetic packing discipline as
# `host_bridge_bram_icm.tcl` (#441) -- that file's own first draft used
# hand-placed hex nibbles and was found WRONG by direct tclsh testing;
# this file builds every value with real shift/OR arithmetic and was
# verified the same way (a full round-trip test across every field,
# including the wider 158-bit PROBE) before being trusted.
#
# BIT MAP — must match host_bridge_sentinel_gather_v1.v's own documented
# layout exactly:
#   SOURCE (91b): [90]=snap_req [89]=cmd_go [88:86]=opcode
#                 [85:84]=target [83:80]=addr [79:0]=data
#   PROBE (158b): [157:126]=free_cycle [125:94]=cmd_count
#                 [93:62]=q_data_out_n [61:58]=h3_flags [57:54]=h2_flags
#                 [53:50]=h1_flags [49:45]=status_core_select
#                 [44]=advance_done [43]=unfreeze_done [42]=icm_load_done
#                 [41]=bram_write_done [40]=bram_read_valid [39:0]=bram_rdata
#   Each h*_flags nibble, bit order (0=LSB): need_data, results_ready,
#   safe, err.
#
# OPCODES (source[88:86]):
#   0=nop  1=BRAM_READ  2=BRAM_WRITE  3=ICM_LOAD  4=UNFREEZE  5=ADVANCE
# TARGETS (source[85:84], meaning depends on opcode):
#   ICM_LOAD: 0=H1 1=H2 2=H3 3=QUEUE.  UNFREEZE: 0=H1 1=H2 2=H3.
# =============================================================================

set INSTANCE 0
if {$argc >= 1} { set INSTANCE [lindex $argv 0] }
set HWMATCH "USB-Blaster"
if {$argc >= 2} { set HWMATCH [lindex $argv 1] }

set ::INST $INSTANCE
set ::HW ""
set ::DEV ""

proc sg_open {match} {
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
proc sg_close {} { end_insystem_source_probe }

# ── low-level source write: real bit-shift arithmetic, same verified
# technique as host_bridge_bram_icm.tcl's own (corrected) approach. ──
proc sg_src_fields {snap go opcode target addr data} {
    set v $data
    set v [expr {$v | (($addr & 0xF) << 80)}]
    set v [expr {$v | (($target & 0x3) << 84)}]
    set v [expr {$v | (($opcode & 0x7) << 86)}]
    set v [expr {$v | (($go & 0x1) << 89)}]
    set v [expr {$v | (($snap & 0x1) << 90)}]
    set hex [format "%023llx" $v]
    write_source_data -instance_index $::INST -value $hex -value_in_hex
}

proc sg_cmd {opcode target addr data} {
    sg_src_fields 0 0 $opcode $target $addr $data
    sg_src_fields 0 1 $opcode $target $addr $data   ;# go 0->1: rising edge -> one pulse
    sg_src_fields 0 0 $opcode $target $addr $data
}

proc sg_snap {} {
    sg_src_fields 0 0 0 0 0 0
    sg_src_fields 1 0 0 0 0 0   ;# snap_req 0->1: latch the probe word
    sg_src_fields 0 0 0 0 0 0
}

# ── read + unpack the 158-bit probe -- verified via a real round-trip
# test against a hand-packed reference before being trusted (see this
# file's own git history / points.md for the verification record). ──
proc sg_read {} {
    set hex [string trim [read_probe_data -instance_index $::INST -value_in_hex]]
    set v [expr {"0x$hex"}]
    return [list \
        bram_rdata       [expr {$v & 0xFFFFFFFFFF}] \
        bram_read_valid  [expr {($v >> 40) & 0x1}] \
        bram_write_done  [expr {($v >> 41) & 0x1}] \
        icm_load_done    [expr {($v >> 42) & 0x1}] \
        unfreeze_done    [expr {($v >> 43) & 0x1}] \
        advance_done     [expr {($v >> 44) & 0x1}] \
        core_select      [expr {($v >> 45) & 0x1F}] \
        h1_need_data     [expr {($v >> 50) & 0x1}] \
        h1_results_ready [expr {($v >> 51) & 0x1}] \
        h1_safe          [expr {($v >> 52) & 0x1}] \
        h1_err           [expr {($v >> 53) & 0x1}] \
        h2_need_data     [expr {($v >> 54) & 0x1}] \
        h2_results_ready [expr {($v >> 55) & 0x1}] \
        h2_safe          [expr {($v >> 56) & 0x1}] \
        h2_err           [expr {($v >> 57) & 0x1}] \
        h3_need_data     [expr {($v >> 58) & 0x1}] \
        h3_results_ready [expr {($v >> 59) & 0x1}] \
        h3_safe          [expr {($v >> 60) & 0x1}] \
        h3_err           [expr {($v >> 61) & 0x1}] \
        q_data_out_n     [expr {($v >> 62) & 0xFFFFFFFF}] \
        cmd_count        [expr {($v >> 94) & 0xFFFFFFFF}] \
        free_cycle       [expr {($v >> 126) & 0xFFFFFFFF}]]
}

proc sg_status {} {
    sg_snap
    array set s [sg_read]
    puts [format "  q_data_out_n=%u | h1(nd=%u rr=%u safe=%u err=%u) h2(nd=%u rr=%u safe=%u err=%u) h3(nd=%u rr=%u safe=%u err=%u) | cmd_count=%u free_cycle=%u" \
          $s(q_data_out_n) \
          $s(h1_need_data) $s(h1_results_ready) $s(h1_safe) $s(h1_err) \
          $s(h2_need_data) $s(h2_results_ready) $s(h2_safe) $s(h2_err) \
          $s(h3_need_data) $s(h3_results_ready) $s(h3_safe) $s(h3_err) \
          $s(cmd_count) $s(free_cycle)]
    return [array get s]
}

# ── real hardware exercise: config every cell, preload the shared BRAM,
# unfreeze every chain, then 12 real ADVANCE-driven rounds, matching
# the exact sequence already sim-proven in tests/fpga/
# tb_top_sentinel_gather_shared_bram_v3.v (points.md #443). ──

# Real SUPER_LATCH values, matching v2's own proven CFG_H1/H2/H3/CFG_Q
# exactly (core_select=3/SEL_ACC for H1-H3, each with inc_dir=N and a
# distinct downstream_mask; core_select=1/SEL_RAM for QUEUE). Computed
# via core_config=(downstream_mask<<8)|(dec_dir<<4)|inc_dir, full value
# =(core_config<<5)|core_select -- verified independently against the
# real RTL's own concatenation order (not just hand-computed once and
# trusted) before being used here.
set CFG_H1 0x4023   ;# downstream_mask=S(0010), dec_dir=0, inc_dir=N(0001), core_select=3
set CFG_H2 0x2023   ;# downstream_mask=N(0001), dec_dir=0, inc_dir=N(0001), core_select=3
set CFG_H3 0x8023   ;# downstream_mask=E(0100), dec_dir=0, inc_dir=N(0001), core_select=3
set CFG_Q  0x1021   ;# RAM core, matching v2's own real CFG_Q pattern, core_select=1

proc sg_full_exercise {} {
    global CFG_H1 CFG_H2 CFG_H3 CFG_Q

    puts "\n--- channel-alive check ---"
    array set s1 [sg_status]
    after 100
    array set s2 [sg_status]
    if {$s2(free_cycle) != $s1(free_cycle)} { puts "PASS: fabric clock alive" } \
    else { puts "FAIL: free_cycle did not advance" }

    puts "\n--- ICM_LOAD all 4 cells ---"
    sg_cmd 3 0 0 $CFG_H1
    sg_cmd 3 1 0 $CFG_H2
    sg_cmd 3 2 0 $CFG_H3
    sg_cmd 3 3 0 $CFG_Q
    array set s [sg_status]
    if {$s(icm_load_done)} { puts "PASS: all 4 cells configured" } else { puts "FAIL: icm_load_done not set" }

    puts "\n--- real preload: 12 BRAM writes (3 chains x 4-value blocks) ---"
    for {set i 0} {$i < 4} {incr i} {
        sg_cmd 2 0 $i             [expr {100 + $i}]
        sg_cmd 2 0 [expr {$i+4}]  [expr {200 + $i}]
        sg_cmd 2 0 [expr {$i+8}]  [expr {300 + $i}]
    }
    puts "PASS: 12 real BRAM writes issued"

    puts "\n--- UNFREEZE all 3 chains ---"
    sg_cmd 4 0 0 0
    sg_cmd 4 1 0 0
    sg_cmd 4 2 0 0
    array set s [sg_status]
    if {$s(unfreeze_done)} { puts "PASS: all 3 chains unfrozen" } else { puts "FAIL: unfreeze_done not set" }

    puts "\n--- 12 real ADVANCE-driven rounds ---"
    set expected_by_visit {1 2 3 4}
    set errors 0
    for {set r 0} {$r < 12} {incr r} {
        sg_cmd 5 0 0 0
        after 5   ;# real fabric completion is nanoseconds; this margin is generous
        array set s [sg_status]
        set visit [expr {$r / 3}]
        set expected [lindex $expected_by_visit $visit]
        if {$s(q_data_out_n) != $expected} {
            incr errors
            puts "FAIL: round $r -- q_data_out_n=$s(q_data_out_n), expected $expected"
        }
    }
    if {$errors == 0} { puts "PASS: all 12 real rounds produced the correct running result" }

    puts "\n--- final real completion status ---"
    array set s [sg_status]
    if {$s(h1_safe) && $s(h2_safe) && $s(h3_safe) && !$s(h1_err) && !$s(h2_err) && !$s(h3_err)} {
        puts "PASS: all 3 chains report real, correct completion status on real hardware"
    } else {
        puts "FAIL: not every chain reports safe completion with no errors"
    }

    puts "\n=== FULL EXERCISE complete -- see PASS/FAIL lines above for the real hardware result ==="
}

sg_open $HWMATCH
sg_full_exercise
sg_close
