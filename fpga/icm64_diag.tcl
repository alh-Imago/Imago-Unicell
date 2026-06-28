# icm64_diag.tcl — localise the fired=0 result on top_arria10_64.
# Reads the probe at each stage to split the path in half:
#   1. cycle_count ticking?      -> probe alive + fabric clocking (vs dead read)
#   2. armed/outset after config?-> source writes landing + commands configuring
#   3. fire after inject?        -> the fire path itself
# No reflash. Run: quartus_stp -t icm64_diag.tcl [INST] [HWM]

set INST 0
if {$argc >= 1} { set INST [lindex $argv 0] }
set HWM "USB-Blaster"
if {$argc >= 2} { set HWM [lindex $argv 1] }
set ::INST $INST

proc uc_open {m} { set ns [get_hardware_names]; set ::HW [lindex $ns 0]
    foreach h $ns { if {[string match "*$m*" $h]} { set ::HW $h; break } }
    set ::DEV [lindex [get_device_names -hardware_name $::HW] 0]
    puts "Hardware : $::HW"; puts "Device   : $::DEV"
    start_insystem_source_probe -device_name $::DEV -hardware_name $::HW }
proc uc_close {} { end_insystem_source_probe }
proc sf {snap go cmd data} { set hi [expr {(($snap&1)<<1)|($go&1)}]
    write_source_data -instance_index $::INST -value [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]] -value_in_hex }
proc cmd {cb cd} { sf 0 0 $cb $cd; sf 0 1 $cb $cd; sf 0 0 $cb $cd }
# snapshot at view selector $sel; return raw probe word
proc rd {sel} { sf 1 0 $sel 0x0; sf 0 0 $sel 0x0
    return [expr {"0x[string trim [read_probe_data -instance_index $::INST -value_in_hex]]"}] }
proc fld {v hi lo} { set w [expr {$hi-$lo+1}]; set m [expr {(1<<$w)-1}]; return [expr {($v>>$lo)&$m}] }

uc_open $HWM
puts "================= DIAG: top_arria10_64 path localisation ================="

# ---- STEP 1: is the probe alive / fabric clocking? cycle_count = probe[31:0] ----
set a [rd 0x0]; after 50; set b [rd 0x0]
set cyc_a [fld $a 31 0]; set cyc_b [fld $b 31 0]
puts [format "STEP 1  cycle_count: %u then %u   %s" $cyc_a $cyc_b \
      [expr {($cyc_a!=0 || $cyc_b!=0) && ($cyc_a!=$cyc_b) ? "OK (probe live, fabric clocking)" : \
             ($cyc_a!=0||$cyc_b!=0) ? "probe reads but cycle static (check clk)" : \
             "** ZERO — probe read DEAD or no clock (widths/selector/connection) **"}]]

# ---- STEP 2: do config commands LAND? read armed (sel1) + outset (sel2) ----
cmd 0x00000007 0x00A50100   ;# BOOT_COMMIT -> RUN, auth=0xA5
cmd 0x00000018 0x00000100   ;# SET_TARGET 0x100
cmd 0x14A00003 0x00000200   ;# SET_OUTPUT_ADDR=0x200 (held target)
cmd 0x14A00004 0x5280082C   ;# RECONFIGURE PASS_B armed
set arm [fld [rd 0x1] 47 32]
set ost [fld [rd 0x2] 47 32]
puts [format "STEP 2  after config: armed_count=%u  output_set_count=%u   %s" $arm $ost \
      [expr {$arm>0 ? "OK (source writes landing, cells configuring)" : \
             "** 0 — commands NOT landing (source path / ISSP packing / opcode) **"}]]

# ---- STEP 3: cell-0 latch readback (sel3): topology + in/out address ----
set l [rd 0x3]
puts [format "STEP 3  cell0 latch: cmd_latch[lo32]=0x%08x  in=0x%04x  out=0x%04x" \
      [fld $l 79 48] [fld $l 95 80] [fld $l 47 32]]

# ---- STEP 4: methodology write + preload + inject, then read fire ----
cmd 0x00000018 0x00000100   ;# SET_TARGET 0x100
cmd 0x14A00019 0x00008800   ;# SET_METHOD: in_shift_en + shift_amt=4
cmd 0x14A40000 0x00000000   ;# preload -> a_arrived
cmd 0x00000001 0x01002340   ;# INJECT 0x01002340 @ 0x0100
set v [rd 0x0]
set seen [fld $v 96 96]; set od [fld $v 79 48]; set oa [fld $v 95 80]
puts [format "STEP 4  after inject: fired=%u  out_addr=0x%04x  out_data=0x%08x" $seen $oa $od]
puts [format "        (want fired=1 out_data=0x10023400; unshifted=0x01002340 => SET_METHOD issue)"]

uc_close
puts "=== diag done ==="
