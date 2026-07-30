# zone1_route_latch_isolated.tcl — ISOLATED variant of zone1_route_latch.tcl
# (points.md #59, 2026-07-30 follow-up).
#
# The original zone1_route_latch.tcl deliberately re-primed via SWAP_AB with
# NO reset between cases, to test whether the same back-to-back-rearm
# hazard the FIRST (flawed) version of tb_v3_route_latch.v hit in sim would
# also show up on real silicon. It did -- worse than sim, in fact (see
# points.md #59 follow-up note): results drifted toward the HIGH pattern
# (N|E+local) across successive runs with no recompile/reboot between them.
#
# This variant isolates the variable the same way the CLEAN version of the
# sim testbench did (the one that passed all 9 checks): full CMD_ARRAY_RESET
# + reboot + reconfigure between every case, so each comparator evaluation
# starts from a genuinely clean cell state. If this comes back clean, the
# comparator/routing-latch mechanism itself is confirmed correct on real
# silicon, and the back-to-back-rearm timing hazard is confirmed real and
# separate -- worth its own investigation before the RAM-read runtime
# mechanism (which will do exactly this kind of rapid re-trigger).
#
#   quartus_stp -t zone1_route_latch_isolated.tcl [INST] [HWM]

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

    # Full setup, repeated FRESH before every case (CMD_ARRAY_RESET first --
    # per the opcode table this needs a nonzero auth_token in cmd_bus[28:21],
    # the same 0x0528 prefix already used everywhere else here).
    #
    # FIX (2026-07-30, after the first all-zero run): SET_TARGET (op24=0x18)
    # must be (re-)held before every config_match-gated command, same as
    # zone1_cardinal_edge.tcl's proven pattern -- this script originally
    # omitted it entirely, including before SWAP_AB (config_match-gated),
    # which most likely meant SWAP_AB never actually landed and the cell
    # never got a threshold primed at all -- an unconsummated first arrival
    # every time, no fire, explaining the deterministic all-zero result.
    proc setup_and_run_case {inst label value} {
        set TGT 0x0000
        cmd $inst 0x05280008 0x00000000          ;# CMD_ARRAY_RESET (auth): back to BOOT
        cmd $inst 0x00000007 0x00A50000          ;# BOOT_COMMIT -> RUN, auth 0xA5
        cmd $inst 0x00000018 $TGT                 ;# SET_TARGET (hold before RECONFIGURE)
        cmd $inst 0x05280004 0x0002082C           ;# RECONFIGURE: PASS_B+armed+latch_in+output_set
        cmd $inst 0x00000018 $TGT                 ;# re-hold target
        cmd $inst 0x05280025 0x45044005           ;# CMD_SET_ROUTE_LATCH (op37): same packed word
        cmd $inst 0x00000018 $TGT                 ;# re-hold target for the prime
        cmd $inst 0x05280012 0x00000050            ;# SWAP_AB: prime threshold a_data=0x50 (fresh cell)
        cmd $inst 0x00000001 $value                 ;# INJECT: addr=0, value in low bits
        after 60
        set n_seen    [fld [rd $inst 0x7] 32 32]
        set e_seen    [fld [rd $inst 0x5] 32 32]
        set lbus_seen [fld [rd $inst 0x6] 32 32]
        puts "=== CASE: $label (fresh reset+reconfigure) ==="
        puts [format "  north seen=%d   east seen=%d   local bus seen=%d" $n_seen $e_seen $lbus_seen]
        return [list $n_seen $e_seen $lbus_seen]
    }

    set low  [setup_and_run_case $INST "LOW  0x10 < threshold 0x50 -> expect pattern_low (E-only)"    0x00000010]
    puts [expr {([lindex $low 0]==0 && [lindex $low 1]==1) ? \
        "  VERDICT: PASS - east only, matches pattern_low" : \
        "  VERDICT: CHECK - expected north=0 east=1"}]

    set eq   [setup_and_run_case $INST "EQUAL 0x50 = threshold 0x50 -> expect pattern_equal (N-only)"  0x00000050]
    puts [expr {([lindex $eq 0]==1 && [lindex $eq 1]==0) ? \
        "  VERDICT: PASS - north only, matches pattern_equal" : \
        "  VERDICT: CHECK - expected north=1 east=0"}]

    set high [setup_and_run_case $INST "HIGH 0x90 > threshold 0x50 -> expect pattern_high (N|E)"       0x00000090]
    puts [expr {([lindex $high 0]==1 && [lindex $high 1]==1) ? \
        "  VERDICT: PASS - both N and E, matches pattern_high" : \
        "  VERDICT: CHECK - expected north=1 east=1"}]

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== zone1 route_latch (isolated) test done ==="
