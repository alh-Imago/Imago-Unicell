# top_super_nano_feedback_test_v1.sdc — points.md #523: same clocking convention as every
# other project here (and top_unicell_super_test_v1.sdc's own real,
# already-correct approach -- explicit create_clock + create_generated_
# clock, not automatic derivation, per this project's own hard-won
# derive_clocks phantom-clock lesson, confirmed on every timing arc
# prior to #237). 100.00 MHz single-ended on CLK_100M, divided by 4
# internally to a 25 MHz fabric clock via div_cnt[1].

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
