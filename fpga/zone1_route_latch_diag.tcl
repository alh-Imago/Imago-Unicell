# zone1_route_latch_diag.tcl -- DIAGNOSTIC variant, reads a_data (view 4)
# directly right after each SWAP_AB, before injecting. Same no-reset
# sequence as zone1_route_latch.tcl, but instead of inferring what a_data
# must have been from the bridge outcome, this reads it directly.
#
#   quartus_stp -t zone1_route_latch_diag.tcl [INST] [HWM]

set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }

if {[catch {
    set ns [get_hardware_names]; set HW [lindex $ns 0]
    foreach h $ns { if {[string match "*$HWM*" $h]} { set HW $h; break } }
    set DEV [lindex [get_device_names -hardware_name $HW] 0]
    puts "Hardware : $HW"; puts "Device   : $DEV"
    start_insystem_source_probe -device_name $DEV -hardware_name $HW

    proc sf {inst snap go cmd data} { set hi [expr {(($snap&1)<<1)|($go&1)}]
        write_source_data -instance_index $inst -value [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]] -value_in_hex }
    proc cmd {inst cb cd} { sf $inst 0 0 $cb $cd; sf $inst 0 1 $cb $cd; sf $inst 0 0 $cb $cd }
    proc rd {inst sel} { sf $inst 1 0 $sel 0x0; sf $inst 0 0 $sel 0x0
        set s [read_probe_data -instance_index $inst -value_in_hex]
        return [expr {"0x[string trim $s]"}] }
    proc fld {v hi lo} { set w [expr {$hi-$lo+1}]; return [expr {($v>>$lo)&((1<<$w)-1)}] }

    set c1 [fld [rd $INST 0x0] 31 0]; after 80
    set c2 [fld [rd $INST 0x0] 31 0]
    puts [format "snapshot: cycle %u -> %u  %s" $c1 $c2 \
        [expr {$c2!=$c1 ? "OK" : "** STATIC (clock/snapshot dead) **"}]]

    # view4 = cell-0 data view: snap_out_data[79:48] = dbg0_a_data,
    # snap_armed[47:32] = fixed sentinel 0xDA7A (sanity check the read).
    proc read_a_data {inst label} {
        set v [rd $inst 0x4]
        set ad [fld $v 79 48]
        set sentinel [fld $v 47 32]
        puts [format "  \[%s\] a_data=0x%08x  (sentinel=0x%04x %s)" $label $ad $sentinel \
            [expr {$sentinel==0xDA7A ? "OK" : "** WRONG VIEW OR STALE READ **"}]]
        return $ad
    }

    # FIX (2026-07-30): one CMD_ARRAY_RESET at the very start ONLY -- NOT
    # between cases (that would defeat the point of this script). Discovered
    # that rst_all (= rst | array_rst_req | auth_rst_pulse) feeds the ISSP
    # bridge's sticky "seen" counters as well as the array itself -- meaning
    # this script, having never called CMD_ARRAY_RESET at all, was inheriting
    # whatever bridge-seen state was left over from WHATEVER RAN BEFORE IT
    # in the same session (e.g. the isolated test's own HIGH case, which
    # legitimately fires both bridges). Since a_data was already confirmed
    # correct in every case via the _diag script, this one reset establishes
    # a clean starting baseline for the sticky views without touching the
    # actual thing being tested (whether back-to-back re-priming corrupts
    # the comparator across cases).
    cmd $INST 0x05280008 0x00000000          ;# CMD_ARRAY_RESET (auth) -- baseline only

    # ---- One-time setup, identical to zone1_route_latch.tcl ----
    cmd $INST 0x00000007 0x00A50000          ;# BOOT_COMMIT -> RUN, auth 0xA5
    cmd $INST 0x05280004 0x0002082C          ;# RECONFIGURE: PASS_B+armed+latch_in+output_set
    cmd $INST 0x05280025 0x45044005           ;# CMD_SET_ROUTE_LATCH (op37)
    read_a_data $INST "after setup, before any case"

    proc run_case_diag {inst label value} {
        set TGT 0x0000
        cmd $inst 0x00000018 $TGT                 ;# SET_TARGET
        cmd $inst 0x05280012 0x00000050            ;# SWAP_AB: prime threshold a_data=0x50
        read_a_data $inst "$label: right after SWAP_AB, BEFORE inject"
        cmd $inst 0x00000001 $value                 ;# INJECT
        after 60
        read_a_data $inst "$label: after inject/fire"
        set n_seen    [fld [rd $inst 0x7] 32 32]
        set e_seen    [fld [rd $inst 0x5] 32 32]
        set lbus_seen [fld [rd $inst 0x6] 32 32]
        puts "=== CASE: $label ==="
        puts [format "  north seen=%d   east seen=%d   local bus seen=%d" $n_seen $e_seen $lbus_seen]
    }

    run_case_diag $INST "LOW  0x10 < threshold 0x50" 0x00000010
    run_case_diag $INST "EQUAL 0x50 = threshold 0x50" 0x00000050
    run_case_diag $INST "HIGH 0x90 > threshold 0x50" 0x00000090

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== zone1 route_latch DIAGNOSTIC done ==="
