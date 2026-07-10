# zone1_cardinals.tcl — PLAN near-term Step 1: confirm CARDINAL routing works in
# all four directions. Only EAST was ever proven on silicon (points.md #18);
# this test exercises N/S/E/W identically, using the SAME proven transit_smoke.tcl
# sequence (auth prefix 0x0528, BOOT_COMMIT mask 0xA5), varying only the
# routing_mask payload and which sticky-capture view is read back.
#
# REQUIRES THE REFLASHED BUILD (top_arria10_zone1_v3.v + pcie/unicell_issp_bridge.v,
# 2026-07-10 changes): brings out N/S/W bridge sticky capture alongside the
# existing EAST one, selector views 7/8/9 (see unicell_issp_bridge.v header).
#
# routing_mask bit map (unicell_zone64_v3.v: fire_to_n/s/e/w from za_out_routing):
#   bit0=N(1)  bit1=S(2)  bit2=E(4)  bit3=W(8)
#
# Each direction: transit_only=1 (route-across ONLY) -- the cleanest single-
# direction signal, exactly the case points.md #18 already proved for EAST.
#   EXPECT per direction: that direction's bridge_seen=1, LOCAL bus lbus_seen=0.
#
#   quartus_stp -t zone1_cardinals.tcl [INST] [HWM]

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

    # dir_bit: routing_mask payload for this direction. view_sel: ISSP selector
    # for that direction's sticky-capture (5=E,7=N,8=S,9=W).
    proc run_direction {inst label dir_bit view_sel} {
        upvar 1 TGT TGT
        puts "=== CASE: $label (routing_mask=$dir_bit, view=$view_sel) ==="
        cmd $inst 0x05280008 0x00000000          ;# CMD_ARRAY_RESET (auth): revert to BOOT, no reflash needed between cases
        cmd $inst 0x00000007 0x00A50000          ;# BOOT_COMMIT -> RUN, auth 0xA5
        cmd $inst 0x00000018 $TGT                 ;# SET_TARGET
        cmd $inst 0x05280003 0x00000200           ;# SET_OUTPUT_ADDR 0x200 (held target)
        cmd $inst 0x05280004 0x5282082C           ;# RECONFIGURE PASS_B armed (proven word)
        cmd $inst 0x00000018 $TGT                 ;# re-hold target
        cmd $inst 0x05280022 $dir_bit              ;# METH_SET_ROUTING(op34=0x22): this direction's bit
        cmd $inst 0x00000018 $TGT
        cmd $inst 0x05280023 0x00000001            ;# METH_SET_TRANSIT(op35=0x23): transit_only=1 (route-across ONLY)
        cmd $inst 0x00000018 $TGT                  ;# hold target for the prime
        cmd $inst 0x05280012 0x00000000            ;# CMD_SWAP_AB (auth): primes a_arrived
        cmd $inst 0x00000001 [expr {($TGT<<16)|0x00AA}]  ;# INJECT: addr=TGT[31:16], value=0xAA
        after 60

        set t [rd $inst $view_sel]
        set seen [fld $t 32 32]
        set data [fld $t 79 48]
        set addr [fld $t 95 80]
        set l [rd $inst 0x6]
        set lbus_seen [fld $l 32 32]

        puts [format "  %s bridge : seen=%d data=0x%08x addr=0x%04x   LOCAL bus seen=%d" \
            [string toupper $label] $seen $data $addr $lbus_seen]
        puts [expr {($seen==1 && $lbus_seen==0) ? \
            "  VERDICT: PASS - crossed $label, local bus quiet (transit-only, as EAST already proved)" : \
            "  VERDICT: CHECK - expected seen=1 lbus_seen=0"}]
    }

    run_direction $INST "north" 1 0x7
    run_direction $INST "south" 2 0x8
    run_direction $INST "east"  4 0x5
    run_direction $INST "west"  8 0x9

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== zone1 cardinals test done ==="

# ─────────────────────────────────────────────────────────────────────────────
# REFLASH BEFORE RUNNING (same caveat as transit_smoke.tcl): this build changed
# top_arria10_zone1_v3.v (N/S/W bridge wiring + sticky capture) and
# pcie/unicell_issp_bridge.v (widened selector, 3 new views) -- a fresh Quartus
# compile + flash is required before this script will see anything on views
# 7/8/9. Bundle zone1_wired_or.tcl into the same JTAG session afterward (it
# needs no new RTL, but re-running it after this reflash re-confirms #32 still
# holds on the updated build).
