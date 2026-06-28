# icm64_probe_sanity.tcl — minimal: is the PROBE READ itself working?
# Reads the raw probe string (NO parsing) several times. Distinguishes:
#   - empty / short string  -> probe width or read mechanism wrong (ISSP IP)
#   - all-zeros, static      -> fabric not clocking (PLL/clock not reaching zones)
#   - non-zero, changing     -> probe live + fabric clocking (the earlier zero was a parse bug)
# Robust cleanup so a Tcl error can't crash quartus_stp. Run: quartus_stp -t icm64_probe_sanity.tcl

set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }

if {[catch {
    set ns [get_hardware_names]
    set HW [lindex $ns 0]
    foreach h $ns { if {[string match "*$HWM*" $h]} { set HW $h; break } }
    set DEV [lindex [get_device_names -hardware_name $HW] 0]
    puts "Hardware : $HW"
    puts "Device   : $DEV"
    start_insystem_source_probe -device_name $DEV -hardware_name $HW

    puts "--- raw probe reads (no snapshot trigger), repeated ---"
    for {set i 0} {$i < 5} {incr i} {
        set raw [read_probe_data -instance_index $INST -value_in_hex]
        puts [format "  read %d : len=%d  raw='%s'" $i [string length $raw] $raw]
        after 100
    }

    puts "--- now with a snapshot trigger (sel 0) between reads ---"
    proc sf {inst snap go cmd data} {
        set hi [expr {(($snap&1)<<1)|($go&1)}]
        write_source_data -instance_index $inst -value [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]] -value_in_hex
    }
    for {set i 0} {$i < 3} {incr i} {
        sf $INST 1 0 0x0 0x0
        sf $INST 0 0 0x0 0x0
        set raw [read_probe_data -instance_index $INST -value_in_hex]
        puts [format "  snap %d : len=%d  raw='%s'" $i [string length $raw] $raw]
        after 100
    }

    end_insystem_source_probe
} err]} {
    puts "ERROR: $err"
    catch { end_insystem_source_probe }
}
puts "=== probe sanity done ==="
