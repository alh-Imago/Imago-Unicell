# icm64_readstate_loop.tcl — repeatability check for §8a (PCIE_ARRIA10_NOTES.md).
#
# Runs the SAME config+readback sequence as icm64_readstate.tcl, N times in a
# row, inside ONE JTAG session (no reprogram, no reboot between iterations).
# Purpose: confirm the uart_rx tie-off fix (commit 1c5ea5e) is deterministic,
# not "got lucky once" -- expect every iteration to show armed=1,
# output_addr=0x0200, out_seen=1, matching the 2026-07-28 silicon-confirmed
# result. A single flaky iteration here would mean candidate 1 (floating
# UART_RX) isn't the whole story and candidate 3 (the 210d45e regression
# check) needs reopening.
#
# Usage: quartus_stp -t icm64_readstate_loop.tcl [N] [INST] [HWM]
#   N    — number of iterations (default 10)
#   INST — ISSP instance index (default 0, same as icm64_readstate.tcl)
#   HWM  — hardware name match (default "USB-Blaster")

set N 10
if {$argc >= 1} { set N [lindex $argv 0] }
set INST 0
if {$argc >= 2} { set INST [lindex $argv 1] }
set HWM "USB-Blaster"
if {$argc >= 3} { set HWM [lindex $argv 2] }

set pass_count 0
set fail_count 0

if {[catch {
    set ns [get_hardware_names]; set HW [lindex $ns 0]
    foreach h $ns { if {[string match "*$HWM*" $h]} { set HW $h; break } }
    set DEV [lindex [get_device_names -hardware_name $HW] 0]
    puts "Hardware : $HW"; puts "Device   : $DEV"
    puts "Running $N iterations of the config+readback sequence..."
    start_insystem_source_probe -device_name $DEV -hardware_name $HW

    proc sf {inst snap go cmd data} { set hi [expr {(($snap&1)<<1)|($go&1)}]
        set val [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]]
        set tries 0
        while {1} {
            if {![catch { write_source_data -instance_index $inst -value $val -value_in_hex } werr]} { return }
            incr tries
            if {$tries >= 5} { error "write_source_data failed after 5 retries: $werr" }
            puts "  (retry $tries/5: write_source_data glitch -- $werr)"
            after 50
        }
    }
    proc cmd {inst cb cd} { sf $inst 0 0 $cb $cd; sf $inst 0 1 $cb $cd; sf $inst 0 0 $cb $cd }
    proc rd {inst sel} { sf $inst 1 0 $sel 0x0; sf $inst 0 0 $sel 0x0
        set tries 0
        while {1} {
            if {![catch { read_probe_data -instance_index $inst -value_in_hex } s]} { break }
            incr tries
            if {$tries >= 5} { error "read_probe_data failed after 5 retries: $s" }
            puts "  (retry $tries/5: read_probe_data glitch -- $s)"
            after 50
        }
        return [expr {"0x[string trim $s]"}] }
    proc fld {v hi lo} { set w [expr {$hi-$lo+1}]; return [expr {($v>>$lo)&((1<<$w)-1)}] }

    for {set i 1} {$i <= $N} {incr i} {
        puts "\n=== iteration $i/$N ==="

        # snapshot-alive sanity, same as icm64_readstate.tcl
        set c1 [fld [rd $INST 0x0] 31 0]; after 30
        set c2 [fld [rd $INST 0x0] 31 0]
        set clocking [expr {$c2 != $c1}]

        # same known-good config sequence (docs/V3_COMMAND_CONTRACT.md §7)
        cmd $INST 0x05280008 0x00000000   ;# ARRAY_RESET
        cmd $INST 0x00000007 0x00A50000   ;# BOOT_COMMIT
        cmd $INST 0x00000018 0x00000000   ;# SET_TARGET -> CELL_ID 0
        cmd $INST 0x05280003 0x00000200   ;# SET_OUTPUT_ADDR 0x200
        cmd $INST 0x05280004 0x5282082C   ;# RECONFIGURE
        cmd $INST 0x00000018 0x00000000   ;# SET_TARGET -> CELL_ID 0
        cmd $INST 0x05280022 0x00000004   ;# ROUTING -> east
        cmd $INST 0x00000018 0x00000000   ;# SET_TARGET -> CELL_ID 0
        cmd $INST 0x05280023 0x00000001   ;# TRANSIT -> route-across-only
        cmd $INST 0x00000018 0x00000000   ;# SET_TARGET -> CELL_ID 0
        cmd $INST 0x05280012 0x00000000   ;# SWAP_AB
        cmd $INST 0x00000001 0x000000AA   ;# INJECT -> addr 0, value 0xAA

        set l [rd $INST 0x3]
        set cmd_latch  [fld $l 79 48]
        set armed      [fld [fld $l 79 48] 22 22]
        set output_addr [fld $l 47 32]

        set d [rd $INST 0x4]
        set marker_ok [expr {[fld $d 47 32] == 0xDA7A}]

        set o [rd $INST 0x0]
        set out_seen  [fld $o 96 96]
        set out_addr  [fld $o 95 80]
        set out_data  [fld $o 79 48]
        set out_count [fld $o 112 97]
        set armed_count [fld $o 47 32]

        puts [format "  clocking=%s cmd_latch=0x%08x armed=%d output_addr=0x%04x" \
              [expr {$clocking ? "OK" : "STATIC"}] $cmd_latch $armed $output_addr]
        puts [format "  marker_ok=%s out_seen=%d out_addr=0x%04x out_data=0x%08x out_count=%u armed_count=%u" \
              [expr {$marker_ok ? "OK" : "MISMATCH"}] $out_seen $out_addr $out_data $out_count $armed_count]

        # Pass criterion for this iteration: matches the 2026-07-28
        # silicon-confirmed pattern (armed=1, output_addr as set, output
        # actually fired, debug-view marker sane). Does NOT pin exact
        # out_count/armed_count values since those may legitimately vary
        # run to run depending on prior state -- only checks the invariants
        # that were broken pre-fix.
        if {$clocking && $armed == 1 && $output_addr == 0x0200 && $out_seen == 1 && $marker_ok} {
            puts "  -> PASS"
            incr pass_count
        } else {
            puts "  -> FAIL"
            incr fail_count
        }
    }

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; puts "--- full Tcl stack trace ---"; puts $::errorInfo; catch { end_insystem_source_probe } }

puts "\n=== summary: $pass_count/$N passed, $fail_count/$N failed ==="
if {$fail_count == 0 && $pass_count == $N} {
    puts "=== ALL ITERATIONS CONSISTENT -- fix looks deterministic ==="
} else {
    puts "=== INCONSISTENT RESULTS -- do not treat candidate 1 as fully closed, see PCIE_ARRIA10_NOTES.md 8a ==="
}
