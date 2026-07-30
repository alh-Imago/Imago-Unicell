# zone1_route_latch.tcl — silicon proof of the COMPARATOR + DYNAMIC ROUTING
# LATCH primitive (points.md #49/#51, 2026-07-30) — the sim case
# tb_v3_route_latch.v already proved, replayed on real Arria 10 zone1 silicon.
#
# ONE static cell configuration throughout (routing_mask=N|E open,
# cardinal_edge=all-local, dynamic_route_en=1, patterns loaded in one shot
# via the new CMD_SET_ROUTE_LATCH opcode=37). Threshold (a_data) re-primed
# to a fixed value before each case via CMD_SWAP_AB (op18) -- three
# different injected values against the SAME threshold take three
# genuinely different routes on hardware that was never reconfigured
# between cases (only re-armed):
#
#   pattern_low   = E-only (4) -- selected when incoming <  threshold
#   pattern_equal = N-only (1) -- selected when incoming == threshold
#   pattern_high  = N|E    (5) -- selected when incoming >  threshold
#
# REQUIRES: the routing-latch build of unicell64_v3.v (points.md #58 was
# cardinal_edge; this is the follow-on #49/#51 build, cmd_latch widened to
# 128 bits) -- cell-only RTL change, no top-level/.qsf/.qsys change, same
# recompile+reflash as #58 was. Reflash BEFORE running; reboot after
# reprogramming before any subsequent PCIe test (standing rule).
#
#   quartus_stp -t zone1_route_latch.tcl [INST] [HWM]

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

    # ── Setup: BOOT -> RUN, topology=PASS_B+armed+latch_in (CMD_RECONFIGURE),
    # then the whole routing latch in one CMD_SET_ROUTE_LATCH word.
    # auth prefix 0x0528 (auth_token=0xA5, matching BOOT_COMMIT's stored
    # auth_mask), same convention as zone1_cardinals.tcl/zone1_cardinal_edge.tcl.
    cmd $INST 0x00000007 0x00A50000          ;# BOOT_COMMIT -> RUN, auth 0xA5
    cmd $INST 0x05280004 0x0002082C          ;# RECONFIGURE: PASS_B+armed+latch_in+output_set
    # CMD_SET_ROUTE_LATCH (op37=0x25): routing_mask=5, cardinal_edge=0,
    # pattern_low=4, pattern_equal=1, pattern_high=5, dynamic_route_en=1.
    # Packed word: 0x45044005 (see tb_v3_route_latch.v for the bit-by-bit build).
    cmd $INST 0x05280025 0x45044005

    # cardinal_edge=0 (all-local) -- REUSING zone1_cardinals.tcl's proven
    # sticky-capture views: 7=north, 5=east, 6=local bus.
    proc run_case {inst label value} {
        cmd $inst 0x05280012 0x00000050            ;# SWAP_AB: re-prime threshold a_data=0x50
        cmd $inst 0x00000001 $value                 ;# INJECT: addr=0 (TGT[31:16]), value in low bits
        after 60
        set n_seen    [fld [rd $inst 0x7] 32 32]
        set e_seen    [fld [rd $inst 0x5] 32 32]
        set lbus_seen [fld [rd $inst 0x6] 32 32]
        puts "=== CASE: $label ==="
        puts [format "  north seen=%d   east seen=%d   local bus seen=%d" $n_seen $e_seen $lbus_seen]
        return [list $n_seen $e_seen $lbus_seen]
    }

    set low  [run_case $INST "LOW  0x10 < threshold 0x50 -> expect pattern_low (E-only)"    0x00000010]
    puts [expr {([lindex $low 0]==0 && [lindex $low 1]==1) ? \
        "  VERDICT: PASS - east only, matches pattern_low" : \
        "  VERDICT: CHECK - expected north=0 east=1"}]

    set eq   [run_case $INST "EQUAL 0x50 = threshold 0x50 -> expect pattern_equal (N-only)"  0x00000050]
    puts [expr {([lindex $eq 0]==1 && [lindex $eq 1]==0) ? \
        "  VERDICT: PASS - north only, matches pattern_equal" : \
        "  VERDICT: CHECK - expected north=1 east=0"}]

    set high [run_case $INST "HIGH 0x90 > threshold 0x50 -> expect pattern_high (N|E)"       0x00000090]
    puts [expr {([lindex $high 0]==1 && [lindex $high 1]==1) ? \
        "  VERDICT: PASS - both N and E, matches pattern_high" : \
        "  VERDICT: CHECK - expected north=1 east=1"}]

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== zone1 route_latch test done ==="

# ─────────────────────────────────────────────────────────────────────────────
# NOTE (from sim, tb_v3_route_latch.v): the FIRST version of the sim test ran
# all three cases back-to-back with NO reset between them, relying on
# latch_in's continuous rearm -- this produced a spurious extra EAST
# assertion on the EQUAL case that vanished once each case got a full
# array reset first. This tcl deliberately re-primes via SWAP_AB before
# each case (no reset) to test the SAME closer-to-real-use continuous-rearm
# path the sim first tried -- if the same spurious-extra-bridge symptom
# shows up here on silicon, that's a genuine finding about back-to-back
# re-arm timing (relevant to the upcoming RAM-read runtime mechanism, which
# will do exactly this kind of rapid re-trigger), not a route-latch bug --
# don't chase it as one. If it does NOT show up here, note that too: it
# would mean the sim-only artifact needed the full stimulus-timing
# characteristics of Icarus's zero-delay scheduling, not a real hazard.
