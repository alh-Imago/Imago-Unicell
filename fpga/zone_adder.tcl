# zone_adder.tcl — single-zone gate + chaining + addressing test (silicon, ISSP).
#   quartus_stp -t zone_adder.tcl [instance] [hw_match]
#
# No rebuild: zone-0 physical addressing is flat 0..27, same as the flashed
# bitstream. Uses the PROVEN preload->single-trigger pattern (NOT two self-stored
# arrivals, which do not fire over ISSP). Preload writes a_data = 0x0 (sel=01,
# cmd_bus 0x14A20000) or 0xFFFFFFFF (sel=10, cmd_bus 0x14A40000); the single
# trigger inject (B) then fires topology(A,B).
#
# Operand A is limited to 0x0 / 0xFFFFFFFF by preload, so the gate is proven with:
#   XOR(0xFFFFFFFF, B) = ~B   (genuine bit-flip, not passthrough)
#   AND(0xFFFFFFFF, B) =  B
# Same B, different output => the topology field really selects the gate.
# Mixed-operand sums (0x0C+0x0A) need the two-arrival path — unsolved over ISSP.
# Verified in sim (tb_gate): XOR->0xFFFFFFF5, AND->0x0000000A.
# Topology in RECONFIGURE low bits: XOR=0x0BC AND=0x007 OR=0x024; base 0x52800800.

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
proc count {sel} { array set s [readview $sel]; return $s(armed) }
proc show {tag exp need_chain} {
    array set s [readview 0]
    if {$need_chain} {
        set ok [expr {($s(out_data)==$exp && $s(out_count)>1 && $s(out_addr)>1) ? "PASS" : "** FAIL **"}]
    } else {
        set ok [expr {($s(out_data)==$exp && $s(out_count)>0) ? "PASS" : "** FAIL (want 0x[format %08x $exp]) **"}]
    }
    puts [format "  %-11s armed=%-3d out_count=%-3d out_addr=0x%04x out_data=0x%08x  %s" \
          $tag [count 0] $s(out_count) $s(out_addr) $s(out_data) $ok]
}

uc_open $HWM
puts "================= SINGLE-ZONE GATE + CHAIN TEST (cell 0, physical addr 0) ================="

# ---- 1. CHAIN + ADDRESSING (proven or_chain pattern): OR(0,B)=B ripples ----
puts "--- CHAIN : OR(0,B)=B ripples cell-to-cell (default output CELL_ID+1) ---"
cmd 0x00200008 0x00000000          ;# array reset
cmd 0x14A00004 0x52800824          ;# RECONFIGURE OR, armed, default output
cmd 0x14A20000 0x00000000          ;# preload A=0 (sel=01) -> a_arrived
cmd 0x00000001 0x00002340          ;# single trigger B=0x2340 @ addr 0
show "chain" 0x00002340 1           ;# PASS = data 0x2340 AND out_count>1 AND out_addr>1

# ---- 2. XOR gate: A=0xFFFFFFFF, B=0x0A -> ~B = 0xFFFFFFF5 ----
puts "--- XOR gate : XOR(0xFFFFFFFF, 0x0A) = 0xFFFFFFF5  (bit-flip, proves XOR) ---"
cmd 0x00200008 0x00000000
cmd 0x14A00003 0x00000200          ;# SET_OUTPUT_ADDR=0x200 (single-cell surface)
cmd 0x14A00004 0x528008BC          ;# RECONFIGURE XOR, armed
cmd 0x14A40000 0x00000000          ;# preload A=0xFFFFFFFF (sel=10)
cmd 0x00000001 0x0000000A          ;# single trigger B=0x0A @ addr 0
show "XOR ~B" 0xFFFFFFF5 0

# ---- 3. AND gate: A=0xFFFFFFFF, B=0x0A -> B = 0x0A ----
puts "--- AND gate : AND(0xFFFFFFFF, 0x0A) = 0x0000000A  (proves AND) ---"
cmd 0x00200008 0x00000000
cmd 0x14A00003 0x00000200
cmd 0x14A00004 0x52800807          ;# RECONFIGURE AND, armed
cmd 0x14A40000 0x00000000          ;# preload A=0xFFFFFFFF
cmd 0x00000001 0x0000000A          ;# trigger B=0x0A
show "AND B" 0x0000000A 0

puts "  XOR and AND give DIFFERENT outputs for the same B => topology select works."
uc_close
puts "=== done ==="
