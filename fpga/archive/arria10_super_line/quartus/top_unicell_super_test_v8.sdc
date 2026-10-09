# top_unicell_super_test_v8.sdc — points.md #573: real Quartus timing
# constraints for the full 8-core self-test top-level. Identical
# clocking convention to every other project here: 100.00 MHz single-
# ended on CLK_100M, divided by 4 internally to a 25 MHz fabric clock
# via div_cnt[1]. SDC present from the start -- the missing-SDC trap
# this project already hit once (#241/#242) will not be repeated here.

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
