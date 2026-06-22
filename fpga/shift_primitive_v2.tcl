# shift_primitive_v2.tcl — corrected nibble shift validation (proven firing pattern).
# Layers on issp_unicell.tcl (uc_open / uc_cmd / uc_snap / uc_status / uc_read).
#
# WHY v2: v1 armed all 448 cells (config + RECONFIGURE encoding confirmed on silicon)
# but no cell fired (out_count 0) — it relied on two self-stored bus arrivals, which
# is unproven over ISSP. v2 uses the PROVEN iCEBreaker pattern instead:
#   preload a_data (sets a_arrived) -> ONE shifted trigger -> PASS_B emits B<<4.
# PASS_B (topology 0x02C) outputs B, the trigger value, so the shift on the inject
# shows up directly at the output.
#
# Also: SET_OUTPUT_ADDR is issued LAST so output_set is definitely set, and each
# vector RE-PRELOADS (a fire resets a_arrived).
#
# Read results from uc_status: out_count must INCREMENT and out_data must match.

source issp_unicell.tcl
uc_open "*"                    ;# <-- set your instance match string

# ── configure one PASS_B cell on every fresh cell (broadcast; auth gate) ────────
uc_cmd 0x00000007 0x00A50100   ;# BOOT_COMMIT  in=0x100 auth=0xA5 -> RUN
uc_cmd 0x14A00004 0x5280082C   ;# RECONFIGURE  PASS_B(0x02C), armed, auth=0xA5
uc_cmd 0x14A00003 0x00000200   ;# SET_OUTPUT_ADDR out=0x200 (output_set=1) -- LAST

proc prime {} { uc_cmd 0x14A40000 0x00000000 }   ;# preload a_data=ONES -> a_arrived=1

proc fire {label cpu_bus W expect} {
    prime                       ;# a_arrived=1 (single trigger will fire)
    uc_cmd $cpu_bus $W          ;# one trigger arrival (B = W, optionally shifted)
    uc_snap
    puts "  $label W=[format 0x%08X $W] expect=[format 0x%08X $expect]"
    puts "    status: [uc_status]"   ;# read out_count (must move) + out_data (=expect)
}

puts "=== DIAGNOSTIC A: plain inject, no shift (does ANY cell fire?) ==="
# W[31:16]=0x0100 is the destination address; no shift, so out = W.
fire "PLAIN " 0x00000001 0x01002340 0x01002340

puts "=== DIAGNOSTIC B: shifted inject (shift_in_en, nibbles=W\[3:0\]=1) ==="
fire "SHIFT " 0x00080001 0x01000001 0x10000010
fire "SHIFT " 0x00080001 0x01002341 0x10023410
fire "SHIFT " 0x00080001 0x0100ABC1 0x100ABC10

puts ""
puts "READ: in each status line, out_count must INCREMENT vs the previous, and"
puts "out_data must equal 'expect'. If DIAGNOSTIC A does not move out_count, the"
puts "data-bus inject path over ISSP (cpu_addr/bus_valid) is the gap, not the shift."
puts "=== done ==="
