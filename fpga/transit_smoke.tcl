# transit_smoke.tcl — on-silicon smoke test for the TRANSIT primitive (points.md #18).
# REWRITTEN 2026-07-08 to build on the PROVEN fire sequence from icm64_diag.tcl
# (the earlier version used SWAP_AB + a wrong inject encoding and nothing fired).
#
# Proven pattern (from icm64_diag.tcl, known to fire a cell on this silicon):
#   BOOT_COMMIT (auth 0xA5) -> SET_TARGET 0 (CELL_ID) -> SET_OUTPUT_ADDR (held target)
#   -> RECONFIGURE(op4) PASS_B armed (0x5282082C) -> preload(0x14A4) -> INJECT(op1)
#   INJECT: opcode 1, cpu_data[31:16]=address(=input_address 0), cpu_data[15:0]=value.
#
# This test adds ONLY the routing + transit methodology writes on top of that
# proven sequence, then reads:
#   selector 5 (transit view): did the value cross the EAST bridge? (bre_seen)
#   selector 0 (fired output):  did it present on the LOCAL bus? (out_seen)
# transit=1 -> expect crossed + local suppressed ; transit=0 -> crossed + local present.
#
# AUTH (corrected 2026-07-08): this fresh build uses the 11-bit auth scheme --
# auth_token = cmd_bus[29:19], matched against stored auth_mask (cmd_latch[63:53],
# set at boot from cmd_data[23:16]). BOOT stores mask 0x0A5 (from 0x00A50000).
# Config words must therefore carry token 0x0A5 at [29:19] => prefix 0x0528xxxx
# (RECONFIGURE 0x05280004, SET_OUTPUT 0x05280003, ROUTING 0x05280022, TRANSIT
# 0x05280023), and preload (preload_sel=01 at [18:17]) => 0x052A0000.
# NOTE: the OLD baseline tcls (icm64_readstate/icm64_diag) use prefix 0x14A0xxxx,
# which put the token at the OLDER 8-bit position [28:21]; against THIS 11-bit
# RTL that decodes to token 0x294 != 0x0A5, so config is silently refused (only
# address-lane writes land -- exactly the 'input_addr sets but topology/armed
# stay 0' symptom seen on the first run). Those old tcls need the same 0x0528
# correction for this bitstream.
#
#   quartus_stp -t transit_smoke.tcl [INST] [HWM]

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

    set TGT 0x0000

    proc run_case {inst transit label} {
        upvar 1 TGT TGT
        puts "=== CASE: transit_only=$transit ($label) ==="
        cmd $inst 0x00000007 0x00A50000          ;# BOOT_COMMIT -> RUN, auth 0xA5
        cmd $inst 0x00000018 $TGT                 ;# SET_TARGET 0x100
        cmd $inst 0x05280003 0x00000200           ;# SET_OUTPUT_ADDR 0x200 (held target)
        cmd $inst 0x05280004 0x5282082C           ;# RECONFIGURE PASS_B armed (proven word)
        cmd $inst 0x00000018 $TGT                 ;# re-hold target
        cmd $inst 0x05280022 0x00000004           ;# METH_SET_ROUTING(op34=0x22): routing_mask=E(4)
        cmd $inst 0x00000018 $TGT
        set tdata [expr {$transit ? 0x00000001 : 0x00000000}]
        cmd $inst 0x05280023 $tdata               ;# METH_SET_TRANSIT(op35=0x23): transit_only bit0
        cmd $inst 0x00000018 $TGT                 ;# hold target for the prime
        cmd $inst 0x05280012 0x00000000           ;# CMD_SWAP_AB (auth): primes a_arrived (preload_sel REMOVED from RTL)
        cmd $inst 0x00000001 [expr {($TGT<<16)|0x00AA}]  ;# INJECT: addr=TGT[31:16], value=0xAA
        after 60

        set t [rd $inst 0x5]
        set bre_seen [fld $t 32 32]
        set bre_data [fld $t 79 48]
        set bre_addr [fld $t 95 80]
        set o [rd $inst 0x0]
        set out_seen  [fld $o 96 96]
        set out_data  [fld $o 79 48]
        set out_count [fld $o 112 97]

        puts [format "  EAST bridge : seen=%d data=0x%08x addr=0x%04x" $bre_seen $bre_data $bre_addr]
        puts [format "  LOCAL bus   : seen=%d data=0x%08x count=%u" $out_seen $out_data $out_count]
        if {$transit} {
            puts [expr {($bre_seen==1 && $out_seen==0) ? \
                "  VERDICT: PASS - crossed east, local suppressed (TRANSIT WORKS ON DIE)" : \
                "  VERDICT: CHECK - expected bre_seen=1,out_seen=0"}]
        } else {
            puts [expr {($bre_seen==1 && $out_seen==1) ? \
                "  VERDICT: PASS - crossed east AND presented local (control OK)" : \
                "  VERDICT: CHECK - expected bre_seen=1,out_seen=1"}]
        }
    }

    run_case $INST 1 "route-across-only"
    run_case $INST 0 "route-and-local (control)"

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== transit smoke done ==="
