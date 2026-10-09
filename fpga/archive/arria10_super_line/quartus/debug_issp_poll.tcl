# =============================================================================
# debug_issp_poll.tcl — real diagnostic extension of debug_issp_read.tcl:
# reads the probe MANY times over a genuinely long real window (default
# 15 reads, 500ms apart -- 7 real seconds, ~10+ full toggle periods at
# the expected ~0.67s heartbeat period), rather than just twice. Runs
# against whatever bitstream is already programmed -- no rebuild needed.
#
# RUN:
#     quartus_stp -t debug_issp_poll.tcl [n_reads] [gap_ms]
#   defaults: n_reads=15, gap_ms=500
#
# WHAT THIS ANSWERS: does heartbeat EVER change, anywhere in a long real
# window -- a much stronger claim than "didn't change across these
# specific two reads." If every single read comes back identical across
# the WHOLE window, that's strong, real evidence the design is
# genuinely stuck (not just unlucky sampling), narrowing the real
# problem toward the clock/reset side rather than the debug channel
# itself (which #530 already proved works correctly, on branch cell,
# with an identical read mechanism).
# =============================================================================

set N   15
set GAP 500
if {$argc >= 1} { set N   [lindex $argv 0] }
if {$argc >= 2} { set GAP [lindex $argv 1] }

set HWMATCH "USB-Blaster"
set names [get_hardware_names]
if {[llength $names] == 0} { error "No JTAG hardware found." }
set HW [lindex $names 0]
foreach h $names { if {[string match "*$HWMATCH*" $h]} { set HW $h; break } }
set DEV [lindex [get_device_names -hardware_name $HW] 0]

puts "Hardware : $HW"
puts "Device   : $DEV"
puts "Polling $N times, ${GAP}ms apart (~[expr {$N * $GAP / 1000.0}]s total window)"
puts ""

proc clean_hex {s} {
    if {[string equal -nocase [string range $s 0 1] "0x"]} {
        return [string range $s 2 end]
    }
    return $s
}

start_insystem_source_probe -device_name $DEV -hardware_name $HW

set prev_hb -1
set changes 0
for {set i 0} {$i < $N} {incr i} {
    set p [read_probe_data -instance_index 0 -value_in_hex]
    set v [expr "0x[clean_hex $p]"]
    set err [expr {$v & 1}]
    set hb  [expr {($v >> 1) & 1}]
    set mark ""
    if {$prev_hb != -1 && $hb != $prev_hb} { incr changes; set mark "  <-- CHANGED" }
    puts [format "read %2d: raw=%s err_sticky=%d heartbeat=%d%s" $i $p $err $hb $mark]
    set prev_hb $hb
    if {$i < $N - 1} { after $GAP }
}

end_insystem_source_probe

puts ""
if {$changes == 0} {
    puts "REAL FINDING: heartbeat NEVER changed across $N reads over a"
    puts "genuine multi-second window. This is strong evidence the design"
    puts "is genuinely stuck, not a sampling artifact -- the clock is very"
    puts "likely not reaching hb_cnt (or something is holding it in reset),"
    puts "since hb_cnt itself has no other real dependency that could stop it."
} else {
    puts "Heartbeat changed $changes time(s) across $N reads -- the design"
    puts "IS genuinely running. If it changed at least once, it's alive;"
    puts "the earlier 2-read snapshot just happened to land on a stable window."
}
