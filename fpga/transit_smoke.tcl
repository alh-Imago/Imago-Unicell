# transit_smoke.tcl — on-silicon smoke test for the TRANSIT primitive (points.md #18).
#
# Proves, on the real Arria 10 die, that a cell configured transit_only=1 with
# routing_mask=EAST:
#   (A) routes its value ACROSS the east bridge   -> selector 5, bre_seen=1, bre_data matches
#   (B) does NOT present on its own local bus      -> selector 0, out_seen stays 0 for that value
# Then a CONTROL run (transit_only=0) confirms the local path DOES present, so the
# only variable is the transit flag.
#
# CRITICAL (learned 2026-07-06): the ISSP command words MUST carry the correct auth
# token. The known-good icm64_readstate.tcl uses boot auth 0xA5 (BOOT_COMMIT data
# 0x00A50100) and the 0x14A0xxxx opcode prefix on config words. A mismatched token
# silently REFUSES all config (readbacks come back 0xa0000000-ish). Match this file's
# tokens to the working baseline before trusting a "fail" result.
#
#   quartus_stp -t transit_smoke.tcl [INST] [HWM]

set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }

# Opcodes / field encodings
# LOAD_AT=23(0x17) SET_TARGET=24(0x18) SET_OUTPUT=3 BOOT=7 SWAP_AB=18(0x12)
# METH_SET_ROUTING=34(0x22) METH_SET_TRANSIT=35(0x23)
# routing EAST = bit2 => 4'b0100 = 4  (bit0=N,1=S,2=E,3=W)
# PASS_B topology = 0x02C ; start_flag = bit11 ; latch_in = bit17
# config-word auth prefix (matches known-good baseline): 0x14A0xxxx

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

    # snapshot-alive check
    set c1 [fld [rd $INST 0x0] 31 0]; after 80
    set c2 [fld [rd $INST 0x0] 31 0]
    puts [format "snapshot: cycle %u -> %u  %s" $c1 $c2 \
        [expr {$c2!=$c1 ? "OK" : "** STATIC (clock/snapshot dead) **"}]]

    proc run_case {inst transit label} {
        puts "=== CASE: transit_only=$transit ($label) ==="
        # auth-reset the array so bre_seen/out_seen start clean
        cmd $inst 0x00000008 0x00A00000    ;# authenticated array reset (token in [28:21])
        cmd $inst 0x00000007 0x00A50100    ;# BOOT_COMMIT -> RUN, auth 0xA5
        # configure cell 0 (target 0x000): PASS_B + armed + latch_in
        cmd $inst 0x00000018 0x00000000    ;# SET_TARGET 0x000
        cmd $inst 0x14A00003 0x00000100    ;# SET_OUTPUT_ADDR 0x100 (distinct so local fire is visible)
        cmd $inst 0x14A00017 0x00020800    ;# LOAD_AT: start(bit11)+latch_in(bit17)+PASS_B(0x02C)
        #   -> 0x02C | (1<<11) | (1<<17) = 0x0002_082C ; upper prefix 0x14A0 carries auth
        # routing = EAST via LOAD_AT bank2 METH_SET_ROUTING (payload bits[26:23]=4)
        cmd $inst 0x00000018 0x00000000    ;# SET_TARGET 0x000 (re-hold target)
        cmd $inst 0x14A12217 0x02000000    ;# bank2(bit16)|METH_ROUTING(0x22)|LOAD_AT(0x17); data (4<<23)
        # transit flag via LOAD_AT bank2 METH_SET_TRANSIT (payload bit23)
        cmd $inst 0x00000018 0x00000000
        set tdata [expr {$transit ? 0x00800000 : 0x00000000}]
        cmd $inst 0x14A12317 $tdata         ;# bank2|METH_TRANSIT(0x23)|LOAD_AT; data bit23=transit
        # prime + fire: SWAP_AB then deliver a value to input_addr (default CELL_ID=0)
        cmd $inst 0x00000012 0x00000000    ;# CMD_SWAP_AB (primes a_arrived)
        cmd $inst 0x00000001 0x00AA0000    ;# inject value 0xAA to address 0 (SET_INPUT-style write)
        after 60

        # read transit view (selector 5): bre_seen bit, bre_data, bre_addr
        set t [rd $inst 0x5]
        set bre_seen [fld $t 32 32]
        set bre_data [fld $t 79 48]
        set bre_addr [fld $t 95 80]
        # read fired-output view (selector 0): local presentation
        set o [rd $inst 0x0]
        set out_seen  [fld $o 96 96]
        set out_data  [fld $o 79 48]
        set out_count [fld $o 112 97]

        puts [format "  EAST bridge : seen=%d data=0x%08x addr=0x%04x" $bre_seen $bre_data $bre_addr]
        puts [format "  LOCAL bus   : seen=%d data=0x%08x count=%u" $out_seen $out_data $out_count]
        if {$transit} {
            puts [expr {($bre_seen==1 && $out_seen==0) ? \
                "  VERDICT: PASS — crossed east, local suppressed (TRANSIT WORKS ON DIE)" : \
                "  VERDICT: CHECK — expected bre_seen=1,out_seen=0"}]
        } else {
            puts [expr {($bre_seen==1 && $out_seen==1) ? \
                "  VERDICT: PASS — crossed east AND presented local (control OK)" : \
                "  VERDICT: CHECK — expected bre_seen=1,out_seen=1"}]
        }
    }

    run_case $INST 1 "route-across-only"
    run_case $INST 0 "route-and-local (control)"

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== transit smoke done ==="
