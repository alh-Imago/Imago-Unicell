# bram_controller_test.sdc — points.md #259/#260 continuation: standalone
# bram_controller_v1.v (40-bit) real M20K inference + size/timing check.
# Same clocking convention as every other project here.

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
