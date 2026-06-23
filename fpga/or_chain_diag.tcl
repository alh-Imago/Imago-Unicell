# or_chain_diag.tcl — SELF-CONTAINED. Two parts:
#   PART A: proven PASS_B config (BOOT_COMMIT + SET_OUTPUT + RECONFIGURE) — board
#           self-check. Expect out_count>=1, out_data=0x01002340. If this FAILS,
#           the bitstream/board is the problem, not the chain config.
#   PART B: the or_chain physical-mode config (RECONFIGURE-only) WITH per-step
#           cell-0 readback (view 3 = cmd_latch/in/out addr, view 4 = a_data).
#           This shows whether cell-0 is actually configured to fire (output_set,
#           start_flag, output_addr=1) and whether it fired.
#
# Resolves the impossible reading: arrived->0 with out_count=0 cannot both be
# true under the RTL (a fire clears a_arrived AND loads out_buf -> drains to
# out_valid). So either the .sof is stale or cell-0 isn't in the state we assume.
# View encoding (unicell_issp_bridge): src_cpu_bus[2:0]=3 cell0 latch, =4 a_data.

if {![info exists ::INST]} { set ::INST 0 }

proc sf {snap go cmd data} {
    set hi [expr {(($snap & 1) << 1) | ($go & 1)}]
    write_source_data -instance_index $::INST \
        -value [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]] -value_in_hex
}
# issue a command (pulses cmd_go = 1-cycle cpu_valid)
proc cmd {cb cd} { sf 0 0 $cb $cd; sf 0 1 $cb $cd; sf 0 0 $cb $cd }
# raw probe read -> field list
proc rd {} {
    set v [expr {"0x[string trim [read_probe_data -instance_index $::INST -value_in_hex]]"}]
    return [list armed    [expr {($v>>32)&0xFFFF}] \
                 out_data [expr {($v>>48)&0xFFFFFFFF}] \
                 out_addr [expr {($v>>80)&0xFFFF}] \
                 seen     [expr {($v>>96)&0x1}] \
                 out_count [expr {($v>>97)&0xFFFF}]]
}
# snapshot a given view (src_cpu_bus=view, snap rising edge, NO cmd_go) -> fields
proc readview {view} { sf 0 0 $view 0; sf 1 0 $view 0; sf 0 0 0 0; array set s [rd]; return [array get s] }

proc showout {tag} {
    array set s [readview 0]
    puts [format "  %-18s out_count=%-3d out_addr=0x%04x out_data=0x%08x seen=%d" \
          $tag $s(out_count) $s(out_addr) $s(out_data) $s(seen)]
}
proc arrived {} { array set s [readview 1]; return $s(armed) }
proc armedN {} { array set s [readview 0]; return $s(armed) }
proc outsetN {} { array set s [readview 2]; return $s(armed) }

# cell-0 decode: view3 gives cmd_latch(out_data), input_addr(out_addr), output_addr(armed)
proc cell0 {tag} {
    array set a [readview 3]
    set cl   $a(out_data)
    set ina  $a(out_addr)
    set outa $a(armed)
    array set b [readview 4]
    set adata $b(out_data)
    set start   [expr {($cl>>22)&1}]
    set oset    [expr {($cl>>19)&1}]
    set startc  [expr {($cl>>11)&1}] ;# compact v2.3 start_flag at bit 11
    set topo    [expr {$cl & 0x3FF}]
    puts [format "  cell0 %-12s cmd_latch=0x%08x topo=0x%03x out_set\[19\]=%d start\[22\]=%d start\[11\]=%d  in=0x%04x out=0x%04x a_data=0x%08x" \
          $tag $cl $topo $oset $start $startc $ina $outa $adata]
}

puts "=================================================================="
puts "PART A — PROVEN PASS_B self-check (board health). Expect out_count>=1."
puts "=================================================================="
cmd 0x00200008 0x00000000                         ;# reset
cmd 0x00000007 0x00A50100                          ;# BOOT_COMMIT in=0x100 auth=0xA5 -> RUN
cmd 0x14A00003 0x00000200                          ;# SET_OUTPUT_ADDR out=0x200 (output_set=1)
cmd 0x14A00004 0x5280082C                          ;# RECONFIGURE PASS_B armed
cell0 "after cfg"
puts [format "  armed=%d output_set=%d arrived=%d" [armedN] [outsetN] [arrived]]
cmd 0x14A40000 0x00000000                          ;# preload sel=10 (0xFFFFFFFF)
cell0 "after preload"
puts [format "  arrived=%d (expect 448)" [arrived]]
cmd 0x00000001 0x01002340                          ;# inject W
cell0 "after inject"
showout "after inject"
puts "  >>> PASS_B oracle: out_count>=1, out_data=0x01002340. If 0 -> bitstream/board."

puts ""
puts "=================================================================="
puts "PART B — or_chain physical-mode config (RECONFIGURE-only) + cell0 reads"
puts "=================================================================="
cmd 0x00200008 0x00000000                          ;# reset
cell0 "after reset"
cmd 0x14A00004 0x52800824                          ;# RECONFIGURE OR (no BOOT_COMMIT, no SET_OUTPUT)
cell0 "after OR cfg"
puts [format "  armed=%d output_set=%d arrived=%d (expect armed=448 outset=448)" [armedN] [outsetN] [arrived]]
cmd 0x14A20000 0x00000000                          ;# preload sel=01 (0x0)
cell0 "after preload"
puts [format "  arrived=%d (expect 448)" [arrived]]
cmd 0x00000001 0x00002340                          ;# inject B at addr 0
cell0 "after inject"
showout "after inject"
puts "  KEY READS:"
puts "   - after-OR-cfg out_set\[19\]=1 and out=0x0001 ? (cell0 fire-ready, default addr)"
puts "   - after-inject arrived drop + out_count : both move together or contradict?"
puts "   - a_data after inject : 0=didn't fire/consumed, 0x2340=stored as new arrival"
puts "=== done ==="
