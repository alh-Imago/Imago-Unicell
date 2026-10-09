# =============================================================================
# debug_issp_read.tcl — points.md #528/#529: minimal quartus_stp harness
# for the 2-bit debug ISSP channel (debug_issp_probe_v1.v). A real,
# JTAG-readable answer to "did this self-test pass" that doesn't depend
# on whether LED0_N/LED1_N actually reach a physical LED on this board
# (the still-open real question from #528).
#
# RUN (after programming the .sof onto the board):
#     quartus_stp -t debug_issp_read.tcl [hw_name_match]
#   default: hw_name_match = "USB-Blaster"
#
# This is a READ-ONLY snapshot -- no waveform, no live view, no need to
# watch a clock. `read_probe_data` returns the probe's CURRENT value at
# the instant of the call. Since the self-test's own FSM runs to
# completion and then holds its final state forever (every one of
# #523's self-tests ends in a S_DONE state that just sits there), any
# read after programming will show the real, final, settled result --
# there's no "catch it at the right moment" timing to worry about.
#
# BIT MAP -- must match debug_issp_probe_v1.v exactly:
#   probe[0] = err_sticky  -- 0 = no error ever latched (real PASS)
#   probe[1] = heartbeat   -- must be OBSERVED TO CHANGE across two
#                             reads a moment apart to prove the design
#                             is genuinely clocking, not frozen. A
#                             single read of heartbeat=0 or =1 proves
#                             nothing by itself -- it's a real, moving
#                             signal, not a static flag. The two reads
#                             are spaced 2 real seconds apart (several
#                             full toggle periods at the real ~0.67s
#                             period) specifically so a stuck-at-the-
#                             same-value result is a genuine finding,
#                             not plausible bad luck on a single narrow
#                             sampling window.
# =============================================================================

set HWMATCH "USB-Blaster"
if {$argc >= 1} { set HWMATCH [lindex $argv 0] }

set names [get_hardware_names]
if {[llength $names] == 0} { error "No JTAG hardware found. Is the cable plugged in / jtagd running?" }
set HW [lindex $names 0]
foreach h $names { if {[string match "*$HWMATCH*" $h]} { set HW $h; break } }
set DEV [lindex [get_device_names -hardware_name $HW] 0]

puts "Hardware : $HW"
puts "Device   : $DEV"

start_insystem_source_probe -device_name $DEV -hardware_name $HW

# Strip any 0x/0X prefix read_probe_data may already include before
# adding our own -- avoids a doubled "0x0x..." prefix, the real bug
# that broke the first version of this script.
proc clean_hex {s} {
    if {[string equal -nocase [string range $s 0 1] "0x"]} {
        return [string range $s 2 end]
    }
    return $s
}

set p1 [read_probe_data -instance_index 0 -value_in_hex]
after 2000
set p2 [read_probe_data -instance_index 0 -value_in_hex]

end_insystem_source_probe

set v1 [expr "0x[clean_hex $p1]"]
set v2 [expr "0x[clean_hex $p2]"]
set err1  [expr {$v1 & 1}]
set hb1   [expr {($v1 >> 1) & 1}]
set hb2   [expr {($v2 >> 1) & 1}]

puts ""
puts "Read 1: raw=0x$p1  err_sticky=$err1  heartbeat=$hb1"
puts "Read 2: raw=0x$p2  heartbeat=$hb2  (2s later)"
puts ""

if {$hb1 == $hb2} {
    puts "WARNING: heartbeat did not change across a 2-second gap --"
    puts "several real toggle periods at ~0.67s. This is now a genuine"
    puts "reason to suspect the design is stuck (possibly held in"
    puts "reset), not statistical bad luck on a narrow sampling window."
    puts "err_sticky's own 0 value cannot be trusted as a real pass"
    puts "while this warning fires -- 0 is also err_sticky's own reset"
    puts "default, so a stuck design and a genuinely passing one look"
    puts "identical on err_sticky alone. Re-run this script once more"
    puts "to confirm before concluding anything."
} else {
    puts "Heartbeat changed -- the design is genuinely clocking, not frozen."
}

if {$err1 == 0} {
    puts "err_sticky = 0 -- REAL PASS. No error ever latched."
} else {
    puts "err_sticky = 1 -- REAL FAIL. An error latched at some point during the self-test."
}
