# transit_diag.tcl — step-by-step diagnosis of the transit config+fire chain.
# Reads cell-0 state AFTER EACH stage so we can see exactly where it breaks,
# instead of only the final (currently all-zero) result.
#
#   quartus_stp -t transit_diag.tcl [INST] [HWM]

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

    proc show_cell0 {inst tag} {
        set l [rd $inst 0x3]
        set lat [fld $l 79 48]; set ia [fld $l 95 80]; set oa [fld $l 47 32]
        puts [format "  %-22s cmd_latch=0x%08x (topo=0x%03x start=%d latch_in=%d transit=%d rmask=0x%x) in=0x%04x out=0x%04x" \
            $tag $lat [fld $lat 9 0] [fld $lat 22 22] [fld $lat 26 26] [fld $lat 15 15] [fld $lat 14 11] $ia $oa]
    }

    set c1 [fld [rd $INST 0x0] 31 0]; after 60
    set c2 [fld [rd $INST 0x0] 31 0]
    puts [format "snapshot: %u -> %u  %s" $c1 $c2 [expr {$c2!=$c1?"OK":"** STATIC **"}]]

    set TGT 0x0000
    puts "--- STEP 0: post-reset state ---"
    show_cell0 $INST "post-reset"

    puts "--- STEP 1: BOOT_COMMIT (auth mask 0xA5, input 0) ---"
    cmd $INST 0x00000007 0x00A50000
    cmd $INST 0x00000018 $TGT
    show_cell0 $INST "after boot+target"

    puts "--- STEP 2: RECONFIGURE PASS_B armed (token 0x0A5) ---"
    cmd $INST 0x05280004 0x5282082C
    show_cell0 $INST "after reconfigure"

    puts "--- STEP 3: SET_OUTPUT_ADDR 0x200 ---"
    cmd $INST 0x00000018 $TGT
    cmd $INST 0x05280003 0x00000200
    show_cell0 $INST "after set_output"

    puts "--- STEP 4: routing=E, transit=1 ---"
    cmd $INST 0x00000018 $TGT
    cmd $INST 0x05280022 0x00000004
    cmd $INST 0x00000018 $TGT
    cmd $INST 0x05280023 0x00000001
    show_cell0 $INST "after routing+transit"

    puts "--- STEP 5: prime (SWAP_AB) + inject, read fire ---"
    cmd $INST 0x00000018 $TGT
    cmd $INST 0x05280012 0x00000000
    cmd $INST 0x00000001 [expr {($TGT<<16)|0x00AA}]
    after 40
    set o [rd $INST 0x0]
    puts [format "  fired: out_seen=%d out_addr=0x%04x out_data=0x%08x count=%u" \
        [fld $o 96 96] [fld $o 95 80] [fld $o 79 48] [fld $o 112 97]]
    set t [rd $INST 0x5]
    puts [format "  east : bre_seen=%d data=0x%08x addr=0x%04x" [fld $t 32 32] [fld $t 79 48] [fld $t 95 80]]

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== transit diag done ==="
