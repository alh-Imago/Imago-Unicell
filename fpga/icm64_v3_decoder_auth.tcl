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

set OP_SET_TARGET   24
set TARGET_CELL     0

uc_open $HWM
puts "========= v3 two-slot decoder + 11-bit auth on silicon ========="
puts "target cell = $TARGET_CELL (SET_TARGET latches it; config ops 23/25 use the held target)"

# --- boot: SET_TARGET the cell, then write 11-bit auth 0x0A5 into [63:53], commit to RUN ---
cmd $OP_SET_TARGET   $TARGET_CELL
cmd $CMD_LOAD_AT     [expr {(0x0A5<<20)|0x0}]
cmd $CMD_BOOT_COMMIT 0x00A50100
puts "boot: SET_TARGET $TARGET_CELL; wrote 11-bit auth 0x0A5 -> \[63:53\]; committed to RUN"

# --- A-only SET_MASK 0x3C (auth 0x0A5) — SET_TARGET first (op25 uses held target) ---
cmd $OP_SET_TARGET $TARGET_CELL
cmd [mword $METH_SET_MASK 0 0 0 0x0A5] 0x0000003C
puts "A-only SET_MASK 0x3C issued (auth ok)"

# --- A+B compose: SHIFT_OUT(A)=0x07 + LANE(B)=0x2, B_valid, arm ---
cmd $OP_SET_TARGET $TARGET_CELL
cmd [mword $METH_SET_SHIFT_OUT $METH_SET_LANE 1 1 0x0A5] [expr {(0x2<<16)|0x07}]
puts "compose SHIFT_OUT(A)=7 + LANE(B)=2, armed"

# --- wrong auth 0x111 -> must be REJECTED ---
cmd $OP_SET_TARGET $TARGET_CELL
cmd [mword $METH_SET_MASK 0 0 0 0x111] 0x000000FF
puts "wrong-auth SET_MASK issued (should be REJECTED)"

# --- FREEZE the cell so nothing is in flight, THEN read (quiescent, stable snapshot) ---
set CMD_FREEZE 5
cmd $OP_SET_TARGET $TARGET_CELL
cmd $CMD_FREEZE 0x00000000
puts "froze target cell for quiescent readback"

# --- read BANK 0 then BANK 1 of the SAME cell. Settle after each bank-select before sampling. ---
# op26: cell index in low bits, bank in bit16. Extra reads let dbg_bank + mux settle.
cmd 26 [expr {$TARGET_CELL | 0x00000000}]
rd_raw ; # discard first (settle)
set v0 [rd_raw]
cmd 26 [expr {$TARGET_CELL | 0x00010000}]
rd_raw ; # discard first (settle)
set v1 [rd_raw]
puts "bank0 (lower \[31:0\]) = 0x[format %08x [expr {$v0 & 0xFFFFFFFF}]]"
puts "bank1 (upper \[63:32\]) = 0x[format %08x [expr {$v1 & 0xFFFFFFFF}]]"
puts ""
puts "VERIFY in bank1 (upper half = cmd_latch\[63:32\]):"
puts "  bits \[7:0\]  = nibble_mask  -> expect 0x22 (last valid mask; NOT 0xFF = wrong-auth rejected)"
puts "  bits \[19:17\]= lane_cut     -> expect 0x2 (compose worked)"
puts "  bits \[16:15\]= shift bits    -> out_shift_en=1"
puts "  bits \[14:9\] = shift_amt     -> expect 0x07"
puts "  bits \[31:21\]= auth_mask     -> expect 0x0A5 (UNCHANGED through all methodology writes)"
set upper [expr {$v1 & 0xFFFFFFFF}]
puts ""
puts "  decoded: mask=0x[format %02x [expr {$upper & 0xFF}]]  auth=0x[format %03x [expr {($upper>>21)&0x7FF}]]  lane=0x[format %x [expr {($upper>>17)&0x7}]]"
if {[expr {($upper>>21)&0x7FF}] == 0x0A5} {
    puts "  >>> AUTH held at 0x0A5 on silicon through all methodology writes — auth relocation VERIFIED"
} else {
    puts "  >>> CHECK auth: got 0x[format %03x [expr {($upper>>21)&0x7FF}]] want 0x0A5"
}
uc_close
puts "=== done ==="
