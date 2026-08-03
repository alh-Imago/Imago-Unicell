# stripped_zone750.sdc — points.md #150: 750-cell zone, Alan's actual
# per-zone target.

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
