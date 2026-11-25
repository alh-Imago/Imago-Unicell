# inspect_shd_v1.tcl - READ ONLY: open the routed checkpoint of a build and print how Vivado built the shared data RAM `shd` (block 0): the RAMB18 settings and what drives its address, enable and clock pins.
# Why (ledger #1477): reads of the shared RAM in the Vivado-built bitstream return word 0's value whatever the address; one explanation is a different read latency than the RTL assumes.
# Usage (Vivado terminal, from s-core/k7):   vivado -mode batch -source vivado/inspect_shd_v1.tcl -tclargs hd8s4u1n1 2>&1 | tee inspect_shd_hd8s4u1n1.txt       UNTESTED (written without a Tcl interpreter)
set name [lindex $argv 0]
open_checkpoint vivado_out_$name/routed.dcp
set cells [get_cells -hier -filter {REF_NAME == RAMB18E1 && NAME =~ *shd_reg*}]
puts "shd RAMB18 cells found: [llength $cells]"
foreach c [lrange $cells 0 1] {
    puts "\n=== $c"
    foreach p {RAM_MODE READ_WIDTH_A WRITE_WIDTH_A WRITE_MODE_A DOA_REG READ_WIDTH_B WRITE_WIDTH_B WRITE_MODE_B DOB_REG IS_CLKARDCLK_INVERTED IS_CLKBWRCLK_INVERTED RDADDR_COLLISION_HWCONFIG} {
        if {[catch {set v [get_property $p $c]}]} { set v "(no such property)" }
        puts [format "  %-26s %s" $p $v]
    }
    foreach pn {CLKARDCLK CLKBWRCLK ENARDEN ENBWREN REGCEAREGCE WEA[0] WEBWE[0] ADDRARDADDR[5] ADDRARDADDR[6] ADDRARDADDR[7] ADDRARDADDR[8] ADDRARDADDR[9] ADDRARDADDR[10] ADDRARDADDR[11] ADDRARDADDR[12] ADDRARDADDR[13] ADDRBWRADDR[5] ADDRBWRADDR[6] ADDRBWRADDR[13]} {
        set pin [get_pins -quiet $c/$pn]
        if {$pin eq ""} { puts "  pin $pn : none"; continue }
        set net [get_nets -quiet -of_objects $pin]
        if {$net eq ""} { puts "  pin $pn : no net"; continue }
        set drv [get_pins -quiet -of_objects $net -filter {DIRECTION == OUT}]
        puts "  pin $pn : net $net  driven by [expr {$drv eq "" ? "(constant or port)" : "$drv ([get_property REF_NAME [get_cells -of_objects $drv]])"}]"
    }
}
