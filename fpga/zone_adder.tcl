# zone_adder.tcl — single-zone ADDER + chaining + addressing test (silicon).
#   quartus_stp -t zone_adder.tcl [instance] [hw_match]
#
# No rebuild needed: zone 0 physical addressing is flat 0..27, same as the flashed
# bitstream. Tests the half-adder primitive on cell 0 and the OR chain.
#   A and B are delivered as the TWO arrivals: inject A (1st -> stored), inject B
#   (2nd -> fires topology(A,B)). Preload sel writes only fixed 0/1 patterns, so
#   arbitrary operands must come from injects.
# Topology in RECONFIGURE low bits: XOR=0x0BC, AND=0x007, OR=0x024; base 0x52800800.
# Verified in sim (tb_zone_adder.v): XOR(0x0C,0x0A)=0x6, AND=0x8, chain ripples.

set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }
set ::INST $INST

proc uc_open {m} {
    set ns [get_hardware_names]; set ::HW [lindex $ns 0]
    foreach h $ns { if {[string match "*$m*" $h]} { set ::HW $h; break } }
    set ::DEV [lindex [get_device_names -hardware_name $::HW] 0]
    puts "Hardware : $::HW"; puts "Device   : $::DEV"
    start_insystem_source_probe -device_name $::DEV -hardware_name $::HW
}
proc uc_close {} { end_insystem_source_probe }
proc sf {snap go cmd data} {
    set hi [expr {(($snap&1)<<1)|($go&1)}]
    write_source_data -instance_index $::INST -value [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]] -value_in_hex
}
proc cmd {cb cd} { sf 0 0 $cb $cd; sf 0 1 $cb $cd; sf 0 0 $cb $cd }
proc rd {} {
    set v [expr {"0x[string trim [read_probe_data -instance_index $::INST -value_in_hex]]"}]
    return [list armed [expr {($v>>32)&0xFFFF}] out_data [expr {($v>>48)&0xFFFFFFFF}] \
                 out_addr [expr {($v>>80)&0xFFFF}] out_count [expr {($v>>97)&0xFFFF}]]
}
proc readview {v} { sf 0 0 $v 0; sf 1 0 $v 0; sf 0 0 0 0; return [rd] }
proc show {tag exp} {
    array set s [readview 0]
    set ok [expr {$s(out_data)==$exp ? "OK" : "** MISMATCH (want 0x[format %08x $exp]) **"}]
    puts [format "  %-12s out_count=%-3d out_addr=0x%04x out_data=0x%08x  %s" \
          $tag $s(out_count) $s(out_addr) $s(out_data) $ok]
}

# RECONFIGURE payloads (base | topology)
set RC_XOR 0x528008BC
set RC_AND 0x52800807
set RC_OR  0x52800824

uc_open $HWM

puts "================= SINGLE-ZONE ADDER TEST (cell 0, physical addr 0) ================="

puts "--- HALF-ADDER SUM : out = A XOR B ---"
cmd 0x00200008 0x00000000          ;# array reset
cmd 0x14A00003 0x00000200          ;# SET_OUTPUT_ADDR = 0x200
cmd 0x14A00004 $RC_XOR             ;# RECONFIGURE topology=XOR, armed
cmd 0x00000001 0x0000000C          ;# inject A=0x0C @ addr 0 (1st arrival -> stored)
cmd 0x00000001 0x0000000A          ;# inject B=0x0A @ addr 0 (2nd arrival -> fire)
show "XOR sum" 0x00000006           ;# expect 0x0C ^ 0x0A = 0x06

puts "--- HALF-ADDER CARRY : out = A AND B ---"
cmd 0x00200008 0x00000000
cmd 0x14A00003 0x00000200
cmd 0x14A00004 $RC_AND
cmd 0x00000001 0x0000000C
cmd 0x00000001 0x0000000A
show "AND carry" 0x00000008         ;# expect 0x0C & 0x0A = 0x08

puts "--- CHAIN + ADDRESSING : OR(0,B)=B ripples cell-to-cell ---"
cmd 0x00200008 0x00000000
cmd 0x14A00004 $RC_OR              ;# OR, default output CELL_ID+1
cmd 0x14A20000 0x00000000          ;# preload A=0 (sel=01)
cmd 0x00000001 0x00002340          ;# inject B=0x2340 @ addr 0
show "chain" 0x00002340             ;# B intact; out_count>1 and out_addr advanced = chain

puts "  (chain PASS = out_data 0x2340 AND out_count>1 AND out_addr>0x0001)"
uc_close
puts "=== done ==="
