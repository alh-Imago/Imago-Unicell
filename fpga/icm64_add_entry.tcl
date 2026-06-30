# icm64_add_entry.tcl — ADDER ENTRY stage on silicon (64-bit cell, top_arria10_64/zone1).
# The two stage-0 cells of the packed adder = the model's ENTRY POINTS:
#   G = a & b   (cell0, AND, emit 0x200)
#   P = a ^ b   (cell1, XOR, emit 0x201)
# Present a,b at the entry; each fans to BOTH cells; two-arrival fires each. Mirrors
# tb_zone64_add_entry.v exactly: LOAD per-cell gates via LOAD_AT (op23, addr-gated, NOT
# broadcast RECONFIGURE — RECONFIGURE would smear one gate over both), FREEZE (inert),
# RELEASE as one (the controller->physics handoff), THEN present a,b.
#   a=0x1234, b=0xABCD -> G=a&b=0x00000204, P=a^b=0x0000B9F9
# Run: quartus_stp -t icm64_add_entry.tcl [INST] [HWM]

set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }
set ::INST $INST

proc uc_open {m} { set ns [get_hardware_names]; set ::HW [lindex $ns 0]
    foreach h $ns { if {[string match "*$m*" $h]} { set ::HW $h; break } }
    set ::DEV [lindex [get_device_names -hardware_name $::HW] 0]
    puts "Hardware : $::HW"; puts "Device   : $::DEV"
    start_insystem_source_probe -device_name $::DEV -hardware_name $::HW }
proc uc_close {} { end_insystem_source_probe }
proc sf {snap go cmd data} { set hi [expr {(($snap&1)<<1)|($go&1)}]
    write_source_data -instance_index $::INST -value [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]] -value_in_hex }
proc cmd {cb cd} { sf 0 0 $cb $cd; sf 0 1 $cb $cd; sf 0 0 $cb $cd }
proc rd_raw {} { sf 1 0 0x00000000 0x0; sf 0 0 0x00000000 0x0
    return [expr {"0x[string trim [read_probe_data -instance_index $::INST -value_in_hex]]"}] }

uc_open $HWM
puts "================= 64-bit adder ENTRY: G=a&b, P=a^b ================="

# --- LOAD: per-cell gates via LOAD_AT (addr-gated), output addrs, on physical CELL_ID targets ---
# G = cell0: AND, emit 0x200
cmd 0x00000018 0x00000000   ;# SET_TARGET cell0
cmd 0x14A00003 0x00000200   ;# SET_OUTPUT_ADDR 0x200
cmd 0x14A00017 0x52800807   ;# LOAD_AT cell0 = AND (0x007), armed (RC|gate)
# P = cell1: XOR, emit 0x201
cmd 0x00000018 0x00000001   ;# SET_TARGET cell1
cmd 0x14A00003 0x00000201   ;# SET_OUTPUT_ADDR 0x201
cmd 0x14A00017 0x528008BC   ;# LOAD_AT cell1 = XOR (0x0BC), armed

# --- FREEZE all (inert), then RELEASE as ONE = the controller->physics handoff ---
cmd 0x14A00005 0x00000000   ;# CMD_FREEZE (broadcast, auth)
cmd 0x14A00006 0x00000000   ;# CMD_RELEASE (broadcast) -> go live

# --- present a then b at the entry points (fan-out: a,b to BOTH cell0 and cell1) ---
cmd 0x00000001 0x00001234   ;# a=0x1234 -> cell0 [A]
cmd 0x00000001 0x0000ABCD   ;# b=0xABCD -> cell0 [B -> fire G]
cmd 0x00000001 0x00011234   ;# a=0x1234 -> cell1 [A]
cmd 0x00000001 0x0001ABCD   ;# b=0xABCD -> cell1 [B -> fire P]

# --- read the fired outputs (selector 0 = last fired out_data/out_addr/out_seen) ---
set v [rd_raw]
set seen [expr {($v>>96)&0x1}]
set od   [expr {($v>>48)&0xFFFFFFFF}]
set oa   [expr {($v>>80)&0xFFFF}]
puts [format "  last fired: out_addr=0x%04x out_data=0x%08x seen=%d" $oa $od $seen]
puts "  want: G(0x200)=0x00000204  P(0x201)=0x0000B9F9"
puts "  (probe shows the LAST fired cell; both should fire — re-run reads may show either."
puts "   For per-cell readback use DEBUG_SELECT build + icm64_readstate.tcl on cell0/cell1.)"
if {$seen && ($od==0x00000204 || $od==0x0000B9F9)} {
    puts "  >>> ENTRY firing on silicon (a fired output matches G or P)."
} else {
    puts "  >>> CHECK: no matching fired output (seen=$seen od=[format 0x%08x $od])."
}
uc_close
puts "=== done ==="
