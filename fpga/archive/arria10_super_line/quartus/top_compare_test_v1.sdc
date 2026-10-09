# top_compare_test_v1.sdc — points.md #548: real clocking convention
# already established across this project, real create_clock +
# create_generated_clock (not automatic derivation, matching this
# project's own hard-won derive_clocks phantom-clock lesson).

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
