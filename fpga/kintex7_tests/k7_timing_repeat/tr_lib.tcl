# tr_lib.tcl -- helpers for the k7_timing_repeat kit (OpenOCD). Works with the k7_freeze_load (v3) bitstream: USER1 = IR 0x02, every scan is 86 words of 32 bits.
# Clone of the scan helpers in ../k7_freeze_load/freeze_lib.tcl (that file is left untouched). Writes only the design's own control register, never flash.
proc tr_xfer {vals} {
    set f {}
    foreach v $vals { lappend f 32 $v }
    return [drscan xc7.tap {*}$f]
}
proc tr_cmd {w0 w1} {
    set v [list $w0 $w1]
    for {set i 2} {$i < 86} {incr i} { lappend v 0 }
    return [tr_xfer $v]
}
proc tr_read {label} { puts "SNAP $label [tr_cmd 0 0]" }
# restart the run; word0 = freeze count T (0xFFFFFFFF = never freeze), word1 = go + valid = 5
proc tr_go {T} { return [tr_cmd $T 5] }
proc tr_release {} { return [tr_cmd 0xFFFFFFFF 6] }

# TEST A: N free runs. Each one restarts the run, waits, and reads the whole grid. The run is about 1,562 clocks (31 us); wait_ms is far longer than that.
proc tr_free_loop {N wait_ms} {
    for {set i 0} {$i < $N} {incr i} {
        tr_go 0xFFFFFFFF
        after $wait_ms
        tr_read "free_$i"
    }
}
# TEST B: for each count T in the list, M times: restart and freeze at T, read, release, wait, read. The freeze-and-release must not move the clock of the last result.
proc tr_freeze_loop {Ts M wait_ms} {
    foreach T $Ts {
        for {set i 0} {$i < $M} {incr i} {
            tr_go $T
            after $wait_ms
            tr_read "frz${T}_$i"
            tr_release
            after $wait_ms
            tr_read "rel${T}_$i"
        }
    }
}
