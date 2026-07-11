# clock_walk.tcl — reads the clock-walk diagnostic's 32-bit `locked` probe
# (points.md #30, PLAN Step 2). Companion to fpga/verilog/clock_walk_top.v +
# fpga/quartus/clock_walk.qsf. v2 (2026-07-11): expanded from 8 to 32 bits.
#
# Bit map (see clock_walk_top.v header for the full pin table):
#   0  1C_CHT   1  1C_RX0  2  1C_RX1  3  1C_RX2  4  1C_RX3  5  1C_RX4  6  1C_RX5  7  1C_CHB
#   8  1D_CHT   9  1D_RX0  10 1D_RX1  11 1D_RX2  12 1D_RX3  13 1D_RX4  14 1D_RX5  15 1D_CHB (*)
#   16 1E_CHT   17 1E_RX0  18 1E_RX1  19 1E_RX2  20 1E_RX3  21 1E_RX4  22 1E_RX5  23 1E_CHB
#   24 1F_CHT   25 1F_RX0  26 1F_RX1  27 1F_RX2  28 1F_RX3  29 1F_RX4  30 1F_RX5  31 1F_CHB
#   (*) bit15 = the "strongest candidate" from v1 that turned out dead on all
#   4 legal I/O standards, on two independent physical cards.
#
# Bits 0,7,8,15,16,23,24,31 are the 8 dedicated CHT/CHB pins already tested in
# v1 (all dead on HCSL/LVDS/LVPECL/CML). Bits 1-6,9-14,17-22,25-30 are the 24
# NEW per-channel RX/REFCLKn pins, untested until this build.
#
# EXPECTED: exactly one bit set. If ZERO bits are ever set across several
# reads, do NOT conclude "none of them are wired" -- check the I/O standard
# first (this build defaults all 32 to HCSL; sweep LVDS/LVPECL/CML next, same
# as v1), per points.md #30's documented false-negative mode. If TWO OR MORE
# bits are set, that's also informative -- worth a closer look, not a discard.
#
#   quartus_stp -t clock_walk.tcl [INST] [HWM]

set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }

set NAMES {1C_CHT 1C_RX0 1C_RX1 1C_RX2 1C_RX3 1C_RX4 1C_RX5 1C_CHB \
           1D_CHT 1D_RX0 1D_RX1 1D_RX2 1D_RX3 1D_RX4 1D_RX5 1D_CHB \
           1E_CHT 1E_RX0 1E_RX1 1E_RX2 1E_RX3 1E_RX4 1E_RX5 1E_CHB \
           1F_CHT 1F_RX0 1F_RX1 1F_RX2 1F_RX3 1F_RX4 1F_RX5 1F_CHB}

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

    # LIVENESS CHECK FIRST -- same idiom as every zone1_*.tcl script. If this
    # doesn't advance, CLK never came alive and the locked bits below are
    # meaningless regardless of refclk pin or I/O standard.
    set c1 [fld [read_probe 0] 63 32]; after 80
    set c2 [fld [read_probe 0] 63 32]
    puts [format "snapshot: cycle %u -> %u  %s" $c1 $c2 \
        [expr {$c2!=$c1 ? "OK" : "** STATIC (CLK dead, stop here) **"}]]

    if {$c2 == $c1} {
        puts "Not proceeding to read locked bits -- fix CLK first."
    } else {
    proc read_locked {inst} { return [fld [read_probe $inst] 31 0] }

    # Read several times, a short interval apart -- a genuinely locked PLL
    # stays locked; a spurious/metastable read would be expected to wobble.
    for {set i 0} {$i < 5} {incr i} {
        set v [read_locked $INST]
        puts [format "read %d: locked_bits = 0x%08x  (%032b)" $i $v $v]
        after 200
    }

    set v [read_locked $INST]
    set count 0
    set which {}
    for {set b 0} {$b < 32} {incr b} {
        if {($v >> $b) & 1} {
            incr count
            lappend which "bit$b=[lindex $NAMES $b]"
        }
    }
    puts "=== RESULT ==="
    if {$count == 0} {
        puts "ZERO bits locked (out of 32). Do NOT conclude \"none of them\" --"
        puts "sweep the I/O standard next (this build defaults all 32 to HCSL;"
        puts "try LVDS/LVPECL/CML same as v1) before ruling anything out."
    } elseif {$count == 1} {
        puts "EXACTLY ONE bit locked: $which"
        puts "This is the expected result -- that pin carries the host's 100 MHz"
        puts "PCIe reference clock. Proceed to add the PCIe hard IP against this"
        puts "measured pin (docs/PCIE_ARRIA10_NOTES.md)."
    } else {
        puts "MULTIPLE bits locked ($count): $which"
        puts "Unexpected -- worth a closer look before picking one."
    }
    }

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== clock walk done ==="
