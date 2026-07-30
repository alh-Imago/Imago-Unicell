# zone1_cardinal_edge.tcl — silicon proof of the PER-EDGE cardinal_edge
# primitive (points.md #42/#58, 2026-07-30) — the sim case tb_v3_cardinal_edge.v
# already proved, replayed on real Arria 10 zone1 silicon.
#
# Same proven sequence/auth framing as zone1_cardinals.tcl (auth prefix
# 0x0528, BOOT_COMMIT mask 0xA5), but this time routing TWO directions at
# once (N|E = routing_mask 5) and varying cardinal_edge instead of the old
# single transit_only bit:
#
#   Case A: cardinal_edge = E-only (4'b0100 = 4). E is cardinal-only, N is
#     not. EXPECT: north bridge seen=1, east bridge seen=1, AND local bus
#     seen=1 -- N (one of the two active routing directions) keeps local
#     alive even while E on the SAME fire is a pure conduit. This is the
#     new capability -- a single global transit_only bit could not produce
#     this combination.
#   Case B: cardinal_edge = N|E (4'b0101 = 5), legacy-equivalent -- every
#     active direction cardinal-only. EXPECT: both bridges seen=1, local
#     bus seen=0 -- matches the old global-bit result, now reached via the
#     granular field (METH_SET_CARDINAL_EDGE, opcode 36 = 0x24) instead of
#     METH_SET_TRANSIT (opcode 35 = 0x23, already proven separately in
#     zone1_cardinals.tcl / transit_smoke.tcl).
#
# REQUIRES: the cardinal_edge build of unicell64_v3.v (points.md #58) --
# only the cell RTL changed, no top-level/.qsf/.qsys change, so this is a
# straight recompile+reflash of the existing zone1 Quartus project, not a
# new project. Reflash BEFORE running (JTAG wipes BAR0/config space too --
# reboot after reprogramming before any subsequent PCIe test, standing rule).
#
#   quartus_stp -t zone1_cardinal_edge.tcl [INST] [HWM]

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

    # cardinal_val: cardinal_edge[3:0] payload (bit0=N,1=S,2=E,3=W), same bit
    # convention as routing_mask. north_view/east_view: ISSP sticky-capture
    # selectors for those two bridges (7=N, 5=E, per zone1_cardinals.tcl).
    proc run_case {inst label cardinal_val} {
        upvar 1 TGT TGT
        puts "=== CASE: $label (routing_mask=N|E=5, cardinal_edge=$cardinal_val) ==="
        cmd $inst 0x05280008 0x00000000          ;# CMD_ARRAY_RESET (auth): revert to BOOT, no reflash needed between cases
        cmd $inst 0x00000007 0x00A50000          ;# BOOT_COMMIT -> RUN, auth 0xA5
        cmd $inst 0x00000018 $TGT                 ;# SET_TARGET
        cmd $inst 0x05280003 0x00000200           ;# SET_OUTPUT_ADDR 0x200 (held target)
        cmd $inst 0x05280004 0x5282082C           ;# RECONFIGURE PASS_B armed (proven word)
        cmd $inst 0x00000018 $TGT                 ;# re-hold target
        cmd $inst 0x05280022 0x00000005            ;# METH_SET_ROUTING(op34=0x22): N|E = 5
        cmd $inst 0x00000018 $TGT
        cmd $inst 0x05280024 $cardinal_val         ;# METH_SET_CARDINAL_EDGE(op36=0x24): this case's mask
        cmd $inst 0x00000018 $TGT                  ;# hold target for the prime
        cmd $inst 0x05280012 0x00000000            ;# CMD_SWAP_AB (auth): primes a_arrived
        cmd $inst 0x00000001 [expr {($TGT<<16)|0x00AA}]  ;# INJECT: addr=TGT[31:16], value=0xAA
        after 60

        set tn [rd $inst 0x7]; set n_seen [fld $tn 32 32]
        set te [rd $inst 0x5]; set e_seen [fld $te 32 32]
        set l  [rd $inst 0x6]; set lbus_seen [fld $l 32 32]

        puts [format "  north bridge: seen=%d   east bridge: seen=%d   LOCAL bus seen=%d" \
            $n_seen $e_seen $lbus_seen]
        return [list $n_seen $e_seen $lbus_seen]
    }

    set caseA [run_case $INST "E-only cardinal (new: mixed edges)" 0x00000004]
    puts [expr {([lindex $caseA 0]==1 && [lindex $caseA 1]==1 && [lindex $caseA 2]==1) ? \
        "  VERDICT: PASS - both bridges crossed AND local still driven (N kept it alive)" : \
        "  VERDICT: CHECK - expected north=1 east=1 local=1"}]

    set caseB [run_case $INST "N|E cardinal (legacy-equivalent control)" 0x00000005]
    puts [expr {([lindex $caseB 0]==1 && [lindex $caseB 1]==1 && [lindex $caseB 2]==0) ? \
        "  VERDICT: PASS - both bridges crossed, local suppressed (matches old global-bit result)" : \
        "  VERDICT: CHECK - expected north=1 east=1 local=0"}]

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== zone1 cardinal_edge test done ==="
