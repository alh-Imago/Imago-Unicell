# top_unicell_super_test_v2.sdc — points.md #421/#422: real Quartus
# timing constraints for the v2 super carrier shell (adds SEL_SEQ).
# Identical clocking convention to every other project here, including
# the v1 shell this compares against: 100.00 MHz single-ended on
# CLK_100M, divided by 4 internally to a 25 MHz fabric clock via
# div_cnt[1]. SDC present from the start -- the missing-SDC trap this
# project already hit once (every pre-fix Fmax figure measured against
# a phantom ~1GHz auto-derived clock) will not be repeated here.

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
