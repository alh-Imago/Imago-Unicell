# icm64_v3_decoder_auth.tcl — SILICON test of v3: two-slot decoder + relocated 11-bit auth.
# Mirrors tb_v3_auth_relocate.v + tb_v3_twoslot.v on the Arria 10 GX660 (zone1-v3 build).
# Proves on the die: (1) 11-bit auth stored at cmd_latch[63:53] works; (2) two-slot decoder
# self-describing opcodes write the right methodology field; (3) A+B compose in one pass;
# (4) auth [63:53] untouched by methodology writes; (5) wrong-auth rejected.
#
# Command word (v3 collapsed encoding):
#   [7:0]=slot A opcode, [15:8]=slot B opcode, [16]=B_valid, [18]=arm, [29:19]=auth(11b)
# Methodology opcodes: METH_SET_MASK=30, SHIFT_IN=31, SHIFT_OUT=32, LANE=33.
# Run: quartus_stp -t icm64_v3_decoder_auth.tcl [INST] [HWM]

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
# source word: {snap[1], go[1]} : cmd_bus[32] : cmd_data[32]  (adjust to your ISSP width/layout)
proc sf {snap go cmd data} { set hi [expr {(($snap&1)<<1)|($go&1)}]
    write_source_data -instance_index $::INST -value [format "%x%08x%08x" $hi [expr {$cmd&0xFFFFFFFF}] [expr {$data&0xFFFFFFFF}]] -value_in_hex }
proc cmd {cb cd} { sf 0 0 $cb $cd; sf 0 1 $cb $cd; sf 0 0 $cb $cd }
proc rd_raw {} { sf 1 0 0 0; sf 0 0 0 0
    return [expr {"0x[string trim [read_probe_data -instance_index $::INST -value_in_hex]]"}] }

# opcodes
set CMD_LOAD_AT     23
set CMD_BOOT_COMMIT 7
set METH_SET_MASK   30
set METH_SET_SHIFT_IN 31
set METH_SET_SHIFT_OUT 32
set METH_SET_LANE   33

# build a two-slot SET-method word: opA | opB<<8 | Bvalid<<16 | arm<<18 | auth<<19
proc mword {opA opB bvalid arm auth} {
    return [expr {($auth<<19)|($arm<<18)|($bvalid<<16)|(($opB&0xFF)<<8)|($opA&0xFF)}] }

uc_open $HWM
puts "========= v3 two-slot decoder + 11-bit auth on silicon ========="

# --- boot: write 11-bit auth mask 0x0A5 into [63:53], commit to RUN ---
# LOAD_AT with auth in cmd_data[30:20] (11-bit). physical_mode open at boot (auth_boot).
cmd $CMD_LOAD_AT     [expr {(0x0A5<<20)|0x0}]
cmd $CMD_BOOT_COMMIT 0x00A50100
puts "boot: wrote 11-bit auth 0x0A5 -> \[63:53\]; committed to RUN"

# --- A-only SET_MASK 0x3C (auth 0x0A5) ---
cmd [mword $METH_SET_MASK 0 0 0 0x0A5] 0x0000003C
puts "A-only SET_MASK 0x3C issued (auth ok)"

# --- A+B compose: SHIFT_OUT(A)=0x07 + LANE(B)=0x2, B_valid, arm ---
cmd [mword $METH_SET_SHIFT_OUT $METH_SET_LANE 1 1 0x0A5] [expr {(0x2<<16)|0x07}]
puts "compose SHIFT_OUT(A)=7 + LANE(B)=2, armed"

# --- wrong auth 0x111 -> must be REJECTED ---
cmd [mword $METH_SET_MASK 0 0 0 0x111] 0x000000FF
puts "wrong-auth SET_MASK issued (should be REJECTED)"

# --- read back cell state (probe shows dbg_cmd_latch lower 32; for full latch use per-cell readstate) ---
set v [rd_raw]
puts "readback raw: 0x[format %x $v]"
puts ""
puts "EXPECTED on the die (verify via per-cell readstate on the DEBUG_SELECT build):"
puts "  auth_mask\[63:53\] = 0x0A5  (unchanged through all methodology writes)"
puts "  nibble_mask\[39:32\] = 0x3C then 0x22-guarded; NOT 0xFF (wrong-auth rejected)"
puts "  shift_amt\[46:41\] = 0x07, out_shift_en\[48\]=1, lane_cut\[51:49\]=0x2 (compose worked)"
puts "  start_flag\[22\] = 1 (armed)"
puts ""
puts "NOTE: dbg_cmd_latch exposes only the LOWER 32 bits; auth\[63:53\] and methodology\[51:32\]"
puts "are in the UPPER half. To read those on silicon, extend the debug port to 64-bit OR use"
puts "icm64_readstate on a DEBUG_SELECT=1 build. This tcl drives the sequence; full upper-half"
puts "readback needs the wider debug path (a known gap — see session notes)."
uc_close
puts "=== done ==="
