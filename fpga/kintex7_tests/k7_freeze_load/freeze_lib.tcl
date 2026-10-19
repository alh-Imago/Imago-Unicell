# freeze_lib.tcl -- helpers for the k7_freeze_load kit (OpenOCD). USER1 = IR 0x02. Every scan is 86 words of 32 bits.
proc fz_xfer {vals} {
    set f {}
    foreach v $vals { lappend f 32 $v }
    return [drscan xc7.tap {*}$f]
}
proc fz_cmd {w0 w1} {
    set v [list $w0 $w1]
    for {set i 2} {$i < 86} {incr i} { lappend v 0 }
    return [fz_xfer $v]
}
proc fz_read {label} { puts "SNAP $label [fz_cmd 0 0]" }
# restart the run, freeze at count T (valid + go = 5)
proc fz_go {T} { return [fz_cmd $T 5] }
# release (valid + release = 6)
proc fz_release {} { return [fz_cmd 0xFFFFFFFF 6] }
# freeze now (valid + freeze_now = 0x14)
proc fz_pause {} { return [fz_cmd 0xFFFFFFFF 20] }
# load a saved snapshot (a list of 86 hex words from a SNAP line); the grid stays frozen
proc fz_load {snap} {
    set fl [expr "0x[lindex $snap 2]"]
    set ncap [expr {$fl & 0xFF}]
    set k [expr {($fl >> 8) & 0xFF}]
    set v [list 0xFFFFFFFF 12 "0x[lindex $snap 1]" [expr {($k << 8) | $ncap}] "0x[lindex $snap 3]" "0x[lindex $snap 4]" "0x[lindex $snap 6]" 0]
    for {set i 8} {$i < 34} {incr i} { lappend v 0 }
    for {set i 34} {$i < 86} {incr i} { lappend v "0x[lindex $snap $i]" }
    return [fz_xfer $v]
}
# the round trip: freeze at T and save (S); run to D (a different state) (D); load S (L); release (F)
proc fz_saveload {T D} {
    fz_go $T; after 30
    set S [fz_cmd 0 0]; puts "SNAP S $S"
    fz_go $D; after 30
    puts "SNAP D [fz_cmd 0 0]"
    fz_load $S; after 10
    puts "SNAP L [fz_cmd 0 0]"
    fz_release; after 150
    puts "SNAP F [fz_cmd 0 0]"
}
