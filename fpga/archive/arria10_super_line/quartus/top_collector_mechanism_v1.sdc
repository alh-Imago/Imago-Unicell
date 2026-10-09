# top_collector_mechanism_v1.sdc — points.md #403/#404: first real
# Quartus attempt for the header/collector/command/queue RAM-interface
# mechanism (#381/#382/#390/#395/#396/#397). Same clocking convention as
# every other project here: 100.00 MHz single-ended on CLK_100M, divided
# by 4 internally to a 25 MHz fabric clock via div_cnt[1].

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
