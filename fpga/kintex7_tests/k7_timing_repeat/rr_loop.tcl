# rr_loop.tcl -- used by runner_repeat.sh after the folder's own run_lib.tcl. Feed the same command N times, wait, read the whole register each time.
proc rr_loop {N cmdfile wait_ms} {
    for {set i 0} {$i < $N} {incr i} {
        rn_cmd_file $cmdfile
        after $wait_ms
        rn_read "run_$i"
    }
}
