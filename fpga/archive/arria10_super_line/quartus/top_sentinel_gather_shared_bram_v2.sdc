# top_sentinel_gather_shared_bram_v2.sdc — points.md #436: real Quartus
# timing constraints for the collector_relay_v1-based redesign. Same
# clocking convention as v1 and every other project here: 100.00 MHz
# single-ended on CLK_100M, divided by 4 internally to a 25 MHz fabric
# clock via div_cnt[1]. Missing SDC has been a real, documented trap
# before (every pre-fix Fmax figure this project ever measured was
# against a phantom ~1GHz auto-derived clock, not the real 25MHz
# target) -- this file exists from the start, not added after a bad
# first measurement.

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
