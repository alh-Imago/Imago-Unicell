# icm64_readstate.tcl — read everything the ISSP bridge can expose about cell state,
# and diagnose whether the SNAPSHOT mechanism itself is alive.
#
# IMPORTANT: the current bridge exposes ONLY CELL 0 (dbg0_*). There is no per-cell
# debug select in this bitstream, so "all cells" is not readable on die yet (that
# needs a debug-select RTL addition + reflash). This reads cell-0 across the views,
# and tests cycle_count ticking to tell "snapshot dead" from "cells empty".
#
# Run AFTER a config sequence (or run icm64_diag.tcl first to configure). Standalone
# it reads the post-reset state. quartus_stp -t icm64_readstate.tcl [INST] [HWM]

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

    # --- snapshot-alive test: cycle_count must change across two snapshots ---
    puts "--- snapshot health (cycle_count must TICK) ---"
    set c1 [fld [rd $INST 0x0] 31 0]; after 80
    set c2 [fld [rd $INST 0x0] 31 0]
    puts [format "  cycle_count: %u -> %u   %s" $c1 $c2 \
        [expr {$c2!=$c1 ? "OK (snapshot live, fabric clocking)" : \
               "** STATIC — snapshot not capturing OR clock dead; reads below will be zero **"}]]

    # --- configure the zone using the documented known-good sequence ---
    # (docs/V3_COMMAND_CONTRACT.md section 7 -- silicon-proven). NOTE:
    # CMD_ARRAY_RESET, CMD_BOOT_COMMIT, and CMD_RECONFIGURE are all BROADCASTS
    # (no config_match/addr_match gate in the RTL) -- this applies to every
    # cell in the zone (NUM_CELLS=25 in this build), not just cell 0. Only
    # CMD_LOAD_AT (opcode 23) is per-cell targeted. The debug READBACK below
    # is still limited to cell 0 only (no per-cell debug select in this
    # bitstream) -- that is a readback limitation, not a config limitation.
    # Auth token is an 11-bit field at cmd_bus[29:19] (module-port comment
    # calling it "[28:21], 8-bit" is STALE -- verified against this doc's
    # own proven sequence: 0x0528xxxx decodes to auth=0x0A5 at [29:19]).
    cmd $INST 0x05280008 0x00000000   ;# ARRAY_RESET   -> all cells to boot (clears stale state)
    cmd $INST 0x00000007 0x00A50000   ;# BOOT_COMMIT   -> RUN, auth_mask=0x0A5
    cmd $INST 0x00000018 0x00000000   ;# SET_TARGET    -> CELL_ID 0
    cmd $INST 0x05280003 0x00000200   ;# SET_OUTPUT_ADDR 0x200
    cmd $INST 0x05280004 0x5282082C   ;# RECONFIGURE   -> PASS_B, armed, latch_in
    cmd $INST 0x00000018 0x00000000   ;# SET_TARGET    -> CELL_ID 0
    cmd $INST 0x05280022 0x00000004   ;# ROUTING       -> east
    cmd $INST 0x00000018 0x00000000   ;# SET_TARGET    -> CELL_ID 0
    cmd $INST 0x05280023 0x00000001   ;# TRANSIT       -> route-across-only
    cmd $INST 0x00000018 0x00000000   ;# SET_TARGET    -> CELL_ID 0
    cmd $INST 0x05280012 0x00000000   ;# SWAP_AB       -> prime a_arrived
    cmd $INST 0x00000001 0x000000AA   ;# INJECT        -> addr 0, value 0xAA -> fires

    # --- CELL 0 latch view (selector 3): lower-32 cmd_latch, in, out ---
    set l [rd $INST 0x3]
    puts "--- CELL 0 latch (selector 3) — the ONLY cell exposed by this bitstream ---"
    puts [format "  cmd_latch\[31:0\] = 0x%08x   (topology\[9:0\]=0x%03x  armed=%d)" \
          [fld $l 79 48] [fld [fld $l 79 48] 9 0] [fld [fld $l 79 48] 22 22]]
    puts [format "  input_addr     = 0x%04x" [fld $l 95 80]]
    puts [format "  output_addr    = 0x%04x" [fld $l 47 32]]

    # --- CELL 0 a_data view (selector 4) ---
    set d [rd $INST 0x4]
    puts "--- CELL 0 a_data (selector 4) ---"
    puts [format "  a_data         = 0x%08x  (0xDA7A marker in armed field = %s)" \
          [fld $d 79 48] [expr {[fld $d 47 32]==0xDA7A ? "view OK" : "view MISMATCH"}]]

    # --- fired-output view (selector 0) ---
    set o [rd $INST 0x0]
    puts "--- fired output (selector 0) ---"
    puts [format "  out_seen=%d out_addr=0x%04x out_data=0x%08x out_count=%u armed_count=%u" \
          [fld $o 96 96] [fld $o 95 80] [fld $o 79 48] [fld $o 112 97] [fld $o 47 32]]

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== readstate done ==="
