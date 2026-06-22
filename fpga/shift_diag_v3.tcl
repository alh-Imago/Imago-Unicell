# shift_diag_v3.tcl — localise the inject failure using the new aggregate counters.
# Requires the rebuild with arrived_count / output_set_count instrumentation.
# Counters (read via uc_count): 0=armed 1=arrived 2=output_set.

source issp_unicell.tcl
uc_open "*"

proc counts {tag} {
    set a [uc_count 0]; set o [uc_count 2]; set r [uc_count 1]
    array set s [uc_read]
    puts [format "  %-16s armed=%-3d output_set=%-3d arrived=%-3d out_count=%d out_data=0x%08x" \
          $tag $a $o $r $s(out_count) $s(out_data)]
}

puts "=== STEP 1: fresh (after this script's own reset, expect all ~0) ==="
counts "fresh"

puts "=== STEP 2: configure PASS_B, in=0x100 out=0x200, auth=0xA5 ==="
uc_cmd 0x00000007 0x00A50100   ;# BOOT_COMMIT
uc_cmd 0x14A00004 0x5280082C   ;# RECONFIGURE PASS_B armed
uc_cmd 0x14A00003 0x00000200   ;# SET_OUTPUT_ADDR (output_set=1)
counts "after config"
puts "    expect: armed=448 output_set=448 arrived=0"

puts "=== STEP 3: preload a_data (sets a_arrived) ==="
uc_cmd 0x14A40000 0x00000000   ;# preload ONES -> a_arrived=1
counts "after preload"
puts "    expect: arrived=448  (if 0 -> preload/command path not reaching cells)"

puts "=== STEP 4: plain inject W=0x01002340 (no shift) ==="
uc_cmd 0x00000001 0x01002340
counts "after inject"
puts "    KEY: if arrived drops 448->~0 the inject REACHED cells (zone fix live);"
puts "         if arrived stays 448 the inject was DROPPED (fix not in bitstream);"
puts "         if arrived dropped but out_count=0 -> output path, not inject."
puts "=== done ==="
