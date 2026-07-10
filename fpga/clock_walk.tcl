# clock_walk.tcl — reads the clock-walk diagnostic's 8-bit `locked` probe
# (points.md #30, PLAN Step 2). Companion to fpga/verilog/clock_walk_top.v +
# fpga/quartus/clock_walk.qsf. No source/command protocol needed -- this is a
# read-only probe, so no cmd_go/snap_req dance like the fabric bridge scripts.
#
# Bit map (see clock_walk_top.v header for the full pin table):
#   0 REFCLK_GXBL1C_CHT   1 REFCLK_GXBL1C_CHB   2 REFCLK_GXBL1D_CHT
#   3 REFCLK_GXBL1D_CHB (strongest candidate)   4 REFCLK_GXBL1E_CHT
#   5 REFCLK_GXBL1E_CHB   6 REFCLK_GXBL1F_CHT   7 REFCLK_GXBL1F_CHB
#
# EXPECTED: exactly one bit set (IEI ties the other 7 refclk pins to GND per
# PCG-01017). If ZERO bits are ever set across several reads, do NOT conclude
# "none of them are wired" -- check the I/O standard first (HCSL vs AC-coupled
# alternatives), per points.md #30's documented false-negative mode. If TWO OR
# MORE bits are set, that's also informative (IEI wired something unexpected)
# -- worth a closer look, not a discard.
#
#   quartus_stp -t clock_walk.tcl [INST] [HWM]

set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }

set NAMES {REFCLK_GXBL1C_CHT REFCLK_GXBL1C_CHB REFCLK_GXBL1D_CHT REFCLK_GXBL1D_CHB \
           REFCLK_GXBL1E_CHT REFCLK_GXBL1E_CHB REFCLK_GXBL1F_CHT REFCLK_GXBL1F_CHB}

if {[catch {
    set ns [get_hardware_names]; set HW [lindex $ns 0]
    foreach h $ns { if {[string match "*$HWM*" $h]} { set HW $h; break } }
    set DEV [lindex [get_device_names -hardware_name $HW] 0]
    puts "Hardware : $HW"; puts "Device   : $DEV"
    start_insystem_source_probe -device_name $DEV -hardware_name $HW

    proc read_locked {inst} {
        set s [read_probe_data -instance_index $inst -value_in_hex]
        return [expr {"0x[string trim $s]"}]
    }

    # Read several times, a short interval apart -- a genuinely locked PLL
    # stays locked; a spurious/metastable read would be expected to wobble.
    for {set i 0} {$i < 5} {incr i} {
        set v [read_locked $INST]
        puts [format "read %d: locked_bits = 0x%02x  (%08b)" $i $v $v]
        after 200
    }

    set v [read_locked $INST]
    set count 0
    set which {}
    for {set b 0} {$b < 8} {incr b} {
        if {($v >> $b) & 1} {
            incr count
            lappend which "bit$b=[lindex $NAMES $b]"
        }
    }
    puts "=== RESULT ==="
    if {$count == 0} {
        puts "ZERO bits locked. Do NOT conclude \"none of them\" -- check the I/O"
        puts "standard (HCSL vs AC-coupled) before ruling anything out."
    } elseif {$count == 1} {
        puts "EXACTLY ONE bit locked: $which"
        puts "This is the expected result -- that pin pair carries the host's"
        puts "100 MHz PCIe reference clock. Proceed to add the PCIe hard IP"
        puts "against this measured pin (docs/PCIE_ARRIA10_NOTES.md)."
    } else {
        puts "MULTIPLE bits locked ($count): $which"
        puts "Unexpected -- IEI wired more than one refclk pin, or a false lock"
        puts "(e.g. a floating/AC-coupled pin near its threshold). Worth a closer"
        puts "look before picking one."
    }

    end_insystem_source_probe
} err]} { puts "ERROR: $err"; catch { end_insystem_source_probe } }
puts "=== clock walk done ==="
