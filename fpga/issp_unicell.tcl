# =============================================================================
# issp_unicell.tcl — quartus_stp harness for the UniCell ISSP test channel
#
# RUN (once v1.1a is compiled and programmed):
#     quartus_stp -t issp_unicell.tcl [instance_index] [hw_name_match]
#   defaults: instance_index = 0, hw_name_match = "USB-Blaster"
#
# Run it wherever quartus_stp AND the USB-Blaster live together (full Quartus on
# Windows for sure; Linux too if your standalone install has quartus_stp). The
# script auto-discovers the cable, so no hard-coded names.
#
# Default action = the channel-alive check the hung ISSP editor denied us:
# snapshot cycle_count, wait, snapshot again, confirm it advanced. That proves
# the JTAG read path, the snapshot logic, and the 25 MHz fabric clock in one go.
#
# BIT MAP — must match unicell_issp_bridge.v:
#   SOURCE (66b): [65]=snap_req [64]=cmd_go [63:32]=cpu_bus [31:0]=cpu_data
#   PROBE (113b): [112:97]=out_count [96]=out_seen [95:80]=out_addr
#                 [79:48]=out_data  [47:32]=armed   [31:0]=cycle
# =============================================================================

set INSTANCE 0
if {$argc >= 1} { set INSTANCE [lindex $argv 0] }
set HWMATCH "USB-Blaster"
if {$argc >= 2} { set HWMATCH [lindex $argv 1] }

set ::INST $INSTANCE
set ::HW ""
set ::DEV ""

# ── open / close ─────────────────────────────────────────────────────────────
proc uc_open {match} {
    set names [get_hardware_names]
    if {[llength $names] == 0} { error "No JTAG hardware found. Is the cable plugged in / jtagd running?" }
    set ::HW [lindex $names 0]
    foreach h $names { if {[string match "*$match*" $h]} { set ::HW $h; break } }
    set ::DEV [lindex [get_device_names -hardware_name $::HW] 0]
    puts "Hardware : $::HW"
    puts "Device   : $::DEV"
    puts "Instance : $::INST"
    start_insystem_source_probe -device_name $::DEV -hardware_name $::HW
}
proc uc_close {} { end_insystem_source_probe }

# ── low-level source write ───────────────────────────────────────────────────
# Build the hex string from <=32-bit chunks so we never lean on Tcl bignum
# formatting. hi nibble carries bits 65:64 (snap_req, cmd_go).
proc uc_src_fields {snap go cmd data} {
    set hi [expr {(($snap & 1) << 1) | ($go & 1)}]
    set hex [format "%x%08x%08x" $hi [expr {$cmd & 0xFFFFFFFF}] [expr {$data & 0xFFFFFFFF}]]
    write_source_data -instance_index $::INST -value $hex -value_in_hex
}

# ── inject one command: 1-cycle cpu_valid pulse with cpu_bus/cpu_data set ─────
proc uc_cmd {cmd_word data_word} {
    uc_src_fields 0 0 $cmd_word $data_word ;# present cmd/data, go=0
    uc_src_fields 0 1 $cmd_word $data_word ;# go 0->1 : rising edge -> one pulse
    uc_src_fields 0 0 $cmd_word $data_word ;# go=1->0
}

# ── take a readback snapshot (rising edge on snap_req) ────────────────────────
proc uc_snap {} {
    uc_src_fields 0 0 0 0
    uc_src_fields 1 0 0 0 ;# snap_req 0->1 : latch {cycle,armed,out*,count}
    uc_src_fields 0 0 0 0
}

# ── read + unpack the probe into a Tcl dict-style list ───────────────────────
proc uc_read {} {
    set hex [string trim [read_probe_data -instance_index $::INST -value_in_hex]]
    set v [expr {"0x$hex"}]
    return [list \
        cycle     [expr {$v & 0xFFFFFFFF}] \
        armed     [expr {($v >> 32) & 0xFFFF}] \
        out_data  [expr {($v >> 48) & 0xFFFFFFFF}] \
        out_addr  [expr {($v >> 80) & 0xFFFF}] \
        out_seen  [expr {($v >> 96) & 0x1}] \
        out_count [expr {($v >> 97) & 0xFFFF}]]
}

# ── snapshot + read + pretty-print ───────────────────────────────────────────
proc uc_status {} {
    uc_snap
    array set s [uc_read]
    puts [format "  cycle=%u armed=%u out_seen=%u out_count=%u out_addr=0x%04x out_data=0x%08x" \
          $s(cycle) $s(armed) $s(out_seen) $s(out_count) $s(out_addr) $s(out_data)]
    return [array get s]
}

# ═════════════════════════════════════════════════════════════════════════════
uc_open $HWMATCH

puts "\n--- channel-alive: cycle_count must advance between snapshots ---"
array set a [uc_status]
after 250
array set b [uc_status]
if {$b(cycle) != $a(cycle)} {
    puts "PASS: cycle moved [expr {$b(cycle) - $a(cycle)}] ticks — JTAG read path + fabric clock are live."
} else {
    puts "FAIL: cycle did not change. Check: correct .sof programmed, instance_index,"
    puts "      and that the IP was built with Use Source Clock = CLK."
}

# --- write-path smoke test: authenticated array reset (opcode 8, auth!=0) -----
# Decoded in top_arria10 as: cpu_bus[7:0]==8 && cpu_bus[28:21]!=0.
# auth=1 -> cmd_word = (1<<21)|8 = 0x00200008. Effect isn't visible until cells
# are configured, but it confirms the command path doesn't stall.
puts "\n--- write-path: issue auth reset (cmd 0x00200008) ---"
uc_cmd 0x00200008 0x00000000
uc_status

uc_close
puts "\ndone."
# Build real test vectors with uc_cmd {cmd_word data_word} + uc_status; the
# shift-adder sequence gets wired to your command generator next.
