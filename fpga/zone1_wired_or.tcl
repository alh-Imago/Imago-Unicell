# zone1_wired_or.tcl — on-silicon reproduction of points.md #32 / tb_v3_wired_or.v
# (the sim testbench that PASSED 2026-07-10). Runs on the CURRENTLY FLASHED
# single-zone bitstream (top_arria10_zone1_v3.v) -- no reflash needed. #32's
# phenomenon lives entirely in unicell_array64_v3.v's existing wired-OR combine,
# already present on the die; this only needs the ordinary per-cell config
# opcodes (CMD_ARRAY_RESET, BOOT_COMMIT, SET_TARGET, RECONFIGURE, SET_OUTPUT_ADDR,
# CMD_SWAP_AB) that transit_smoke.tcl already proved work on this build, plus the
# existing default probe view (selector 0: out_seen/out_addr_l/out_data_l/out_count).
#
# SAME auth scheme as transit_smoke.tcl (11-bit auth_token=cmd_bus[29:19], stored
# mask 0x0A5 from BOOT_COMMIT's cmd_data[23:16]): config words carry prefix
# 0x0528xxxx.
#
# Three cells (CELL_ID 0,1,2 in zone z00), topology=PASS_A (output=own preloaded
# a_data, ignores the actual value of the second/triggering arrival -- isolates
# the bus-combine behaviour), all booted onto the SAME shared listen address
# (0x0000) so ONE inject triggers all three on the same tick.
#
#   RUN 1 (same_addr): all three -> output_address 100, data 0x1/0x2/0x4.
#     EXPECT: out_count==1, out_addr_l==100, out_data_l==0x7 (free OR reduction).
#   RUN 2 (diff_addr): cell0,1 -> 100, cell2 -> 101, same data.
#     EXPECT: out_count==1, out_addr_l==101 (LAST firer wins, not 100),
#             out_data_l==0x7 STILL (cell0/1's data bled into cell2's address).
#
#   quartus_stp -t zone1_wired_or.tcl [INST] [HWM]

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

    set SHARED_ADDR 0x0000

    # Configure one cell: topology=PASS_A + start_flag + latch_in via CMD_LOAD_AT
    # (opcode 23 -- config_match-gated on the address lane, per-cell targeted).
    # NOT CMD_RECONFIGURE (opcode 4): that opcode is auth_ok-gated ONLY, no
    # config_match, so it BROADCASTS to every cell regardless of SET_TARGET --
    # using it here would silently re-clear every earlier cell's a_arrived on
    # each subsequent cell's configuration pass (the exact documented anti-
    # pattern CMD_LOAD_AT exists to avoid). Then its own output_address, then
    # SWAP_AB-preload a_data (must be LAST -- both LOAD_AT and SET_OUTPUT_ADDR
    # clear a_arrived as a side effect).
    proc config_cell {inst target out_addr aval} {
        cmd $inst 0x00000018 $target             ;# SET_TARGET
        cmd $inst 0x05280017 0x00020800           ;# CMD_LOAD_AT (0x17=23): topology=PASS_A(0) + start_flag[11] + latch_in[17]
        cmd $inst 0x00000018 $target              ;# re-hold target
        cmd $inst 0x05280003 $out_addr             ;# SET_OUTPUT_ADDR
        cmd $inst 0x00000018 $target              ;# re-hold target
        cmd $inst 0x05280012 $aval                 ;# CMD_SWAP_AB: a_data=aval, a_arrived=1
    }

    proc run_case {inst label c0addr c1addr c2addr} {
        upvar 1 SHARED_ADDR SHARED_ADDR
        puts "=== CASE: $label ==="
        cmd $inst 0x05280008 0x00000000            ;# CMD_ARRAY_RESET (auth): all cells -> BOOT, counters clear
        cmd $inst 0x00000007 0x00A50000             ;# BOOT_COMMIT: shared listen addr 0, auth_mask=0xA5, all cells -> RUN

        config_cell $inst 0 $c0addr 0x1
        config_cell $inst 1 $c1addr 0x2
        config_cell $inst 2 $c2addr 0x4

        # Single shared trigger: one inject to the common listen address. All
        # three cells already have a_arrived=1 (from SWAP_AB) -- this is their
        # simultaneous SECOND arrival, so all three fire on the same tick.
        cmd $inst 0x00000001 [expr {($SHARED_ADDR<<16)|0x00AA}]
        after 60

        set o [rd $inst 0x0]
        set out_seen  [fld $o 96 96]
        set out_count [fld $o 112 97]
        set out_addr  [fld $o 95 80]
        set out_data  [fld $o 79 48]

        puts [format "  out_seen=%d out_count=%d out_addr=0x%04x out_data=0x%08x" \
            $out_seen $out_count $out_addr $out_data]
        return [list $out_count $out_addr $out_data]
    }

    set r1 [run_case $INST "same-addr (all -> 100)" 100 100 100]
    puts [expr {([lindex $r1 0]==1 && [lindex $r1 1]==100 && [lindex $r1 2]==7) ? \
        "  VERDICT: PASS - free N-way OR reduction (out_count=1, addr=100, data=0x7)" : \
        "  VERDICT: CHECK - expected out_count=1 addr=0x64 data=0x7"}]

    set r2 [run_case $INST "diff-addr (cell0,1 -> 100, cell2 -> 101)" 100 100 101]
    puts [expr {([lindex $r2 0]==1 && [lindex $r2 1]==101 && [lindex $r2 2]==7) ? \
        "  VERDICT: PASS - corruption mode confirmed (out_count=1, addr=101=LAST firer, data=0x7=contaminated)" : \
        "  VERDICT: CHECK - expected out_count=1 addr=0x65 data=0x7"}]

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== zone1 wired-OR test done ==="

# ─────────────────────────────────────────────────────────────────────────────
# NOTE: no reflash needed -- this rides the CURRENTLY flashed single-zone
# bitstream (the one transit_smoke.tcl / points.md #18 already proved). The
# phenomenon under test is in unicell_array64_v3.v, unrelated to the transit/
# routing_mask RTL that bitstream carries. If a reflash happens between now and
# running this (e.g. for the four-cardinal Step 1 build), this script still
# applies unchanged -- CMD_ARRAY_RESET + BOOT_COMMIT at the top of each case
# handles the "already running from a previous test" case exactly as
# transit_smoke.tcl does.
#
# CORRECTED 2026-07-10 (post first silicon run): the first version used
# CMD_RECONFIGURE for the topology write, which broadcasts to every cell
# (auth_ok-gated only, no config_match) -- each subsequent cell's config step
# silently re-cleared the PREVIOUS cell's a_arrived, so only the LAST configured
# cell ever ended up armed. Silicon showed exactly this: out_data==cell2's value
# alone in both cases, never the OR. Fixed to CMD_LOAD_AT (opcode 23,
# config_match-gated, per-cell targeted), matching tb_v3_wired_or.v exactly.
