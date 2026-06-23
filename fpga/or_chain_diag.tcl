# or_chain_diag.tcl — board self-check + cell-0 readback. Same harness as
# or_chain.tcl (sources nothing).  quartus_stp -t or_chain_diag.tcl [inst] [hw_match]
#
# PART A: proven PASS_B config (BOOT_COMMIT + SET_OUTPUT + RECONFIGURE) on the
#         CURRENTLY FLASHED .sof. Expect out_count>=1, out_data=0x01002340.
#         out_count=0 here => the ISSP output capture is NOT wired in this build
#         (UART-lineage) — fabric may be fine, the probe is blind.
# PART B: or_chain physical-mode config (RECONFIGURE-only) WITH per-step cell-0
#         reads: view 3 = cmd_latch/in/out addr, view 4 = a_data.
# View encoding (unicell_issp_bridge): src_cpu_bus[2:0]=3 cell0 latch, =4 a_data.

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
# snapshot a given view (src_cpu_bus=v, snap rising edge, NO cmd_go) -> rd list
proc readview {v} { sf 0 0 $v 0; sf 1 0 $v 0; sf 0 0 0 0; return [rd] }
proc count {sel} { array set s [readview $sel]; return $s(armed) }
proc show {tag} {
    array set s [readview 0]
    puts [format "  %-14s armed=%-3d arrived=%-3d  out_count=%-3d out_addr=0x%04x out_data=0x%08x" \
          $tag [count 0] [count 1] $s(out_count) $s(out_addr) $s(out_data)]
}
# cell-0 decode: view3 -> cmd_latch(out_data) input_addr(out_addr) output_addr(armed)
proc cell0 {tag} {
    array set a [readview 3]
    set cl $a(out_data); set ina $a(out_addr); set outa $a(armed)
    array set b [readview 4]; set adata $b(out_data)
    set oset   [expr {($cl>>19)&1}]
    set start22 [expr {($cl>>22)&1}]
    set start11 [expr {($cl>>11)&1}]
    set topo   [expr {$cl & 0x3FF}]
    puts [format "  cell0 %-12s cmd_latch=0x%08x topo=0x%03x outset19=%d start22=%d start11=%d in=0x%04x out=0x%04x a_data=0x%08x" \
          $tag $cl $topo $oset $start22 $start11 $ina $outa $adata]
}

uc_open $HWM

puts "=================================================================="
puts "PART A - PROVEN PASS_B self-check. Expect out_count>=1, out_data=0x01002340"
puts "=================================================================="
cmd 0x00200008 0x00000000
cmd 0x00000007 0x00A50100   ;# BOOT_COMMIT in=0x100 auth=0xA5 -> RUN
cmd 0x14A00003 0x00000200   ;# SET_OUTPUT_ADDR out=0x200 (output_set=1)
cmd 0x14A00004 0x5280082C   ;# RECONFIGURE PASS_B armed
cell0 "after cfg"
show  "after cfg"
cmd 0x14A40000 0x00000000   ;# preload sel=10 (0xFFFFFFFF)
cell0 "after preload"
show  "after preload"
cmd 0x00000001 0x01002340   ;# inject W
cell0 "after inject"
show  "after inject"
puts "  >>> if out_count>=1 here, ISSP output capture WORKS on this .sof"
puts "  >>> if out_count=0 here, output capture is blind in this build (the answer)"

puts ""
puts "=================================================================="
puts "PART B - or_chain physical-mode (RECONFIGURE-only) + cell0 reads"
puts "=================================================================="
cmd 0x00200008 0x00000000
cell0 "after reset"
cmd 0x14A00004 0x52800824   ;# RECONFIGURE OR, no BOOT_COMMIT, no SET_OUTPUT
cell0 "after OR cfg"
show  "after OR cfg"
cmd 0x14A20000 0x00000000   ;# preload sel=01 (0x0)
cell0 "after preload"
show  "after preload"
cmd 0x00000001 0x00002340   ;# inject B at addr 0
cell0 "after inject"
show  "after inject"
puts "  KEY: after-OR-cfg outset19=1 and out=0x0001 ? (cell0 fire-ready)"
puts "       a_data after inject : 0=consumed/none, 0x2340=stored as new arrival"

uc_close
puts "=== done ==="
