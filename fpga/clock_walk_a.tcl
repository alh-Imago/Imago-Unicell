# clock_walk_a.tcl — reads Build A's 12-bit locked probe (points.md #30)
# Bit map: 0=1C_RX0 1=1C_RX1 2=1C_RX2 3=1C_RX3 4=1C_RX4 5=1C_RX5
#          6=1D_RX0 7=1D_RX1 8=1D_RX2 9=1D_RX3 10=1D_RX4 11=1D_RX5
#   quartus_stp -t clock_walk_a.tcl [INST] [HWM]

set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }

set NAMES {1C_RX0 1C_RX1 1C_RX2 1C_RX3 1C_RX4 1C_RX5 1D_RX0 1D_RX1 1D_RX2 1D_RX3 1D_RX4 1D_RX5}

if {[catch {
    set ns [get_hardware_names]; set HW [lindex $ns 0]
    foreach h $ns { if {[string match "*$HWM*" $h]} { set HW $h; break } }
    set DEV [lindex [get_device_names -hardware_name $HW] 0]
    puts "Hardware : $HW"; puts "Device   : $DEV"
    start_insystem_source_probe -device_name $DEV -hardware_name $HW

    proc read_probe {inst} {
        set s [read_probe_data -instance_index $inst -value_in_hex]
        return [expr {"0x[string trim $s]"}]
    }
    proc fld {v hi lo} { set w [expr {$hi-$lo+1}]; return [expr {($v>>$lo)&((1<<$w)-1)}] }

    set c1 [fld [read_probe 0] 43 12]; after 80
    set c2 [fld [read_probe 0] 43 12]
    puts [format "snapshot: cycle %u -> %u  %s" $c1 $c2 \
        [expr {$c2!=$c1 ? "OK" : "** STATIC (CLK dead, stop here) **"}]]

    if {$c2 == $c1} {
        puts "Not proceeding to read locked bits -- fix CLK first."
    } else {
    proc read_locked {inst} { return [fld [read_probe $inst] 11 0] }

    for {set i 0} {$i < 5} {incr i} {
        set v [read_locked $INST]
        puts [format "read %d: locked_bits = 0x%03x  (%012b)" $i $v $v]
        after 200
    }

    set v [read_locked $INST]
    set count 0
    set which {}
    for {set b 0} {$b < 12} {incr b} {
        if {($v >> $b) & 1} { incr count; lappend which "bit$b=[lindex $NAMES $b]" }
    }
    puts "=== RESULT (Build A: banks 1C+1D) ==="
    if {$count == 0} {
        puts "ZERO bits locked (out of 12). Run Build B next (banks 1E+1F) before"
        puts "sweeping I/O standards on this half."
    } elseif {$count == 1} {
        puts "EXACTLY ONE bit locked: $which -- likely candidate found."
    } else {
        puts "MULTIPLE bits locked ($count): $which -- worth a closer look."
    }
    }

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== clock walk (Build A) done ==="
