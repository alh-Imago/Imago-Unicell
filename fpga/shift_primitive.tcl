# shift_primitive.tcl — nibble shift_in_en validation on the Arria 10 fabric.
# Layers on issp_unicell.tcl (uc_open / uc_cmd / uc_snap / uc_read / uc_status).
#
#   set match to your ISSP instance match string, then:  quartus_stp -t shift_primitive.tcl
#
# Cell: one PASS cell, in=0x100 out=0x200, auth=0xA5 (broadcast onto all fresh cells).
# Verified end-to-end against unicell.v / unicell_array.v / top_arria10.v.
#
# TWO landmines this harness encodes the fixes for:
#  1. v2.3 RECONFIGURE is a COMPACT payload (start_flag at cmd_data[11], NOT bit 22).
#     The old UART mk_cfg would leave start_flag=0 -> cell never arms. Fixed below.
#  2. Arria10 DATA_WRITE packs ONE word: bus_addr=cpu_data[31:16],
#     bus_data=cpu_data(full), shift_nibbles=cpu_data[3:0]. Address, value and
#     shift count SHARE the word, so test words are shaped 0xADDR_yyyN.

source issp_unicell.tcl
uc_open "*"                    ;# <-- set your instance match string

# ── configure one PASS cell on every fresh cell (broadcast; auth gate) ──────────
uc_cmd 0x00000007 0x00A50100   ;# BOOT_COMMIT  in=0x100 auth=0xA5 -> RUN
uc_cmd 0x14A00003 0x00000200   ;# SET_OUTPUT_ADDR out=0x200 (auth=0xA5)
uc_cmd 0x14A00004 0x52800800   ;# RECONFIGURE  PASS topology, armed, auth=0xA5

# ── a (shifted) inject is just a DATA_WRITE uc_cmd: cpu_bus=opcode+shift, cpu_data=W
#    W[31:16]=addr(0x0100)  W[15:4]=payload  W[3:0]=nibble count
proc shift_test {W} {
    set exp [format 0x%08X [expr {($W << 4) & 0xFFFFFFFF}]]
    # two-arrival PASS: 1st inject (shifted) -> a_data=W<<4 ; 2nd -> trigger fire
    uc_cmd 0x00080001 $W       ;# DATA_WRITE + shift_in_en, nibbles=W[3:0]
    uc_cmd 0x00080001 $W
    uc_snap
    set got [uc_read]
    puts [format "  SHIFT  W=0x%08X  exp=%s  got=%s  %s" \
          $W $exp $got [expr {$got eq $exp ? "PASS" : "FAIL"}]]
}
proc control_test {W} {
    set exp [format 0x%08X $W]
    uc_cmd 0x00000001 $W       ;# DATA_WRITE, no shift
    uc_cmd 0x00000001 $W
    uc_snap
    set got [uc_read]
    puts [format "  CTRL   W=0x%08X  exp=%s  got=%s  %s" \
          $W $exp $got [expr {$got eq $exp ? "PASS" : "FAIL"}]]
}

puts "=== nibble shift_in_en validation (expect SHIFT=W<<4, CTRL=W) ==="
foreach W {0x01000001 0x01002341 0x0100ABC1} { shift_test $W }
control_test 0x01002340
puts "=== done ==="
