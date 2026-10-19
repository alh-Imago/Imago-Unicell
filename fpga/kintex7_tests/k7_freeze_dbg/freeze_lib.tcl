# freeze_lib.tcl -- helpers for the k7_freeze kit (OpenOCD). USER1 = IR 0x02. Every scan is 84 words of 32 bits.
proc fz_scan {w0 w1} {
    set f [list 32 $w0 32 $w1]
    for {set i 2} {$i < 84} {incr i} { lappend f 32 0 }
    return [drscan xc7.tap {*}$f]
}
# read only (command word 1 = 0: the valid bit is clear, so nothing is changed)
proc fz_read {label} { puts "SNAP $label [fz_scan 0 0]" }
# go (restart the run) with freeze at count T: command word 0 = T, word 1 = go + valid = 5
proc fz_go {T} { fz_scan $T 5 }
# release: word 1 = release + valid = 6
proc fz_release {} { fz_scan 0xFFFFFFFF 6 }
